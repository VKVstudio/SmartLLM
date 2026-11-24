"""Orchestrator planning: two fresh LLM sessions, Python only validates.

Session 1 `strategy` (offer analyst): reads ONLY the brief -> business goal, CTA, every offer the client sells (with a
quote from the brief as evidence), known facts vs facts the client must still supply, page names in the client's
business language.
Session 2 `site_plan` (architect): brief + strategy JSON + canon router + renderable catalogue -> canon, sitemap,
per-page sections (intent + covered offers + fact source) and an image plan.

Python (1) describes the catalogue of renderable primitives, (2) validates both JSONs against the schema, the user's
explicit constraints and the strategy (every offer covered, hero image per page, lead form on contact, fact blocks
backed by a known fact or marked placeholder) and (3) re-asks the same session with the concrete errors.
It never invents structure or content.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from .pages import PRESET_PAGES, page_available_blocks

FOOTER = "footer"  # shared chrome partial rendered last on every page (not a design decision)
MIN_SECTIONS = 3
IMAGE_BLOCKS = {"hero", "gallery", "team", "about"}
FACT_BLOCKS = {"stats", "team", "testimonials", "pricing", "locations"}  # need real facts or an explicit placeholder
MAX_PAGES_WITH = {"pricing": 2, "faq": 2}  # a block (or page of that name) on more pages repeats itself
LEAD_GOALS = {"leads", "quote", "booking", "bookings", "orders", "contact", "consultation", "sales"}
MAX_RETRIES = 2
MAX_PAGES = 7
ARCHITECT_RETRIES = 3
MAX_TOKENS = 6000
STRATEGY_TOKENS = 3000

GenerateFn = Callable[[str, str, int], dict[str, Any]]


def page_catalogue() -> dict[str, list[str]]:
    """Renderable blocks per page in NEUTRAL (alphabetical) order, so the list order does not suggest a page order."""
    return {p["slug"]: sorted(b for b in page_available_blocks(p["slug"]) if b != FOOTER) for p in PRESET_PAGES}


def _words(s: str) -> int:
    return len(re.findall(r"\w+", s or ""))


def _norm_tokens(s: str) -> set[str]:
    return {w[:5] for w in re.findall(r"\w+", (s or "").lower()) if len(w) > 2}


# ---------------------------------------------------------------- session 1: strategy (offers first)

def build_strategy_messages(brief: str, lang_pref: str) -> tuple[str, str]:
    sys_msg = (
        "You are the SmartLLM offer strategist, a fresh session with one job: read a client brief like a senior "
        "marketer and extract, without inventing anything, what the business sells, to whom, and what the website must "
        "make visitors do. Return ONLY valid JSON."
    )
    example = {
        "brand_name": "exact brand as written in the brief",
        "business": "one sentence: what the business is, where",
        "audience": ["concrete audience segments named or clearly implied by the brief"],
        "goal_type": "one of: trial | leads | quote | booking | orders | sales | awareness",
        "primary_cta": "the main action, in the site language",
        "offers": [
            {"id": "short_snake_id", "name": "offer name in the site language",
             "detail": "what exactly it is, 10-25 words, only from the brief", "evidence": "exact words copied from the brief"}
        ],
        "known_facts": ["facts stated in the brief (city, team size, product features, trial length...)"],
        "client_must_supply": ["facts a good site needs that the brief does not give (prices, names, testimonials...)"],
        "page_names": {"services": "how THIS business would name that page, e.g. 'Мастер-классы' not 'Услуги'"},
        "positioning": "one sentence: why choose them, only from the brief",
        "audience_angles": [{"audience": "segment", "pains": ["what they struggle with today (reasoned, not a fact)"],
                             "objections": ["what stops them from buying"], "questions": ["what they ask before the CTA"]}],
    }
    user_msg = (
        f"Client brief:\n{brief}\n\nSite language setting: {lang_pref} (write names/labels in the site language; "
        "for bilingual sites use the first language).\n\n"
        "Rules:\n"
        "- List EVERY distinct thing the client sells or does as its own offer (each product line, service and venue; "
        "a cafe inside a workshop is its own offer). Missing an offer means half the business disappears from the site.\n"
        "- 'evidence' must be words copied from the brief. Do not add offers the brief does not mention.\n"
        "- Never invent numbers, prices, names, addresses, clients or awards: put what is missing into client_must_supply.\n"
        "- audience_angles: reason like a marketer about each segment's pains, objections and pre-purchase questions. "
        "These are your reasoned hypotheses (not facts) and give every page its own angle; be concrete to this niche.\n"
        "- offer 'detail': say what the offer concretely includes and for whom, using every detail the brief gives.\n"
        + "- page_names: use the client's own vocabulary for the pages a site like this needs "
        "(keys from: index, about, services, portfolio, pricing, blog, team, faq, contact).\n"
        f"Return JSON exactly like: {json.dumps(example, ensure_ascii=False)}"
    )
    return sys_msg, user_msg


def validate_strategy(raw: Any, brief: str) -> tuple[dict[str, Any] | None, list[str]]:
    errs: list[str] = []
    if not isinstance(raw, dict):
        return None, ["response is not a JSON object"]
    brief_tok = _norm_tokens(brief)
    offers: list[dict[str, str]] = []
    ids: set[str] = set()
    for i, o in enumerate(raw.get("offers") or []):
        if not isinstance(o, dict):
            continue
        oid = re.sub(r"[^a-z0-9_]+", "_", str(o.get("id") or "").lower()).strip("_")
        name = str(o.get("name") or "").strip()
        if not oid or not name:
            errs.append(f"offers[{i}] needs 'id' and 'name'")
            continue
        if oid in ids:
            errs.append(f"offer id '{oid}' is duplicated")
            continue
        ev = str(o.get("evidence") or "")
        if not (_norm_tokens(ev) & brief_tok):
            errs.append(f"offer '{oid}': 'evidence' must quote the brief; '{ev[:60]}' is not in it")
            continue
        ids.add(oid)
        offers.append({"id": oid, "name": name[:80], "detail": str(o.get("detail") or "")[:300], "evidence": ev[:200]})
    if not offers:
        errs.append("'offers' must list every offer from the brief (at least one)")
    goal = str(raw.get("goal_type") or "").strip().lower()
    if not goal:
        errs.append("'goal_type' is required")
    if errs:
        return None, errs
    names = raw.get("page_names") if isinstance(raw.get("page_names"), dict) else {}
    return {
        "brand_name": str(raw.get("brand_name") or "").strip()[:60],
        "business": str(raw.get("business") or "")[:300],
        "audience": [str(x)[:120] for x in (raw.get("audience") or [])][:6],
        "goal_type": goal,
        "primary_cta": str(raw.get("primary_cta") or "")[:80],
        "offers": offers,
        "known_facts": [str(x)[:160] for x in (raw.get("known_facts") or []) if str(x).strip()][:20],
        "client_must_supply": [str(x)[:160] for x in (raw.get("client_must_supply") or []) if str(x).strip()][:20],
        "page_names": {str(k).lower(): str(v)[:40] for k, v in names.items() if str(v).strip()},
        "positioning": str(raw.get("positioning") or "")[:300],
        "audience_angles": [
            {"audience": str(x.get("audience") or "")[:80],
             **{k: [str(v)[:140] for v in (x.get(k) or [])][:4] for k in ("pains", "objections", "questions")}}
            for x in (raw.get("audience_angles") or []) if isinstance(x, dict)
        ][:4],
    }, []


# ---------------------------------------------------------------- session 2: site plan (architect)

def _constraints_text(c: dict[str, Any]) -> str:
    lines = []
    if c.get("canon_id"):
        lines.append(f"- canon_id is FIXED by the user: {c['canon_id']}")
    if c.get("pages"):
        lines.append(f"- pages are FIXED by the user (exactly these, in this order): {json.dumps(c['pages'])}")
    for slug, blocks in (c.get("page_blocks") or {}).items():
        lines.append(f"- page '{slug}' sections are FIXED by the user (exactly these blocks, you choose the order, hero first): {json.dumps(blocks)}")
    return "\n".join(lines) or "- none: you decide everything"


def _needs_lead_form(strategy: dict[str, Any] | None) -> bool:
    g = str((strategy or {}).get("goal_type") or "")
    return any(k in g for k in LEAD_GOALS)


def build_messages(
    brief: str, lang_pref: str, router_md: str, valid_canons: list[str], constraints: dict[str, Any],
    strategy: dict[str, Any] | None = None,
) -> tuple[str, str]:
    sys_msg = (
        "You are the SmartLLM lead Orchestrator (site architect + art director), a fresh session. From a client brief and "
        "the strategist's offer analysis you decide the whole site plan for the best possible business result: visual "
        "canon, sitemap (a single page only if the brief really is one landing), the sections of every page in order, and "
        "what every image must show. Think like a senior agency: real inner pages for what the business sells, proof before "
        "price, one clear CTA path. Respect user constraints exactly. Return ONLY valid JSON."
    )
    example = {
        "brand_name": "exact brand from the brief",
        "tagline": "4-8 words",
        "canon_id": "one id from the router",
        "canon_reason": "why this canon fits this business and audience, max 40 words",
        "pages": [
            {"slug": "index", "nav_label": "label in the client's business language", "purpose": "what this page must achieve",
             "offers": ["offer ids this page sells"],
             "sections": [{"block": "hero", "intent": "what this section says, with a concrete detail from the brief",
                           "offers": ["offer ids"], "facts": "known"}]},
        ],
        "image_plan": [{"page": "index", "block": "hero", "subject": "concrete photographable scene for this section"}],
        "client_must_supply": ["facts the copy still needs"],
    }
    strat_txt = (
        "Strategist analysis (fresh session; trust it, do not contradict it):\n" + json.dumps(strategy, ensure_ascii=False) + "\n\n"
        if strategy else ""
    )
    lead_rule = (
        "- The goal is leads/bookings/orders: the 'contact' page (if present) MUST contain the 'contact' block (the form), "
        "and the home page must end in a path to it.\n"
        if _needs_lead_form(strategy) else ""
    )
    user_msg = (
        f"Client brief:\n{brief}\n\nSite language setting: {lang_pref}\n\n"
        + strat_txt
        + f"Canon router (pick by 'fits', respect 'avoid'):\n{router_md}\n\n"
        f"Valid canon_id values: {', '.join(valid_canons)}\n\n"
        "Renderable pages and the blocks each page can contain (alphabetical, not an order; footer is added automatically):\n"
        f"{json.dumps(page_catalogue(), ensure_ascii=False)}\n\n"
        f"User constraints:\n{_constraints_text(constraints)}\n\n"
        "Hard rules (a validator checks them and will send your JSON back):\n"
        f"- 'index' is the first page; every page starts with 'hero'; {MIN_SECTIONS}+ sections per page.\n"
        "- Each block id appears at most once per page (it renders once). One 'features' section can present several offers "
        "as cards; give an offer more room with a different block (process, pricing, gallery, about) or its own page.\n"
        "- Use only blocks listed for THAT page in the catalogue (e.g. check whether 'cta' exists on faq/contact before using it).\n"
        "- image_plan: EVERY page has an image for its hero; extra images only for gallery/team/about sections that exist on that page.\n"
        "- Every offer id from the strategist appears in the 'offers' of at least one section; a main offer gets its own page or a dedicated section.\n"
        f"- 'pricing' and 'faq' (as a block or as a page) appear on at most {MAX_PAGES_WITH['pricing']} pages each.\n"
        f"- Sections with blocks {sorted(FACT_BLOCKS)} set \"facts\": \"known\" only if the strategist's known_facts cover "
        "them, otherwise \"facts\": \"placeholder\" and the missing fact goes into client_must_supply.\n"
        + lead_rule
        + "Quality guidance (why it matters, use judgement):\n"
        "- Intents are briefs for the copywriter: 12-25 words each, naming concrete details from the brief (formats, audiences, "
        "places, product features) rather than generic phrases; never reuse the same sentence on two sections.\n"
        "- What follows the hero should differ by page: inner-page visitors already saw the brand story, so lead with what "
        "that page is for. Manifesto/testimonials only where they move the visitor toward the CTA (usually 1-2 pages).\n"
        "- Home page: 5-7 sections; enough to show every offer and the CTA, not more.\n"
        "- nav_label uses the client's business vocabulary (strategist page_names), in the site language.\n"
        "- purposes at most 20 words; image subjects are real photographable scenes for this business "
        "(no UI screenshots or readable text), each different.\n"
        f"Return JSON exactly like: {json.dumps(example, ensure_ascii=False)}"
    )
    return sys_msg, user_msg


def validate(
    raw: Any, valid_canons: list[str], constraints: dict[str, Any], strategy: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    errs: list[str] = []
    if not isinstance(raw, dict):
        return None, ["response is not a JSON object"]
    cat = page_catalogue()
    canon = str(raw.get("canon_id") or "").strip()
    if constraints.get("canon_id"):
        if canon != constraints["canon_id"]:
            errs.append(f"canon_id must be '{constraints['canon_id']}' (user constraint)")
    elif canon not in valid_canons:
        errs.append(f"canon_id '{canon}' is not one of the valid ids")
    offer_ids = [o["id"] for o in (strategy or {}).get("offers") or []]
    pages_raw = raw.get("pages") if isinstance(raw.get("pages"), list) else []
    if not pages_raw:
        errs.append("'pages' must be a non-empty list")
    pages: list[dict[str, Any]] = []
    seen: set[str] = set()
    covered: set[str] = set()
    for i, p in enumerate(pages_raw):
        if not isinstance(p, dict):
            errs.append(f"pages[{i}] is not an object")
            continue
        slug = str(p.get("slug") or "").strip().lower()
        if slug not in cat:
            errs.append(f"pages[{i}].slug '{slug}' is not renderable; use one of {list(cat)}")
            continue
        if slug in seen:
            errs.append(f"page '{slug}' listed twice")
            continue
        seen.add(slug)
        secs: list[dict[str, Any]] = []
        used: set[str] = set()
        for j, sct in enumerate(p.get("sections") if isinstance(p.get("sections"), list) else []):
            blk = str((sct.get("block") if isinstance(sct, dict) else sct) or "").strip().lower()
            if blk == FOOTER:
                continue
            if blk not in cat[slug]:
                errs.append(f"page '{slug}' section {j}: block '{blk}' is not available on this page; allowed {cat[slug]}")
                continue
            if blk in used:
                msg_dup = (f"page '{slug}': block '{blk}' appears more than once. Each block id renders once per page, so "
                           f"merge them into ONE '{blk}' section whose intent covers all those offers (a features block shows "
                           "several offers as cards), or use a different block (process, pricing, about, gallery) or another page")
                if msg_dup not in errs:
                    errs.append(msg_dup)
                continue
            used.add(blk)
            d = sct if isinstance(sct, dict) else {}
            s_offers = [str(x).lower() for x in (d.get("offers") or []) if isinstance(x, str)]
            if offer_ids:
                bad = [x for x in s_offers if x not in offer_ids]
                if bad:
                    errs.append(f"page '{slug}' section '{blk}': unknown offer ids {bad}; use {offer_ids}")
                covered.update(x for x in s_offers if x in offer_ids)
            facts = str(d.get("facts") or "").strip().lower()
            if strategy is not None and blk in FACT_BLOCKS and facts not in ("known", "placeholder"):
                errs.append(f"page '{slug}' section '{blk}' needs \"facts\": \"known\" or \"placeholder\"")
            secs.append({"block": blk, "intent": str(d.get("intent") or "")[:400], "offers": s_offers,
                         **({"facts": facts} if facts else {})})
        if not secs or secs[0]["block"] != "hero":
            errs.append(f"page '{slug}' must start with 'hero'")
        if len(secs) < MIN_SECTIONS:
            errs.append(f"page '{slug}' needs at least {MIN_SECTIONS} sections")
        fixed = (constraints.get("page_blocks") or {}).get(slug)
        if fixed and sorted(b for b in fixed if b != FOOTER) != sorted(s["block"] for s in secs):
            errs.append(f"page '{slug}' must contain exactly the user's blocks {fixed}")
        if slug == "contact" and _needs_lead_form(strategy) and "contact" not in used and not fixed:
            errs.append("page 'contact' must contain the 'contact' block (the lead form) because the goal is leads/bookings")
        pages.append({"slug": slug, "nav_label": str(p.get("nav_label") or "")[:40], "purpose": str(p.get("purpose") or "")[:300],
                      "offers": [str(x).lower() for x in (p.get("offers") or []) if isinstance(x, str)], "sections": secs})
    if pages and pages[0]["slug"] != "index":
        errs.append("the first page must be 'index'")
    if constraints.get("pages") and [p["slug"] for p in pages] != list(constraints["pages"]):
        errs.append(f"pages must be exactly {constraints['pages']} (user constraint)")
    if strategy is not None and not constraints.get("page_blocks"):
        for blk, lim in MAX_PAGES_WITH.items():
            hits = [p["slug"] for p in pages if p["slug"] == blk or any(s["block"] == blk for s in p["sections"])]
            if len(hits) > lim:
                errs.append(f"'{blk}' appears on {len(hits)} pages {hits}; keep it on at most {lim}")
        missing = [o for o in offer_ids if o not in covered]
        if missing:
            errs.append(f"offers not covered by any section: {missing}; give each its own section or page")
        # Same intent on two sections = template text.
        seen_int: dict[str, str] = {}
        for p in pages:
            for s in p["sections"]:
                key = re.sub(r"\W+", " ", s["intent"].lower()).strip()
                if key and key in seen_int:
                    errs.append(f"intent repeated on {seen_int[key]} and {p['slug']}/{s['block']}; make each specific")
                seen_int.setdefault(key, f"{p['slug']}/{s['block']}")
    img_plan = []
    dropped_imgs: list[str] = []
    hero_imgs: set[str] = set()
    for k, it in enumerate(raw.get("image_plan") or []):
        if not isinstance(it, dict):
            continue
        pg, blk = str(it.get("page") or "").lower(), str(it.get("block") or "").lower()
        if pg not in seen:
            errs.append(f"image_plan[{k}] refers to unknown page '{pg}'")
            continue
        page_secs = next((x["sections"] for x in pages if x["slug"] == pg), [])
        # An extra image on a block that is absent or cannot show images is simply not renderable: drop it with a
        # note instead of failing the plan (the real requirement, a hero image per page, is checked below).
        if blk not in [x["block"] for x in page_secs] or blk not in IMAGE_BLOCKS:
            dropped_imgs.append(f"{pg}/{blk}")
            continue
        if blk == "hero":
            hero_imgs.add(pg)
        img_plan.append({"page": pg, "block": blk, "subject": str(it.get("subject") or "")[:400]})
    no_hero = [p["slug"] for p in pages if p["slug"] not in hero_imgs]
    if strategy is not None and no_hero:
        errs.append(f"image_plan has no hero image for pages {no_hero}; every page needs one")
    if errs:
        return None, errs
    must = [str(x)[:160] for x in (raw.get("client_must_supply") or []) if str(x).strip()]
    for x in (strategy or {}).get("client_must_supply") or []:
        if x not in must:
            must.append(x)
    return {
        "brand_name": str(raw.get("brand_name") or (strategy or {}).get("brand_name") or "").strip()[:60],
        "tagline": str(raw.get("tagline") or "").strip()[:80],
        "canon_id": constraints.get("canon_id") or canon,
        "canon_reason": str(raw.get("canon_reason") or "")[:400],
        "pages": pages,
        "image_plan": img_plan,
        "client_must_supply": must[:24],
        **({"dropped_images": dropped_imgs} if dropped_imgs else {}),
        **({"strategy": strategy} if strategy else {}),
    }, []


def quality_notes(plan: dict[str, Any]) -> list[str]:
    """Soft, non-blocking observations for the orchestrator report (not used to reject)."""
    notes = []
    short = [f"{p['slug']}/{s['block']}" for p in plan["pages"] for s in p["sections"] if _words(s["intent"]) < 8]
    if short:
        notes.append(f"thin intents (<8 words): {short[:6]}")
    home = next((p for p in plan["pages"] if p["slug"] == "index"), None)
    if home and not 5 <= len(home["sections"]) <= 7:
        notes.append(f"home has {len(home['sections'])} sections (guidance 5-7)")
    for blk in ("manifesto", "testimonials"):
        n = sum(1 for p in plan["pages"] if any(s["block"] == blk for s in p["sections"]))
        if n > 2:
            notes.append(f"{blk} on {n} pages")
    return notes


# ---------------------------------------------------------------- runner

PATCH_EXAMPLE = {
    "replace_pages": [{"slug": "page to rewrite", "nav_label": "...", "purpose": "...", "offers": [], "sections": []}],
    "remove_pages": ["slug of a page to drop"],
    "add_pages": [{"slug": "new page, same schema"}],
    "image_plan": [{"page": "...", "block": "...", "subject": "FULL image plan again, only if it must change"}],
    "client_must_supply": ["only if it must change"],
}


def apply_patch(prev: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Mechanical merge of an architect patch into its previous plan (no content decisions)."""
    if isinstance(patch.get("pages"), list) and patch.get("canon_id"):
        return patch  # the model returned a whole plan: take it as is
    out = json.loads(json.dumps(prev, ensure_ascii=False))
    pages = [p for p in out.get("pages") or [] if isinstance(p, dict)]
    by_slug = {str(p.get("slug") or "").lower(): k for k, p in enumerate(pages)}
    for rp in patch.get("replace_pages") or []:
        if isinstance(rp, dict) and str(rp.get("slug") or "").lower() in by_slug:
            pages[by_slug[str(rp["slug"]).lower()]] = rp
        elif isinstance(rp, dict) and rp.get("slug"):
            pages.append(rp)
    drop = {str(x).lower() for x in patch.get("remove_pages") or []}
    pages = [p for p in pages if str(p.get("slug") or "").lower() not in drop]
    for ap in patch.get("add_pages") or []:
        if isinstance(ap, dict) and ap.get("slug") and str(ap["slug"]).lower() not in {str(p.get("slug")).lower() for p in pages}:
            pages.append(ap)
    out["pages"] = pages
    for key in ("image_plan", "client_must_supply", "canon_id", "canon_reason", "tagline", "brand_name"):
        if patch.get(key):
            out[key] = patch[key]
    if drop and not patch.get("image_plan"):
        out["image_plan"] = [it for it in out.get("image_plan") or [] if str((it or {}).get("page") or "").lower() not in drop]
    return out


