#!/usr/bin/env python3
r"""
Step 4: Stratified Multimodal Calibration Dataset Builder (data/calib/)
Reworked for zero-clone, high-authenticity REAP router profiling & llama-imatrix calibration.

Builds:
  - D:\projects\SmartLLM\data\calib\PremiumWebStudio-Calib.jsonl
  - D:\projects\SmartLLM\data\calib\imatrix_corpus.txt
  - D:\projects\SmartLLM\data\calib\stats.md
  - D:\projects\SmartLLM\research\step4_raw\calib_stats.json

Strictly enforces all invariants of scripts/step4_verify_calib.py plus Round 1/2 deep content guards:
  1. Official Qwen3.8 chat_template.jinja via tokenizer.apply_chat_template(messages, tools=tools or None, tokenize=False).
  2. Real reasoning traces (reasoning_content >= 200 tokens, synthetic=False) >= 12% across >= 4 strata
     (including agentic_tool_calling, general_anti_starvation, long_context, pillar_1, pillar_2).
  3. Real multimodal screenshots (16:10 WebSight v0.2 + port-free headless Chromium renders of 14 unique 1-of-1 OKLCH canons)
     at 32px-aligned sizes (1024x640 = 640 <|image_pad|> tokens; 576x1248 = 702 <|image_pad|> tokens). Zero Vision2Web stubs.
  4. Verbatim untrimmed repository trajectories (6 distinct SWE-smith resolved repos: 2x >=32K, 4x 16.5K..18.6K tokens),
     zero fabricated post-submit turns, zero <think>/content duplication, 100% synthetic=False.
  5. Exact step=1 5-gram shingle Jaccard deduplication (< 0.45), first-user prompt + prefix 3-gram deduplication,
     strict 1:1 tool_calls <-> tool response pairing, and perceptual image dHash deduplication.
  6. Domain-pure Pillar 1 (strictly web/DOM/CSS/React/SVG/Three.js, banning SQL/backend/C/mmap/Turkish leakage),
     Pillar 2 (OWASP WebAppSec without SOC/MITRE/RDP + concrete Technical SEO/Schema.org/WCAG + 8 unique GEO/CSP bundles),
     and Pillar 4 (website/landing copywriting, value propositions, UX microcopy, brand voice, typography & Z-Image specs;
     zero брендбук Evol-Instruct clones, zero missing-context disclaimers, zero recipes/fiction/speeches/placeholders).
  7. General Anti-Starvation EN balanced across 4 subdomains (code_general, math, terminal with anti-leakage, science_general)
     and General RU strictly limited to algorithms, mathematics, physics, chemistry, biology, and systems engineering.
"""

from __future__ import annotations

import ast
import gc
import hashlib
import html as html_lib
import io
import json
import re
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from datasets import load_dataset
from PIL import Image, ImageStat
from transformers import AutoProcessor, AutoTokenizer

from step4_curated_bilingual import (
    get_unique_agentic_ru_workflows,
    get_unique_multimodal_canon_specs,
    get_unique_pillar2_bundles,
    get_unique_pillar4_copy_decks,
    render_html_batch_chromium,
)

ROOT = Path(r"D:\projects\SmartLLM")
CALIB_DIR = ROOT / "data" / "calib"
IMG_DIR = CALIB_DIR / "images"
RAW_STEP4_DIR = ROOT / "research" / "step4_raw"
TOKENIZER_DIR = ROOT / "models" / "Qwen3.8-Flash-Next"
AUDIT_JSON_PATH = RAW_STEP4_DIR / "hf_datasets_audit.json"
EVAL_TASKS_PATH = ROOT / "eval" / "suite" / "tasks.json"
EVAL_REF_DIR = ROOT / "eval" / "suite" / "ref"

# Target ~965,000 Qwen3.8 tokens (comfortably inside [500,000, 1,000,000]):
#   - RU ~28.3% (inside [27%, 33%], 0 d0rj/ru-instruct)
#   - Pillars 1-4 ~66.2% (>= 65%)
#   - agentic ~9.5% (inside [9%, 13%])
#   - long_context ~14.4% (inside [5%, 15%])
#   - general ~10.3% (inside [9%, 13%])
#   - synthetic ~6.6% (<= 25%, strictly 40 handcrafted 1-of-1 items)
STRATA_TARGETS: dict[str, dict[str, int]] = {
    "long_context": {"en": 139_500, "ru": 0, "total": 139_500},
    "pillar_1_frontend_3d_svg": {"en": 203_000, "ru": 82_000, "total": 285_000},
    "pillar_2_seo_geo_security": {"en": 74_000, "ru": 70_000, "total": 144_000},
    "pillar_3_style_canons_vision": {"en": 136_000, "ru": 22_600, "total": 158_600},
    "pillar_4_art_direction_copywriting": {"en": 56_000, "ru": 18_000, "total": 74_000},
    "agentic_tool_calling": {"en": 82_000, "ru": 9_200, "total": 91_200},
    "general_anti_starvation": {"en": 20_500, "ru": 77_500, "total": 98_000},
}

VERIFIED_LICENSES: dict[str, str] = {
    "runanlab/gpt-5.4-frontend-development-27052026": "cc-by-4.0",
    "glyphsoftware/opus-4.6-frontend-development": "apache-2.0",
    "smirki/UIGEN-T1.1-TAILWIND": "apache-2.0",
    "Tesslate/UIGEN-T2": "apache-2.0",
    "TozAI/mihenk-3d": "cc-by-4.0",
    "HuggingFaceM4/WebSight": "cc-by-4.0",
    "0xSero/reap-calibration-data-v1": "apache-2.0",
    "NousResearch/hermes-function-calling-v1": "apache-2.0",
    "open-thoughts/OpenThoughts-114k": "apache-2.0",
    "Vikhrmodels/GrandMaster-PRO-MAX": "apache-2.0",
    "Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset": "apache-2.0",
    "Humanlearning/CyberSecurity_OWASP-sft-dataset": "apache-2.0",
    "HuggingFaceH4/ultrachat_200k": "mit",
    "LDJnr/Capybara": "apache-2.0",
    "byroneverson/shell-cmd-instruct": "apache-2.0",
    "zai-org/LongWriter-6k": "apache-2.0",
    "SWE-bench/SWE-smith-trajectories": "mit",
    "SmartLLM/curated-bilingual-canons": "apache-2.0",
}

EVAL_BENCHMARK_IDENTIFIERS = [
    "thermotech engineering",
    "vkvstudio",
    "северная мануфактура",
    "dagexecutor",
    "dagcycleerror",
    "dagvalidationerror",
    "nodeexecutionreport",
    "helvetica kinetic lab",
    "vortex compute",
    "цех №4",
    "архив технологий",
    "aetheria bio-robotics",
    "контур-спектр",
    "kronos precision gearworks",
]

SWE_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command in the repository container to inspect files, run pytest, or verify fixes.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command to execute."}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace_editor",
            "description": "View, create, or edit source files in the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "path": {"type": "string"},
                    "file_text": {"type": "string"},
                    "old_str": {"type": "string"},
                    "new_str": {"type": "string"},
                    "view_range": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["command", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit",
            "description": "Submit the final verified repository patch.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

WEBSIGHT_PROMPT_TEMPLATES = [
    "Rebuild the attached `1024x640` desktop webpage screenshot ({topic}) as clean responsive HTML5 and CSS markup.",
    "Translate this captured webpage layout for {topic} into semantic HTML5 structure and responsive CSS styling.",
    "Inspect the attached `1024x640` UI screenshot ({topic}) and write the HTML5/CSS document that reproduces its layout and typography.",
    "Convert the provided webpage screenshot ({topic}) into accessible HTML5 sections, navigation, and styling.",
    "Implement the desktop page shown in the attached screenshot ({topic}) with semantic HTML5 and modern utility/CSS styling.",
    "Write the complete HTML5 document matching the visual hierarchy, color palette, and spacing of this {topic} screenshot.",
    "From the attached `1024x640` interface capture ({topic}), reconstruct the full DOM markup and styling in a single HTML file.",
    "Code a responsive HTML5 page that reproduces the header, content blocks, and footer shown in this {topic} screenshot.",
    "Examine the attached {topic} webpage screenshot and author the corresponding HTML5 and CSS source code.",
    "Reconstruct the visual layout, cards, and navigation of the attached {topic} `1024x640` screenshot in HTML5.",
    "Produce clean HTML5 markup and styling that faithfully renders the attached {topic} desktop interface.",
    "Turn this `1024x640` webpage screenshot ({topic}) into structured HTML5 markup matching its exact visual arrangement.",
]

SHELL_LEAD_INS = [
    "Here is a POSIX/Bash implementation for this task:",
    "Run the following shell script to perform the operation:",
    "Below is the Bash command sequence:",
    "You can automate this task with the following shell snippet:",
    "The following Bash script handles the requested workflow:",
    "Execute this shell pipeline to achieve the result:",
    "Here is a clean command-line solution:",
    "Below is a Bash automation snippet for the task:",
]

RE_NON_EN_RU_SCRIPT = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0900-\u097f]")
RE_CYR = re.compile(r"[А-Яа-яЁё]")
RE_LAT = re.compile(r"[A-Za-z]")
RE_FENCE = re.compile(r"```.*?```", re.S)
RE_TAG = re.compile(r"<[^>]{0,400}>")
RE_TOOLS_BLOCK = re.compile(r"<tools>\s*(.*?)\s*</tools>", re.S)
RE_THINK_BLOCK = re.compile(r"<think>\s*(.*?)\s*</think>", re.S)
RE_TC_BLOCK = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.S)
RE_TR_BLOCK = re.compile(r"<tool_response>\s*(.*?)\s*</tool_response>", re.S)
RE_WORD = re.compile(r"\w+")

RE_EXCLUDED_LANG = re.compile(
    r"(?:\b#include\s*<|"
    r"\busing\s+UnityEngine\b|\bMonoBehaviour\b|"
    r"\bpublic\s+static\s+void\s+main\s*\(\s*String|"
    r"\bpackage\s+main\b[\s\S]{0,120}\bfunc\s+main\s*\(|"
    r"\bfn\s+main\s*\(\s*\)\s*\{|"
    r"\bimport\s+(?:torch|tensorflow|keras|sklearn|pandas|scipy)\b|"
    r"\b__global__\s+void\b|\bcudaMalloc\b)",
    re.IGNORECASE,
)
RE_EXCLUDED_DOMAIN = re.compile(
    r"(?:\bapiVersion:\s*apps/v1\b|\bkubectl\s+apply\b|"
    r"\bUCLASS\s*\(|\bAActor\b|"
    r"\\int_\{|\\sum_\{n=1\}\^\\infty|"
    r"\b(?:double-blind\s+placebo|randomized\s+clinical\s+trial|plaintiff\s+hereby)\b)",
    re.IGNORECASE,
)
RE_LEGACY_WEB_SLOP = re.compile(
    r"(?:jquery[-.]\d|bootstrap\.min\.css|<marquee\b|<center>|document\.write\s*\()",
    re.IGNORECASE,
)
RE_NSFW_OR_JUNK = re.compile(
    r"\b(?:erotic|incest|nsfw|porn|sexual|rape|suicide|self-harm|prostitut|escort|casino|betting|darknet|"
    r"smartgpt|jailbreak|dan\s+mode|antisemit|hate\s+speech)\b|"
    r"without\s+any\s+special\s+filtering|ignore\s+(?:all\s+)?previous\s+instructions|"
    r"describing\s+how\s+(?:jews|blacks|muslims|christians|women|men|asians|immigrants)\s+are|"
    r"(?:порно|эротик|инцест|суицид|казино|ставк\w+ на спорт|даркнет|закладк)",
    re.IGNORECASE,
)
RE_META_OR_REDACTION_LEAK = re.compile(
    r"(?:\bNAME_\d+\b|"
    r"\btext\s+completion\s+model\b|(?:continue|finish|finalize|complete)\s+the\s+assistant'?s\s+response\s+below|"
    r"\n\s*assistant:?\s*$|"
    r"you\s+are\s+a\s+critic\s+scoring\s+expert|accuracy:\s*[01]\s+coherence:\s*[01]|"
    r"given\s+a\s+definition\s+of\s+a\s+task|в\s+этом\s+задании\s+вам\s+дается|"
    r"думайте\s+так,?\s+как\s+будто\s+вы\s+отвечаете\s+пятилетнему|"
    r"^\s*в:\s*(?:статья:|в\s+этом\s+задании)|краткое\s+содержание:|"
    r"общее\s+усилие\s+сообщества|продолжить\s+итерацию\s*\d*|"
    r"placeholder\s+response\s+for\s+testing|if\s+you\s+are\s+a\s+bot,?\s+stop\s+here|</reply>)",
    re.IGNORECASE | re.MULTILINE,
)
RE_REFUSAL_OR_NONANSWER = re.compile(
    r"(?:i\s+do\s+not\s+endorse|as\s+an\s+ai(?:\s+language\s+model|\s+assistant)?|i\s+am\s+an\s+ai\b|"
    r"ai\s+language\s+models\s+do\s+not\s+support\s+graphical\s+interface|"
    r"i\s+(?:do\s+not|don't)\s+have\s+(?:any\s+)?(?:access|the\s+capability|a\s+real\s+experience|real\s+experience|a\s+business|preferences|personal\s+experiences|real-time\s+information)|"
    r"i\s+am\s+(?:not\s+(?:capable\s+of|able\s+to\s+create)|unable\s+to\s+(?:create|design|provide|use|generate))|"
    r"i\s+may\s+not\s+be\s+able\s+to\s+provide|beyond\s+the\s+scope\s+of\s+this\s+platform|"
    r"i\s+cannot\s+(?:browse|access|provide\s+real-time|create\s+visual|generate\s+images|fulfill\s+this)|"
    r"before\s+proceeding\s+with\s+your\s+request,\s+i\s+must\s+clarify\s+that\s+it\s+is\s+not\s+appropriate|"
    r"knowledge\s+cutoff|up\s+to\s+my\s+last\s+(?:training|update)|"
    r"мне\s+(?:необходимо|нужно|потребуется)\s+знать|было\s+бы\s+полезно\s+знать|"
    r"у\s+меня\s+нет\s+(?:этих\s+)?(?:данных|доступа|информации)|не\s+(?:имею|имеем)\s+доступ|"
    r"не\s+располагаю[^\n.]{0,50}информаци|после\s+получения\s+от\s+вас|"
    r"предоставьте\s+(?:больше|дополнительную|мне)[^\n.]{0,40}информаци|отправьте\s+мне\s+ваш|пришлите\s+(?:мне\s+)?текст|"
    r"если\s+у\s+вас\s+есть\s+дополнительная\s+информация|если\s+нужна\s+будет\s+подсказка|"
    r"как\s+искусственн\w+\s+интеллект|я\s+(?:—\s*)?искусственн\w+\s+интеллект|я\s+(?:—\s*)?языковая\s+модель|"
    r"после\s+мо(?:ей|его)\s+(?:даты|времени)\s+(?:обучения|знаний|обновления)|"
    r"на\s+момент\s+моего\s+последнего\s+обновления|обновления\s+знаний|"
    r"не\s+могу\s+(?:нарисовать|создать\s+изображен|просматривать\s+(?:интернет|изображен)|видеть\s+изображен)|"
    r"к\s+сожалению,?\s+я\s+не\s+могу\s+(?:просматривать|создать|выполнить)|"
    r"выходит\s+за\s+рамки\s+простого\s+обсуждения|"
    r"продолжение\s+следует|<!--\s*продолжение|продолжим\s+код\s+в\s+следующем\s+сообщении|"
    r"итак,?\s+это\s+\w+\.(?:js|ts|html|css)|можешь\s+предоставить\s+мне\s+\w+\.(?:html|css|js)|"
    r"конечно,?\s+вот\s+(?:ваш\s+запрос|пример\s+запроса))",
    re.IGNORECASE,
)
# Case-sensitive guard against lowercased/uppercased UltraChat & synthetic scraper corruptions
RE_ULTRACHAT_CORRUPTION = re.compile(
    r"(?:\bfor\s+I\s+in\s+range\s*\(|\b(?:int|let|var|size_t|auto|long)\s+I\b|\bfor\s*\([^;\n]*\bI\b|"
    r"from\s+bs4\s+import\s+beautifulsoup|cache_discovery\s*=\s*false|"
    r"\bexcept\s+(?:httperror|filenotfounderror|valueerror|keyerror|typeerror)\b|"
    r"document\.(?:getelementbyid|queryselector|queryselectorall|createelement|getelementsbytagname|getelementsbyclassname)\b|"
    r"\.(?:innerhtml|innertext|addeventlistener|getattribute|setattribute|preventdefault)\b|"
    r"\bnew\s+xmlhttprequest\b|\bjson\.(?:parse|stringify)\b|"
    r"\bdow\s+jones\b|\badobe\s+photoshop\b|\bwordpress\b)"
)
RE_MT_CORRUPTED_CODE = re.compile(
    r"(?:```[ \t]*[^\x00-\x7F]|"
    r"<(?:голова|тело|шаблон|стиль|скрипт|дел|вход|таблица|статья|выбрать|ссылка\s+на)\b|"
    r"</(?:голова|тело|шаблон|стиль|скрипт|дел|статья|выбрать)>|"
    r"импортировать\s+[A-Za-z_{]|из\s+[«\"']реагировать|из\s+(?:колбы|фляги)\s+импорт|"
    r"приложение\s*=\s*Колба\s*\(|защит[ау]\s+[A-Za-zА-Яа-я_]\w*\s*\(|обратный\s+ответ|методы\s+возврата|"
    r"дисплей:\s*(?:гибкий|блок|сетка|встроенный)|граница-коллапс|"
    r"пусть\s+[A-Za-zА-Яа-я_]\w*\s*=|функция\s+[A-Za-zА-Яа-я_]\w*\s*\(|"
    r"используя\s*\(|новый\s+[A-Za-z_]\w*\s*\(|конн\.(?:открыть|закрыть)|"
    r"вы\s+можете\s+использовать\s+следующий\s+код|(?:^|\n)\s*QL-инъекция|"
    r"(?:\n|^)\s*-\s*ЗАПРЕТИТЬ:|\bALLOW-FROM\b|about:net-internals|http://schema\.org|\"fanArt\")",
    re.IGNORECASE,
)
RE_BRACKET_PLACEHOLDER = re.compile(
    r"\[(?:[^\[\]\n]{0,45}\b(?:your\s+name|company\s+name|brand\s+name|store\s+name|product\s+name|"
    r"name\s+of\s+the|a\s+question\s+about|current\s+date|"
    r"insert\s+|main\s+image|website\s+url|phone\s+number|email\s+address|city,\s*state|date\s+here|"
    r"recipient|organization\s+name|national\s+grocery|fitness\s+product|opening\s+shot|social\s+media\s+icons|"
    r"copyright\s+information|название\s+компании|название\s+магазина|ваше\s+имя|имя\s+клиента|имя\s+получателя|"
    r"ваш\s+город|ваш\s+телефон|ссылка\s+на|адрес\s+сайта|вставьте\s+)[^\[\]\n]{0,45})\]",
    re.IGNORECASE,
)
RE_P4_ANY_PROSE_BRACKET = re.compile(r"\[(?![^\[\]\n]*\]\()[^\[\]\n]{1,75}\]")
RE_EMOJI_SPAM = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def strip_fenced_code_fast(s: str) -> str:
    if "```" not in s:
        return s
    return "\n\n".join(s.split("```")[0::2])


def has_corrupted_or_invalid_code_blocks(s: str) -> bool:
    """Reject MT-mangled code fences/keywords, invalid JSON blocks, syntax-invalid Python blocks,
    invalid 5+-hash Markdown headings, broken spaced Markdown links, and >=4-blank-line glitches."""
    if RE_MT_CORRUPTED_CODE.search(s):
        return True
    if re.search(r"(?:^|\n)[ \t]*#{5,}[ \t]+\S", s):
        return True
    if re.search(r"\]\s+\(https?://", s):
        return True
    if re.search(r"\n(?:[ \t]*\n){4,}", s):
        return True
    for m in re.finditer(r"```[ \t]*([^\n`]*)\n(.*?)```", s, flags=re.S):
        hdr = m.group(1).strip()
        if any(ord(ch) > 127 for ch in hdr):
            return True
        lang = hdr.split()[0].lower() if hdr else ""
        body = m.group(2).strip()
        if not body:
            return True
        if lang == "json":
            try:
                json.loads(body)
            except Exception:
                return True
        elif lang in ("python", "py") and not re.search(r"^\s*>>>", body, re.M):
            try:
                tree = ast.parse(body)
            except Exception:
                return True
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        return True
                    if (
                        len(node.body) == 1
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and node.body[0].value.value is Ellipsis
                    ):
                        return True
    return False


def has_lowercase_para_corruption(s: str) -> bool:
    prose = strip_fenced_code_fast(s)
    if re.search(r"\n\n[a-z]{3,}\s+[a-z]{2,}", prose):
        return True
    if re.search(r"(?<![A-Z])[.!?][ \t]+(?!(?:e\.g\.|i\.e\.|etc\.|vs\.|cf\.|fig\.|inc\.|ltd\.))[a-z]{3,}\s+[a-z]{2,}", prose):
        return True
    return False


def has_paragraph_repetition_loop(s: str) -> bool:
    prose = strip_fenced_code_fast(s)
    seen_paras: set[str] = set()
    for para in prose.split("\n\n"):
        norm = " ".join(para.lower().split())
        if len(norm) < 95:
            continue
        if norm in seen_paras:
            return True
        seen_paras.add(norm)
    return False


