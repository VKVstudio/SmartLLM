"""Studio pipeline stage: vision loop with Qwen (mmproj): check every image a site shows (subject vs block, style, ANATOMY), write alt/caption
from what is visible, regenerate failures with Z-Image (new seed + anatomy guard), re-check; max 2 regen rounds.
Model switches are batched: [Qwen: check all] -> [Z-Image: regen all failures] -> [Qwen: re-check regenerated] ...
Called by the orchestrator after Z-Image and by POST /api/orchestrator/vision-check."""
import html, json, re, shutil, subprocess, sys, time, tempfile, secrets
from pathlib import Path
from PIL import Image  # noqa: E402
try:
    from .os_compat import subprocess_kwargs
except ImportError:  # executed as a standalone script
    from smartllm_studio.os_compat import subprocess_kwargs

SYS = ("You are a strict art director checking AI-generated photos for a website. Look carefully at the image. "
       "First count, for EVERY visible person, their hands, arms and fingers, and look at faces. Reply JSON only: "
       "{\"sees\": \"what is actually in the image, 1 sentence\", \"people\": number of people, "
       "\"anatomy_ok\": true|false (false if ANY person has an extra or missing hand/arm/leg, a hand that belongs to nobody, "
       "fused or extra fingers, a melted or doubled face), \"anatomy_issue\": \"empty or what exactly is wrong\", "
       "\"match\": 1-5 (5 = clearly shows the block topic and fits the style; 1-2 = wrong subject, garbled text/UI, broken object), "
       "\"problem\": \"empty or the concrete mismatch\", \"alt\": \"accurate alt text <=14 words in LANG describing what is visible\"}")
ANAT_GUARD = ", anatomically correct, every person has exactly two arms and two hands, natural five-finger hands, no extra limbs, no text"
MAX_ROUNDS = 2



def collect(site: Path) -> dict[str, dict]:
    seen: dict[str, dict] = {}
    for page in sorted(site.glob("*.html")):
        doc = page.read_text(encoding="utf-8")
        for sec_id, sec in re.findall(r'<section[^>]*id="([a-z_]+)"[^>]*>(.*?)</section>', doc, flags=re.S):
            h = re.search(r"<h[12][^>]*>(.*?)</h[12]>", sec, flags=re.S)
            heading = re.sub(r"<[^>]+>", "", h.group(1)).strip() if h else ""
            for src, alt in re.findall(r'<img src="(assets/[^"?]+)[^"]*"[^>]*?alt="([^"]*)"', sec):
                if src not in seen and "logo" not in src:
                    seen[src] = {"page": page.name, "block": sec_id, "heading": html.unescape(heading), "alt_before": html.unescape(alt)}
    return seen


def check(state, tmp: Path, site: Path, src: str, info: dict, lang: str, canon: str) -> dict:
    img_p = site / src
    im = Image.open(img_p).convert("RGB")
    small = tmp / (img_p.stem + f"_{int(time.time()*1000)}.jpg")
    im.resize((896, int(896 * im.height / im.width))).save(small, quality=88)
    user = (f"Site: {site.name}. Visual canon: {canon}. Page: {info['page']}. Block: {info['block']} - heading: \"{info['heading']}\". "
            f"Intended subject: \"{info['alt_before']}\". Alt language: {lang}.")
    t0 = time.time()
    res = state.llm.generate_vision_json(SYS.replace("LANG", lang), user, [small], max_tokens=500)
    res = res if isinstance(res, dict) else {}
    row = {"src": src, **info, **{k: res.get(k) for k in ("sees", "people", "anatomy_ok", "anatomy_issue", "match", "problem", "alt")}, "secs": round(time.time() - t0, 1)}
    m = row.get("match")
    row["fail"] = (row.get("anatomy_ok") is False) or (isinstance(m, (int, float)) and m <= 2)
    pass
    return row