def _run_session(
    generate_json: GenerateFn, sys_msg: str, user_msg: str, max_tokens: int,
    check: Callable[[dict[str, Any]], tuple[dict[str, Any] | None, list[str]]],
    last_finish: Callable[[], str] | None, label: str, retries: int = MAX_RETRIES, patch_mode: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], dict[str, Any]]:
    """One fresh session: ask, validate, re-ask with the concrete errors.

    patch_mode (architect): the retry shows the FULL previous plan and asks only for the pages/parts that the errors
    name; valid pages are kept verbatim by a mechanical merge, so a fix cannot break what already passed.
    """
    attempts: list[dict[str, Any]] = []
    msg, raw, prev_ok = user_msg, {}, {}
    for attempt in range(retries + 1):
        answer = generate_json(sys_msg, msg, max_tokens) or {}
        finish = str(last_finish() if last_finish else "") or ""
        if not answer:
            why = "cut off at the output limit (too long)" if finish == "length" else "empty or not valid JSON"
            attempts.append({"session": label, "attempt": attempt + 1, "errors": [f"response {why}"], "finish_reason": finish, "raw": {}})
            msg = (
                f"{user_msg}\n\nYour previous answer was {why}, so nothing could be parsed. Return the COMPLETE JSON again, "
                "more compact (keep the required detail, drop filler), no prose outside the JSON."
            ) if not prev_ok else msg
            continue
        raw = apply_patch(prev_ok, answer) if (patch_mode and prev_ok) else answer
        out, errs = check(raw)
        attempts.append({"session": label, "attempt": attempt + 1, "errors": errs, "finish_reason": finish,
                         "mode": "patch" if (patch_mode and prev_ok) else "full", "raw": answer})
        if out:
            return out, attempts, raw
        if patch_mode:
            prev_ok = raw
            named = sorted({m for e in errs for m in re.findall(r"page '([a-z]+)'", e)} | {m for e in errs for m in re.findall(r"(?:on|and) ([a-z]+)/", e)})
            img_hint = ("Your patch MUST include the complete corrected 'image_plan'.\n" if any("image" in e for e in errs) else "")
            msg = (
                f"{user_msg}\n\nThis is your current plan (full JSON):\n{json.dumps(raw, ensure_ascii=False)}\n\n"
                "The validator found these problems:\n- " + "\n- ".join(errs) + "\n\n"
                + (f"Pages to replace: {named}.\n" if named else "")
                + img_hint
                + "Fix ONLY what these problems name and keep everything else. Return a PATCH JSON (not the whole plan): "
                "'replace_pages' with the complete corrected page objects you change, optional 'remove_pages'/'add_pages', "
                "and 'image_plan' (the complete list) only if images must change. Fixing one problem must not create another "
                "(e.g. moving pricing must not leave an offer uncovered; a rewritten intent must stay specific).\n"
                f"Patch format: {json.dumps(PATCH_EXAMPLE, ensure_ascii=False)}"
            )
        else:
            msg = (
                f"{user_msg}\n\nYour previous JSON was rejected by the validator. Fix ALL of these errors and return the full JSON again:\n- "
                + "\n- ".join(errs)
                + f"\nPrevious JSON:\n{json.dumps(raw, ensure_ascii=False)}"
            )
    return None, attempts, raw