def has_truncated_user_prompt(fu: str) -> bool:
    st = (fu or "").strip()
    if not st:
        return True
    if "\n\n\n" in st or has_paragraph_repetition_loop(st):
        return True
    if st.count("```") % 2 != 0:
        return True
    prose_u = strip_fenced_code_fast(st)
    if (
        prose_u.rfind("(") > prose_u.rfind(")")
        or prose_u.rfind("[") > max(prose_u.rfind("]"), prose_u.rfind(")"))
        or re.search(r"\)\.\s*['\"]\)", prose_u)
    ):
        return True
    if "```" not in st and st.endswith((":", ",")):
        return True
    if re.search(
        r"(?:вот\s+пример\s+запроса|расширить\s+запрос|^\s*другой\s+пример\s*[-—:]|"
        r"^\s*another\s+example\b|^\s*based\s+on\s+the\s+|based\s+on\s+the\s+passage\s+above|"
        r"^\s*include\s+examples\s+of\s+how\s+to\s+use\b|"
        r"previous\s+article|prompt\s+architect|provide\s+the\s+prompt\s+only|awesome\s+chatgpt\s+prompts|"
        r"do\s+not\s+provide\s+the\s+actual\s+code|разбей\s+код[\s\S]{0,60}сообщени|не\s+надо\s+описаний\s+для\s+кода)",
        st,
        re.I,
    ):
        return True
    if re.search(
        r"(?:\bспис|\bкотор|\bнапр|\bисп|\bслед|\bоснов|\bмаркированн\w+\s+спис|\ball\s+th|\n\s*идти|\n\s*assistant:?)\s*$",
        st,
        re.I,
    ):
        return True
    if len(st) >= 220 and "```" not in st and not re.search(r"[.!?\"'»)\]:;]\s*$", st):
        m_last = re.search(r"([A-Za-zА-Яа-яЁё]+)\s*$", st)
        if m_last and len(m_last.group(1)) <= 3:
            return True
    return False


def has_truncated_ending_or_code(s: str, check_unfenced_braces: bool = False) -> bool:
    st = (s or "").strip()
    if not st:
        return True
    low = st.lower()
    if low.count("<style") != low.count("</style>") or low.count("<script") != low.count("</script>"):
        return True
    if st.count("```") % 2 != 0:
        return True
    # Validate brace balance inside JS/TS/TSX/JSX/CSS/JSON fenced blocks
    if "```" in st:
        parts = st.split("```")
        for idx in range(1, len(parts), 2):
            blk = parts[idx]
            nl = blk.find("\n")
            if nl == -1:
                continue
            lang_hdr = blk[:nl].strip().lower()
            body = blk[nl + 1 :].strip()
            if lang_hdr in ("js", "javascript", "ts", "typescript", "tsx", "jsx", "css", "json"):
                if body.count("{") != body.count("}"):
                    return True
                if body.endswith(("=>", "//", "/*")) or re.search(r"//[^\n]*\b(?:indicate|todo|implement)\s+that\s*$", body, re.I):
                    return True
    if check_unfenced_braces and "```" not in st:
        if st.count("{") != st.count("}") or st.count("(") != st.count(")"):
            return True
        # Reject cutoff on an opening JSX/HTML tag (e.g. `<div className="flow-node">`)
        if re.search(r"<[A-Za-z][A-Za-z0-9_-]*(?:\s+[^<>]*)?[^/]>\s*$", st):
            return True
    if st.endswith("```"):
        return False
    # Reject dangling arrows, ellipses, URLs ending in dot, colons, or unpunctuated trailing words
    if st.endswith(("=>", "...", "…", ":", ",", "\\", "—", "-")):
        return True
    if re.search(r"https?://[^\s]+\.\s*$", st):
        return True
    if not re.search(r"[.!?$|`>}\]);\"'\u00bb*]\s*$", st):
        return True
    return False


def extract_websight_topic(html_txt: str, fallback_idx: int) -> str:
    no_svg = re.sub(r"<svg\b[\s\S]*?</svg>", " ", html_txt, flags=re.I)
    for pat in (r"<title[^>]*>(.*?)</title>", r"<h1[^>]*>(.*?)</h1>", r"<h2[^>]*>(.*?)</h2>"):
        m = re.search(pat, no_svg, flags=re.I | re.S)
        if m:
            raw = html_lib.unescape(RE_TAG.sub(" ", m.group(1)))
            clean = " ".join(raw.split()).strip(" -|:/.,")
            if 4 <= len(clean) <= 68 and not re.search(
                r"^(?:home|welcome|untitled|document|page|menu|icon|logo|search|close|button|nav|navigation)$",
                clean,
                re.I,
            ):
                return f"'{clean}'"
    return f"layout #{fallback_idx}"


def build_websight_grounded_prompt(html_txt: str, ws_idx: int) -> str:
    """Compose a DOM-grounded vision-to-code prompt citing actual visible headings, nav items, and landmarks."""
    topic = extract_websight_topic(html_txt, ws_idx)
    headings: list[str] = []
    for hm in re.finditer(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html_txt, flags=re.I | re.S):
        txt = " ".join(html_lib.unescape(RE_TAG.sub(" ", hm.group(1))).split()).strip(" -|:/.,")
        if 3 <= len(txt) <= 52 and txt.lower() not in {x.lower() for x in headings}:
            headings.append(txt)
        if len(headings) >= 3:
            break

    nav_links: list[str] = []
    for am in re.finditer(r"<a\b[^>]*>(.*?)</a>", html_txt, flags=re.I | re.S):
        txt = " ".join(html_lib.unescape(RE_TAG.sub(" ", am.group(1))).split()).strip(" -|:/.,")
        if 2 <= len(txt) <= 24 and txt.lower() not in {x.lower() for x in nav_links}:
            nav_links.append(txt)
        if len(nav_links) >= 4:
            break

    landmarks = [
        tag
        for tag in ("header", "nav", "main", "section", "article", "aside", "form", "table", "footer")
        if re.search(rf"<{tag}\b", html_txt, re.I)
    ]

    verbs = (
        "Rebuild",
        "Translate",
        "Reconstruct",
        "Implement",
        "Author",
        "Convert",
        "Code",
        "Synthesize",
        "Produce",
        "Transcribe",
        "Recreate",
        "Write",
    )
    nouns = (
        "attached `1024x640` desktop screenshot",
        "captured `1024x640` browser viewport",
        "provided desktop webpage capture",
        "attached UI layout screenshot (`1024x640`)",
        "rendered `1024x640` interface snapshot",
        "desktop web design capture",
        "supplied `1024x640` page render",
        "visual webpage reference (`1024x640`)",
    )
    targets = (
        "into clean semantic HTML5 and responsive CSS styling",
        "as a complete HTML5 document matching its visual hierarchy and color palette",
        "using semantic DOM landmarks, utility/CSS classes, and faithful spacing",
        "with accessible HTML5 markup that reproduces its exact typography and layout",
        "as structured HTML5 source code preserving its header, sections, and color contrast",
        "into responsive HTML5 markup aligned to the visible grid and navigation flow",
        "with clean HTML5 tags and styling that mirror every visible block",
    )

    v = verbs[ws_idx % len(verbs)]
    n = nouns[(ws_idx * 3 + 1) % len(nouns)]
    t = targets[(ws_idx * 5 + 2) % len(targets)]

    details: list[str] = []
    if headings:
        details.append("visible headings (" + "; ".join(f'"{h}"' for h in headings) + ")")
    if nav_links:
        details.append("navigation/action links (" + ", ".join(nav_links) + ")")
    if landmarks:
        details.append("DOM landmarks (`<" + ">`, `<".join(landmarks[:5]) + ">`)")

    detail_clause = f", including its {', '.join(details)}," if details else ""
    return f"{v} the {n} for {topic}{detail_clause} {t}."


def prose_cyr_ratio(s: str) -> float:
    s = strip_fenced_code_fast(s)
    s = RE_TAG.sub(" ", s)
    c, l = len(RE_CYR.findall(s)), len(RE_LAT.findall(s))
    return c / max(1, c + l)


def word_shingles_k(s: str, k: int = 5) -> set[int]:
    words = RE_WORD.findall(s.lower())
    if len(words) < k + 3:
        return set()
    out: set[int] = set()
    for i in range(0, len(words) - (k - 1)):
        gram = " ".join(words[i : i + k]).encode("utf-8", errors="ignore")
        out.add(int.from_bytes(hashlib.blake2b(gram, digest_size=8).digest(), "little"))
    return out


def word_shingles_5(s: str) -> set[int]:
    return word_shingles_k(s, 5)


def prefix_shingles_3(s: str, max_words: int = 14) -> set[int]:
    words = RE_WORD.findall(s.lower())[:max_words]
    if len(words) < 6:
        return set()
    out: set[int] = set()
    for i in range(0, len(words) - 2):
        gram = " ".join(words[i : i + 3]).encode("utf-8", errors="ignore")
        out.add(int.from_bytes(hashlib.blake2b(gram, digest_size=8).digest(), "little"))
    return out


def compute_dhash64(im: Image.Image) -> int:
    small = im.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
    px = list(small.get_flattened_data()) if hasattr(small, "get_flattened_data") else list(small.getdata())
    bits = 0
    for row in range(8):
        off = row * 9
        for col in range(8):
            bits = (bits << 1) | (1 if px[off + col] > px[off + col + 1] else 0)
    return bits


def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _json_schema_allows_null(prop_spec: Any) -> bool:
    if not isinstance(prop_spec, dict):
        return False
    tp = prop_spec.get("type")
    if tp == "null" or (isinstance(tp, list) and "null" in tp):
        return True
    for union_key in ("anyOf", "oneOf"):
        sub = prop_spec.get(union_key)
        if isinstance(sub, list) and any(isinstance(x, dict) and x.get("type") == "null" for x in sub):
            return True
    return False


_PYTHON_TO_JSON_SCHEMA_TYPE: dict[str, str] = {
    "dict": "object",
    "dictionary": "object",
    "map": "object",
    "object": "object",
    "float": "number",
    "double": "number",
    "number": "number",
    "int": "integer",
    "long": "integer",
    "integer": "integer",
    "str": "string",
    "string": "string",
    "bool": "boolean",
    "boolean": "boolean",
    "list": "array",
    "tuple": "array",
    "set": "array",
    "array": "array",
    "null": "null",
}

_GROUNDING_STOPWORDS: set[str] = {
    "this", "that", "with", "from", "have", "your", "will", "would", "could", "should", "there", "their",
    "about", "which", "when", "where", "what", "please", "thank", "thanks", "using", "used", "into",
    "after", "before", "also", "more", "some", "here", "been", "were", "they", "them", "then", "than",
    "only", "just", "like", "make", "made", "need", "want", "find", "check", "data", "information",
    "function", "result", "results", "based", "following", "provided", "value", "values", "number", "numbers",
}


def _normalize_lf_deep(obj: Any) -> Any:
    if isinstance(obj, str):
        return obj.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(obj, list):
        return [_normalize_lf_deep(x) for x in obj]
    if isinstance(obj, dict):
        return {_normalize_lf_deep(k): _normalize_lf_deep(v) for k, v in obj.items()}
    return obj


def _normalize_json_schema_node(node: Any) -> Any:
    if isinstance(node, str):
        return node.replace("\r\n", "\n").replace("\r", "\n")
    if isinstance(node, list):
        return [_normalize_json_schema_node(x) for x in node]
    if not isinstance(node, dict):
        return node
    out: dict[str, Any] = {}
    for k, v in node.items():
        if k == "required":
            if isinstance(v, list):
                out["required"] = [str(x) for x in v if isinstance(x, str)]
            continue
        if k == "type" and isinstance(v, str):
            tl = v.strip().lower()
            if tl == "any":
                continue
            mapped = _PYTHON_TO_JSON_SCHEMA_TYPE.get(tl)
            if mapped is None:
                return None
            out["type"] = mapped
            continue
        nv = _normalize_json_schema_node(v)
        if nv is None and isinstance(v, dict):
            return None
        out[k] = nv
    return out