def regen(state, site: Path, rows: list[dict], rnd: int) -> list[str]:
    """Z-Image re-render of failed items (LLM already stopped). Old files kept in .smartllm/rejected/."""
    batch = json.loads((site / ".smartllm" / "render_batch.json").read_text(encoding="utf-8"))
    by_id = {b["id"]: b for b in batch}
    items = []
    for r in rows:
        bid = Path(r["src"]).stem
        b = by_id.get(bid)
        if not b:
            print("no batch item for", bid, flush=True)
            continue
        rej = site / ".smartllm" / "rejected"
        rej.mkdir(parents=True, exist_ok=True)
        shutil.copy2(site / r["src"], rej / f"{bid}.r{rnd}.png")
        p = b["prompt"]
        if r.get("anatomy_ok") is False:
            # two simultaneous hand actions ("shaping clay while holding a cup") is what makes Z-Image draw a third hand
            p = re.sub(r",?\s*while (?:also )?(?:holding|carrying|sipping|drinking|pouring|lifting)[^,.]*", "", p, flags=re.I)
            if "anatomically correct" not in p:
                p = p + ANAT_GUARD
        items.append({**b, "prompt": p, "seed": secrets.SystemRandom().randrange(1, 2_000_000_000), "output_path": str(site / r["src"])})
    if not items:
        return []
    man = site / ".smartllm" / f"regen_batch.r{rnd}.json"
    man.write_text(json.dumps(items, indent=2), encoding="utf-8")
    im = state.image_jobs
    cmd = [str(im.sd_cli_bin), "--diffusion-model", str(im.dit_model_path), "--llm", str(im.te_model_path), "--vae", str(im.vae_model_path),
           "--type", "q8_0", "--clip-on-cpu", "--vae-tiling", "--sampling-method", "euler", "--flow-shift", "3.0", "--steps", "8",
           "--cfg-scale", "1.0", "-p", items[0]["prompt"], "-o", items[0]["output_path"], "--batch-json", str(man)]
    t0 = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, check=False, **subprocess_kwargs())
    print(f"REGEN round {rnd}: {len(items)} images rc={res.returncode} {round(time.time()-t0)}s {res.stderr[-300:] if res.returncode else ''}", flush=True)
    return [Path(i["output_path"]).relative_to(site).as_posix() for i in items] if res.returncode == 0 else []



def apply_vision_alts(doc: str, vision: dict) -> str:
    """Renderer hook: alt text / captions written by the vision model from what is visible (non-failing images only)."""
    for r in (vision or {}).get("images") or []:
        alt, src = str(r.get("alt") or "").strip(), str(r.get("src") or "")
        if not alt or not src or r.get("fail"):
            continue
        esc = html.escape(alt, quote=True)
        doc = re.sub(r'(<img src="' + re.escape(src) + r'[^"]*"[^>]*?alt=")[^"]*(")', lambda m: m.group(1) + esc + m.group(2), doc)
        doc = re.sub(r'(<img src="' + re.escape(src) + r'[^>]*>\s*<figcaption[^>]*>)[^<]*(</figcaption>)', lambda m: m.group(1) + html.escape(alt) + m.group(2), doc)
    return doc


def run_vision_stage(state, site: Path, canon: str = "", lang: str = "", log=print) -> dict:
    """Qwen(mmproj) checks every image -> Z-Image regenerates failures (anatomy/subject) -> Qwen re-checks; <= MAX_ROUNDS.
    Model switches are batched; one model in VRAM at a time. Writes .smartllm/memory/vision_check.json."""
    site = Path(site)
    if not getattr(state.llm, "vision_enabled", False):
        return {"skipped": "no mmproj"}
    tmp = Path(tempfile.mkdtemp())
    lang = lang or ("Russian" if site.name.endswith("_ru") else "English")
    images = collect(site)
    report = {src: check(state, tmp, site, src, info, lang, canon) for src, info in images.items()}
    history = []
    try:
        for rnd in range(1, MAX_ROUNDS + 1):
            fails = [r for r in report.values() if r.get("fail")]
            if not fails:
                break
            state.llm.stop()
            for src in regen(state, site, fails, rnd):
                history.append({"round": rnd, "src": src, "before": report[src]})
                report[src] = check(state, tmp, site, src, images[src], lang, canon)
    finally:
        state.llm.stop()
    out = {"images": list(report.values()), "regenerated": history, "still_failing": [s for s, r in report.items() if r.get("fail")]}
    mem = site / ".smartllm" / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "vision_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"vision stage {site.name}: {len(report)} checked, {len(history)} regenerated, still failing {out['still_failing']}")
    return out