def run_strategy(
    generate_json: GenerateFn, brief: str, lang_pref: str, last_finish: Callable[[], str] | None = None,
) -> dict[str, Any]:
    sm, um = build_strategy_messages(brief, lang_pref)
    out, attempts, raw = _run_session(generate_json, sm, um, STRATEGY_TOKENS, lambda r: validate_strategy(r, brief), last_finish, "strategy")
    return {"ok": bool(out), "strategy": out, "attempts": attempts, "raw": raw}


# ---------------------------------------------------------------- per-page pipeline (orchestrator + page sub-agents)

def build_sitemap_messages(brief: str, lang_pref: str, router_md: str, valid_canons: list[str], constraints: dict[str, Any],
                           strategy: dict[str, Any]) -> tuple[str, str]:
    sys_msg = (
        "You are the SmartLLM lead Orchestrator, a fresh session. Decide only the canon and the SITEMAP: which pages the "
        "site has, what each page must achieve, which offers it sells and its editorial angle. Page sub-agents will later "
        "compose the sections of each page from your brief, so make every page's job distinct. Return ONLY valid JSON."
    )
    example = {
        "brand_name": "exact brand", "tagline": "4-8 words",
        "canon_id": "one id from the router", "canon_reason": "max 40 words",
        "pages": [{"slug": "index", "nav_label": "client vocabulary", "purpose": "max 20 words",
                   "offers": ["offer ids"], "angle": "the audience pain/question this page answers, 10-20 words"}],
    }
    lead = _needs_lead_form(strategy)
    user_msg = (
        f"Client brief:\n{brief}\n\nSite language: {lang_pref}\n\n"
        f"Strategist analysis (trust it):\n{json.dumps(strategy, ensure_ascii=False)}\n\n"
        f"Canon router (pick by 'fits', respect 'avoid'):\n{router_md}\n\nValid canon_id values: {', '.join(valid_canons)}\n\n"
        f"Renderable page slugs: {sorted(page_catalogue())}\n"
        f"User constraints:\n{_constraints_text(constraints)}\n\n"
        "Rules (validated): 'index' first; every strategist offer is listed in the 'offers' of at least one page; "
        f"pricing and faq pages: at most one each.\n"
        + ("- The goal is leads/bookings: include a 'contact' page.\n" if lead else "")
        + "Guidance (why): a main offer with enough substance deserves its own page (visitors who want it should land on "
        "it directly); minor offers can share a page. 4-7 pages is typical for a small business; do not create a page that "
        "would only repeat another. Every page needs real content from the brief: a 'blog' only if the client publishes "
        "articles, a 'portfolio' only if they show past work or products, a 'team' page only if people are the product; "
        "otherwise the copywriter has to invent it (an empty 'Case Studies' page for a new product hurts trust; the validator rejects it). "
        "Distinct service lines in the brief (e.g. brand films vs expedition documentaries) are separate offers and usually separate pages. Each page needs a different angle taken from the audience pains/objections/questions, "
        "so no two pages say the same thing. nav_label in the client's vocabulary and site language (strategist page_names).\n"
        f"Return JSON exactly like: {json.dumps(example, ensure_ascii=False)}"
    )
    return sys_msg, user_msg