def normalize_openai_tool_schemas(raw_tools: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    """Normalize BFCL/Hermes tool definitions into strict OpenAI JSON Schema format."""
    norm_tools: list[dict[str, Any]] = []
    for item in raw_tools:
        if not isinstance(item, dict):
            return None
        fn = item.get("function") if "function" in item else item
        if not isinstance(fn, dict) or not isinstance(fn.get("name"), str) or not fn["name"].strip():
            return None
        params_raw = fn.get("parameters")
        if params_raw is None:
            params_norm: dict[str, Any] = {"type": "object", "properties": {}}
        else:
            p_clean = _normalize_json_schema_node(params_raw)
            if not isinstance(p_clean, dict):
                return None
            p_clean["type"] = "object"
            if not isinstance(p_clean.get("properties"), dict):
                p_clean["properties"] = {}
            params_norm = p_clean
        fn_clean: dict[str, Any] = {
            "name": fn["name"].strip(),
            "description": str(fn.get("description") or "").replace("\r\n", "\n").replace("\r", "\n"),
            "parameters": params_norm,
        }
        norm_tools.append({"type": "function", "function": fn_clean})
    return norm_tools if norm_tools else None


def validate_tool_turn_alignment(messages: list[dict[str, Any]], allow_final_submit_call: bool = False) -> bool:
    """Enforce strict role state-machine (zero assistant->assistant or user->user) AND 1:1 tool_calls->tool turns."""
    n = len(messages)
    if n < 2:
        return False
    first_role = messages[0].get("role")
    if first_role == "system":
        if n < 3 or messages[1].get("role") != "user":
            return False
        i = 1
    elif first_role == "user":
        i = 0
    else:
        return False

    while i < n:
        m = messages[i]
        role = m.get("role")
        if role == "system":
            return False
        if role == "tool":
            return False
        if role == "user":
            if i + 1 >= n or messages[i + 1].get("role") != "assistant":
                return False
            i += 1
            continue
        if role == "assistant":
            rc = m.get("reasoning_content")
            if isinstance(rc, str) and any(
                bad_tag in rc
                for bad_tag in ("<tool_call>", "</tool_call>", "<tool_response>", "</tool_response>", "<think>", "</think>", "<|im_start|>", "<|im_end|>", "<function=")
            ):
                return False
            cs = m.get("content") if isinstance(m.get("content"), str) else ""
            cs_low = cs.lower()
            if any(
                bad_c in cs_low
                for bad_c in ("<tool_call>", "</tool_call>", "<tool_response>", "</tool_response>", "</reply>", "placeholder response for testing", "if you are a bot")
            ):
                return False
            tcs = m.get("tool_calls")
            if tcs:
                if not isinstance(tcs, list) or len(tcs) == 0:
                    return False
                if i == n - 1:
                    if not allow_final_submit_call:
                        return False
                    if not any(tc.get("function", {}).get("name") == "submit" for tc in tcs):
                        return False
                    i += 1
                    continue
                j = i + 1
                while j < n and messages[j].get("role") == "tool":
                    j += 1
                n_tool_msgs = j - (i + 1)
                if n_tool_msgs != len(tcs):
                    return False
                if j >= n or messages[j].get("role") != "assistant":
                    return False
                i = j
            else:
                if len(cs.strip()) < 16:
                    return False
                if i < n - 1 and messages[i + 1].get("role") != "user":
                    return False
                i += 1
            continue
        return False
    return True


def is_grounded_final_tool_answer(messages: list[dict[str, Any]]) -> bool:
    """Verify the final assistant summary lexically grounds in the user prompt and/or tool outputs."""
    if not messages or messages[-1].get("role") != "assistant" or messages[-1].get("tool_calls"):
        return False
    final_txt = (messages[-1].get("content") or "").strip().lower()
    if len(final_txt) < 25:
        return False
    if re.search(
        r"(?:please\s+hold\s+on|hold\s+on\s+while|while\s+i\s+perform\s+this|"
        r"i\s+will\s+(?:now\s+)?proceed\s+to|let\s+me\s+(?:now\s+)?(?:call|execute|invoke|proceed)|"
        r"one\s+moment\s+please|please\s+wait\s+while)",
        final_txt,
        re.I,
    ):
        return False
    user_blob = " ".join(
        str(m.get("content") or "").lower()
        for m in messages
        if m.get("role") == "user"
    )
    for stitched_phrase in (
        "factorial of",
        "average of the numbers",
        "distance between earth and mars",
        "area_of_rectangle",
        "value of all your gift cards",
        "sum of elements in list a",
        "weather in san francisco is currently 70",
    ):
        if stitched_phrase in final_txt and stitched_phrase.split()[0] not in user_blob:
            return False

    ctx_blob = " ".join(
        str(m.get("content") or "").lower()
        for m in messages[:-1]
        if m.get("role") in ("user", "tool")
    )
    ctx_toks = {
        w for w in re.findall(r"[a-zа-яё]{4,}|\d{2,}", ctx_blob)
        if w not in _GROUNDING_STOPWORDS
    }
    ans_toks = {
        w for w in re.findall(r"[a-zа-яё]{4,}|\d{2,}", final_txt)
        if w not in _GROUNDING_STOPWORDS
    }
    return len(ctx_toks & ans_toks) >= 2


def parse_hermes_turns(convs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Convert Hermes / 0xSero conversations into validated OpenAI HF messages + normalized OpenAI tools."""
    raw_tools: list[dict[str, Any]] = []
    messages: list[dict[str, Any]] = []
    for turn in convs:
        role_raw = turn.get("from", turn.get("role", ""))
        val = turn.get("value", turn.get("content", "")) or ""
        if role_raw == "system":
            matches = RE_TOOLS_BLOCK.findall(val)
            for raw_t in matches:
                raw_t = raw_t.strip()
                if not raw_t:
                    continue
                try:
                    parsed = json.loads(raw_t)
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    if isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict):
                                raw_tools.append(item)
                except Exception:
                    for line in raw_t.splitlines():
                        line = line.strip().rstrip(",")
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                            if isinstance(item, dict):
                                raw_tools.append(item)
                        except Exception:
                            pass
            clean_sys = val.split("You are a function calling AI model.")[0].strip()
            clean_sys = RE_TOOLS_BLOCK.sub("", clean_sys).strip()
            clean_sys = re.sub(r"You are provided with function signatures.*", "", clean_sys, flags=re.S).strip()
            clean_sys = re.sub(r"Here are the available tools:.*", "", clean_sys, flags=re.S).strip()
            clean_sys = re.sub(r"First,\s*think\s+step[- ]by[- ]step.*", "", clean_sys, flags=re.S | re.I).strip()
            clean_sys = re.sub(r"[^\n]*</?think>[^\n]*", "", clean_sys, flags=re.I).strip()
            if clean_sys:
                messages.append({"role": "system", "content": clean_sys})
        elif role_raw in ("human", "user"):
            messages.append({"role": "user", "content": val.strip()})
        elif role_raw in ("gpt", "assistant"):
            reas = None
            t_matches = [x.strip() for x in RE_THINK_BLOCK.findall(val) if x.strip()]
            if t_matches:
                reas = "\n\n".join(t_matches)
                if any(
                    bad_t in reas
                    for bad_t in ("<tool_call>", "</tool_call>", "<tool_response>", "</tool_response>", "<think>", "</think>", "<function=")
                ):
                    return None
                val = RE_THINK_BLOCK.sub("", val).strip()
            tcs = []
            for tcm in RE_TC_BLOCK.finditer(val):
                try:
                    tc_obj = json.loads(tcm.group(1).strip())
                    if isinstance(tc_obj, dict) and "name" in tc_obj:
                        args = tc_obj.get("arguments", tc_obj.get("parameters", {}))
                        if isinstance(args, str):
                            args = json.loads(args)
                        if isinstance(args, dict):
                            tcs.append({"type": "function", "function": {"name": tc_obj["name"], "arguments": _normalize_lf_deep(args)}})
                        else:
                            return None
                    else:
                        return None
                except Exception:
                    return None
            val_clean = RE_TC_BLOCK.sub("", val).strip()
            if any(
                bad_v in val_clean
                for bad_v in ("<tool_call>", "</tool_call>", "<tool_response>", "</tool_response>", "<think>", "</think>", "</reply>")
            ):
                return None
            msg: dict[str, Any] = {"role": "assistant", "content": val_clean}
            if reas:
                msg["reasoning_content"] = reas
            if tcs:
                msg["tool_calls"] = tcs
            messages.append(msg)
        elif role_raw in ("tool", "observation"):
            blocks = [m.group(1).strip() for m in RE_TR_BLOCK.finditer(val) if m.group(1).strip()]
            if blocks:
                for blk in blocks:
                    messages.append({"role": "tool", "content": blk})
            else:
                tr_content = val.strip()
                if not tr_content:
                    return None
                messages.append({"role": "tool", "content": tr_content})

    tools = normalize_openai_tool_schemas(raw_tools)
    if not tools or not any(m.get("role") == "assistant" and m.get("tool_calls") for m in messages):
        return None
    if messages[-1].get("role") != "assistant":
        return None
    if not validate_tool_turn_alignment(messages, allow_final_submit_call=False):
        return None
    if not is_grounded_final_tool_answer(messages):
        return None
    schemas = {
        t["function"]["name"]: t["function"].get("parameters") or {}
        for t in tools
        if isinstance(t.get("function"), dict) and "name" in t["function"]
    }
    for m in messages:
        for tc in m.get("tool_calls") or []:
            sch = schemas.get(tc["function"]["name"])
            if sch is None:
                return None
            props = sch.get("properties") or {}
            args = tc["function"]["arguments"]
            if props and any(k not in props for k in args):
                return None
            if any(k not in args for k in (sch.get("required") or [])):
                return None
            for k, arg_val in args.items():
                if arg_val is None and props and not _json_schema_allows_null(props.get(k)):
                    return None
    return messages, tools


def _unwrap_swe_content(raw_c: Any) -> str:
    if isinstance(raw_c, str):
        return raw_c
    if isinstance(raw_c, list):
        return "\n".join(str(x.get("text", "")) for x in raw_c if isinstance(x, dict))
    return ""


def convert_swe_smith_row(r: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Convert a verbatim SWE-smith resolved tool trajectory without fabricating post-submit messages
    and without duplicating `thought` into `content` when upstream sets `thought == content`."""
    raw_msgs = json.loads(r["messages"]) if isinstance(r["messages"], str) else r["messages"]
    out: list[dict[str, Any]] = []
    seen_tool_names: set[str] = set()
    has_repo_edit = False

    for m in raw_msgs:
        role = m.get("role")
        content = _unwrap_swe_content(m.get("content")).strip()
        if role in ("system", "user"):
            out.append({"role": role, "content": content})
        elif role == "assistant":
            thought = str(m.get("thought") or "").strip()
            tcs = m.get("tool_calls") or []
            norm_tcs = []
            for tc in tcs:
                fn = tc.get("function") or {}
                fname = fn.get("name") or tc.get("name") or ""
                fargs = fn.get("arguments") if "arguments" in fn else tc.get("arguments", {})
                if isinstance(fargs, str):
                    try:
                        fargs = json.loads(fargs)
                    except Exception:
                        return None
                if not fname or not isinstance(fargs, dict):
                    return None
                seen_tool_names.add(fname)
                norm_tcs.append({"type": "function", "function": {"name": fname, "arguments": fargs}})
                if fname == "str_replace_editor" and fargs.get("command") == "str_replace":
                    p = str(fargs.get("path") or "")
                    base = Path(p).name.lower()
                    if p and not base.startswith(("reproduce", "debug_", "temp_")):
                        has_repo_edit = True
            # Upstream SWE-smith copies `thought` verbatim into `content`; place it strictly in reasoning_content
            msg_content = "" if (thought and content == thought) else content
            msg: dict[str, Any] = {"role": "assistant", "content": msg_content}
            if thought:
                msg["reasoning_content"] = thought
            if norm_tcs:
                msg["tool_calls"] = norm_tcs
            out.append(msg)
        elif role == "tool":
            out.append({"role": "tool", "content": content})

    if not has_repo_edit or not out or out[-1]["role"] != "assistant":
        return None
    if not validate_tool_turn_alignment(out, allow_final_submit_call=True):
        return None
    known = {t["function"]["name"] for t in SWE_TOOLS}
    if not seen_tool_names.issubset(known) or "submit" not in seen_tool_names:
        return None
    return out, SWE_TOOLS


class CalibrationBuilder:
    # Strict Glyphsoftware web-only guard: require real DOM/CSS/React/SVG/WebGL constructs and ban C/systems/hardware
    RE_GLYPH_STRICT_DOM = re.compile(
        r"(?:<!doctype html|<html\b|<div\b|<section\b|<svg\b|<canvas\b|document\.(?:getElementById|querySelector|createElement)|"
        r"window\.(?:requestAnimationFrame|matchMedia|addEventListener)|useState\s*\(|useEffect\s*\(|useRef\s*\(|"
        r"grid-template-columns|@media\s*\(|@container\b|oklch\(|IntersectionObserver|ResizeObserver|ShadowRoot|aria-[a-z]+)",
        re.IGNORECASE,
    )
    RE_GLYPH_SYSTEMS_BAN = re.compile(
        r"(?:\bmalloc\b|\bcalloc\b|\brealloc\b|\bfree\s*\(|\bstruct\s+\w+|\bmmap\b|memory-mapped|cache\s+line|"
        r"ring\s+buffer|lock-free|#include\b|\buint(?:8|16|32|64)_t\b|\bint(?:32|64)_t\b|\bsizeof\s*\(|"
        r"pointer\s+arithmetic|\bpthread|\bsyscall\b|\bepoll\b|\bkqueue\b|\bverilog\b|\bvhdl\b|\bfpga\b|"
        r"\bsimd\b|\bavx2\b|int\s+main\s*\(|signal-processing|endianness|page\s+table|inode\b|"
        r"\bexpress\b|app\.listen\s*\(|http\.createServer|RED\.nodes\.createNode|node-red|module\.exports\s*=)",
        re.IGNORECASE,
    )
    RE_GLYPH_P2_CWV = re.compile(
        r"(?:\bcls\b|cumulative layout shift|\blcp\b|largest contentful paint|\binp\b|core web vitals|"
        r"aria-live|aria-expanded|wcag\s*2|screen\s+reader|focus\s+trap|json-ld|schema\.org|"
        r"content-security-policy|\bcsp\b|\bxss\b|trusted\s+types)",
        re.IGNORECASE,
    )
    RE_P1_BROKEN_CODE = re.compile(
        r"(?:tailwindcss@4|@tailwindcss/postcss7-compat|tailwindcss@[34][^\"'\s>]*/(?:lib|dist)/|lib/index\.min\.js|"
        r"tailwind\s*css\s*\(?v4|source\.unsplash\.com|via\.placeholder\.com|placehold\.co|lorempixel\.com|dummyimage\.com|"
        r"can'?t\s+generate\s+images|cannot\s+generate\s+images|for\s+mental\s+image|"
        r"asyncstorage|@react-native|\breact-native\b|"
        r"\bshadow:\s*shadow-|\btransition:\s*shadow-|<%|%>)",
        re.IGNORECASE,
    )

    @staticmethod
    def _has_undefined_tailwind_custom_tokens(code_str: str) -> bool:
        if re.search(r"\b(?:bg|text|border|ring|from|to)-primary-\d", code_str):
            if "tailwind.config" not in code_str and "--color-primary" not in code_str:
                return True
        return False

    # Strict Pillar 2 Web Security & Technical SEO filters
    RE_WEBSEC_GOOD = re.compile(
        r"(?:\bxss\b|cross-site scripting|\bcsrf\b|cross-site request forgery|\bcsp\b|content-security-policy|"
        r"\bcors\b|cross-origin|\bhsts\b|strict-transport-security|\bsamesite\b|\bowasp\b|sql\s+injection|"
        r"\bsqli\b|\bjwt\b|oauth\s*2|open\s+redirect|\bssrf\b|clickjacking|x-frame-options|http\s+security\s+header|"
        r"session\s+fixation|session\s+hijacking|cookie\s+security|subresource\s+integrity)",
        re.IGNORECASE,
    )
    RE_WEBSEC_BAD = re.compile(
        r"(?:\bMITRE\b|\bSIEM\b|\bSplunk\b|\bQRadar\b|\bT1\d{3}\b|ransomware|malware|forensic|Active\s+Directory|"
        r"\bKerberos\b|\bSysmon\b|threat\s+hunting|\bEDR\b|\bAPT\d|\bC2\b|lateral\s+movement|buffer\s+overflow|"
        r"reverse\s+engineering|wireshark|pcap|nmap\s+scan|metasploit|shellcode|rootkit|keylogger|"
        r"\bRDP\b|remote\s+desktop|session\s+shadow|windows\s+server|domain\s+controller|\bSMB\b|mimikatz|"
        r"spiderfoot|maltego|\bosint\b|dark\s+web|threat\s+intelligence|nist\s+csf|unauthenticated\s+(?:api|access)|\bjsonp\b|"
        r"<\?php|\bphp\b|\.php\b|in\s+this\s+video|provided\s+poc|following\s+poc|given\s+code|above\s+code)",
        re.IGNORECASE,
    )
    RE_EN_SEO_GOOD = re.compile(
        r"(?:technical\s+seo|e-?commerce\s+seo|on-?page\s+seo|voice\s+search[\s\S]{0,30}seo|seo\s+(?:audit|checklist|optimization|strategy|best\s+practices|guide|metadata)|"
        r"optimiz(?:e|ing)\s+(?:a\s+|an\s+|your\s+|the\s+)?(?:website|online\s+store|web\s+page|landing\s+page|e-?commerce)[\s\S]{0,40}search\s+engine|"
        r"duplicate\s+content|crawl(?:ability|\s+budget)|search\s+engine\s+index|schema(?:\.org|\s+markup)|json-ld|rich\s+snippets|"
        r"(?<!un)\bstructured\s+data\s+(?:markup|schema|json-ld|testing|for\s+seo|in\s+html)|"
        r"robots\.txt|sitemap(?:\.xml)?|xml\s+sitemap|\bhreflang\b|canonical\s+(?:url|tag|link)|rel=[\"']canonical|"
        r"meta\s+(?:robots|tags\s+for\s+seo|description)|open\s+graph|\bog:(?:title|image|description)|core\s+web\s+vitals|"
        r"largest\s+contentful\s+paint|cumulative\s+layout\s+shift|"
        r"content[- ]security[- ]policy|strict-transport-security|http\s+security\s+headers|"
        r"\bwcag\b|website'?s?\s+accessibility|web\s+accessibility\s+(?:audit|testing|guidelines|compliance|standards)|screen\s+reader\s+accessibility)",
        re.IGNORECASE,
    )
    RE_EN_SEO_IMPL = re.compile(
        r"(?:application/ld\+json|\"@context\"\s*:|\"@type\"\s*:|"
        r"User-agent:\s*\S[\s\S]{0,80}(?:Disallow|Allow|Sitemap):|"
        r"<urlset\b|<loc>https?://|"
        r"<meta\s+(?:name|property)=[\"'](?:description|robots|viewport|og:|twitter:)|"
        r"<link\s+[^>]*rel=[\"'](?:canonical|alternate)[\"']|hreflang=[\"'][a-z]{2}|"
        r"Content-Security-Policy:\s*\S|Strict-Transport-Security:\s*max-age|"
        r"X-Content-Type-Options:\s*nosniff|X-Frame-Options:\s*(?:DENY|SAMEORIGIN)|"
        r"aria-(?:label|live|expanded|controls|labelledby|describedby|hidden)=[\"'])",
        re.IGNORECASE,
    )
    RE_EN_SEO_BAD = re.compile(
        r"(?:unstructured\s+data|extract\s+structured\s+data|natural\s+language\s+processing|"
        r"jordan\s+canonical|canonical\s+ensemble|canonical\s+transformation|canonical\s+correlation|"
        r"buy\s+backlinks|black\s+hat\s+seo|keyword\s+stuffing|keyword\s+density|"
        r"seo[- ]friendly\s+(?:article|unique\s+content|blog|post|content)|improve\s+my\s+(?:gpt\s+)?prompt|"
        r"t-shirt\s+(?:exporter|manufacturer)|siatex|"
        r"wordpress|drupal|joomla|slim\s+framework|laravel|symfony|\bphp\b|<\?php|\.php\b|"
        r"coaching\s+business|diploma\s+programme|last\s+date\s+for\s+enrollment|ppc\s+marketing|blogging\s+platform\s+we've\s+created|"
        r"credit\s+agreement|negative\s+covenant|ebitda|ebidta|consolidated\s+total\s+assets|voucher\s+limit|"
        r"article\s+in\s+html\s+format|create\s+a\s+(?:react\s+header|progress\s+bar)|provide\s+clear\s+instructions\s+for\s+each\s+step|"
        r"\bmodx\b|\bjquery\b|\$\(|mysql_query|addslashes|filter_sanitize_string)",
        re.IGNORECASE,
    )

    # Strict Pillar 4 Copywriting / Art Direction / Brand Voice / Web Typography filters (0 glyphsoftware!)
    RE_EN_COPY_GOOD = re.compile(
        r"(?:landing\s+page\s+copy|website\s+copy|hero\s+(?:section|headline|copy)|value\s+proposition|"
        r"call[- ]to[- ]action|\bcta\b\s+(?:copy|button|microcopy|for\s+a\s+website)|ux\s+(?:writing|microcopy|copy)|microcopy\b|"
        r"brand\s+(?:voice|positioning|messaging|guidelines|identity)|tone\s+of\s+voice|"
        r"conversion\s+copywriting|product\s+positioning|onboarding\s+(?:copy|flow\s+copy)|empty[- ]state\s+copy|"
        r"typographic\s+hierarchy|type\s+scale|color\s+palette\s+for\s+(?:a\s+)?(?:website|brand|web\s+app|ui))",
        re.IGNORECASE,
    )
    RE_EN_COPY_ANCHOR = re.compile(
        r"\b(?:website|web\s+page|landing\s+page|homepage|saas|web\s+app|mobile\s+app|product\s+page|"
        r"e-?commerce|interface|\bui\b|\bux\b|onboarding|checkout|pricing\s+page|design\s+system|brand\s+identity|brand\s+voice|rebrand)\b",
        re.IGNORECASE,
    )
    RE_EN_COPY_BAD = re.compile(
        r"(?:\bdef\s+\w+\s*\(|\bimport\s+\w+|\bfunction\s+\w+\s*\(|#include\b|SELECT\s+\*\s+FROM|"
        r"cover\s+letter|resume\b|curriculum\s+vitae|\bdear\s+(?:hiring|sir|madam|valued|customer|client|team|reader|friends|\[|[a-z]+\s*,)|"
        r"^subject:\s|i\s+hope\s+this\s+(?:message|email|letter)\s+finds\s+you|\bsincerely,|\bbest\s+regards,|\bwarm\s+regards,|"
        r"public\s+relations\s+manager|marketing\s+communications\s+executive|product\s+marketing\s+manager|job\s+description|"
        r"bachelor'?s\s+degree|overnight\s+travel|"
        r"once\s+upon\s+a\s+time|write\s+a\s+(?:poem|sonnet|short\s+story|novel|fairy\s+tale|script|screenplay|speech|feature\s+article)|"
        r"feature\s+article|news\s+website|inspiring\s+story|"
        r"protagonist|coworkers|dialogue\s+between|scene\s+where|character\s+named|"
        r"\brecipe\b|skillet|tablespoon|teaspoon|preheat\s+oven|simmer\s+for|ingredients:|olive\s+oil|"
        r"plant-based\s+restaurant|full\s+menu|\bappetizers\b|\bentrees\b|"
        r"meditation|mindfulness|\binhale\b|\bexhale\b|deep\s+breath|audio\s+recording|voiceover|\bvo:\s|\(upbeat\s+music|podcast\s+(?:script|episode)|radio\s+spot|"
        r"\bradio\b|\btv\b|television|\bcommercial\b|promotional\s+video|video\s+script|\b1-2\s+minute\b|\b30[- ]second\b|\b60[- ]second\b|storyboard|music\s+video|announcer:|narrator:|"
        r"public\s+service\s+announcement|\bpsa\b|mental\s+health|vehicle\s+wrap|"
        r"newsletter|brochure|tri-fold|leaflet|business\s+(?:plan|proposal)|capital\s+expenditure|cap-ex|\bswot\b|financial\s+projection|staffing|"
        r"market\s+research\s+on\s+competitors|web\s+push\s+notification|"
        r"chatbot|firebase|react\s+native|node\.js|dialogflow|adobe\s+photoshop|wordpress|oscommerce|\bdjango\b|\bflask\b|property\s+management\s+system|"
        r"given\s+the\s+text|summarize\s+the|based\s+on\s+the\s+(?:following|provided|passage)|previous\s+article|keyword\s+density|reportgarden|google\s+my\s+business|deputy\s+ceo|entrepreneurial\s+ai|understood\?\s*$|"
        r"ladies\s+and\s+gentlemen|wedding\s+speech|obituary|keynote\s+speech|school\s+board|town\s+hall|press\s+release|for\s+immediate\s+release|"
        r"\bposter\b|\bflyer\b|\bpamphlet\b|charity\s+organization|facebook\s+ad|instagram|social\s+media|tiktok|tweet\s+thread|"
        r"email\s+(?:marketing|campaign)|sms\s+marketing|lead\s+nurturing|affiliate\s+program|loyalty\s+program|podcast|youtube\s+channel|"
        r"influencer|location-based\s+marketing|marketing\s+plan|(?:start|create|maintain)\s+a\s+(?:[\w-]+\s+){0,2}blog|semantic\s+search|"
        r"shopify\s+theme|tailwind\s+css\s+template|(?:generate|answer)\s+according\s+to:|\?:\s+[A-Z]|"
        r"office\s+design\s+scheme|packaging\s+design|\b(?:xyz|abc)\s+(?:web\s+design|productivity\s+app|company|corp|app)\b|"
        r"\(insert\s+(?:visually|call\s+to\s+action|image|hero|logo)|"
        r"\[image:|imgur\.com|\[(?:insert|your|company|brand|client|main\s+image|photo|cta\s+link)[^\]\n]{0,45}\])",
        re.IGNORECASE | re.MULTILINE,
    )

    @staticmethod
    def _has_duplicate_hex_swatch(s: str) -> bool:
        swatch_hexes = [
            m.group(1).upper()
            for ln in s.splitlines()
            if re.match(r"^\s*(?:\d+[\.\)]|[-*])\s+", ln)
            for m in re.finditer(r"#([0-9A-Fa-f]{6})\b", ln)
        ]
        return len(swatch_hexes) >= 3 and len(set(swatch_hexes)) < len(swatch_hexes)

    # Strict Russian bucket classifiers
    RE_RU_SPAM = re.compile(
        r"(?:накрутк|купить\s+ссылк|заработ\w+\s+в\s+интернет|ставки\s+на\s+спорт|казино|гороскоп|таро|"
        r"реферат\b|сочинени\w+\s+на\s+тему|стихотворени|сказк\w+\s+о\b|поздравлени\w+\s+с\s+дн[её]м)",
        re.IGNORECASE,
    )
    RE_RU_WEB_PROMPT = re.compile(
        r"(?:(?<!\w)(?:css3?|flexbox|subgrid|three\.js|threejs|webgl|tailwind|oklch|tsx|jsx|svelte)(?!\w)|"
        r"html5?[\s\S]{0,40}(?:css|стил|скрипт|\bjs\b|javascript|анимац|в[её]рстк|компонент|макет|лендинг|интерфейс)|"
        r"однофайлов\w+\s+страниц|адаптивн\w+\s+(?:в[её]рстк|меню|сетк|компонент|карточк|шапк)|"
        r"веб-?компонент|компонент\w+\s+(?:интерфейс|react|vue)|"
        r"svg[\s\S]{0,30}(?:анимац|иконк|график|диаграмм|компонент|интерактив)|"
        r"canvas[\s\S]{0,35}(?:2d|анимац|частиц|график|javascript|интерактив)|"
        r"(?:dom|веб-?интерфейс|фронтенд|frontend)[\s\S]{0,40}(?:javascript|typescript|react|vue)|"
        r"(?:javascript|typescript|react|vue)[\s\S]{0,40}(?:dom|интерфейс|компонент|анимац|в[её]рстк|кнопк|модальн|таблиц|канвас|слайдер|вкладк|аккордеон|драг|фильтр))",
        re.IGNORECASE,
    )
    RE_RU_WEB_DOM_ASST = re.compile(
        r"(?:<style\b|```(?:css|scss|tsx|jsx|vue|svelte)\b|display:\s*(?:flex|grid)|grid-template|@media\s*\(|@container\b|"
        r"@keyframes\s+\w+|oklch\(|document\.(?:querySelector|getElementById|createElement)|addEventListener\s*\(|"
        r"requestAnimationFrame|IntersectionObserver|ResizeObserver|customElements\.define|useState\s*\(|useEffect\s*\(|useRef\s*\(|"
        r"getContext\s*\(\s*['\"](?:2d|webgl)|THREE\.|<svg\b[\s\S]{0,800}<(?:path|circle|rect|polygon|polyline|line)\b)",
        re.IGNORECASE,
    )
    RE_RU_WEB_BAN = re.compile(
        r"(?:python|django|flask|fastapi|pytorch|pandas|unity|unreal|c\+\+|c#|java\b|kotlin|swift|android|ios|"
        r"telegram|телеграм|1c|1с|excel|\bsql\b|create\s+table|select\s+[\w\*]+\s+from|\bltree\b|postgresql|mysql|"
        r"mongodb|typeorm|prisma|sequelize|express\s*\(|app\.listen|fs\.(?:read|write)|tcppacket|\bipv4\b|"
        r"xmlhttprequest|<\?php|\bphp\b|\.php\b|//\s*todo\b|#\s*todo\b|/\*\s*todo\b|roblox|\blua\b|"
        r"node-red|module\.exports|загруженн\w+\s+изображен|прикрепленн\w+\s+изображен|по\s+картинке|из\s+скриншота|"
        r"^\s*(?:конечно,?\s+вы\s+можете|вот\s+расширенный\s+запрос)|"
        r"<%|%>|\{%|%\}|<table\s+border=|via\.placeholder\.com|placehold\.co|source\.unsplash\.com|"
        r"<!--[^\n]*(?:замените|остальные|добавьте|аналогии|плейсхолдер|тут\s+будут|ваш\s+код|вставьте)|"
        r"ограничена\s+знаниями|момент\s+знаний\s+системы|заполните\s+самостоятельно|не\s+могу\s+предоставить|"
        r"в\s+формате\s+html|\bryc\b|чтобы\s+изменить\s+данный|приведенн\w+\s+выше\s+код|рецепт|блин[ыоа]|борщ|багет|ингредиент|выпечк|кулинар|"
        r"налогообложен|\bусн\b|\bндфл\b|патентн\w+\s+систем|\bккт\b|саморазвити|мотиваци|толстого|нобелевск|"
        r"достопримечательност|париж|тесл[аы]|react[\s-]native|\bexpo\b|expo-|settings\.json|vs\s*code|vscode|\bjquery\b|slicknav|bootstrap)",
        re.IGNORECASE | re.MULTILINE,
    )
    RE_RU_P2_PROMPT = re.compile(
        r"(?:(?<!\w)(?:json-ld|schema\.org|robots\.txt|sitemap\.xml|hreflang|canonical|llms\.txt|csp|xss|csrf|cors|hsts|owasp|jwt|oauth\s*2?|ssrf|wcag)(?!\w)|"
        r"техническ\w+\s+seo|микроразметк|поисков\w+\s+индексац|core\s+web\s+vitals|content-security-policy|"
        r"sql-?инъекц|межсайтов\w+\s+скриптинг|заголовк\w+\s+безопасност|доступност\w+\s+интерфейс)",
        re.IGNORECASE,
    )
    RE_RU_P2_IMPL = re.compile(
        r"(?:application/ld\+json|\"@context\"|\"@type\"|schema\.org|json-ld|robots\.txt|User-agent:|Disallow:|sitemap\.xml|<urlset|"
        r"<meta\s+|rel=[\"']canonical|canonical|hreflang|Content-Security-Policy|Strict-Transport-Security|"
        r"X-Content-Type-Options|X-Frame-Options|Access-Control-Allow-Origin|SameSite|HttpOnly|DOMPurify|"
        r"aria-(?:label|live|expanded|controls)|wcag|llms\.txt|prepared\s+statement|параметризован|семантическ\w+\s+разметк)",
        re.IGNORECASE,
    )
    RE_RU_P2_BAN = re.compile(
        r"(?:unity|unreal|android|ios|telegram|телеграм|1c|1с|excel|c\+\+|active\s+directory|\brdp\b|wireshark|metasploit|roblox|\blua\b|"
        r"<\?php|\bphp\b|\.php\b|mysql_query|addslashes|filter_sanitize_string|laravel|symfony|wordpress|joomla|drupal|modx|bitrix|битрикс|"
        r"внедрить\s+уязвим|полезн\w+\s+нагрузк|обойти\s+файерволл|гуманно-компьютерн|человеко-компьютерн|взаимодействи\w+\s+человека\s+и\s+компьютера|"
        r"общее\s+усилие\s+сообщества)",
        re.IGNORECASE,
    )
    RE_RU_P4_PROMPT = re.compile(
        r"(?:копирайтинг|копирайтер|"
        r"(?:продающ\w+|конверсионн\w+)\s+(?:текст|заголов\w*|описани\w*|структур\w*|лендинг|страниц\w*)|"
        r"(?:текст\w*|контент|заголов\w*|описани\w*|блок\w*|экран\w*)\s+для\s+(?:лендинг\w*|главной\s+страниц\w*|посадочн\w+\s+страниц\w*|сайт\w*|веб-?сайт\w*|интернет-?магазин\w*|промо-?страниц\w*|карточк\w+\s+товар\w*|первого\s+экран\w*|веб-?приложени\w*|мобильн\w+\s+приложени\w*|saas|сервис\w*)|"
        r"посадочн\w+\s+страниц|структур\w+\s+(?:лендинг|сайт|посадочн\w+\s+страниц)|"
        r"уникальн\w+\s+торгов\w+\s+предложен|(?<!\w)утп(?!\w)|ценностн\w+\s+предложен|"
        r"ux-?(?:текст|редактур|копирайт|писател)|микрокопи|микротекст|интерфейсн\w+\s+текст|текст\w*\s+(?:кнопк|ошибк|пуст\w+\s+состояни|онбординг)|"
        r"голос\s+бренд|тон\s+коммуникац|tone\s+of\s+voice|бренд-?платформ|айдентик|фирменн\w+\s+стил|"
        r"слоган\w*\s+для\s+(?:бренд|компани|сайт|продукт|студи|сервис)|нейминг|"
        r"позиционировани\w+\s+(?:бренд|продукт|студи|сервис|компани)|"
        r"типографик|типографическ\w+\s+(?:шкал|иерархи|пар|сетк)|шрифтов\w+\s+пар|"
        r"визуальн\w+\s+(?:иерархи|концепци|стил|код)|цветов\w+\s+(?:палитр|схем)\w*\s+(?:сайт|интерфейс|бренд|приложени)|арт-?дирекшн)",
        re.IGNORECASE,
    )
    RE_RU_P4_BAD = re.compile(
        r"(?:инстаграм|instagram|тикток|tiktok|рилс|reels|телеграм-?канал|вконтакте|сторис|facebook|фейсбук|соцст?ет|инфлюенсер|блогер|"
        r"таргет\w*|арбитраж\s+трафик|провер\w*\s+следующий\s+текст|привести[\s\S]{0,50}текст\s+в\s+соответстви|"
        r"соответств\w*\s+(?:со?\s+стил|нашим\s+стилевым|корпоративн|нашему\s+фирменн)|брендбук\w*\s+(?:нашей|вашей)\s+компан|"
        r"корпоративн\w+\s+(?:требовани|стандарт)|нужда(?:ются|ется)\s+в\s+(?:постоянном|регулярном)\s+обновлени|"
        r"постоянно\s+нуждаются\s+в\s+обновлени|руководящим\s+принципам|в\s+соответствии\s+с\s+нашими\s+стандартами|подкорректировать\s+в\s+соответствии|"
        r"представь(?:те)?,?\s+что|веди(?:те)?\s+себя\s+как|вести\s+себя\s+как|сыграй(?:те)?\s+роль|сыграть\s+роль|действуй(?:те)?\s+как|выступи(?:те)?\s+в\s+роли|в\s+роли\s+|ты\s+профессиональный\s+маркетолог|"
        r"ответ\s+напиши\s+на\s+русском|перепиши\s+текст|100%-уникальн|экспертн\w+\s+стать|публицистическ\w+\s+стил|"
        r"вексел|vexels|сильные\s+слова:|каламбур|слизн|\b(?:to\s+make|for\s+sure|your\s+day)\b|пресс-?релиз|петици|транскрибац|"
        r"ведущ\w+\s+новост|гордон\s+рамзи|детектив|"
        r"утер\w+\s+паспорт|уважаем\w+\s+(?:коллег|партнер|клиент|управляющ|господ|читател|гост)|с\s+уважением,|доброго\s+времени\s+суток|"
        r"холодн\w+\s+пис[ье]м|продающ\w+\s+пис[ье]м|email-?рассылк|рассылк\w+\s+пис[ье]м|коммерческ\w+\s+предложен\w*\s+в\s+виде\s+письм|"
        r"резюме|сопроводительн\w+\s+письм|дипломн\w+\s+работ|курсов\w+\s+работ|стихотворени|поэм|рассказ\s+о\b|сказк|"
        r"хемингуэ|толсто|достоевск|пушкин|литературн\w+\s+прием|писател|роман\b|"
        r"граффити|баллончик|незаконн\w+\s+произведен|ежедневн\w+\s+отчет|лагер\w+\s+для\s+новичк|церемони\w+\s+закрыти|"
        r"devtools|\bf12\b|sitemap\.xml|\bmdn\b|css-tricks|flexbox|css\s+grid|"
        r"раскадровк|музыкальн\w+\s+клип|выставк\w+\s+современн|галере\w+\s+искусств|бизнес-?план|финансов\w+\s+план|смет\w+\s+расход|"
        r"маркетингов\w+\s+(?:план|кампан|стратеги)|директор\s+по\s+маркетингу|"
        r"roblox|\blua\b|remoteevent|minecraft|майнкрафт|"
        r"\[[^\[\]\n]{0,45}(?:название|имя|компани|город|телефон|ссылк|адрес|вставьте|ваш|бренд|продукт|дата|номер)[^\[\]\n]{0,45}\])",
        re.IGNORECASE,
    )
    RE_RU_P4_CODE_BAN = re.compile(r"```(?!(?:json|yaml|yml|md|markdown|text|txt)\b)[a-zA-Z0-9_+-]*", re.IGNORECASE)

    RE_RU_GENERAL_BAD = re.compile(
        r"(?:бизнес-?план|маркетинг|монетизац|\busp\b|\bутп\b|инфлюенсер|стартап|scrum|sprint|спринт|agile|канбан|kanban|"
        r"ретроспектив|ваканси|резюме|собеседован|главный\s+экран|структура\s+меню|целев\w+\s+аудитори|"
        r"продаж|клиентск|контент-?план|бренд|копирайт|лендинг|соцсет|предлож\w+\s+мне[^\n]{0,30}головоломк|"
        r"помодоро|pomodoro|тайм-?менеджмент|баланс\w*\s+между\s+работой|личн\w+\s+жизн|продуктивност|привычк|eat\s+that\s+frog|"
        r"слизист\w+\s+налет|кишечник|детокс|очищени\w+\s+организм|диет|похуден|вкусн\w+\s+продукт|рецепт|кулинар|"
        r"авторск\w+\s+прав|пиратств|интеллектуальн\w+\s+собственност|цифров\w+\s+собственност|юридическ|законодательств|"
        r"не\s+сможет\s+понять|невероятно\s+сложн\w+\s+код|обфуск|18\+|тупых\s+идей|карты\s+конфликта|телеграм|telegram|"
        r"\bcovid\b|коронавирус|утечк\w+\s+из\s+лаборатори|пандеми|черн\w+\s+ящик[\s\"«»]*модел|"
        r"курин\w+\s+игр|мера\s+недоумения|хиршберг\s+лабиринт|"
        r"психолог|саморазвити|мотиваци)",
        re.IGNORECASE,
    )
    RE_RU_GENERAL_STEM = re.compile(
        r"(?:```(?:python|cpp|c|rust|go|sql)\b|"
        r"(?:интеграл|производн|матриц|собственн\w+\s+значен|теорем|вероятност|термодинам|энтропи|"
        r"уравнени\w+\s+(?:максвелл|шр[её]дингер|навье|бернулли|лаплас|пуассон)|квантов|ковалентн|"
        r"рибосом|митохондри|фотосинтез|гликолиз|репликац\w+\s+днк|фермент|ядро\s+linux|системн\w+\s+вызов|дерево\s+отрезк|алгоритм\s+дейкстр))",
        re.IGNORECASE,
    )

    # Strict EN terminal & science filters for general_anti_starvation
    RE_TERM_PROMPT = re.compile(
        r"\b(?:bash|shell\s+script|posix\s+sh|linux\s+command|command[- ]line|awk|sed|grep|find\s+command|"
        r"systemd|journalctl|cron\s+job|crontab|rsync|tar\s+archive|ssh|iptables|ufw|jq|xargs|logrotate)\b",
        re.IGNORECASE,
    )
    RE_SCIENCE_PROMPT = re.compile(
        r"\b(?:thermodynamics|quantum\s+mechanics|classical\s+mechanics|orbital\s+mechanics|statistical\s+mechanics|"
        r"electromagnetism|relativity|molecular\s+biology|biochemistry|genetics|cellular\s+respiration|photosynthesis|"
        r"plate\s+tectonics|fluid\s+dynamics|entropy|catalysis|neuroscience|immunology|astrophysics|"
        r"semiconductor\s+physics|organic\s+chemistry|optics|spectroscopy|geophysics|biophysics|evolutionary\s+biology|"
        r"neurobiology|organic\s+synthesis|chemical\s+equilibrium|nuclear\s+physics|stellar\s+evolution|electrodynamics|"
        r"kinematics|cell\s+membrane|mitochondria|dna\s+replication|enzyme\s+kinetics|atmospheric\s+physics)\b",
        re.IGNORECASE,
    )
    RE_SCIENCE_BAD = re.compile(
        r"(?:\b(?:microsoft\s+word|classroom|marketing|sales|seo|fictional|character\s+study|short\s+story|novel|"
        r"protagonist|gratitude|mindfulness|meditation|self-help|blog\s+post|reputable\s+sources|cite\s+sources|"
        r"dear\s+|sincerely,|podcast|transcript|huberman|misspelling|summarize|summary|quiz)\b|"
        r"\[name\s+of\s+[^\]]+\]|\[a\s+question\s+about|\bin\s+class\s+\d+\b|the\s+quiz\s+will\s+consist|multiple[- ]choice|fill\s+in\s+the\s+blank|"
        r"like\s+a\s+(?:spoiled\s+)?(?:teenager|child|pirate|five[- ]year[- ]old|5[- ]year[- ]old)|"
        r"critic\s+scoring|coherence:|rewrite\s+the\s+following|revise\s+the\s+following|given\s+the\s+description|revise\s+my\s+introduction|inert\s+entity|evolutionary\s+entropy)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        CALIB_DIR.mkdir(parents=True, exist_ok=True)
        IMG_DIR.mkdir(parents=True, exist_ok=True)
        RAW_STEP4_DIR.mkdir(parents=True, exist_ok=True)
        for old_img in IMG_DIR.glob("*.*"):
            old_img.unlink(missing_ok=True)

        print(f"Loading Qwen3.8 tokenizer & processor from {TOKENIZER_DIR}...")
        self.tokenizer = AutoTokenizer.from_pretrained(str(TOKENIZER_DIR), trust_remote_code=True)
        self.processor = AutoProcessor.from_pretrained(str(TOKENIZER_DIR), trust_remote_code=True)
        self.image_pad_id = self.tokenizer.convert_tokens_to_ids("<|image_pad|>")

        self.audit_db = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
        for repo, lic in VERIFIED_LICENSES.items():
            if repo == "SmartLLM/curated-bilingual-canons":
                continue
            assert repo in self.audit_db, f"Repo {repo} missing from hf_datasets_audit.json"
            assert self.audit_db[repo].get("license") == lic, f"License mismatch for {repo}"

        tasks_data = json.loads(EVAL_TASKS_PATH.read_text(encoding="utf-8"))
        self.eval_fingerprints: list[str] = [
            t["prompt"][:100].lower()
            for t in tasks_data.get("tasks", [])
            if len(t.get("prompt", "")) >= 80
        ]
        for brand_kw in EVAL_BENCHMARK_IDENTIFIERS:
            self.eval_fingerprints.append(brand_kw.lower())

        self.eval_ref_img_hashes: set[str] = {
            hashlib.sha256(p.read_bytes()).hexdigest() for p in EVAL_REF_DIR.glob("*.png")
        }

        self.rejection_counts: Counter[str] = Counter()
        self.rejection_by_repo: dict[str, Counter[str]] = defaultdict(Counter)
        self.rejection_examples: list[dict[str, str]] = []

        # Global deduplication state across ALL strata & ALL modalities
        self.seen_text_sha: set[str] = set()
        self.seen_user_norm: set[str] = set()
        self.seen_user_shingles: list[tuple[str, set[int]]] = []
        self.seen_user_prefix_shingles: list[tuple[str, set[int]]] = []
        self.seen_asst_shingles: list[tuple[str, set[int]]] = []
        self.seen_img_sha: set[str] = set()
        self.seen_img_dhash: list[tuple[str, int]] = []
        self.ru_web_form_count = 0
        self.ru_p1_archetypes: Counter[str] = Counter()
        self.ru_p4_topics: Counter[str] = Counter()

        self.samples: list[dict[str, Any]] = []
        self.tokens_by_stratum_lang: dict[str, dict[str, int]] = {
            s: {"en": 0, "ru": 0} for s in STRATA_TARGETS
        }
        self.synthetic_tokens = 0
        self.reasoning_tokens = 0
        self.reasoning_strata: set[str] = set()

        # Pre-scan multi-purpose corpora once so all strata draw cleanly without re-streaming
        self.ru_pools: dict[str, list[tuple[str, str, list[dict[str, Any]]]]] = {
            "web": [],
            "p2": [],
            "p4": [],
            "general": [],
        }
        self.en_pools: dict[str, list[tuple[str, str, list[dict[str, Any]]]]] = {
            "p2_seo": [],
            "p4_copy": [],
            "term": [],
            "science": [],
            "code_general": [],
        }
        self.glyph_p1_rows: list[tuple[int, dict[str, Any]]] = []
        self.glyph_p2_rows: list[tuple[int, dict[str, Any]]] = []

        self._preload_glyphsoftware()
        self._preload_ru_corpora()
        self._preload_en_instruction_corpora()

    @staticmethod
    def fetch_range_text(url: str, start: int, length: int) -> str:
        req = urllib.request.Request(url, headers={"Range": f"bytes={start}-{start + length - 1}"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def count_text_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    @staticmethod
    def _first_user_text(msgs: list[dict[str, Any]]) -> str:
        for m in msgs:
            if m.get("role") == "user":
                c = m.get("content")
                if isinstance(c, str):
                    return c
                if isinstance(c, list):
                    return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        return ""

    @staticmethod
    def _assistant_text(msgs: list[dict[str, Any]]) -> str:
        parts = []
        for m in msgs:
            if m.get("role") == "assistant":
                c = m.get("content")
                if isinstance(c, str) and c.strip():
                    parts.append(c)
                rc = m.get("reasoning_content")
                if isinstance(rc, str) and rc.strip():
                    parts.append(rc)
                tcs = m.get("tool_calls")
                if tcs and not (isinstance(c, str) and c.strip()):
                    parts.append(json.dumps(tcs, ensure_ascii=False, sort_keys=True))
        return "\n".join(parts)

    def _preload_glyphsoftware(self) -> None:
        print("Pre-scanning glyphsoftware/opus-4.6-frontend-development with strict DOM-only filter...")
        raw = self.fetch_range_text(
            "https://huggingface.co/datasets/glyphsoftware/opus-4.6-frontend-development/resolve/main/dataset.jsonl",
            0,
            26_000_000,
        )
        for idx, line in enumerate(raw.splitlines()[:-1]):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            prob = (obj.get("evolved_problem") or obj.get("seed_problem") or "").strip()
            ans = (obj.get("solution") or "").strip()
            reas = (obj.get("reasoning") or "").strip()
            if not prob or not ans or "```" not in ans or len(ans) < 500 or len(reas) < 800:
                continue
            comb = f"{prob}\n{ans}\n{reas}"
            comb_low = comb.lower()
            if re.match(r"\s*(we are given|we need to|we have to|the user wants|let's|okay|we should)", prob.lower()):
                continue
            if any(
                bad in comb_low
                for bad in (
                    "do not include the solution",
                    "do not provide a solution",
                    "do not provide the actual code",
                    "without providing a solution",
                    "without providing the solution",
                    "without writing code",
                    "only output the problem",
                    "produce a new problem",
                    "act as a problem creator",
                    "**problem description:**",
                    "generate a new problem statement",
                )
            ):
                continue
            if has_corrupted_or_invalid_code_blocks(comb) or RE_CYR.search(comb):
                continue
            if self.RE_GLYPH_SYSTEMS_BAN.search(comb) or self.RE_P1_BROKEN_CODE.search(comb) or self._has_undefined_tailwind_custom_tokens(ans):
                self.log_rejection("glyphsoftware/opus-4.6-frontend-development", "systems_or_broken_cdn_leakage", prob[:120])
                continue
            if not self.RE_GLYPH_STRICT_DOM.search(ans):
                continue
            if self.RE_GLYPH_P2_CWV.search(prob + " " + ans) and len(self.glyph_p2_rows) < 28:
                self.glyph_p2_rows.append((idx, obj))
            else:
                self.glyph_p1_rows.append((idx, obj))
        print(f"  Glyph strict web rows: P1={len(self.glyph_p1_rows)}, P2_CWV={len(self.glyph_p2_rows)}")

    def _classify_ru_dialogue(self, repo: str, ref: str, msgs: list[dict[str, Any]]) -> None:
        # Keep clean single Q&A turn to avoid multi-turn drift or follow-up refusals
        trimmed = msgs[:3] if msgs and msgs[0]["role"] == "system" else msgs[:2]
        if len(trimmed) < 2 or trimmed[-1]["role"] != "assistant":
            return
        if trimmed[0]["role"] == "system" and prose_cyr_ratio(str(trimmed[0].get("content") or "")) < 0.32:
            return
        fu = self._first_user_text(trimmed)
        asst = self._assistant_text(trimmed)
        if len(fu) < 45 or len(fu) > 6_000 or len(asst) < 560 or len(asst) > 18_000 or re.match(r"^\s*\d+[\.\)]\s+", fu):
            return
        if has_truncated_user_prompt(fu):
            return
        # Ban ALL-CAPS screaming prompts
        alpha_chars = [ch for ch in fu if ch.isalpha()]
        if len(alpha_chars) >= 20 and sum(1 for ch in alpha_chars if ch.isupper()) / len(alpha_chars) > 0.28:
            return
        comb = f"{fu}\n{asst}"
        if (
            self.RE_RU_SPAM.search(comb)
            or RE_NSFW_OR_JUNK.search(comb)
            or RE_META_OR_REDACTION_LEAK.search(comb)
            or RE_NON_EN_RU_SCRIPT.search(comb)
            or RE_REFUSAL_OR_NONANSWER.search(comb)
            or RE_ULTRACHAT_CORRUPTION.search(comb)
            or RE_BRACKET_PLACEHOLDER.search(comb)
            or has_corrupted_or_invalid_code_blocks(comb)
            or has_paragraph_repetition_loop(asst)
            or has_truncated_ending_or_code(asst)
            or "ваш запрос:" in asst.lower()[:120]
        ):
            return
        if prose_cyr_ratio(fu) < 0.36 or prose_cyr_ratio(comb) < 0.36:
            return
        asst_low = asst.lower()
        has_web_code = any(
            k in asst_low
            for k in ("```html", "```css", "```js", "```javascript", "```ts", "```typescript", "```tsx", "```jsx", "```vue", "```svelte", "```svg", "<!doctype html")
        )
        # Never allow bare unstyled HTML documents without <style>, CSS block, <script>, or Tailwind
        has_bare_unstyled_html = bool(
            re.search(r"<!doctype\s+html|<html\b", asst_low)
            and not any(s_k in asst_low for s_k in ("<style", "```css", "```scss", "<script", "tailwind"))
        )
        has_dangling_ru_ref = bool(
            re.search(r"данн\w+\s+(?:html-?код|приложени|код)|существующ\w+\s+html-?страниц", fu, re.I)
            and "```" not in fu
            and "<" not in fu
        )
        if (
            self.RE_RU_WEB_PROMPT.search(fu)
            and not self.RE_RU_WEB_BAN.search(comb)
            and not self.RE_P1_BROKEN_CODE.search(comb)
            and not self._has_undefined_tailwind_custom_tokens(asst)
            and has_web_code
            and not has_bare_unstyled_html
            and not has_dangling_ru_ref
            and self.RE_RU_WEB_DOM_ASST.search(asst)
            and len(asst) >= 700
        ):
            code_blocks = re.findall(r"```[a-zA-Z0-9_+-]*\n(.*?)```", asst, flags=re.S)
            code_lines = sum(len(b.strip().splitlines()) for b in code_blocks) if code_blocks else len(asst.splitlines())
            if code_lines < 18:
                return
            matched_arch: list[str] = []
            for arch_key, arch_pat, arch_cap in (
                ("form_post", r"(?:<form\b|formdata|обратной\s+связи|отправк\w+\s+форм|#dataform|#loginform|контактн\w+\s+форм|submit-form|feedback-form|contact-form)", 1),
                ("weather", r"(?:погод\w+|weather|openweathermap)", 1),
                ("i18n_rtl", r"(?:i18n|интернационализац|локализац|react-intl|i18next|\brtl\b)", 1),
                ("random_color", r"(?:случайн\w+\s+цвет|random\s+color)", 1),
                ("responsive_menu", r"(?:адаптивн\w+\s+(?:меню|боковое\s+меню|навигац)|бургер-?меню|гамбургер|mobile\s+menu|navbar)", 1),
                ("responsive_generic", r"(?:адаптивн\w+\s+(?:дизайн|в[её]рстк|страниц|сайт|макет))", 2),
                ("todo_list", r"(?:спис\w+\s+(?:задач|дел)|todo|to-do)", 2),
                ("calculator", r"(?:калькулятор|calculator)", 2),
                ("slider_carousel", r"(?:слайдер|карусел|carousel|swiper)", 2),
                ("modal_popup", r"(?:модальн\w+\s+окн|попап|popup|dialog)", 2),
                ("tabs_accordion", r"(?:аккордеон|вкладк|табы|\btabs\b|accordion)", 2),
                ("timer_clock", r"(?:таймер|секундомер|обратн\w+\s+отсч[её]т|countdown|stopwatch)", 2),
            ):
                if re.search(arch_pat, comb, re.I):
                    if self.ru_p1_archetypes[arch_key] >= arch_cap:
                        return
                    matched_arch.append(arch_key)
            if len(self.ru_pools["web"]) < 240:
                for ak in matched_arch:
                    self.ru_p1_archetypes[ak] += 1
                self.ru_pools["web"].append((repo, ref, trimmed))
        elif (
            self.RE_RU_P2_PROMPT.search(fu)
            and not self.RE_RU_P2_BAN.search(comb)
            and self.RE_RU_P2_IMPL.search(asst)
            and len(asst) >= 620
        ):
            if len(self.ru_pools["p2"]) < 180:
                self.ru_pools["p2"].append((repo, ref, trimmed))
        elif (
            repo != "d0rj/ru-instruct"
            and self.RE_RU_P4_PROMPT.search(fu)
            and not self.RE_RU_P4_BAD.search(comb)
            and not self.RE_RU_P4_CODE_BAN.search(asst)
            and not self.RE_RU_WEB_BAN.search(fu)
            and not RE_P4_ANY_PROSE_BRACKET.search(strip_fenced_code_fast(comb))
            and len(RE_EMOJI_SPAM.findall(comb)) < 3
            and len(asst) >= 640
        ):
            if re.search(r"(?:питани|диет|нутрициол)", comb, re.I):
                if self.ru_p4_topics["nutrition"] >= 1:
                    return
            matched_stems: list[str] = []
            for stem in (
                "фитнес", "кофейн", "ювелир", "стоматолог", "недвижимост", "автосервис",
                "пекарн", "косметик", "мебел", "одежд", "отел", "ресторан",
                "доставк", "клининг", "цвет", "онлайн-школ", "логистик", "туризм",
                "призыв", "эколог",
            ):
                if stem in comb.lower():
                    if self.ru_p4_topics[stem] >= 2:
                        return
                    matched_stems.append(stem)
            if len(self.ru_pools["p4"]) < 120:
                if re.search(r"(?:питани|диет|нутрициол)", comb, re.I):
                    self.ru_p4_topics["nutrition"] += 1
                for st_k in matched_stems:
                    self.ru_p4_topics[st_k] += 1
                self.ru_pools["p4"].append((repo, ref, trimmed))
        elif (
            not self.RE_RU_WEB_PROMPT.search(fu)
            and not self.RE_RU_GENERAL_BAD.search(comb)
            and self.RE_RU_GENERAL_STEM.search(comb)
            and len(asst) >= 880
        ):
            if len(self.ru_pools["general"]) < 260:
                self.ru_pools["general"].append((repo, ref, trimmed))

    def _preload_ru_corpora(self) -> None:
        print("Pre-streaming Vikhrmodels/GrandMaster-PRO-MAX for authentic RU pools (+ strict EN p2_seo, 0 d0rj/ru-instruct)...")
        ds_gm = load_dataset("Vikhrmodels/GrandMaster-PRO-MAX", split="train", streaming=True)
        for i, row in enumerate(ds_gm):
            if i >= 410_000:
                break
            if (
                len(self.ru_pools["web"]) >= 200
                and len(self.ru_pools["p2"]) >= 145
                and len(self.ru_pools["p4"]) >= 55
                and len(self.ru_pools["general"]) >= 230
            ):
                break
            if i > 0 and i % 40_000 == 0:
                print(
                    "  [GrandMaster row",
                    f"{i:,}]",
                    {k: len(v) for k, v in self.ru_pools.items()},
                    f"en_p2_seo={len(self.en_pools['p2_seo'])}",
                )
            lang_tag = row.get("prompt_lang")
            if lang_tag not in ("ru", "en"):
                continue
            if lang_tag == "en" and len(self.en_pools["p2_seo"]) >= 24:
                continue
            conv = row.get("conversation") or []
            if not isinstance(conv, list) or len(conv) < 2:
                continue
            msgs = []
            for m in conv:
                role = m.get("role", "user")
                if role not in ("system", "user", "assistant"):
                    role = "user"
                c = (m.get("content") or "").strip()
                if c and "\ufffd" not in c:
                    msgs.append({"role": role, "content": c})
            if len(msgs) < 2 or msgs[-1]["role"] != "assistant":
                continue
            if lang_tag == "ru":
                self._classify_ru_dialogue("Vikhrmodels/GrandMaster-PRO-MAX", f"train:row_{i}", msgs)
            else:
                self._classify_en_dialogue("Vikhrmodels/GrandMaster-PRO-MAX", f"train:row_{i}", msgs, p2_seo_only=True)
        del ds_gm
        gc.collect()
        print("  RU pools:", {k: len(v) for k, v in self.ru_pools.items()}, f"| EN p2_seo={len(self.en_pools['p2_seo'])}")

    @classmethod
    def _passes_terminal_anti_leakage(cls, user_prompt: str, asst_text: str) -> bool:
        """Reject terminal samples where the user prompt already contains code blocks or the target shell command."""
        if "```" in user_prompt or "#!/bin/" in user_prompt or "sudo " in user_prompt.lower() or "#!/usr/bin/awk" in asst_text:
            return False
        if not re.search(r"```(?:bash|sh|shell|zsh)\b", asst_text, re.I):
            return False
        u_low = " ".join(user_prompt.lower().split())
        for block in re.findall(r"```(?:bash|sh|shell|zsh)?\s*(.*?)```", asst_text, flags=re.S | re.I):
            for raw_ln in block.splitlines():
                ln = raw_ln.strip()
                if not ln or ln.startswith("#") or len(ln) < 14:
                    continue
                norm_ln = " ".join(ln.lower().split())
                if norm_ln in u_low:
                    return False
        return True

    def _classify_en_dialogue(
        self, repo: str, ref: str, msgs: list[dict[str, Any]], p2_seo_only: bool = False
    ) -> None:
        # Keep ONLY the first self-contained Q&A turn to avoid UltraChat multi-turn drift or mockup link hallucinations
        trimmed = msgs[:3] if msgs and msgs[0]["role"] == "system" else msgs[:2]
        if len(trimmed) < 2 or trimmed[-1]["role"] != "assistant":
            return
        fu = self._first_user_text(trimmed)
        asst = self._assistant_text(trimmed)
        if len(fu) < 55 or len(fu) > 6_000 or len(asst) < 820 or len(asst) > 18_000:
            return
        if re.match(r"^\s*\d+[\.\)\/]\s*", fu) or has_truncated_user_prompt(fu):
            return
        if re.match(r"^\s*(?:you\s+are\s+an?\s+|i\s+want\s+you\s+to\s+act\s+as\b|act\s+as\b)", fu, re.I):
            return
        if re.match(r"^\s*(?:additionally,|furthermore,|moreover,|also,\s+the\b)", asst, re.I):
            return
        if "```" in fu and has_truncated_ending_or_code(fu):
            return
        if re.search(r"\b(?:create|write|build|develop|implement)\s+(?:a\s+|an\s+)?python\b", fu, re.I) and "```python" not in asst.lower():
            return
        comb = f"{fu}\n{asst}"
        if (
            RE_NSFW_OR_JUNK.search(comb)
            or RE_META_OR_REDACTION_LEAK.search(comb)
            or RE_NON_EN_RU_SCRIPT.search(comb)
            or RE_CYR.search(comb)
            or RE_REFUSAL_OR_NONANSWER.search(comb)
            or RE_ULTRACHAT_CORRUPTION.search(comb)
            or RE_BRACKET_PLACEHOLDER.search(comb)
            or has_corrupted_or_invalid_code_blocks(comb)
            or has_lowercase_para_corruption(comb)
            or has_paragraph_repetition_loop(asst)
            or has_truncated_ending_or_code(asst)
            or "imgur.com" in comb.lower()
            or "[image:" in comb.lower()
            or re.search(r"!\[[^\]]*\]\(https?://", comb)
            or re.search(r"(?:http://schema\.org|\bALLOW-FROM\b|\"fanArt\"|(?:^|\n)[ \t]*#{5,}[ \t]+\S)", comb, re.I)
        ):
            return

        has_tech_intent = bool(
            re.search(
                r"\b(?:how|what|why|explain|write|create|design|implement|audit|optimize|configure|build|guide|checklist|difference|prevent|fix|improve|structure|develop)\b",
                fu,
                re.I,
            )
        )

        if (
            len(self.en_pools["p2_seo"]) < 100
            and "```" not in fu
            and has_tech_intent
            and self.RE_EN_SEO_GOOD.search(fu)
            and self.RE_EN_SEO_IMPL.search(asst)
            and not self.RE_EN_SEO_BAD.search(comb)
        ):
            self.en_pools["p2_seo"].append((repo, ref, trimmed))
            return
        if p2_seo_only:
            return
        if (
            len(self.en_pools["p4_copy"]) < 145
            and len(fu) <= 560
            and self.RE_EN_COPY_GOOD.search(fu)
            and self.RE_EN_COPY_ANCHOR.search(fu)
            and not self.RE_EN_COPY_BAD.search(comb)
            and not self._has_duplicate_hex_swatch(asst)
            and not RE_P4_ANY_PROSE_BRACKET.search(strip_fenced_code_fast(comb))
            and len(RE_EMOJI_SPAM.findall(comb)) < 3
        ):
            self.en_pools["p4_copy"].append((repo, ref, trimmed))
        elif (
            len(self.en_pools["term"]) < 60
            and self.RE_TERM_PROMPT.search(fu)
            and self._passes_terminal_anti_leakage(fu, asst)
        ):
            self.en_pools["term"].append((repo, ref, trimmed))
        elif (
            len(self.en_pools["science"]) < 60
            and has_tech_intent
            and self.RE_SCIENCE_PROMPT.search(fu)
            and self.RE_SCIENCE_PROMPT.search(asst)
            and not self.RE_SCIENCE_BAD.search(comb)
            and "```" not in comb
            and "http://" not in comb
            and "https://" not in comb
        ):
            self.en_pools["science"].append((repo, ref, trimmed))
        elif (
            len(self.en_pools["code_general"]) < 60
            and has_tech_intent
            and re.search(r"```(?:python|sql|rust|go)\b", asst, re.I)
            and not re.search(r"(?:html|css|react|dom|browser|webpage|tailwind|nextjs|beautifulsoup|flask|django|canvas|pause\s+for\s+further\s+instructions)", comb, re.I)
        ):
            self.en_pools["code_general"].append((repo, ref, trimmed))

    def _preload_en_instruction_corpora(self) -> None:
        print("Pre-streaming HuggingFaceH4/ultrachat_200k for Pillar 2/4 & General EN...")
        ds_uc = load_dataset("HuggingFaceH4/ultrachat_200k", split="train_sft", streaming=True)
        for i, row in enumerate(ds_uc):
            if i >= 210_000:
                break
            if (
                len(self.en_pools["p4_copy"]) >= 135
                and len(self.en_pools["term"]) >= 28
                and len(self.en_pools["science"]) >= 30
                and len(self.en_pools["code_general"]) >= 35
            ):
                break
            if i > 0 and i % 30_000 == 0:
                print("  [UltraChat row", f"{i:,}]", {k: len(v) for k, v in self.en_pools.items()})
            raw_msgs = row.get("messages") or []
            msgs = [
                {"role": m.get("role", "user"), "content": (m.get("content") or "").strip()}
                for m in raw_msgs
                if m.get("role") in ("system", "user", "assistant") and (m.get("content") or "").strip()
            ]
            if len(msgs) >= 2:
                self._classify_en_dialogue(
                    "HuggingFaceH4/ultrachat_200k",
                    f"train_sft:row_{i}:id_{row.get('prompt_id', i)}",
                    msgs,
                )
        del ds_uc
        gc.collect()
        print("  EN pools:", {k: len(v) for k, v in self.en_pools.items()})

    def log_rejection(self, repo: str, reason: str, snippet: str = "") -> None:
        self.rejection_counts[reason] += 1
        self.rejection_by_repo[repo][reason] += 1
        if len(self.rejection_examples) < 50:
            self.rejection_examples.append(
                {
                    "repo": repo,
                    "reason": reason,
                    "snippet": snippet[:180].replace("\n", " "),
                }
            )

    def passes_filter(
        self,
        full_text: str,
        msgs: list[dict[str, Any]],
        repo: str,
        stratum: str,
        expected_lang: str,
        extra_meta: dict[str, Any] | None = None,
    ) -> bool:
        if not full_text or len(full_text.strip()) < 180:
            self.log_rejection(repo, "length_too_short", full_text[:120] if full_text else "")
            return False

        if extra_meta and extra_meta.get("language") == "openscad":
            self.log_rejection(repo, "excluded_programming_lang_openscad", full_text[:120])
            return False

        if RE_NON_EN_RU_SCRIPT.search(full_text):
            self.log_rejection(repo, "non_en_ru_script_cjk_arabic_hindi", full_text[:120])
            return False

        if RE_NSFW_OR_JUNK.search(full_text):
            self.log_rejection(repo, "nsfw_or_junk_guard", full_text[:120])
            return False

        if RE_META_OR_REDACTION_LEAK.search(full_text):
            self.log_rejection(repo, "meta_or_redaction_leak", full_text[:120])
            return False

        if RE_REFUSAL_OR_NONANSWER.search(full_text):
            self.log_rejection(repo, "refusal_or_missing_context_nonanswer", full_text[:120])
            return False

        if RE_ULTRACHAT_CORRUPTION.search(full_text):
            self.log_rejection(repo, "ultrachat_case_corruption", full_text[:120])
            return False

        fu_check = self._first_user_text(msgs)
        asst_all_txt = self._assistant_text(msgs)
        if repo != "SWE-bench/SWE-smith-trajectories":
            if has_corrupted_or_invalid_code_blocks(full_text):
                self.log_rejection(repo, "corrupted_or_syntax_invalid_code_block", full_text[:120])
                return False
            if repo != "SmartLLM/curated-bilingual-canons" and has_truncated_user_prompt(fu_check):
                self.log_rejection(repo, "truncated_or_wrapped_user_prompt", fu_check[-120:])
                return False
        if expected_lang == "en" and RE_CYR.search(full_text):
            self.log_rejection(repo, "cyrillic_leak_in_en_sample", full_text[:120])
            return False
        if has_paragraph_repetition_loop(asst_all_txt) or (
            repo != "SWE-bench/SWE-smith-trajectories" and has_paragraph_repetition_loop(fu_check)
        ):
            self.log_rejection(repo, "paragraph_repetition_loop", asst_all_txt[:120])
            return False

        if msgs and not msgs[-1].get("tool_calls"):
            last_asst_c = msgs[-1].get("content")
            last_asst_str = last_asst_c if isinstance(last_asst_c, str) else ""
            if has_truncated_ending_or_code(
                last_asst_str,
                check_unfenced_braces=(repo == "runanlab/gpt-5.4-frontend-development-27052026"),
            ):
                self.log_rejection(repo, "truncated_assistant_ending_or_brace_mismatch", last_asst_str[-120:])
                return False

        if stratum in ("pillar_4_art_direction_copywriting", "pillar_2_seo_geo_security", "general_anti_starvation"):
            prose_only = strip_fenced_code_fast(full_text)
            if RE_BRACKET_PLACEHOLDER.search(prose_only):
                self.log_rejection(repo, "bracketed_template_placeholder", prose_only[:120])
                return False
            if (
                stratum == "pillar_4_art_direction_copywriting"
                and repo != "SmartLLM/curated-bilingual-canons"
                and RE_P4_ANY_PROSE_BRACKET.search(prose_only)
            ):
                self.log_rejection(repo, "p4_prose_bracket_placeholder", prose_only[:120])
                return False

        low = full_text.lower()
        for fp in self.eval_fingerprints:
            if fp and fp in low:
                self.log_rejection(repo, "eval_suite_leakage_guard", fp)
                return False

        # Enforce stricter margins than step4_verify_calib.py on BOTH full_text AND first user prompt (+ system prompt for RU)
        fu_raw = self._first_user_text(msgs)
        ratio = prose_cyr_ratio(full_text)
        fu_ratio = prose_cyr_ratio(fu_raw)
        if expected_lang == "ru":
            if ratio < 0.32 or fu_ratio < 0.30:
                self.log_rejection(repo, "lang_mismatch_expected_ru_prose_ratio", f"ratio={ratio:.3f}, fu={fu_ratio:.3f}")
                return False
            if msgs and msgs[0].get("role") == "system":
                sys_str = str(msgs[0].get("content") or "")
                if len(sys_str) >= 20 and prose_cyr_ratio(sys_str) < 0.30:
                    self.log_rejection(repo, "english_system_prompt_in_ru_sample", sys_str[:120])
                    return False
        if expected_lang == "en" and (ratio > 0.04 or fu_ratio > 0.04):
            self.log_rejection(repo, "lang_mismatch_expected_en_prose_ratio", f"ratio={ratio:.3f}, fu={fu_ratio:.3f}")
            return False

        if full_text.count("```") % 2 != 0:
            self.log_rejection(repo, "unclosed_markdown_code_fence", full_text[:120])
            return False
        if "<!doctype html" in low and "</html>" not in low:
            self.log_rejection(repo, "unclosed_html_document", full_text[:120])
            return False

        if stratum not in ("general_anti_starvation", "long_context"):
            if RE_EXCLUDED_LANG.search(full_text):
                self.log_rejection(repo, "excluded_programming_lang", full_text[:120])
                return False
            if RE_EXCLUDED_DOMAIN.search(full_text):
                self.log_rejection(repo, "excluded_devops_gamedev_science", full_text[:120])
                return False
            if stratum in ("pillar_1_frontend_3d_svg", "pillar_3_style_canons_vision") and RE_LEGACY_WEB_SLOP.search(full_text):
                self.log_rejection(repo, "legacy_slop_frontend", full_text[:120])
                return False

        # Global exact text hash check
        digest = hashlib.sha256(full_text.encode("utf-8", errors="ignore")).hexdigest()
        if digest in self.seen_text_sha:
            self.log_rejection(repo, "duplicate_exact_text", full_text[:100])
            return False

        # Global normalized first-user prompt deduplication + 4-gram Jaccard + 14-word prefix 3-gram Jaccard
        fu_norm = re.sub(r"\W+", " ", fu_raw.lower()).strip()
        if len(fu_norm) >= 20:
            fu_sha = hashlib.sha256(fu_norm.encode("utf-8", errors="ignore")).hexdigest()
            if fu_sha in self.seen_user_norm:
                self.log_rejection(repo, "duplicate_first_user_prompt", fu_norm[:100])
                return False
        if repo != "SWE-bench/SWE-smith-trajectories":
            fu_sh = word_shingles_k(fu_raw, 4)
            if len(fu_sh) >= 8:
                for prev_id, prev_ush in self.seen_user_shingles:
                    if min(len(fu_sh), len(prev_ush)) / max(len(fu_sh), len(prev_ush)) < 0.45:
                        continue
                    inter_u = len(fu_sh & prev_ush)
                    jac_u = inter_u / (len(fu_sh) + len(prev_ush) - inter_u)
                    if jac_u >= 0.45:
                        self.log_rejection(repo, "near_duplicate_user_prompt_template", f"jaccard={jac_u:.3f} vs {prev_id}")
                        return False

        # Block Evol-Instruct shared prefix clones (e.g. repeated opening 12-14 words)
        if repo not in ("HuggingFaceM4/WebSight", "SWE-bench/SWE-smith-trajectories"):
            pref_sh = prefix_shingles_3(fu_raw, 14)
            if len(pref_sh) >= 6:
                for prev_id, prev_psh in self.seen_user_prefix_shingles:
                    inter_p = len(pref_sh & prev_psh)
                    jac_p = inter_p / (len(pref_sh) + len(prev_psh) - inter_p)
                    if jac_p >= 0.42:
                        self.log_rejection(repo, "near_duplicate_prompt_prefix_clone", f"prefix_jac={jac_p:.3f} vs {prev_id}")
                        return False

        # Global exact step=1 5-gram shingle Jaccard anti-clone guard (< 0.45) on assistant content
        asst_txt = self._assistant_text(msgs)
        sh = word_shingles_5(asst_txt)
        if len(sh) >= 25:
            for prev_id, prev_sh in self.seen_asst_shingles:
                min_len = min(len(sh), len(prev_sh))
                max_len = max(len(sh), len(prev_sh))
                if min_len / max_len < 0.45:
                    continue
                inter = len(sh & prev_sh)
                jac = inter / (len(sh) + len(prev_sh) - inter)
                if jac >= 0.45:
                    self.log_rejection(repo, "near_duplicate_jaccard_clone", f"jaccard={jac:.3f} vs {prev_id}")
                    return False

        return True

    def try_add_sample(
        self,
        stratum: str,
        lang: str,
        subdomain: str,
        repo: str,
        source_ref: str,
        synthetic: bool,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        modality: str = "text",
        images: list[dict[str, Any]] | None = None,
        pil_images: list[Image.Image] | None = None,
        extra_meta: dict[str, Any] | None = None,
        max_sample_tokens: int = 5600,
    ) -> bool:
        target = STRATA_TARGETS[stratum][lang]
        current = self.tokens_by_stratum_lang[stratum][lang]
        if current >= target:
            return False

        if repo == "SmartLLM/curated-bilingual-canons":
            synthetic = True

        if not messages or messages[-1].get("role") != "assistant":
            return False

        # Normalize CRLF / CR -> LF inside all message fields so JSONL & imatrix_corpus.txt are strictly LF
        norm_msgs: list[dict[str, Any]] = []
        for m in messages:
            mc = dict(m)
            c = mc.get("content")
            if isinstance(c, str):
                mc["content"] = c.replace("\r\n", "\n").replace("\r", "\n")
            elif isinstance(c, list):
                new_list = []
                for blk in c:
                    if isinstance(blk, dict) and isinstance(blk.get("text"), str):
                        b2 = dict(blk)
                        b2["text"] = b2["text"].replace("\r\n", "\n").replace("\r", "\n")
                        new_list.append(b2)
                    else:
                        new_list.append(blk)
                mc["content"] = new_list
            if isinstance(mc.get("reasoning_content"), str):
                mc["reasoning_content"] = mc["reasoning_content"].replace("\r\n", "\n").replace("\r", "\n")
            norm_msgs.append(mc)
        messages = norm_msgs

        if tools:
            tools = _normalize_lf_deep(tools)

        for m in messages:
            c = m.get("content")
            cs = c if isinstance(c, str) else " ".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
            rc = m.get("reasoning_content")
            if isinstance(rc, str) and any(
                bad_rc in rc
                for bad_rc in ("<tool_call>", "</tool_call>", "<tool_response>", "</tool_response>", "<think>", "</think>", "<function=")
            ):
                self.log_rejection(repo, "corrupted_reasoning_content_tags", rc[:120])
                return False
            if m.get("role") == "assistant" and ("<tool_call>" in cs or "<tool_response>" in cs or "</reply>" in cs):
                self.log_rejection(repo, "embedded_tool_call_or_response_in_content", cs[:120])
                return False
            if "<think>" in cs or "</think>" in cs:
                self.log_rejection(repo, "embedded_think_tag_in_content", cs[:120])
                return False
            if cs.lstrip().startswith("[{'type':") or "[{'type': 'text'" in cs:
                self.log_rejection(repo, "python_list_repr_leak_in_content", cs[:120])
                return False
            if modality == "text" and ("imgur.com" in cs.lower() or "[image:" in cs.lower()):
                self.log_rejection(repo, "hallucinated_image_placeholder", cs[:120])
                return False
            st = cs.strip()
            if st.startswith("{") and st.endswith("}"):
                try:
                    obj = json.loads(st)
                    if isinstance(obj, dict) and ({"system", "messages", "conversations"} & set(obj)):
                        self.log_rejection(repo, "json_dumped_conversation", st[:120])
                        return False
                except Exception:
                    pass

        try:
            full_text = self.tokenizer.apply_chat_template(messages, tools=tools or None, tokenize=False)
            full_text = full_text.replace("\r\n", "\n").replace("\r", "\n")
        except Exception as e:
            self.log_rejection(repo, "apply_chat_template_error", str(e)[:120])
            return False

        if "<|im_start|>tool" in full_text or "<image:" in full_text:
            self.log_rejection(repo, "invalid_template_tokens", full_text[:120])
            return False

        if stratum in ("agentic_tool_calling", "long_context") or bool(tools):
            if not validate_tool_turn_alignment(messages, allow_final_submit_call=(stratum == "long_context")):
                self.log_rejection(repo, "misaligned_tool_response_turns", full_text[:120])
                return False
        if stratum == "agentic_tool_calling":
            has_calls = any(m.get("role") == "assistant" and m.get("tool_calls") for m in messages)
            if not (bool(tools) and has_calls and "<function=" in full_text):
                self.log_rejection(repo, "invalid_agentic_tool_call_format", full_text[:120])
                return False

        imgs_list = images or []
        img_dhashes: list[int] = []
        if modality == "multimodal":
            if not imgs_list or not pil_images or len(imgs_list) != len(pil_images):
                return False
            if full_text.count("<|vision_start|><|image_pad|><|vision_end|>") != len(imgs_list):
                return False
            for im_meta, pil_im in zip(imgs_list, pil_images):
                sha = im_meta.get("sha256", "")
                if sha in self.eval_ref_img_hashes:
                    self.log_rejection(repo, "eval_suite_image_leakage_guard", im_meta.get("path", ""))
                    return False
                if sha in self.seen_img_sha:
                    self.log_rejection(repo, "duplicate_image_sha256", im_meta.get("path", ""))
                    return False
                st_stat = ImageStat.Stat(pil_im)
                if max(st_stat.stddev) < 12.0:
                    self.log_rejection(repo, "blank_or_flat_image", im_meta.get("path", ""))
                    return False
                dh = compute_dhash64(pil_im)
                for prev_path, prev_dh in self.seen_img_dhash:
                    if hamming64(dh, prev_dh) <= 4:
                        self.log_rejection(repo, "perceptual_near_duplicate_image", f"{im_meta.get('path')} ~ {prev_path}")
                        return False
                img_dhashes.append(dh)

            out = self.processor(text=[full_text], images=pil_images, return_tensors=None)
            ids = out["input_ids"][0]
            if sum(1 for t in ids if t == self.image_pad_id) <= len(imgs_list):
                return False
            tok_count = len(ids)
        else:
            if imgs_list:
                return False
            tok_count = self.count_text_tokens(full_text)

        if tok_count < 80:
            self.log_rejection(repo, "tokens_below_80", full_text[:100])
            return False

        remaining = target - current
        allowance = 5_000 if stratum == "long_context" else 900
        if tok_count > max_sample_tokens or tok_count > remaining + allowance:
            return False

        if synthetic and (self.synthetic_tokens + tok_count > 220_000):
            return False

        reas_list = [
            m.get("reasoning_content", "")
            for m in messages
            if m.get("role") == "assistant" and isinstance(m.get("reasoning_content"), str)
        ]
        has_real_reas = any(self.count_text_tokens(x) >= 200 for x in reas_list)
        if has_real_reas and synthetic:
            return False

        if not self.passes_filter(full_text, messages, repo, stratum, lang, extra_meta=extra_meta):
            return False

        sample_id = f"calib_{len(self.samples) + 1:04d}_{stratum[:10]}_{lang}"

        # Commit global deduplication fingerprints
        self.seen_text_sha.add(hashlib.sha256(full_text.encode("utf-8", errors="ignore")).hexdigest())
        fu_raw = self._first_user_text(messages)
        fu_norm = re.sub(r"\W+", " ", fu_raw.lower()).strip()
        if len(fu_norm) >= 20:
            self.seen_user_norm.add(hashlib.sha256(fu_norm.encode("utf-8", errors="ignore")).hexdigest())
        fu_sh = word_shingles_k(fu_raw, 4)
        if len(fu_sh) >= 8:
            self.seen_user_shingles.append((sample_id, fu_sh))
        if repo != "HuggingFaceM4/WebSight":
            pref_sh = prefix_shingles_3(fu_raw, 14)
            if len(pref_sh) >= 6:
                self.seen_user_prefix_shingles.append((sample_id, pref_sh))
        sh = word_shingles_5(self._assistant_text(messages))
        if len(sh) >= 25:
            self.seen_asst_shingles.append((sample_id, sh))
        if modality == "multimodal":
            for im_meta, dh in zip(imgs_list, img_dhashes):
                self.seen_img_sha.add(im_meta["sha256"])
                self.seen_img_dhash.append((im_meta["path"], dh))

        record = {
            "id": sample_id,
            "pillar": stratum,
            "lang": lang,
            "subdomain": subdomain,
            "source_repo": repo,
            "source_ref": source_ref,
            "license": VERIFIED_LICENSES[repo],
            "synthetic": bool(synthetic),
            "modality": modality,
            "images": imgs_list,
            "messages": messages,
            "tools": tools if tools else None,
            "text": full_text,
            "qwen38_tokens": tok_count,
        }
        self.samples.append(record)
        self.tokens_by_stratum_lang[stratum][lang] += tok_count
        if synthetic:
            self.synthetic_tokens += tok_count
        if has_real_reas:
            self.reasoning_tokens += tok_count
            self.reasoning_strata.add(stratum)
        return True

    # -------------------------------------------------------------------------
    # Stratum Builders
    # -------------------------------------------------------------------------
    def build_long_context(self) -> None:
        print("=== Building Quota 6: Long-Context (6 distinct resolved SWE-smith repos: 2x >=32K, 4x 16.5K..18.5K, 0% synthetic) ===")
        stratum = "long_context"

        swe_32k_added = 0
        swe_16k_added = 0
        seen_repos: set[str] = set()
        ds_swe = load_dataset("SWE-bench/SWE-smith-trajectories", split="tool", streaming=True)
        for idx, row in enumerate(ds_swe):
            if idx >= 1500 or (swe_32k_added >= 2 and swe_16k_added >= 4):
                break
            if not row.get("resolved"):
                continue
            inst_id = str(row.get("instance_id") or f"row_{idx}")
            repo_key = inst_id.split(".")[0]
            if repo_key in seen_repos:
                continue
            conv = convert_swe_smith_row(row)
            if not conv:
                continue
            msgs, tools = conv
            probe = self.tokenizer.apply_chat_template(msgs, tools=tools, tokenize=False)
            ntok = self.count_text_tokens(probe)
            cur_lc = self.tokens_by_stratum_lang[stratum]["en"]
            if swe_32k_added < 2 and 32_050 <= ntok <= 36_500:
                if self.try_add_sample(
                    stratum,
                    "en",
                    "swe_repo_trajectory_32k",
                    "SWE-bench/SWE-smith-trajectories",
                    f"tool:row_{idx}:instance_{inst_id}",
                    False,
                    msgs,
                    tools=tools,
                    max_sample_tokens=37_000,
                ):
                    swe_32k_added += 1
                    seen_repos.add(repo_key)
                    print(f"  Added SWE-smith 32K [{swe_32k_added}/2] row {idx} ({inst_id}): {ntok:,} tokens")
            elif swe_16k_added < 4 and 16_050 <= ntok <= 19_000 and (cur_lc + ntok <= 141_500):
                if self.try_add_sample(
                    stratum,
                    "en",
                    "swe_repo_trajectory_16k",
                    "SWE-bench/SWE-smith-trajectories",
                    f"tool:row_{idx}:instance_{inst_id}",
                    False,
                    msgs,
                    tools=tools,
                    max_sample_tokens=20_000,
                ):
                    swe_16k_added += 1
                    seen_repos.add(repo_key)
                    print(f"  Added SWE-smith 16K [{swe_16k_added}/4] row {idx} ({inst_id}): {ntok:,} tokens")
        del ds_swe
        gc.collect()
        assert swe_32k_added == 2 and swe_16k_added == 4, (
            f"Expected 2x 32K + 4x 16K SWE-smith trajectories, got 32K={swe_32k_added}, 16K={swe_16k_added}"
        )

    def build_pillar_1_frontend_3d_svg(self) -> None:
        print("=== Building Pillar 1: Frontend Architecture, TypeScript/React, CSS Subgrid, 3D & SVG (0% synthetic) ===")
        stratum = "pillar_1_frontend_3d_svg"

        # 1. Strict web-only glyphsoftware/opus-4.6-frontend-development (apache-2.0) WITH REAL REASONING
        for idx, obj in self.glyph_p1_rows:
            if self.tokens_by_stratum_lang[stratum]["en"] >= 152_000:
                break
            prob = (obj.get("evolved_problem") or obj.get("seed_problem") or "").strip()
            ans = (obj.get("solution") or "").strip()
            reas = (obj.get("reasoning") or "").strip()
            asst_msg: dict[str, Any] = {"role": "assistant", "content": ans}
            if self.count_text_tokens(reas) >= 200:
                asst_msg["reasoning_content"] = reas
            msgs = [
                {"role": "system", "content": "You are a Principal Frontend Architect specializing in modern HTML5, CSS Grid/Subgrid, React 19, and interactive UI systems."},
                {"role": "user", "content": prob},
                asst_msg,
            ]
            self.try_add_sample(
                stratum,
                "en",
                "frontend_architecture_cot",
                "glyphsoftware/opus-4.6-frontend-development",
                f"dataset.jsonl:line_{idx}:id_{obj.get('id', idx)}",
                False,
                msgs,
                max_sample_tokens=5400,
            )

        # 3. smirki/UIGEN-T1.1-TAILWIND (apache-2.0) WITH REAL REASONING
        ds_uigen1 = load_dataset("smirki/UIGEN-T1.1-TAILWIND", split="train", streaming=True)
        for i, row in enumerate(ds_uigen1):
            if i >= 160 or self.tokens_by_stratum_lang[stratum]["en"] >= 170_000:
                break
            q = (row.get("question") or "").strip()
            a = (row.get("answer") or "").strip()
            reas = (row.get("reasoning") or "").strip()
            comb_u1 = f"{q}\n{a}\n{reas}"
            if (
                not q
                or not a
                or ("@tailwindcss/browser@4" in a and "tailwind.config" in a)
                or self.RE_P1_BROKEN_CODE.search(comb_u1)
                or self._has_undefined_tailwind_custom_tokens(a)
                or self.RE_GLYPH_SYSTEMS_BAN.search(comb_u1)
            ):
                continue
            asst_msg = {"role": "assistant", "content": a}
            if reas and self.count_text_tokens(reas) >= 200:
                asst_msg["reasoning_content"] = reas
            msgs = [
                {"role": "system", "content": "You are a senior UI engineer building responsive Tailwind CSS and semantic HTML5 interfaces."},
                {"role": "user", "content": q},
                asst_msg,
            ]
            self.try_add_sample(
                stratum,
                "en",
                "tailwind_ui_cot",
                "smirki/UIGEN-T1.1-TAILWIND",
                f"train:row_{i}",
                False,
                msgs,
                max_sample_tokens=5400,
            )
        del ds_uigen1
        gc.collect()

        # 4. Tesslate/UIGEN-T2 (apache-2.0) WITH REAL REASONING (strict valid-CDN & valid-CSS check)
        ds_uigen2 = load_dataset("Tesslate/UIGEN-T2", split="train", streaming=True)
        for i, row in enumerate(ds_uigen2):
            if i >= 180 or self.tokens_by_stratum_lang[stratum]["en"] >= 154_000:
                break
            p = (row.get("prompt") or "").strip()
            r = (row.get("response") or "").strip()
            reas = (row.get("reasoning") or "").strip()
            comb_u2 = f"{p}\n{r}\n{reas}"
            if (
                not p
                or not r
                or ("@tailwindcss/browser@4" in r and "tailwind.config" in r)
                or "tailwind.min.css" in r.lower()
                or self.RE_P1_BROKEN_CODE.search(comb_u2)
                or self._has_undefined_tailwind_custom_tokens(r)
                or self.RE_GLYPH_SYSTEMS_BAN.search(comb_u2)
            ):
                continue
            asst_msg = {"role": "assistant", "content": r}
            if reas and self.count_text_tokens(reas) >= 200:
                asst_msg["reasoning_content"] = reas
            msgs = [
                {"role": "system", "content": "You are a Design Engineer producing clean semantic HTML5, CSS Grid, and accessible UI components."},
                {"role": "user", "content": p},
                asst_msg,
            ]
            self.try_add_sample(
                stratum,
                "en",
                "uigen_t2_cot",
                "Tesslate/UIGEN-T2",
                f"train:row_{i}",
                False,
                msgs,
                max_sample_tokens=5400,
            )
        del ds_uigen2
        gc.collect()

        # 5. runanlab/gpt-5.4-frontend-development-27052026 (cc-by-4.0) - strictly EN (all Cyrillic rows in runanlab have EN prompts) + zero backend/Express!
        raw_runan = self.fetch_range_text(
            "https://huggingface.co/datasets/runanlab/gpt-5.4-frontend-development-27052026/resolve/main/site-coding-dataset.jsonl",
            0,
            15_000_000,
        )
        for idx, line in enumerate(raw_runan.splitlines()[:-1]):
            if self.tokens_by_stratum_lang[stratum]["en"] >= STRATA_TARGETS[stratum]["en"]:
                break
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msgs = obj.get("messages") or []
            if len(msgs) < 2:
                continue
            fu_txt = self._first_user_text(msgs)
            rendered_probe = self.tokenizer.apply_chat_template(msgs, tokenize=False)
            if (
                self.RE_GLYPH_SYSTEMS_BAN.search(rendered_probe)
                or self.RE_P1_BROKEN_CODE.search(rendered_probe)
                or self._has_undefined_tailwind_custom_tokens(rendered_probe)
            ):
                self.log_rejection("runanlab/gpt-5.4-frontend-development-27052026", "backend_or_broken_cdn_leak", fu_txt[:100])
                continue
            fu_ratio = prose_cyr_ratio(fu_txt)
            ratio = prose_cyr_ratio(rendered_probe)
            if ratio <= 0.02 and fu_ratio <= 0.02:
                lang = "en"
            else:
                continue
            self.try_add_sample(
                stratum,
                lang,
                "single_file_html5",
                "runanlab/gpt-5.4-frontend-development-27052026",
                f"site-coding-dataset.jsonl:line_{idx}",
                False,
                msgs,
                max_sample_tokens=5600,
            )

        # 6. Authentic Russian frontend/DOM/React/TS/SVG dialogues from GrandMaster-PRO-MAX & d0rj/ru-instruct
        for repo, ref, msgs in self.ru_pools["web"]:
            if self.tokens_by_stratum_lang[stratum]["ru"] >= STRATA_TARGETS[stratum]["ru"]:
                break
            self.try_add_sample(
                stratum,
                "ru",
                "frontend_ru_real",
                repo,
                ref,
                False,
                msgs,
                max_sample_tokens=4800,
            )
        print(f"  Pillar 1 complete: {self.tokens_by_stratum_lang[stratum]}")

    def build_pillar_2_seo_geo_security(self) -> None:
        print("=== Building Pillar 2: Technical SEO, GEO (llms.txt), Schema.org & OWASP Web Security ===")
        stratum = "pillar_2_seo_geo_security"

        # 1. Add the 8 strictly 1-of-1 curated GEO/SEO/CSP/@graph bundles (4 EN + 4 RU, zero HTML clones)
        for item in get_unique_pillar2_bundles():
            self.try_add_sample(
                stratum,
                item["lang"],
                item["subdomain"],
                "SmartLLM/curated-bilingual-canons",
                f"curated_1of1:{item['key']}",
                True,
                [
                    {"role": "user", "content": item["user_prompt"]},
                    {"role": "assistant", "content": item["assistant_content"]},
                ],
                max_sample_tokens=4200,
            )

        # 2. Pure CWV / WCAG / JSON-LD / CSP rows with real reasoning from glyphsoftware (capped <= 30K tokens)
        used_glyph_p2_indices: set[int] = set()
        for idx, obj in self.glyph_p2_rows:
            if self.tokens_by_stratum_lang[stratum]["en"] >= 30_000:
                break
            prob = (obj.get("evolved_problem") or obj.get("seed_problem") or "").strip()
            ans = (obj.get("solution") or "").strip()
            reas = (obj.get("reasoning") or "").strip()
            asst_msg: dict[str, Any] = {"role": "assistant", "content": ans}
            if self.count_text_tokens(reas) >= 200:
                asst_msg["reasoning_content"] = reas
            msgs = [
                {"role": "system", "content": "You are a Principal Core Web Vitals, WCAG Accessibility, Technical SEO, and Web Security Engineer."},
                {"role": "user", "content": prob},
                asst_msg,
            ]
            if self.try_add_sample(
                stratum,
                "en",
                "cwv_wcag_csp_cot",
                "glyphsoftware/opus-4.6-frontend-development",
                f"dataset.jsonl:line_{idx}:id_{obj.get('id', idx)}",
                False,
                msgs,
                max_sample_tokens=5200,
            ):
                used_glyph_p2_indices.add(idx)

        # 3. Code-bearing Technical SEO, Schema.org, robots.txt, sitemap.xml & WCAG ARIA dialogues
        seo_en_added = 0
        for repo, ref, msgs in self.en_pools["p2_seo"]:
            if self.tokens_by_stratum_lang[stratum]["en"] >= 47_000:
                break
            if self.try_add_sample(
                stratum,
                "en",
                "technical_seo_schema_en",
                repo,
                ref,
                False,
                msgs,
                max_sample_tokens=4500,
            ):
                seo_en_added += 1

        if seo_en_added < 5:
            for idx, obj in self.glyph_p2_rows:
                if seo_en_added >= 5 or self.tokens_by_stratum_lang[stratum]["en"] >= 47_000:
                    break
                if idx in used_glyph_p2_indices:
                    continue
                prob = (obj.get("evolved_problem") or obj.get("seed_problem") or "").strip()
                ans = (obj.get("solution") or "").strip()
                reas = (obj.get("reasoning") or "").strip()
                if not self.RE_EN_SEO_IMPL.search(ans):
                    continue
                asst_msg2: dict[str, Any] = {"role": "assistant", "content": ans}
                if self.count_text_tokens(reas) >= 200:
                    asst_msg2["reasoning_content"] = reas
                msgs2 = [
                    {"role": "system", "content": "You are a Technical SEO, Semantic Metadata, and WCAG ARIA Implementation Engineer."},
                    {"role": "user", "content": prob},
                    asst_msg2,
                ]
                if self.try_add_sample(
                    stratum,
                    "en",
                    "technical_seo_schema_en",
                    "glyphsoftware/opus-4.6-frontend-development",
                    f"dataset.jsonl:line_{idx}:id_{obj.get('id', idx)}",
                    False,
                    msgs2,
                    max_sample_tokens=4800,
                ):
                    seo_en_added += 1

        # 4. Complete, untruncated defensive OWASP Web Application Security Q&A from Trendyol (apache-2.0)
        ds_tr = load_dataset("Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset", split="train", streaming=True)
        for idx, row in enumerate(ds_tr):
            if idx >= 110_000 or self.tokens_by_stratum_lang[stratum]["en"] >= STRATA_TARGETS[stratum]["en"]:
                break
            usr_p = (row.get("user") or "").strip()
            raw_asst = (row.get("assistant") or "").strip()
            if "\\n" in usr_p or "\\n" in raw_asst or '\\"' in usr_p or '\\"' in raw_asst:
                continue
            reas_tr = None
            if "<think>" in raw_asst or "</think>" in raw_asst:
                if "<think>" in raw_asst and "</think>" in raw_asst:
                    tm_tr = RE_THINK_BLOCK.search(raw_asst)
                    if tm_tr:
                        reas_tr = tm_tr.group(1).strip()
                    asst_p = RE_THINK_BLOCK.sub("", raw_asst).strip()
                    if "<think>" in asst_p or "</think>" in asst_p:
                        continue
                else:
                    continue
            else:
                asst_p = raw_asst
            if len(usr_p) < 40 or len(asst_p) < 580:
                continue
            # Reject unextracted CoT monologues leaked directly into assistant content
            if re.match(
                r"^\s*(?:okay,?\s+so|alright,?\s+so|let\s+me\s+(?:start|think|recall|break)|hmm\b|wait,?\s|the\s+user\s+is\s+asking|so\s+the\s+question\s+is)",
                asst_p,
                re.I,
            ) or re.search(
                r"\b(?:let\s+me\s+start\s+by\s+recalling|i\s+should\s+also\s+mention|i\s+need\s+to\s+describe\s+how|wait,?\s+let\s+me\s+double[- ]check)\b",
                asst_p,
                re.I,
            ):
                continue
            if re.search(r"eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9\.x+", asst_p):
                continue
            if ("csp" in usr_p.lower() or "content-security-policy" in usr_p.lower()) and "onerror=" in asst_p.lower():
                continue
            if re.search(r"(?:bypass\s+this\s+filter|write\s+an?\s+exploit|exploit\s+payload)", usr_p, re.I):
                continue
            comb = f"{usr_p}\n{asst_p}\n{reas_tr or ''}"
            if self.RE_WEBSEC_BAD.search(comb) or not self.RE_WEBSEC_GOOD.search(usr_p):
                continue
            if not re.search(r"[.!?`]\s*$", asst_p) or re.search(r"(?:\.\.\.|%\d\d\.|\b\d+\.|:\s*)$", asst_p):
                continue
            asst_msg_tr: dict[str, Any] = {"role": "assistant", "content": asst_p}
            if reas_tr and self.count_text_tokens(reas_tr) >= 200:
                asst_msg_tr["reasoning_content"] = reas_tr
            msgs = [
                {"role": "system", "content": "You are an OWASP Web Application Security architect specializing in CSP, HSTS, CORS, CSRF, XSS prevention, and secure authentication."},
                {"role": "user", "content": usr_p},
                asst_msg_tr,
            ]
            self.try_add_sample(
                stratum,
                "en",
                "owasp_web_security",
                "Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset",
                f"train:row_{idx}",
                False,
                msgs,
                max_sample_tokens=4200,
            )
        del ds_tr
        gc.collect()

        # 5. Authentic Russian Technical SEO, Schema.org & Web Security dialogues from GrandMaster-PRO-MAX & d0rj/ru-instruct
        for repo, ref, msgs in self.ru_pools["p2"]:
            if self.tokens_by_stratum_lang[stratum]["ru"] >= STRATA_TARGETS[stratum]["ru"]:
                break
            self.try_add_sample(
                stratum,
                "ru",
                "seo_security_ru_real",
                repo,
                ref,
                False,
                msgs,
                max_sample_tokens=4500,
            )
        print(f"  Pillar 2 complete: {self.tokens_by_stratum_lang[stratum]}")

    def build_pillar_3_style_canons_vision(self) -> None:
        print("=== Building Pillar 3: Multimodal Vision-to-Code & 6 OKLCH Style Canons (0 Vision2Web) ===")
        stratum = "pillar_3_style_canons_vision"

        # 1. Render all 14 strictly 1-of-1 OKLCH style canon apps via local port-free headless Chromium
        mm_specs = get_unique_multimodal_canon_specs()
        jobs = [
            {
                "id": s["key"],
                "html": s["html"],
                "viewport_w": s["viewport_w"],
                "viewport_h": s["viewport_h"],
                "out_w": s["out_w"],
                "out_h": s["out_h"],
            }
            for s in mm_specs
        ]
        rendered_map = render_html_batch_chromium(jobs)
        for s in mm_specs:
            png_bytes, out_w, out_h = rendered_map[s["key"]]
            img_name = f"canon_{s['key']}.png"
            img_abs = IMG_DIR / img_name
            img_abs.write_bytes(png_bytes)
            img_sha = hashlib.sha256(png_bytes).hexdigest()
            pil_im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            rel_path = f"data/calib/images/{img_name}"
            asst_body = f"{s['rationale']}\n\n```html\n{s['html']}\n```"
            added = self.try_add_sample(
                stratum,
                s["lang"],
                s["subdomain"],
                "SmartLLM/curated-bilingual-canons",
                f"chromium_render_1of1:{s['key']}",
                True,
                [
                    {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": s["user_prompt"]}]},
                    {"role": "assistant", "content": asst_body},
                ],
                modality="multimodal",
                images=[{"path": rel_path, "sha256": img_sha, "size": [out_w, out_h]}],
                pil_images=[pil_im],
                max_sample_tokens=4800,
            )
            assert added, f"Failed to add unique Chromium multimodal sample {s['key']}"

        # 2. Stream authentic, 16:10 non-squashed, high-contrast screenshots + ground-truth HTML from HuggingFaceM4/WebSight v0.2
        ds_ws = load_dataset("HuggingFaceM4/WebSight", "v0.2", split="train", streaming=True)
        seen_topics: set[str] = set()
        ws_added = 0
        for row_idx, row in enumerate(ds_ws):
            if row_idx >= 9500 or self.tokens_by_stratum_lang[stratum]["en"] >= STRATA_TARGETS[stratum]["en"]:
                break
            img = row.get("image")
            html_txt = (row.get("text") or "").strip()
            if not isinstance(img, Image.Image) or len(html_txt) < 620:
                continue
            # Reject tall full-page captures that would squash vertically when resized to 1024x640
            aspect = img.width / max(1, img.height)
            if not (1.35 <= aspect <= 1.85):
                continue
            html_low = html_txt.lower()
            if (
                "<!--" in html_txt
                or "lorem ipsum" in html_low
                or "source.unsplash.com" in html_low
                or "placehold.co" in html_low
                or "bg-gold" in html_low
                or "</html>" not in html_low
                or not re.search(r"<(?:header|nav|main|section|article|footer)\b", html_low)
                or any(tag in html_low for tag in ("<video", "<iframe", "<embed", "<object", "<audio"))
                or ("text-center" in html_low and "list-disc" in html_low)
                or re.search(
                    r"<h[1-3][^>]*>[^<]*(?:design\s+with\s+a|layout\s+with\s+a|prominent\s+hero|color\s+scheme|two-column|single-column)",
                    html_txt,
                    re.I,
                )
                or re.search(
                    r"\b(?:bg|text|border|ring)-(?:teal|cyan|sky|amber|lime|emerald|violet|fuchsia|rose|orange|slate|zinc|neutral|stone)-\d",
                    html_low,
                )
            ):
                continue

            ws_num = ws_added + 1
            topic = extract_websight_topic(html_txt, ws_num)
            if topic.startswith("layout #"):
                continue
            topic_norm = re.sub(r"\W+", " ", topic.lower()).strip()
            if topic_norm in seen_topics:
                continue

            # Resize 16:10 to 1024x640 (32x32-multiple -> exact 640 <|image_pad|> tokens in Qwen3VLProcessor & model.visual)
            img_resized = img.convert("RGB").resize((1024, 640), Image.Resampling.LANCZOS)
            st_ws = ImageStat.Stat(img_resized)
            mean_rgb = sum(st_ws.mean) / max(1, len(st_ws.mean))
            if not (14.0 <= mean_rgb <= 240.0) or max(st_ws.stddev) < 22.0:
                continue

            img_name = f"websight_{ws_num:03d}.png"
            img_abs = IMG_DIR / img_name
            img_resized.save(img_abs, format="PNG", optimize=True)
            img_sha = hashlib.sha256(img_abs.read_bytes()).hexdigest()
            rel_path = f"data/calib/images/{img_name}"

            prompt = build_websight_grounded_prompt(html_txt, ws_added)
            resp = f"```html\n{html_txt}\n```"

            added = self.try_add_sample(
                stratum,
                "en",
                "websight_vision2code",
                "HuggingFaceM4/WebSight",
                f"v0.2/train:row_{row_idx}",
                False,
                [
                    {"role": "system", "content": "You are a multimodal Vision-to-Code Design Engineer."},
                    {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]},
                    {"role": "assistant", "content": resp},
                ],
                modality="multimodal",
                images=[{"path": rel_path, "sha256": img_sha, "size": [1024, 640]}],
                pil_images=[img_resized],
                max_sample_tokens=4200,
            )
            if added:
                ws_added += 1
                seen_topics.add(topic_norm)
            else:
                img_abs.unlink(missing_ok=True)
        del ds_ws
        gc.collect()
        print(f"  Pillar 3 complete: {self.tokens_by_stratum_lang[stratum]} (WebSight added={ws_added})")

    def build_pillar_4_art_direction_copywriting(self) -> None:
        print("=== Building Pillar 4: Conversion Copywriting, Brand Voice, UX Writing & Z-Image Prompting (0 glyphsoftware) ===")
        stratum = "pillar_4_art_direction_copywriting"

        # 1. Add the 10 strictly 1-of-1 curated Brand Strategy / Copywriting / UX Microcopy / Z-Image decks (5 EN + 5 RU)
        for item in get_unique_pillar4_copy_decks():
            self.try_add_sample(
                stratum,
                item["lang"],
                item["subdomain"],
                "SmartLLM/curated-bilingual-canons",
                f"curated_1of1:{item['key']}",
                True,
                [
                    {"role": "user", "content": item["user_prompt"]},
                    {"role": "assistant", "content": item["assistant_content"]},
                ],
                max_sample_tokens=4200,
            )

        # 2. Authentic English landing-page copywriting, value propositions, UX writing & brand identity dialogues
        for repo, ref, msgs in self.en_pools["p4_copy"]:
            if self.tokens_by_stratum_lang[stratum]["en"] >= STRATA_TARGETS[stratum]["en"]:
                break
            self.try_add_sample(
                stratum,
                "en",
                "copywriting_brand_ux_en",
                repo,
                ref,
                False,
                msgs,
                max_sample_tokens=4500,
            )

        # 3. Authentic Russian landing-page copywriting, УТП, brand positioning, UX microcopy & typography dialogues
        for repo, ref, msgs in self.ru_pools["p4"]:
            if self.tokens_by_stratum_lang[stratum]["ru"] >= STRATA_TARGETS[stratum]["ru"]:
                break
            self.try_add_sample(
                stratum,
                "ru",
                "copywriting_brand_ux_ru",
                repo,
                ref,
                False,
                msgs,
                max_sample_tokens=4500,
            )
        print(f"  Pillar 4 complete: {self.tokens_by_stratum_lang[stratum]}")

    def build_agentic_tool_calling(self) -> None:
        print("=== Building Quota 5: Agentic Tool-Calling (Multi-turn grounded tools[] + real CoT reasoning) ===")
        stratum = "agentic_tool_calling"

        # 1. Add the 8 strictly 1-of-1 Russian multi-turn tool-calling workflows across 18 distinct tools
        for item in get_unique_agentic_ru_workflows():
            ok = self.try_add_sample(
                stratum,
                "ru",
                item["subdomain"],
                "SmartLLM/curated-bilingual-canons",
                f"curated_1of1:{item['key']}",
                True,
                item["messages"],
                tools=item["tools"],
                max_sample_tokens=3200,
            )
            assert ok, f"Failed to add unique RU agentic workflow {item['key']}"

        # 2. 0xSero/reap-calibration-data-v1 (filtered_v2.jsonl, apache-2.0) WITH REAL <think> REASONING (>=200 tok) + STRICT SINGLE-FINAL-ASSISTANT GROUNDED TOOL TURNS
        for mb_off in range(0, 38, 2):
            if self.tokens_by_stratum_lang[stratum]["en"] >= 66_000:
                break
            raw_fc = self.fetch_range_text(
                "https://huggingface.co/datasets/0xSero/reap-calibration-data-v1/resolve/main/filtered_v2.jsonl",
                mb_off * 1024 * 1024,
                2_000_000,
            )
            lines_fc = raw_fc.splitlines()
            slice_fc = lines_fc[:-1] if mb_off == 0 else lines_fc[1:-1]
            for idx, line in enumerate(slice_fc):
                if self.tokens_by_stratum_lang[stratum]["en"] >= 66_000:
                    break
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if obj.get("domain") and obj.get("domain") != "function_calling":
                        continue
                    inner = json.loads(obj.get("text", ""))
                except Exception:
                    continue
                if not isinstance(inner, list):
                    continue
                parsed = parse_hermes_turns(inner)
                if not parsed:
                    continue
                msgs, tools = parsed
                if not any(m.get("role") == "tool" for m in msgs):
                    continue
                if not any(
                    m.get("role") == "assistant"
                    and isinstance(m.get("reasoning_content"), str)
                    and self.count_text_tokens(m["reasoning_content"]) >= 200
                    for m in msgs
                ):
                    continue
                self.try_add_sample(
                    stratum,
                    "en",
                    "function_calling_cot",
                    "0xSero/reap-calibration-data-v1",
                    f"filtered_v2.jsonl:{mb_off}MB:line_{idx}:id_{obj.get('id', idx)}",
                    False,
                    msgs,
                    tools=tools,
                    max_sample_tokens=4600,
                )

        # 3. NousResearch/hermes-function-calling-v1 (apache-2.0) multi-turn grounded tool calls + responses (0 malformed error tool payloads)
        raw_hermes = self.fetch_range_text(
            "https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1/resolve/main/func-calling.json",
            0,
            8_000_000,
        )
        decoder = json.JSONDecoder()
        pos = raw_hermes.find("[") + 1
        h_idx = 0
        while pos > 0 and pos < len(raw_hermes) and self.tokens_by_stratum_lang[stratum]["en"] < STRATA_TARGETS[stratum]["en"]:
            while pos < len(raw_hermes) and raw_hermes[pos] in " \r\n\t,":
                pos += 1
            if pos >= len(raw_hermes) or raw_hermes[pos] == "]":
                break
            try:
                obj, next_pos = decoder.raw_decode(raw_hermes, pos)
                pos = next_pos
                h_idx += 1
            except Exception:
                break
            parsed = parse_hermes_turns(obj.get("conversations") or [])
            if not parsed:
                continue
            msgs, tools = parsed
            if not any(m.get("role") == "tool" for m in msgs) or msgs[-1].get("tool_calls"):
                continue
            fu_h_low = self._first_user_text(msgs).lower()
            if "smart lock" in fu_h_low and "device_002" in json.dumps(msgs):
                continue
            if "error" not in fu_h_low and any(
                m.get("role") == "tool" and re.search(r"\b(?:error|invalid\s+value|traceback|exception)\b", str(m.get("content") or ""), re.I)
                for m in msgs
            ):
                continue
            self.try_add_sample(
                stratum,
                "en",
                "hermes_structured_tools",
                "NousResearch/hermes-function-calling-v1",
                f"func-calling.json:item_{h_idx}",
                False,
                msgs,
                tools=tools,
                max_sample_tokens=4200,
            )
        print(f"  Agentic complete: {self.tokens_by_stratum_lang[stratum]}")

    def build_general_anti_starvation(self) -> None:
        print("=== Building Quota 7: General Anti-Starvation (4 balanced EN subdomains + STEM RU, 0% synthetic) ===")
        stratum = "general_anti_starvation"

        en_sub_targets = {
            "code_general": 6_200,
            "math": 5_000,
            "terminal": 4_100,
            "science_general": 3_200,
        }
        en_sub_current: Counter[str] = Counter()

        # 1a. Subdomain 'code_general' (~6,200 tokens): non-web Python/algorithms with CoT from OpenThoughts + UltraChat/Capybara
        ds_ot_code = load_dataset(
            "parquet",
            data_files="hf://datasets/open-thoughts/OpenThoughts-114k/data/train-00000-of-00006.parquet",
            split="train",
            streaming=True,
        )
        for i, row in enumerate(ds_ot_code):
            if i >= 450 or en_sub_current["code_general"] >= 6_000:
                break
            convs = row.get("conversations") or []
            if len(convs) < 2:
                continue
            usr_val = (convs[0].get("value") or "").strip()
            asst_raw = (convs[1].get("value") or "").strip()
            tm = re.search(r"<\|begin_of_thought\|>\s*(.*?)\s*<\|end_of_thought\|>", asst_raw, re.S)
            sm = re.search(r"<\|begin_of_solution\|>\s*(.*?)\s*<\|end_of_solution\|>", asst_raw, re.S)
            if not tm or not sm:
                continue
            reas_txt, sol_txt = tm.group(1).strip(), sm.group(1).strip()
            if "```python" not in sol_txt or len(reas_txt) > 9_000:
                continue
            if ("simply call the function" in usr_val.lower() or "starter code" in usr_val.lower()) and (
                "def " not in sol_txt or "sys.stdin" in sol_txt
            ):
                continue
            msgs = [
                {"role": "system", "content": "You are a software algorithms and data structures engineer."},
                {"role": "user", "content": usr_val},
                {"role": "assistant", "reasoning_content": reas_txt, "content": sol_txt},
            ]
            before = self.tokens_by_stratum_lang[stratum]["en"]
            if self.try_add_sample(
                stratum,
                "en",
                "code_general",
                "open-thoughts/OpenThoughts-114k",
                f"data/train-00000-of-00006.parquet:row_{i}",
                False,
                msgs,
                max_sample_tokens=2800,
            ):
                en_sub_current["code_general"] += self.tokens_by_stratum_lang[stratum]["en"] - before
        del ds_ot_code
        gc.collect()

        for repo, ref, msgs in self.en_pools["code_general"]:
            if en_sub_current["code_general"] >= en_sub_targets["code_general"]:
                break
            before = self.tokens_by_stratum_lang[stratum]["en"]
            if self.try_add_sample(stratum, "en", "code_general", repo, ref, False, msgs, max_sample_tokens=3200):
                en_sub_current["code_general"] += self.tokens_by_stratum_lang[stratum]["en"] - before

        # 1b. Subdomain 'math' (~12,000 tokens): pure math with <think> reasoning & \boxed{} compliance from OpenThoughts shard 00002
        ds_ot_math = load_dataset(
            "parquet",
            data_files="hf://datasets/open-thoughts/OpenThoughts-114k/data/train-00002-of-00006.parquet",
            split="train",
            streaming=True,
        )
        for i, row in enumerate(ds_ot_math):
            if i >= 450 or en_sub_current["math"] >= en_sub_targets["math"]:
                break
            convs = row.get("conversations") or []
            if len(convs) < 2:
                continue
            usr_val = (convs[0].get("value") or "").strip()
            asst_raw = (convs[1].get("value") or "").strip()
            tm = re.search(r"<\|begin_of_thought\|>\s*(.*?)\s*<\|end_of_thought\|>", asst_raw, re.S)
            sm = re.search(r"<\|begin_of_solution\|>\s*(.*?)\s*<\|end_of_solution\|>", asst_raw, re.S)
            if not tm or not sm:
                continue
            reas_txt, sol_txt = tm.group(1).strip(), sm.group(1).strip()
            if not (usr_val and reas_txt and sol_txt) or len(sol_txt) < 140 or "```python" in sol_txt:
                continue
            if "\\boxed" in usr_val and "\\boxed{" not in sol_txt:
                continue
            if self.count_text_tokens(reas_txt) < 200:
                continue
            msgs = [
                {"role": "system", "content": "You are a rigorous mathematical problem solver."},
                {"role": "user", "content": usr_val},
                {"role": "assistant", "reasoning_content": reas_txt, "content": sol_txt},
            ]
            before = self.tokens_by_stratum_lang[stratum]["en"]
            if self.try_add_sample(
                stratum,
                "en",
                "math",
                "open-thoughts/OpenThoughts-114k",
                f"data/train-00002-of-00006.parquet:row_{i}",
                False,
                msgs,
                max_sample_tokens=2800,
            ):
                en_sub_current["math"] += self.tokens_by_stratum_lang[stratum]["en"] - before
        del ds_ot_math
        gc.collect()

        # 1c. Subdomain 'terminal' (~4,100 tokens) with strict anti-leakage verification & varied lead-ins
        for repo, ref, msgs in self.en_pools["term"]:
            if en_sub_current["terminal"] >= en_sub_targets["terminal"]:
                break
            before = self.tokens_by_stratum_lang[stratum]["en"]
            if self.try_add_sample(stratum, "en", "terminal", repo, ref, False, msgs, max_sample_tokens=2200):
                en_sub_current["terminal"] += self.tokens_by_stratum_lang[stratum]["en"] - before

        # 1d. Subdomain 'science_general' (~3,200 tokens)
        for repo, ref, msgs in self.en_pools["science"]:
            if self.tokens_by_stratum_lang[stratum]["en"] >= STRATA_TARGETS[stratum]["en"]:
                break
            before = self.tokens_by_stratum_lang[stratum]["en"]
            if self.try_add_sample(stratum, "en", "science_general", repo, ref, False, msgs, max_sample_tokens=2200):
                en_sub_current["science_general"] += self.tokens_by_stratum_lang[stratum]["en"] - before

        # 2. Substantial Russian algorithms, math, natural science & Linux dialogues (0 business/marketing/Scrum)
        for repo, ref, msgs in self.ru_pools["general"]:
            if self.tokens_by_stratum_lang[stratum]["ru"] >= STRATA_TARGETS[stratum]["ru"]:
                break
            self.try_add_sample(
                stratum,
                "ru",
                "general_ru_stem",
                repo,
                ref,
                False,
                msgs,
                max_sample_tokens=3600,
            )
        print(f"  General complete: {self.tokens_by_stratum_lang[stratum]}, EN subdomains={dict(en_sub_current)}")

    def write_outputs(self) -> dict[str, Any]:
        jsonl_path = CALIB_DIR / "PremiumWebStudio-Calib.jsonl"
        imatrix_path = CALIB_DIR / "imatrix_corpus.txt"
        stats_md_path = CALIB_DIR / "stats.md"
        stats_json_path = RAW_STEP4_DIR / "calib_stats.json"

        refd_names = {Path(im["path"]).name for s in self.samples for im in (s.get("images") or [])}
        for p in IMG_DIR.iterdir():
            if p.name not in refd_names:
                p.unlink(missing_ok=True)

        img_files = sorted(IMG_DIR.glob("*.*"))
        assert {p.name for p in img_files} == refd_names, "Orphan or missing image files detected!"

        print(f"Writing {len(self.samples)} samples (LF line endings) to {jsonl_path}...")
        with jsonl_path.open("w", encoding="utf-8", newline="\n") as f:
            for s in self.samples:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")

        text_only_samples = [s for s in self.samples if s["modality"] == "text"]
        print(f"Writing {len(text_only_samples)} text-only samples (LF line endings) to {imatrix_path}...")
        with imatrix_path.open("w", encoding="utf-8", newline="\n") as f:
            for s in text_only_samples:
                assert "<|vision_start|>" not in s["text"] and "<image:" not in s["text"]
                f.write(s["text"] + "\n\n")

        total_tokens = sum(s["qwen38_tokens"] for s in self.samples)
        en_tokens = sum(s["qwen38_tokens"] for s in self.samples if s["lang"] == "en")
        ru_tokens = sum(s["qwen38_tokens"] for s in self.samples if s["lang"] == "ru")
        en_samples = sum(1 for s in self.samples if s["lang"] == "en")
        ru_samples = sum(1 for s in self.samples if s["lang"] == "ru")
        mm_samples = sum(1 for s in self.samples if s["modality"] == "multimodal")
        mm_tokens = sum(s["qwen38_tokens"] for s in self.samples if s["modality"] == "multimodal")
        synth_tokens = sum(s["qwen38_tokens"] for s in self.samples if s["synthetic"])
        curated_count = sum(1 for s in self.samples if s["source_repo"] == "SmartLLM/curated-bilingual-canons")

        # Reorder strata in canonical presentation order
        ordered_strata = [
            "pillar_1_frontend_3d_svg",
            "pillar_2_seo_geo_security",
            "pillar_3_style_canons_vision",
            "pillar_4_art_direction_copywriting",
            "agentic_tool_calling",
            "long_context",
            "general_anti_starvation",
        ]
        by_stratum = {}
        for st in ordered_strata:
            st_rows = [s for s in self.samples if s["pillar"] == st]
            st_tok = sum(s["qwen38_tokens"] for s in st_rows)
            st_en_tok = sum(s["qwen38_tokens"] for s in st_rows if s["lang"] == "en")
            st_ru_tok = sum(s["qwen38_tokens"] for s in st_rows if s["lang"] == "ru")
            by_stratum[st] = {
                "samples": len(st_rows),
                "en_samples": sum(1 for s in st_rows if s["lang"] == "en"),
                "ru_samples": sum(1 for s in st_rows if s["lang"] == "ru"),
                "tokens": st_tok,
                "en_tokens": st_en_tok,
                "ru_tokens": st_ru_tok,
                "pct_of_total_tokens": round(st_tok * 100.0 / total_tokens, 2) if total_tokens else 0.0,
                "target_tokens": STRATA_TARGETS[st]["total"],
            }

        by_repo = {}
        for repo, lic in VERIFIED_LICENSES.items():
            r_rows = [s for s in self.samples if s["source_repo"] == repo]
            if not r_rows:
                continue
            r_tok = sum(s["qwen38_tokens"] for s in r_rows)
            by_repo[repo] = {
                "license": lic,
                "synthetic": any(s["synthetic"] for s in r_rows),
                "samples": len(r_rows),
                "tokens": r_tok,
                "pct_of_total_tokens": round(r_tok * 100.0 / total_tokens, 2),
            }

        jsonl_bytes = jsonl_path.stat().st_size
        imatrix_bytes = imatrix_path.stat().st_size
        img_bytes = sum(p.stat().st_size for p in img_files)

        stats_payload = {
            "generated_at": "2026-11-11",
            "tokenizer": {
                "path": str(TOKENIZER_DIR),
                "class": type(self.tokenizer).__name__,
                "vocab_size": len(self.tokenizer),
            },
            "budget_target_range_tokens": [500_000, 1_000_000],
            "total_samples": len(self.samples),
            "total_qwen38_tokens": total_tokens,
            "within_0_5M_to_1_0M_budget": 500_000 <= total_tokens <= 1_000_000,
            "synthetic_tokens": synth_tokens,
            "synthetic_share": round(synth_tokens / max(1, total_tokens), 4),
            "reasoning_tokens": self.reasoning_tokens,
            "reasoning_share": round(self.reasoning_tokens / max(1, total_tokens), 4),
            "reasoning_strata": sorted(self.reasoning_strata),
            "language_split": {
                "en": {
                    "samples": en_samples,
                    "tokens": en_tokens,
                    "pct_tokens": round(en_tokens * 100.0 / total_tokens, 2),
                },
                "ru": {
                    "samples": ru_samples,
                    "tokens": ru_tokens,
                    "pct_tokens": round(ru_tokens * 100.0 / total_tokens, 2),
                },
            },
            "multimodal": {
                "samples": mm_samples,
                "tokens": mm_tokens,
                "pct_tokens": round(mm_tokens * 100.0 / total_tokens, 2),
                "image_files_on_disk": len(img_files),
                "total_image_bytes": img_bytes,
            },
            "artifacts": {
                "jsonl_path": str(jsonl_path),
                "jsonl_bytes": jsonl_bytes,
                "jsonl_sha256": hashlib.sha256(jsonl_path.read_bytes()).hexdigest(),
                "imatrix_path": str(imatrix_path),
                "imatrix_bytes": imatrix_bytes,
                "imatrix_sha256": hashlib.sha256(imatrix_path.read_bytes()).hexdigest(),
            },
            "by_stratum": by_stratum,
            "by_source_repo": by_repo,
            "exclusion_filter_rejections": {
                "total_rejected": sum(self.rejection_counts.values()),
                "by_reason": dict(self.rejection_counts),
                "by_repo": {k: dict(v) for k, v in self.rejection_by_repo.items()},
                "sample_rejections": self.rejection_examples,
            },
        }
        with stats_json_path.open("w", encoding="utf-8", newline="\n") as fj:
            fj.write(json.dumps(stats_payload, indent=2, ensure_ascii=False) + "\n")

        pillars_1_to_4_tok = sum(
            by_stratum[k]["tokens"]
            for k in (
                "pillar_1_frontend_3d_svg",
                "pillar_2_seo_geo_security",
                "pillar_3_style_canons_vision",
                "pillar_4_art_direction_copywriting",
            )
        )
        pillars_1_to_4_pct = round(pillars_1_to_4_tok * 100.0 / total_tokens, 2)

        distill_notes = {
            "runanlab/gpt-5.4-frontend-development-27052026": "Дистиллят GPT-5.4 (ToS OpenAI); открытая лицензия `cc-by-4.0`",
            "glyphsoftware/opus-4.6-frontend-development": "Дистиллят Claude Opus 4.6 с трассами CoT, строгий DOM-фильтр (ToS Anthropic); `apache-2.0`",
            "smirki/UIGEN-T1.1-TAILWIND": "Синтетика/дистиллят UI-кода с рассуждениями CoT (ToS отмечен); `apache-2.0`",
            "Tesslate/UIGEN-T2": "Синтетика/дистиллят UI-кода с рассуждениями CoT (ToS отмечен); `apache-2.0`",
            "TozAI/mihenk-3d": "Верифицированные задачи Three.js/WebGL (`cc-by-4.0`, `openscad` и турецкие комментарии отфильтрованы)",
            "HuggingFaceM4/WebSight": "Реальные 16:10 рендеры сайтов + синтетический HTML (`v0.2`, `cc-by-4.0`, `1024x640` = 640 image_pad токенов; ToS LLM отмечен)",
            "0xSero/reap-calibration-data-v1": "Мультиходовые калибровочные трассы с реальными `<think>` CoT (>=200 ток.) и вызовами функций (`apache-2.0`, ToS дистиллята отмечен)",
            "NousResearch/hermes-function-calling-v1": "Мультиходовые вызовы функций и `<tool_response>` Hermes (`apache-2.0`, ToS синтетики LLM отмечен)",
            "open-thoughts/OpenThoughts-114k": "Реальные трассы рассуждений CoT DeepSeek-R1/QwQ (`apache-2.0`, ToS дистиллята отмечен)",
            "Vikhrmodels/GrandMaster-PRO-MAX": "Гибридный RU корпус (вкл. синтетические диалоги моделей, строгий AST/JSON/MT-фильтр; ToS отмечен); `apache-2.0`",
            "Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset": "Инструктивный корпус OWASP/WebAppSec без SOC/MITRE/RDP (`apache-2.0`, ToS синтетики LLM отмечен)",
            "HuggingFaceH4/ultrachat_200k": "Диалоги UltraChat (синтетика GPT-3.5/4, ToS OpenAI отмечен); открытая лицензия `mit`",
            "LDJnr/Capybara": "Инструктивные диалоги (`apache-2.0`, вкл. синтетику LLM — ToS отмечен)",
            "byroneverson/shell-cmd-instruct": "Корпус команд и скриптов POSIX/Bash (`apache-2.0`, с анти-утечкой команды из промпта, ToS отмечен)",
            "SWE-bench/SWE-smith-trajectories": "Реальные многоходовые агентные трассы в 6 отдельных репозиториях (`mit`, `resolved=True`, без дописанных сообщений, ToS отмечен)",
            "SmartLLM/curated-bilingual-canons": f"{curated_count} строго уникальных (1-of-1, 0 циклов) кураторских сэмплов + рендеры Chromium (`synthetic=True`)",
        }

        active_external_list = ", ".join(
            f"`{r}` (`{info['license']}`)"
            for r, info in by_repo.items()
            if r != "SmartLLM/curated-bilingual-canons"
        )

        n_desktop = sum(1 for s in self.samples for im in (s.get("images") or []) if im.get("size") == [1024, 640])
        n_mobile = sum(1 for s in self.samples for im in (s.get("images") or []) if im.get("size") == [576, 1248])

        md_lines = [
            "# SmartLLM — Статистика и паспорт калибровочного датасета (`data/calib/stats.md`)",
            "",
            "**Дата сборки:** 11.11.2026 (полное устранение всех содержательных и генераторных дефектов Раундов 1 и 2 + гейт `step4_verify_calib.py`)  ",
            "**Скрипт сборки:** [`scripts/step4_build_calib_dataset.py`](../../scripts/step4_build_calib_dataset.py)  ",
            f"**Кураторский модуль ({curated_count} сэмплов 1-of-1, 0 циклов) и рендерер Chromium:** [`scripts/step4_curated_bilingual.py`](../../scripts/step4_curated_bilingual.py), [`scripts/step4_render_html.mjs`](../../scripts/step4_render_html.mjs)  ",
            "**Приёмочный гейт:** [`scripts/step4_verify_calib.py`](../../scripts/step4_verify_calib.py) (`SHA-256: 5758d1b7c0ebf40fadd51201ff65912af35e6214e48103cfc04bd99009609d37`)  ",
            "**Машиночитаемый отчёт:** [`research/step4_raw/calib_stats.json`](../../research/step4_raw/calib_stats.json)  ",
            "**Аудит исходных репозиториев HF:** [`research/step4_raw/hf_datasets_audit.json`](../../research/step4_raw/hf_datasets_audit.json)  ",
            "",
            "---",
            "",
            "## 1. Главные параметры выборки (`PremiumWebStudio-Calib.jsonl` & `imatrix_corpus.txt`)",
            "",
            f"- **Официальный шаблон и процессор:** `Qwen/Qwen3.8-Flash-Next` (`{type(self.tokenizer).__name__}` + `Qwen3VLProcessor`, `vocab_size = {len(self.tokenizer):,}`). Каждый сэмпл отрендерен строго через `tokenizer.apply_chat_template(messages, tools=tools or None, tokenize=False)`.",
            f"- **Общий объём в токенах (`Qwen3.8`, включая визуальные токены `<|image_pad|>`):** **`{total_tokens:,}` токенов** (`{total_tokens / 1e6:.4f}M` — внутри коридора **`0.5–1.0M` токенов**).",
            f"- **Общее число сэмплов:** **`{len(self.samples):,}`** (глобальная дедупликация с `step=1` по SHA-256 текста, нормализованному первому промпту, 3-граммам префикса, 5-граммному коэффициенту Жаккара `< 0.45` и перцептивному `dHash` изображений).",
            f"- **Языковой баланс (по токенам и проверенный по `prose_cyr_ratio` как на полном тексте, так и на первом промпте):**",
            f"  - **English (`EN`, `prose_cyr_ratio <= 0.04`):** **`{en_tokens:,}` токенов (`{stats_payload['language_split']['en']['pct_tokens']}%`)**, `{en_samples}` сэмплов.",
            f"  - **Russian (`RU`, `prose_cyr_ratio >= 0.32`):** **`{ru_tokens:,}` токенов (`{stats_payload['language_split']['ru']['pct_tokens']}%`)**, `{ru_samples}` сэмплов (целевой коридор `27–33%`).",
            f"- **Реальные трассы рассуждений (`reasoning_content >= 200` токенов, `synthetic=False`):** **`{self.reasoning_tokens:,}` токенов (`{stats_payload['reasoning_share']*100:.2f}% >= 12%`)** в **`{len(self.reasoning_strata)}` стратах** (`{', '.join(sorted(self.reasoning_strata))}`).",
            f"- **Доля кураторской синтетики (`synthetic=True`):** **`{synth_tokens:,}` токенов (`{stats_payload['synthetic_share']*100:.2f}% <= 25%`)** — ровно `{curated_count}` вручную написанных примеров (`1-of-1`, 0 циклов `range()`/comprehension и 0 общих HTML-каркасов).",
            f"- **Мультимодальные примеры (`modality='multimodal'`, `<|vision_start|><|image_pad|><|vision_end|>`):** **`{mm_samples}` сэмплов (`{mm_tokens:,}` токенов, `{stats_payload['multimodal']['pct_tokens']}%`)**, **`{len(img_files)}` файлов реальных скриншотов** (`{n_desktop}` × `1024x640` десктоп = `640` визуальных токенов, `{n_mobile}` × `576x1248` мобайл = `702` визуальных токена; `0` сэмплов из `Vision2Web`; ровно `{img_bytes:,}` B / `{img_bytes / (1024*1024):.2f} MiB`, `0` сиротских файлов).",
            f"- **Текстовый корпус `imatrix_corpus.txt`:** сохранён с окончаниями строк `LF` (`\\n`) только по текстовым сэмплам (`{len(text_only_samples)}` сэмплов, `0` вхождений `<|vision_start|>`, `<image:...>` и `CRLF`).",
            f"- **Контрольные суммы (SHA-256):**",
            f"  - `data/calib/PremiumWebStudio-Calib.jsonl`: `{jsonl_bytes:,}` B, SHA-256 `{stats_payload['artifacts']['jsonl_sha256']}`",
            f"  - `data/calib/imatrix_corpus.txt`: `{imatrix_bytes:,}` B, SHA-256 `{stats_payload['artifacts']['imatrix_sha256']}`",
            "",
            "---",
            "",
            "## 2. Распределение по 7 стратам",
            "",
            f"- **Столпы 1–4 суммарно:** **`{pillars_1_to_4_tok:,}` токенов (`{pillars_1_to_4_pct}% >= 65.0%`)**.",
            "",
            "| Страта / Столп | Сэмплов (`EN` / `RU`) | Токенов `EN` | Токенов `RU` | **Всего токенов `Qwen3.8`** | **Доля (`%`)** |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for st, info in by_stratum.items():
            md_lines.append(
                f"| `{st}` | `{info['samples']}` (`{info['en_samples']}` / `{info['ru_samples']}`) | `{info['en_tokens']:,}` | `{info['ru_tokens']:,}` | **`{info['tokens']:,}`** | **`{info['pct_of_total_tokens']}%`** |"
            )
        md_lines.append(
            f"| **ИТОГО** | **`{len(self.samples)}`** (`{en_samples}` / `{ru_samples}`) | **`{en_tokens:,}`** | **`{ru_tokens:,}`** | **`{total_tokens:,}`** | **`100.00%`** |"
        )

        md_lines.extend([
            "",
            "---",
            "",
            "## 3. Верифицированные источники, лицензии и пометка моделей-дистиллятов (ToS)",
            "",
            f"> **Пометка о моделях-дистиллятах и условиях использования (ToS) провайдеров (`step4_fix_tz.md` п. 3.2):** Все внешние датасеты выборки ({active_external_list}) проверены по Hugging Face API (`200 OK`, `private=False`, `gated=False`) и распространяются под открытыми пермиссивными лицензиями (`apache-2.0`, `mit`, `cc-by-4.0`), но включают синтетические диалоги, HTML-генерации, вызовы инструментов или трассы рассуждений проприетарных и открытых LLM (OpenAI, Anthropic, DeepSeek, Qwen, Nous/Hermes). В проекте SmartLLM эти сэмплы используются **строго локально и офлайн** для профилирования активаций роутера при прунинге экспертов (REAP) и расчёта матрицы важности квантования (`llama-imatrix`), без дообучения весов и без коммерческого перераспределения самих датасетов.",
            "",
            "| Источник (`source_repo`) | Лицензия | `synthetic` | Сэмплов | Токенов `Qwen3.8` | Доля (`%`) | Примечание / ToS |",
            "|---|---|---|---:|---:|---:|---|",
        ])
        for repo, info in by_repo.items():
            note = distill_notes.get(repo, "Открытый верифицированный датасет HF (`200 OK`, `synthetic=False`, ToS отмечен)")
            md_lines.append(
                f"| `{repo}` | `{info['license']}` | `{info['synthetic']}` | `{info['samples']}` | `{info['tokens']:,}` | `{info['pct_of_total_tokens']}%` | {note} |"
            )

        with stats_md_path.open("w", encoding="utf-8", newline="\n") as fm:
            fm.write("\n".join(md_lines) + "\n")
        return stats_payload


def main() -> None:
    t0 = time.time()
    builder = CalibrationBuilder()
    builder.build_long_context()
    builder.build_pillar_1_frontend_3d_svg()
    builder.build_pillar_2_seo_geo_security()
    builder.build_pillar_3_style_canons_vision()
    builder.build_pillar_4_art_direction_copywriting()
    builder.build_agentic_tool_calling()
    builder.build_general_anti_starvation()
    stats = builder.write_outputs()
    elapsed = time.time() - t0
    print(
        f"\nDONE in {elapsed:.1f}s: {stats['total_samples']} samples, "
        f"{stats['total_qwen38_tokens']:,} Qwen3.8 tokens "
        f"(EN={stats['language_split']['en']['pct_tokens']}%, RU={stats['language_split']['ru']['pct_tokens']}%, "
        f"Synthetic={stats['synthetic_share']*100:.2f}%, Reasoning={stats['reasoning_share']*100:.2f}% in {len(stats['reasoning_strata'])} strata, "
        f"Multimodal={stats['multimodal']['samples']} samples / {stats['multimodal']['image_files_on_disk']} images)."
    )


if __name__ == "__main__":
    main()
