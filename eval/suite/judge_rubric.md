# SmartLLM Offline Eval Suite — Judge Rubric (`eval/suite/judge_rubric.md`)

**Judges:** 2 independent blind evaluators (`Gemini 3.8 Flash`).  
**Constraint:** Strictly offline / local evaluation — no external paid APIs. Each judge inspects the task prompt (`eval/suite/tasks.json`), the generated files (`index.html`, `dag.ts`, `llms.txt`, `_headers`, `DESIGN.md`, `zimage_prompts.json`), the automated audit reports (`static_audit.json`, `runtime_audit.json`), and the rendered screenshots (`shot-desktop.png`, `shot-desktop-full.png`, `shot-mobile.png`, plus `ref/t2.png` or `ref/t12.png` for Vision-to-Code tasks).

---

## 1. Scoring Criteria (`0.0` to `10.0`, step `0.5`)

### 1.1. `canon` — Design Canon & Anti-Slop Fidelity (`0–10`)
- **`9.0–10.0`**: Unmistakable adherence to the requested canon (`Industrial B2B Engineering`, `Swiss Typographic Grid`, `Luxury Minimalism`, `High-Tech SaaS Dark Mode`, `Neo-Brutalism`, `Editorial`, or exact visual match to `ref/t2.png` / `ref/t12.png`, or clean idiomatic TypeScript in `t4`). All colors defined as `oklch()` tokens in `:root`; zero purple-blue default AI gradients, zero generic 3-card bootstrap templates.
- **`7.0–8.5`**: Correct overall tone and OKLCH palette, minor simplifications in grid structure or surface contrast.
- **`4.0–6.5`**: Noticeable drift toward generic template aesthetics or wrong polarity (e.g., light background when dark industrial/SaaS canon was requested).
- **`0.0–3.5`**: Complete disregard of canon, broken CSS, or unstyled HTML.

### 1.2. `design` — Visual Craft, Layout, Graphics & Mobile Responsiveness (`0–10`)
- **`9.0–10.0`**: Crisp typographic hierarchy, balanced whitespace, bespoke multi-element inline `<svg>` schematics or working `<canvas>`/WebGL shaders, zero horizontal overflow at `1440×900` and `375×812`, `CLS = 0`.
- **`7.0–8.5`**: Clean desktop and mobile layout (`overflowX = false`), functional SVG/canvas, minor visual density or alignment imperfections.
- **`4.0–6.5`**: Primitive placeholder graphics (empty boxes instead of schematics), cramped spacing, or minor mobile clipping.
- **`0.0–3.5`**: Broken layout, overlapping text, horizontal scroll overflow on desktop/mobile, or blank render.

### 1.3. `copy` — Domain Depth, Technical Accuracy & Completeness (`0–10`)
- **`9.0–10.0`**: Authentic domain terminology (e.g., `HHV`, `NOx mg/Nm³`, `RT60`, `ISO 3382`, `EUV 13.5 nm High-NA 0.55`, `ГОСТ ИСО 10816-3`, `IT6`), realistic spec tables, verbatim alignment between visible FAQ and `JSON-LD` `FAQPage`.
- **`7.0–8.5`**: Solid domain copy with all required sections present, slightly generic phrasing in 1–2 paragraphs.
- **`4.0–6.5`**: Marketing fluff, repetitive filler text, or missing required sections/files.
- **`0.0–3.5`**: `Lorem ipsum`, truncated output, or hallucinated/nonsensical content.

### 1.4. `ru` — Russian Language Quality (`0–10` for RU tasks `t3, t7, t8, t10`; `null` for EN tasks)
- **`9.0–10.0`**: Natural, idiomatic Russian engineering or architectural/editorial prose (`«Северная Мануфактура»`, `«ЦЕХ №4»`, `«АРХИВ ТЕХНОЛОГИЙ»`, `«КОНТУР-СПЕКТР»`), accurate Russian technical terms (`квалитет точности`, `числовая апертура`, `СКЗ виброскорости`, `шиповое соединение`), proper typography (`«ёлочки»`, `—`).
- **`7.0–8.5`**: Grammatically correct Russian, minor stylistic stiffness or occasional calques.
- **`4.0–6.5`**: Heavy machine-translation feel, awkward English calques, or mixed EN/RU headings where RU was required.
- **`0.0–3.5`**: Broken grammar, untranslated English blocks, or encoding corruption.

---

## 2. Discrepancy Rule (`> 2.0` Points)

`eval/suite/aggregate_judges.py` compares Judge 1 (`judge_1.json`) and Judge 2 (`judge_2.json`) for every `(model, task, criterion)`:
- If `|score_1 - score_2| > 2.0` on any criterion (`canon`, `design`, `copy`, `ru`, or `overall`), the task is automatically marked with `"discrepancy_flagged": true` and listed in the discrepancy table of `eval/suite/results/reference.md`.

---

## 3. Output Schema for Each Judge (`eval/suite/results/judge_1.json` & `judge_2.json`)

```json
{
  "judge_id": "judge_1",
  "model": "gemini-3.8-flash",
  "evaluations": {
    "<model_slug>": {
      "<task_id>": {
        "canon": 9.0,
        "design": 8.5,
        "copy": 9.5,
        "ru": null,
        "overall": 9.0,
        "strengths": "...",
        "weaknesses": "..."
      }
    }
  }
}
```