def validate_sitemap(raw: Any, valid_canons: list[str], constraints: dict[str, Any], strategy: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errs: list[str] = []
    if not isinstance(raw, dict):
        return None, ["response is not a JSON object"]
    cat = page_catalogue()
    canon = str(raw.get("canon_id") or "").strip()
    if constraints.get("canon_id"):
        canon = constraints["canon_id"]
    elif canon not in valid_canons:
        errs.append(f"canon_id '{canon}' is not one of the valid ids")
    offer_ids = [o["id"] for o in strategy.get("offers") or []]
    pages, seen, covered = [], set(), set()
    for k, p in enumerate(raw.get("pages") or []):
        if not isinstance(p, dict):
            continue
        slug = str(p.get("slug") or "").strip().lower()
        if slug not in cat:
            errs.append(f"pages[{k}].slug '{slug}' is not renderable; use one of {sorted(cat)}")
            continue
        if slug in seen:
            errs.append(f"page '{slug}' listed twice")
            continue
        seen.add(slug)
        offs = [str(x).lower() for x in (p.get("offers") or []) if isinstance(x, str)]
        bad = [x for x in offs if x not in offer_ids]
        if bad:
            errs.append(f"page '{slug}': unknown offer ids {bad}; use {offer_ids}")
        covered.update(x for x in offs if x in offer_ids)
        pages.append({"slug": slug, "nav_label": str(p.get("nav_label") or "")[:40], "purpose": str(p.get("purpose") or "")[:300],
                      "offers": [x for x in offs if x in offer_ids], "angle": str(p.get("angle") or "")[:300]})
    if not pages or pages[0]["slug"] != "index":
        errs.append("the first page must be 'index'")
    labels = [p["nav_label"].strip().lower() for p in pages if p["nav_label"].strip()]
    dup_l = sorted({x for x in labels if labels.count(x) > 1})
    if dup_l:
        errs.append(f"nav labels {dup_l} are used by several pages; each menu item must name its own page (home is usually 'Home'/'Главная')")
    if len(labels) < len(pages):
        errs.append("every page needs a nav_label")
    if constraints.get("pages") and [p["slug"] for p in pages] != list(constraints["pages"]):
        errs.append(f"pages must be exactly {constraints['pages']} (user constraint)")
    elif len(pages) > MAX_PAGES:
        errs.append(f"{len(pages)} pages is too many for this business: keep at most {MAX_PAGES}; drop pages that have no real content of their own")
    missing = [o for o in offer_ids if o not in covered]
    if missing:
        errs.append(f"offers not on any page: {missing}; add them to a page's 'offers' (or give them their own page)")
    if _needs_lead_form(strategy) and "contact" not in seen and not constraints.get("pages"):
        errs.append("the goal is leads/bookings: add a 'contact' page")
    if errs:
        return None, errs
    return {"brand_name": str(raw.get("brand_name") or strategy.get("brand_name") or "")[:60], "tagline": str(raw.get("tagline") or "")[:80],
            "canon_id": canon, "canon_reason": str(raw.get("canon_reason") or "")[:400], "pages": pages}, []


def build_page_messages(brief: str, lang_pref: str, strategy: dict[str, Any], sitemap: dict[str, Any], slug: str,
                        done_pages: list[dict[str, Any]], canon_ctx: str, global_notes: list[str],
                        constraints: dict[str, Any]) -> tuple[str, str]:
    page = next(p for p in sitemap["pages"] if p["slug"] == slug)
    allowed = page_catalogue()[slug]
    others = [{"slug": p["slug"], "purpose": p["purpose"], "offers": p["offers"]} for p in sitemap["pages"] if p["slug"] != slug]
    used = [f"{d['slug']}/{s['block']}: {s['intent']}" for d in done_pages for s in d["sections"]]
    pricing_on = [d["slug"] for d in done_pages if any(s["block"] == "pricing" for s in d["sections"]) or d["slug"] == "pricing"]
    faq_on = [d["slug"] for d in done_pages if any(s["block"] == "faq" for s in d["sections"]) or d["slug"] == "faq"]
    lead = _needs_lead_form(strategy) and slug == "contact"
    fixed = (constraints.get("page_blocks") or {}).get(slug)
    sys_msg = (
        "You are a SmartLLM page composer sub-agent in a fresh session. You compose ONE page: its sections in order, what "
        "each section must say (a brief for the copywriter) and its images. Return ONLY valid JSON."
    )
    example = {"sections": [{"block": "hero", "intent": "12-25 words with concrete brief details", "offers": ["offer ids"], "facts": "known|placeholder"}],
               "images": [{"block": "hero", "subject": "concrete photographable scene"}]}
    user_msg = (
        f"Client brief:\n{brief}\n\nSite language: {lang_pref}\nBrand: {sitemap['brand_name']}; canon {sitemap['canon_id']}: {sitemap['canon_reason']}\n\n"
        f"Strategist analysis:\n{json.dumps({k: strategy.get(k) for k in ('goal_type', 'primary_cta', 'offers', 'known_facts', 'client_must_supply', 'audience_angles', 'positioning')}, ensure_ascii=False)}\n\n"
        f"YOUR PAGE: '{slug}' (nav '{page['nav_label']}'). Purpose: {page['purpose']}. Angle: {page['angle']}. Offers to sell here: {page['offers']}.\n"
        f"Other pages (do not do their job): {json.dumps(others, ensure_ascii=False)}\n"
        + (f"Sections already written on other pages (do not repeat or paraphrase them):\n" + "\n".join(used) + "\n" if used else "")
        + (f"\nCanon structure rules:\n{canon_ctx}\n" if canon_ctx else "")
        + f"\nBlocks available on this page (alphabetical, not an order): {allowed}\n"
        + (f"User fixed the blocks of this page (use exactly these, you order them): {fixed}\n" if fixed else "")
        + "Hard rules (validated): start with 'hero'; 3+ sections; each block at most once; only the available blocks; "
        "every offer of this page appears in some section's 'offers'; an image for the hero (extra images only on gallery/team/about "
        f"sections of this page); sections {sorted(FACT_BLOCKS)} set facts 'known' only if known_facts cover them, else 'placeholder' "
        "(never invent numbers, prices, names, addresses, awards).\n"
        + (f"- pricing is already on {pricing_on}: do not add a pricing block here.\n" if len(pricing_on) >= MAX_PAGES_WITH["pricing"] and slug != "pricing" else "")
        + (f"- faq is already on {faq_on}: do not add a faq block here.\n" if len(faq_on) >= MAX_PAGES_WITH["faq"] and slug != "faq" else "")
        + ("- This is the contact page and the goal is leads/bookings: include the 'contact' block (the form).\n" if lead else "")
        + ("- Fix these orchestrator notes: " + "; ".join(global_notes) + "\n" if global_notes else "")
        + "Guidance (why): each intent is a copywriter brief, 12-25 words, naming concrete details from the brief or the "
        "audience pains/questions this page answers; generic phrases make generic copy. "
        + ("Home page: 5-7 sections, enough to show every offer and the CTA path. " if slug == "index" else
           "Inner page: its hero states THIS page's angle (the visitor's question it answers), never the brand pitch from "
           "the home page; 3-6 sections. ")
        + "Manifesto/testimonials only where they move the visitor toward the CTA. A closing CTA should name this page's next step. "
        "Image subjects: real photographable scenes for this business (people, place, physical product, result), different "
        "from the other pages' images; never screens, dashboards or UI.\n"
        "Facts vs hypotheses (why): anything the brief does not state (integrations, delivery, a dedicated manager, client "
        "names, numbers) is a hypothesis; leave it out, or keep it only in a 'placeholder' section phrased as what the client "
        "must confirm, so the copy never presents a guess as a fact. Write every intent in the site language. "
        "If the brief names distinct service lines (e.g. brand films vs expedition documentaries), each section carries only "
        "the offer it is about; one section listing every offer says nothing specific.\n"
        f"Return JSON exactly like: {json.dumps(example, ensure_ascii=False)}"
    )
    return sys_msg, user_msg


SCREEN_RE = re.compile(r"\b(dashboard|interface|screenshot|ui|user interface|app screen|website|web page|screens?|monitors?|on (?:a |the )?(?:laptop|tablet|phone|smartphone)|displaying (?:the )?\w+ (?:app|software|data))\b", re.I)


def _near_duplicate(intent: str, done_pages: list[dict[str, Any]], thr: float = 0.6) -> str:
    a = _norm_tokens(intent)
    if len(a) < 5:
        return ""
    for dp in done_pages:
        for x in dp["sections"]:
            b = _norm_tokens(x["intent"])
            if b and len(a & b) / len(a | b) >= thr:
                return f"{dp['slug']}/{x['block']} (\"{x['intent'][:100]}\")"
    return ""


def _near_dup_image(subj: str, done_pages: list[dict[str, Any]], same_page: list[dict[str, Any]], thr: float = 0.5) -> str:
    a = _norm_tokens(subj)
    if len(a) < 4:
        return ""
    for im in [*(i for dp in done_pages for i in dp.get("images") or []), *same_page]:
        b = _norm_tokens(im.get("subject") or "")
        if b and len(a & b) / len(a | b) >= thr:
            return f"{im.get('page')}/{im.get('block')} (\"{str(im.get('subject'))[:90]}\")"
    return ""


def _cyr_ratio(t: str) -> float:
    letters = [c for c in t if c.isalpha()]
    return (sum(1 for c in letters if "\u0400" <= c <= "\u04ff") / len(letters)) if letters else 1.0


def _intent_key(t: str) -> str:
    return re.sub(r"\W+", " ", (t or "").lower()).strip()


def validate_page(raw: Any, slug: str, page: dict[str, Any], strategy: dict[str, Any], done_pages: list[dict[str, Any]],
                  constraints: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errs: list[str] = []
    if not isinstance(raw, dict):
        return None, ["response is not a JSON object"]
    allowed = page_catalogue()[slug]
    offer_ids = [o["id"] for o in strategy.get("offers") or []]
    used_intents = {_intent_key(s["intent"]) for d in done_pages for s in d["sections"]}
    secs, used, covered = [], set(), set()
    for j, sct in enumerate(raw.get("sections") or []):
        d = sct if isinstance(sct, dict) else {"block": sct}
        blk = str(d.get("block") or "").strip().lower()
        if blk == FOOTER:
            continue
        if blk not in allowed:
            errs.append(f"section {j}: block '{blk}' is not available on '{slug}'; allowed {allowed}")
            continue
        if blk in used:
            errs.append(f"block '{blk}' appears more than once; merge into ONE '{blk}' section (a features block can show several offers as cards) or use another block")
            continue
        used.add(blk)
        intent = str(d.get("intent") or "")[:400]
        near = _near_duplicate(intent, done_pages)
        if near and _intent_key(intent) not in used_intents:
            errs.append(f"'{blk}' intent \"{intent[:120]}\" is nearly the same as {near}; say something this page adds (its angle), not a rephrase")
        if _intent_key(intent) in used_intents:
            twin = next((f"{dp['slug']}/{x['block']}" for dp in done_pages for x in dp["sections"] if _intent_key(x["intent"]) == _intent_key(intent)), "another section")
            hint = (" For a closing CTA name the next step that fits THIS page's visitor (e.g. after comparing plans: "
                    "pick a plan and start the trial; after a workshop schedule: book a date)." if blk == "cta" else "")
            errs.append(f"'{blk}' intent \"{intent[:120]}\" is identical to {twin}; rewrite it for this page's purpose and angle.{hint}")
        used_intents.add(_intent_key(intent))
        offs = [str(x).lower() for x in (d.get("offers") or []) if isinstance(x, str) and str(x).lower() in offer_ids]
        covered.update(offs)
        facts = str(d.get("facts") or "").strip().lower()
        if blk in FACT_BLOCKS and facts not in ("known", "placeholder"):
            errs.append(f"'{blk}' needs \"facts\": \"known\" or \"placeholder\"")
        secs.append({"block": blk, "intent": intent, "offers": offs, **({"facts": facts} if facts else {})})
    if not secs or secs[0]["block"] != "hero":
        errs.append("the page must start with 'hero'")
    if len(secs) < MIN_SECTIONS:
        errs.append(f"at least {MIN_SECTIONS} sections")
    fixed = (constraints.get("page_blocks") or {}).get(slug)
    if fixed and sorted(b for b in fixed if b != FOOTER) != sorted(used):
        errs.append(f"use exactly the user's blocks {fixed}")
    miss = [o for o in page["offers"] if o not in covered]
    if miss:
        errs.append(f"offers of this page not in any section's 'offers': {miss}")
    if slug == "contact" and _needs_lead_form(strategy) and "contact" not in used and not fixed:
        errs.append("include the 'contact' block (the lead form): the goal is leads/bookings")
    imgs, has_hero = [], False
    for it in raw.get("images") or []:
        if not isinstance(it, dict):
            continue
        blk = str(it.get("block") or "").lower()
        subj = str(it.get("subject") or "")
        if SCREEN_RE.search(subj):
            errs.append(f"image '{blk}': \"{subj[:90]}\" shows a screen/UI. The image model renders screens and their text "
                        "as garbage; show the real-world scene instead (people at work, the place, the physical product, the result)")
            continue
        twin_img = _near_dup_image(subj, done_pages, imgs)
        if twin_img:
            errs.append(f"image '{blk}': \"{subj[:90]}\" is nearly the same picture as {twin_img}. Visitors see the same photo "
                        "twice and the pages blur together; choose a different scene (another place, person, object, moment or scale)")
            continue
        if blk in used and blk in IMAGE_BLOCKS and subj.strip():
            imgs.append({"page": slug, "block": blk, "subject": str(it["subject"])[:400]})
            has_hero = has_hero or blk == "hero"
    site_lang = str(constraints.get("_site_lang") or "")
    if site_lang == "ru":
        latin = [s_["block"] for s_ in secs if _cyr_ratio(s_["intent"]) < 0.5]
        if latin:
            errs.append(f"intents of {latin} are not in Russian; the site language is Russian and the copywriter keeps the "
                        "intent's wording, so write every intent in Russian")
    if slug in ("portfolio", "blog", "team"):
        proof = [s_ for s_ in secs if s_["block"] in FACT_BLOCKS or s_["block"] in ("gallery", "blog")]
        if proof and all(s_.get("facts") == "placeholder" or s_["block"] in ("blog",) for s_ in proof) and not any(s_["block"] == "gallery" for s_ in proof):
            errs.append(f"'{slug}' would be an empty page: all its proof is placeholder (no real cases/articles/people in the brief). "
                        "An empty case-studies page hurts trust more than none; the orchestrator should drop this page")
    if not has_hero:
        errs.append("add an image for the hero ('images': [{'block': 'hero', 'subject': ...}])")
    if errs:
        return None, errs
    return {"slug": slug, "nav_label": page["nav_label"], "purpose": page["purpose"], "angle": page.get("angle", ""),
            "offers": page["offers"], "sections": secs, "images": imgs}, []


def redispatch_targets(errs: list[str], sitemap: dict[str, Any], composed: dict[str, dict[str, Any]]) -> list[str]:
    """Which page sub-agents the orchestrator re-dispatches for global-gate errors (mechanical routing only)."""
    out: set[str] = set()
    for e in errs:
        m = re.match(r"'(\w+)' appears on \d+ pages \[(.*?)\]", e)
        if m:
            blk, lst = m.group(1), re.findall(r"'([a-z]+)'", m.group(2))
            keep = {blk, "index"} if blk in lst else {"index"}
            tgt = [x for x in lst if x not in keep]
            out.update(tgt or lst[-1:])
            continue
        m = re.search(r"offers not covered by any section: \[(.*?)\]", e)
        if m:
            for oid in re.findall(r"'([\w]+)'", m.group(1)):
                hosts = [p["slug"] for p in sitemap["pages"] if oid in p["offers"]] or ["index"]
                out.update(hosts)
            continue
        out.update(x for x in re.findall(r"'([a-z]+)'", e) if x in composed)
        out.update(re.findall(r"(?:on|and) ([a-z]+)/", e))
    named = sorted(x for x in out if x in composed)
    return named or [p["slug"] for p in sitemap["pages"] if p["slug"] != "index"][-1:]


def run_site_plan(
    generate_json: GenerateFn,
    brief: str,
    lang_pref: str,
    router_md: str,
    valid_canons: list[str],
    constraints: dict[str, Any] | None = None,
    last_finish: Callable[[], str] | None = None,
    canon_context: Callable[[str], str] | None = None,
    on_report: Callable[[str, str, str, list[str]], None] | None = None,
) -> dict[str, Any]:
    """Orchestrated planning, every step a FRESH session (system+user only):

    strategist -> orchestrator sitemap -> one page-composer sub-agent per page (sees the sitemap and the sections
    already written, not transcripts) -> global gate (validate) -> re-dispatch only the pages that break a global rule.
    Returns {"ok", "plan", "strategy", "attempts", "raw", "notes"}.
    """
    constraints = constraints or {}
    attempts: list[dict[str, Any]] = []
    rep = on_report or (lambda *a: None)

    st = run_strategy(generate_json, brief, lang_pref, last_finish)
    attempts += st["attempts"]
    if not st["ok"]:
        return {"ok": False, "plan": None, "strategy": None, "attempts": attempts, "raw": st["raw"], "notes": []}
    strategy = st["strategy"]
    rep("strategist", "done", f"goal {strategy['goal_type']}; offers {[o['id'] for o in strategy['offers']]}", [])

    sm, um = build_sitemap_messages(brief, lang_pref, router_md, valid_canons, constraints, strategy)
    sitemap, a2, raw = _run_session(generate_json, sm, um, 2500, lambda r: validate_sitemap(r, valid_canons, constraints, strategy), last_finish, "sitemap")
    attempts += a2
    if not sitemap:
        return {"ok": False, "plan": None, "strategy": strategy, "attempts": attempts, "raw": raw, "notes": []}
    rep("orchestrator:sitemap", "done", f"canon {sitemap['canon_id']}; pages {[p['slug'] for p in sitemap['pages']]}", [])
    ctx = canon_context(sitemap["canon_id"]) if canon_context else ""

    def compose(slug: str, done: list[dict[str, Any]], notes: list[str]) -> dict[str, Any] | None:
        page = next(p for p in sitemap["pages"] if p["slug"] == slug)
        sm_p, um_p = build_page_messages(brief, lang_pref, strategy, sitemap, slug, done, ctx, notes, constraints)
        out, a, _raw = _run_session(generate_json, sm_p, um_p, 2500,
                                    lambda r: validate_page(r, slug, page, strategy, done, {**constraints, "_site_lang": lang_pref}), last_finish, f"page:{slug}")
        attempts.extend(a)
        rep(f"page:{slug}", "done" if out else "failed",
            f"{len(out['sections'])} sections, {len(out['images'])} images" if out else "page composer failed", a[-1]["errors"] if a else [])
        return out

    composed: dict[str, dict[str, Any]] = {}
    replans = 0
    while True:
        failed = None
        for p in sitemap["pages"]:
            if p["slug"] in composed:
                continue
            out = compose(p["slug"], list(composed.values()), [])
            if not out:
                failed = p["slug"]
                break
            composed[p["slug"]] = out
        if not failed:
            break
        last_errs = next((a["errors"] for a in reversed(attempts) if a["session"] == f"page:{failed}"), [])
        if failed == "index" or replans >= 1 or constraints.get("pages"):
            return {"ok": False, "plan": None, "strategy": strategy, "attempts": attempts, "raw": {"sitemap": sitemap, "pages": list(composed.values())}, "notes": []}
        # Orchestrator re-plan: a page that cannot be made distinct usually should not exist as a separate page.
        replans += 1
        note = (f"\n\nORCHESTRATOR NOTE: the page sub-agent could not make page '{failed}' different from the pages already "
                f"composed: {'; '.join(last_errs)[:700]}. Re-plan the sitemap: either remove '{failed}' and move its offers to "
                "another page, or give it a clearly different job and angle that the other pages do not cover. Keep the other pages.")
        rep("orchestrator:replan", "issues", f"page '{failed}' not distinct -> re-plan sitemap", last_errs[:2])
        new_map, a3, _raw = _run_session(generate_json, sm, um + note, 2500,
                                         lambda r: validate_sitemap(r, valid_canons, constraints, strategy), last_finish, "sitemap:replan")
        attempts += a3
        if not new_map:
            return {"ok": False, "plan": None, "strategy": strategy, "attempts": attempts, "raw": {"sitemap": sitemap}, "notes": []}
        keep = {p["slug"] for p in new_map["pages"]} - {failed}
        composed = {k: v for k, v in composed.items() if k in keep}
        # Pages that survived keep their sections but take the new sitemap's purpose/offers/angle only if unchanged slug.
        sitemap = new_map
        rep("orchestrator:sitemap", "done", f"re-planned pages {[p['slug'] for p in sitemap['pages']]}", [])

    def assemble() -> dict[str, Any]:
        pages = [composed[p["slug"]] for p in sitemap["pages"]]
        return {**{k: sitemap[k] for k in ("brand_name", "tagline", "canon_id", "canon_reason")},
                "pages": [{k: v for k, v in pg.items() if k != "images"} for pg in pages],
                "image_plan": [im for pg in pages for im in pg["images"]],
                "client_must_supply": list(strategy.get("client_must_supply") or [])}

    plan, errs = validate(assemble(), valid_canons, constraints, strategy)
    for round_ in range(2):
        if plan:
            break
        # Orchestrator re-dispatch: the pages named in the global errors are recomposed with those notes.
        named = redispatch_targets(errs, sitemap, composed)
        rep("orchestrator:gate", "issues", f"round {round_ + 1}: re-dispatch {named}", errs[:4])
        attempts.append({"session": "gate", "attempt": round_ + 1, "errors": errs, "redispatch": named})
        for slug in named:
            if slug not in composed:
                continue
            done = [composed[s] for s in composed if s != slug]
            out = compose(slug, done, errs)
            if out:
                composed[slug] = out
        plan, errs = validate(assemble(), valid_canons, constraints, strategy)
    if not plan:
        attempts.append({"session": "gate", "attempt": 3, "errors": errs})
        return {"ok": False, "plan": None, "strategy": strategy, "attempts": attempts, "raw": assemble(), "notes": []}
    plan["strategy"] = strategy
    for p in plan["pages"]:
        p["angle"] = composed[p["slug"]].get("angle", "")
    return {"ok": True, "plan": plan, "strategy": strategy, "attempts": attempts, "raw": {}, "notes": quality_notes(plan)}


def plan_to_page_blocks(plan: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    pages = [p["slug"] for p in plan["pages"]]
    return pages, {p["slug"]: [s["block"] for s in p["sections"]] + [FOOTER] for p in plan["pages"]}
