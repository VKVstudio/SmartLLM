"""CPU gate: canon-specific layouts (13/16/17) — distinct CSS (<40% overlap), shared header/footer partials, distinct hero markup."""
from __future__ import annotations
import itertools, json, re, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from smartllm_studio.blueprint import compile_project_blueprint, default_project_draft  # noqa: E402
from smartllm_studio.canon_layouts import LAYOUTS, css_overlap  # noqa: E402

PAGES = ["index", "services", "about", "contact"]


def build(canon: str, tmp: Path) -> dict:
    d = default_project_draft("layout_" + canon[:2])
    d.update({"canon_id": canon, "output_dir": str(tmp / canon), "languages": "en", "selected_pages": PAGES, "routes": []})
    d.pop("page_blocks", None)
    bp = compile_project_blueprint(d, repo_root=ROOT.parent)
    out = Path(bp["project_dir"])
    return {"css": (out / "tokens.css").read_text(encoding="utf-8"), "pages": {p: (out / f"{p}.html").read_text(encoding="utf-8") for p in PAGES if (out / f"{p}.html").exists()}}


def run() -> dict:
    res: dict = {"pairs": {}, "hero": {}}
    with tempfile.TemporaryDirectory() as td:
        sites = {c: build(c, Path(td)) for c in LAYOUTS}
    for a, b in itertools.combinations(LAYOUTS, 2):
        ov = css_overlap(sites[a]["css"], sites[b]["css"])
        res["pairs"][f"{a[:2]}-{b[:2]}"] = ov
        assert ov["rule_overlap"] < 0.40 and ov["decl_jaccard"] < 0.40, (a, b, ov)
    for c, s in sites.items():
        assert len(s["pages"]) >= 3, (c, list(s["pages"]))
        headers = {re.sub(r' aria-current="page"', "", re.search(r"<header.*?</header>", h, re.S).group(0)) for h in s["pages"].values()}
        # shared partial: identical except per-page label/issue line
        norm = {re.sub(r'<p class="issue">.*?</p>|<p class="hero-timecode".*?</p>', "", x, flags=re.S) for x in headers}
        assert len(norm) == 1, (c, "header differs across pages")
        footers = {re.search(r"<footer.*?</footer>", h, re.S).group(0) for h in s["pages"].values()}
        assert len(footers) == 1, (c, "footer differs across pages")
        heroes = {re.search(r'<section class="hero-shell"[^>]*data-variant="([a-z_]+)"', h).group(1) for h in s["pages"].values()}
        res["hero"][c] = sorted(heroes)
        for h in s["pages"].values():
            m = re.search(r"<style>(.*?)</style>", h, re.S)
            assert m and "hero-shell{" in m.group(1).replace(" ", ""), c
            assert "Content-Security-Policy" in h
    assert len({tuple(v) for v in res["hero"].values()}) == 3, res["hero"]
    res["status"] = "CANON_LAYOUT_GATES_PASSED"
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
