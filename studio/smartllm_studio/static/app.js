(function () {
  "use strict";

  var store = {
    lang: "ru",
    mode: "constructor",
    step: 1,
    i18n: { en: {}, ru: {} },
    catalog: { canons: [], canon_categories: [], available_blocks: [], preset_pages: [] },
    draft: null,
    logoVariants: [],
    logoBusy: false,
    autofillBusy: false,
    pageBlocks: {},
    pageBlockPrompts: {},
    company: {},
    selectedBlocks: ["hero", "features", "about", "gallery", "pricing", "faq", "contact"],
    selectedPages: ["index", "about", "services", "portfolio", "pricing", "contact"],
    siteType: "single",
    polarity: "auto",
    motion: "motion",
    landingPreset: "gsap_scrollytelling",
    stageOpen: false,
    blockPrompts: {},
    starterHistory: [],
    starterTimer: null,
    starterAbort: null
  };

  var previewTimer = null;
  var previewSeq = 0;

  function el(id) {
    return document.getElementById(id);
  }

  function scheduleLivePreviewRefresh(openStage) {
    if (!store.draft || store.autofillBusy || store.logoBusy) return;
    if (el("s5-build-site-btn") && el("s5-build-site-btn").disabled) return;
    clearTimeout(previewTimer);
    previewTimer = setTimeout(function () {
      var mySeq = ++previewSeq;
      var pid = (store.draft && store.draft.id) || "default";
      var outDir = (el("s1-folder-input") && el("s1-folder-input").value.trim()) || (store.draft && store.draft.output_dir) || "";
      fetch("/api/preview/" + encodeURIComponent(pid), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          canon_id: (store.draft && store.draft.canon_id) || "01_bento_grid",
          polarity: store.polarity,
          motion: store.motion,
          landing_preset: store.landingPreset,
          output_dir: outDir
        })
      })
        .then(function (r) { return r.json(); })
        .then(function (bp) {
          if (mySeq !== previewSeq || !bp || bp.error || !bp.preview_url) return;
          if (bp.revision && store.draft) store.draft.revision = bp.revision;
          if (openStage) setStageOpen(true);
          var ifr = el("live-stage-iframe");
          if (ifr) {
            var routeSel = el("stage-route-select");
            var idx = routeSel ? (parseInt(routeSel.value || "0", 10) || 0) : 0;
            var routes = (bp.routes && bp.routes.length) ? bp.routes : (store.draft && store.draft.routes);
            var route = routes && routes[idx];
            var targetUrl = bp.preview_url;
            if (route && route.filename && route.filename !== "index.html") {
              var revNum = bp.revision || (store.draft && store.draft.revision) || 1;
              targetUrl = "/preview/" + encodeURIComponent(pid) + "/" + route.filename + "?rev=" + revNum;
            }
            var sep = targetUrl.indexOf("?") === -1 ? "?" : "&";
            ifr.src = targetUrl + sep + "t=" + Date.now();
          }
        })
        .catch(function () {});
    }, 180);
  }

  function setStageOpen(open) {
    store.stageOpen = Boolean(open);
    var shell = el("atelier-shell");
    var stg = el("atelier-live-stage");
    if (shell) shell.setAttribute("data-stage-open", store.stageOpen ? "true" : "false");
    if (stg) stg.setAttribute("data-drawer-closed", store.stageOpen ? "false" : "true");
    if (store.stageOpen) {
      var ifr = el("live-stage-iframe");
      if (ifr && (!ifr.getAttribute("src") || ifr.getAttribute("src") === "about:blank")) {
        var pid = (store.draft && store.draft.id) || "default";
        var rev = (store.draft && store.draft.revision) || 1;
        ifr.src = "/preview/" + encodeURIComponent(pid) + "/index.html?rev=" + rev;
      }
    }
  }

  function setPolarity(pol, fromUser) {
    var next = (pol === "light" || pol === "dark") ? pol : "auto";
    store.polarity = next;
    if (store.draft) store.draft.polarity = next;
    ["auto", "light", "dark"].forEach(function (mode) {
      var b = el("s3-polarity-" + mode);
      if (!b) return;
      var active = mode === next;
      b.setAttribute("aria-pressed", active ? "true" : "false");
      b.className = active ? "btn btn-primary" : "btn";
    });
    renderCanons();
    if (fromUser === true) scheduleLivePreviewRefresh(true);
  }

  function normalizeMotionId(val) {
    var low = String(val || "").trim().toLowerCase();
    if (!low || low === "gsap" || low === "gsap_scrolltrigger" || low === "gsap-scrolltrigger" || low === "motion") return "motion";
    if (low === "animejs" || low === "anime") return "animejs";
    if (low === "lenis" || low === "smooth_scroll") return "lenis";
    if (low === "three" || low === "threejs") return "three";
    if (low === "css_scroll_driven" || low === "css") return "css_scroll_driven";
    if (low === "reduced_motion_instant" || low === "minimal" || low === "none") return "reduced_motion_instant";
    return "motion";
  }

  function renderMotionSelects() {
    var motions = (store.catalog && store.catalog.motions) || [
      { id: "motion", name_en: "Motion 14 + Lenis (GSAP-class MIT)", name_ru: "Motion 14 + Lenis (уровень GSAP, MIT)" },
      { id: "animejs", name_en: "Anime.js 4.5 + Lenis Timeline (MIT)", name_ru: "Anime.js 4.5 + Lenis таймлайны (MIT)" },
      { id: "css_scroll_driven", name_en: "Native CSS Scroll-Driven (0 KB JS)", name_ru: "Нативный CSS Scroll-Driven (0 КБ JS)" },
      { id: "lenis", name_en: "Lenis Smooth Scroll (MIT)", name_ru: "Lenis плавный скролл (MIT)" },
      { id: "three", name_en: "Three.js + Lenis Spatial (MIT)", name_ru: "Three.js + Lenis 3D-сцена (MIT)" },
      { id: "reduced_motion_instant", name_en: "Zero-Motion Instant Layout", name_ru: "Без анимаций (мгновенный рендер)" }
    ];
    ["s3-motion-select", "exp-motion-select"].forEach(function (selId) {
      var sel = el(selId);
      if (!sel) return;
      sel.innerHTML = "";
      motions.forEach(function (m) {
        var opt = document.createElement("option");
        opt.value = m.id;
        opt.textContent = store.lang === "ru" ? (m.name_ru || m.name_en || m.id) : (m.name_en || m.id);
        sel.appendChild(opt);
      });
      sel.value = store.motion;
    });
  }

  function setMotion(val, fromUser) {
    var norm = normalizeMotionId(val);
    store.motion = norm;
    if (store.draft) store.draft.motion = norm;
    ["s3-motion-select", "exp-motion-select"].forEach(function (selId) {
      var sel = el(selId);
      if (sel && sel.value !== norm) sel.value = norm;
    });
    if (fromUser === true) scheduleLivePreviewRefresh(true);
  }

  var LANDING_PRESET_FALLBACKS = [
    { id: "gsap_scrollytelling", name_en: "GSAP-Class Scrollytelling Landing", name_ru: "Скроллтеллинг-лендинг (GSAP-класс)", badge_en: "Motion 14 + Lenis", badge_ru: "Motion 14 + Lenis", desc_en: "Sticky pinned stage, numbered chapters, marquee ribbon & counters.", desc_ru: "Липкая сцена с главами при скролле, бегущая строка, счётчики и параллакс.", motion: "motion" },
    { id: "kinetic_showreel", name_en: "Kinetic Showreel & Filmstrip", name_ru: "Кинетический шоурил (Anime.js)", badge_en: "Anime.js 4.5 + Lenis", badge_ru: "Anime.js 4.5 + Lenis", desc_en: "Timeline headline stagger, scroll chapters & 3D tilt frame.", desc_ru: "Таймлайн-каскад заголовков, скролл-главы и 3D-наклон сцены.", motion: "animejs" },
    { id: "bento_interactive", name_en: "Interactive Modular Bento", name_ru: "Интерактивный Bento-лендинг", badge_en: "Motion 14 + Lenis", badge_ru: "Motion 14 + Lenis", desc_en: "Asymmetric 12-col bento modules & spring counters.", desc_ru: "Асимметричная 12-колоночная сетка, модули и пружинный отклик.", motion: "motion" },
    { id: "css_scroll_native", name_en: "Zero-JS Native CSS Scroll-Driven", name_ru: "Нативный CSS Scroll-Driven", badge_en: "0 KB JS", badge_ru: "0 КБ JS", desc_en: "Pure browser compositor timeline with zero JS runtime.", desc_ru: "Чистый композиторный скролл-таймлайн без JS-рантайма.", motion: "css_scroll_driven" },
    { id: "classic_corporate", name_en: "Structured Editorial Architecture", name_ru: "Классический корпоративный", badge_en: "Balanced", badge_ru: "Спокойный ритм", desc_en: "High-readability hierarchy focused on proof & pricing.", desc_ru: "Чёткая деловая иерархия разделов, матриц и максимальная читаемость.", motion: "css_scroll_driven" }
  ];

  function getLandingPresetsList() {
    return (store.catalog && store.catalog.landing_presets && store.catalog.landing_presets.length)
      ? store.catalog.landing_presets
      : LANDING_PRESET_FALLBACKS;
  }

  function renderLandingPresets() {
    var list = getLandingPresetsList();
    var expSel = el("exp-landing-preset");
    if (expSel) {
      expSel.innerHTML = "";
      list.forEach(function (p) {
        var opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = store.lang === "ru" ? (p.name_ru || p.name_en || p.id) : (p.name_en || p.id);
        expSel.appendChild(opt);
      });
      expSel.value = store.landingPreset;
    }
    var grid = el("s3-landing-presets");
    if (!grid) return;
    grid.innerHTML = "";
    list.forEach(function (p) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "landing-preset-card";
      btn.setAttribute("aria-pressed", store.landingPreset === p.id ? "true" : "false");
      var head = document.createElement("div");
      head.className = "landing-preset-head";
      var ttl = document.createElement("strong");
      ttl.textContent = store.lang === "ru" ? (p.name_ru || p.name_en || p.id) : (p.name_en || p.id);
      var badge = document.createElement("span");
      badge.className = "landing-preset-badge";
      badge.textContent = store.lang === "ru" ? (p.badge_ru || p.badge_en || "") : (p.badge_en || "");
      head.appendChild(ttl);
      head.appendChild(badge);
      var desc = document.createElement("span");
      desc.className = "landing-preset-desc";
      desc.textContent = store.lang === "ru" ? (p.desc_ru || p.desc_en || "") : (p.desc_en || "");
      btn.appendChild(head);
      btn.appendChild(desc);
      btn.addEventListener("click", function () {
        setLandingPreset(p.id, true);
      });
      grid.appendChild(btn);
    });
  }

  function setLandingPreset(presetId, fromUser) {
    var list = getLandingPresetsList();
    var chosen = list[0];
    for (var i = 0; i < list.length; i++) {
      if (list[i].id === presetId) {
        chosen = list[i];
        break;
      }
    }
    store.landingPreset = chosen.id;
    if (store.draft) store.draft.landing_preset = chosen.id;
    var expSel = el("exp-landing-preset");
    if (expSel && expSel.value !== chosen.id) expSel.value = chosen.id;
    if (chosen.motion) setMotion(chosen.motion, false);
    renderLandingPresets();
    if (fromUser === true) scheduleLivePreviewRefresh(true);
  }

  function syncProjectPathDisplay(pathStr) {
    var clean = String(pathStr || "").trim();
    if (el("s1-folder-input") && el("s1-folder-input").value !== clean) el("s1-folder-input").value = clean;
    if (el("exp-folder-input") && el("exp-folder-input").value !== clean) el("exp-folder-input").value = clean;
    if (el("s1-folder-input")) el("s1-folder-input").title = clean;
    if (el("exp-folder-input")) el("exp-folder-input").title = clean;
    var readout = el("s5-project-path-readout");
    if (readout) {
      readout.textContent = clean
        ? (store.lang === "ru" ? "Папка сохранения: " : "Save folder: ") + clean
        : "";
    }
  }

  var fpState = { currentDir: "", parentDir: "", mode: "pick", onPicked: null };

  function formatFileBytes(bytes) {
    var n = Number(bytes) || 0;
    if (n < 1024) return n + " B";
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
    return (n / (1024 * 1024)).toFixed(1) + " MB";
  }

  function loadDirectoryIntoPicker(dirPath) {
    var statusEl = el("fp-status");
    if (statusEl) statusEl.textContent = store.lang === "ru" ? "Загрузка каталога..." : "Loading directory...";
    fetch("/api/fs/list?dir=" + encodeURIComponent(dirPath || ""), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || d.error) {
          if (statusEl) statusEl.textContent = (d && d.message) || (d && d.error) || "Error";
          return;
        }
        fpState.currentDir = d.current_dir || "";
        fpState.parentDir = d.parent_dir || "";
        if (el("fp-current-path")) el("fp-current-path").value = fpState.currentDir;
        if (el("fp-up-btn")) el("fp-up-btn").disabled = !fpState.parentDir;

        var drvWrap = el("fp-drives");
        if (drvWrap) {
          drvWrap.innerHTML = "";
          (d.drives || []).forEach(function (drv) {
            var b = document.createElement("button");
            b.type = "button";
            var isCur = fpState.currentDir.toLowerCase().indexOf(drv.toLowerCase()) === 0;
            b.className = isCur ? "btn btn-primary" : "btn";
            b.textContent = drv;
            b.addEventListener("click", function () { loadDirectoryIntoPicker(drv); });
            drvWrap.appendChild(b);
          });
        }

        var dirList = el("fp-dir-list");
        if (dirList) {
          dirList.innerHTML = "";
          var dirs = d.dirs || [];
          if (!dirs.length) {
            var emp = document.createElement("div");
            emp.className = "fp-row fp-row-static";
            emp.textContent = store.lang === "ru" ? "(подпапок нет)" : "(no subfolders)";
            dirList.appendChild(emp);
          } else {
            dirs.forEach(function (item) {
              var row = document.createElement("button");
              row.type = "button";
              row.className = "fp-row";
              var nm = document.createElement("span");
              nm.textContent = item.name;
              var tag = document.createElement("span");
              tag.className = "landing-preset-badge";
              tag.textContent = "DIR";
              row.appendChild(nm);
              row.appendChild(tag);
              row.addEventListener("click", function () { loadDirectoryIntoPicker(item.path); });
              dirList.appendChild(row);
            });
          }
        }

        var fileList = el("fp-file-list");
        if (fileList) {
          fileList.innerHTML = "";
          var files = d.files || [];
          if (!files.length) {
            var fEmp = document.createElement("div");
            fEmp.className = "fp-row fp-row-static";
            fEmp.textContent = store.lang === "ru" ? "(файлов нет)" : "(no files)";
            fileList.appendChild(fEmp);
          } else {
            files.forEach(function (item) {
              var fRow = document.createElement("div");
              fRow.className = "fp-row fp-row-static";
              var fnm = document.createElement("span");
              fnm.textContent = item.name;
              var fsz = document.createElement("span");
              fsz.textContent = formatFileBytes(item.size);
              fRow.appendChild(fnm);
              fRow.appendChild(fsz);
              fileList.appendChild(fRow);
            });
          }
        }
        if (statusEl) {
          statusEl.textContent = (store.lang === "ru" ? "Папок: " : "Folders: ") + (d.dirs || []).length + " · " + (store.lang === "ru" ? "Файлов: " : "Files: ") + (d.files || []).length;
        }
      })
      .catch(function (err) {
        if (statusEl) statusEl.textContent = err && err.message ? err.message : String(err);
      });
  }

  function openFolderPickerModal(initialDir, mode, onPicked) {
    fpState.mode = mode || "pick";
    fpState.onPicked = typeof onPicked === "function" ? onPicked : null;
    if (el("fp-title")) {
      el("fp-title").textContent = fpState.mode === "browse"
        ? (store.lang === "ru" ? "Просмотр папки проекта" : "Inspect Project Folder")
        : (store.lang === "ru" ? "Выбор папки проекта на диске" : "Choose Project Folder on Disk");
    }
    if (el("fp-select-btn")) el("fp-select-btn").hidden = !fpState.onPicked;
    if (el("modal-folder-picker")) el("modal-folder-picker").hidden = false;
    loadDirectoryIntoPicker(initialDir || "");
  }

  function pickProjectFolder(btnId, statusId, sourceInputId) {
    var btn = el(btnId);
    var statusEl = el(statusId);
    var initial = el(sourceInputId) ? el(sourceInputId).value : "";
    if (btn) btn.disabled = true;
    if (statusEl) {
      statusEl.textContent = store.lang === "ru"
        ? "Открыт диалог выбора папки..."
        : "Waiting for folder dialog...";
    }
    fetch("/api/os/pick", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "folder", initial_dir: initial })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.path) {
          syncProjectPathDisplay(d.path);
          if (store.draft) store.draft.output_dir = d.path;
          if (statusEl) {
            statusEl.textContent = (store.lang === "ru" ? "Выбрана папка: " : "Selected folder: ") + d.path;
          }
        } else if (d && (d.fallback === "web_picker" || d.interactive_desktop === false)) {
          if (statusEl) {
            statusEl.textContent = store.lang === "ru"
              ? "Открыт встроенный проводник выбора папки."
              : "Opened built-in studio folder browser.";
          }
          openFolderPickerModal(initial, "pick", function (pickedPath) {
            syncProjectPathDisplay(pickedPath);
            if (store.draft) store.draft.output_dir = pickedPath;
            if (statusEl) {
              statusEl.textContent = (store.lang === "ru" ? "Выбрана папка: " : "Selected folder: ") + pickedPath;
            }
          });
        } else if (statusEl) {
          statusEl.textContent = store.lang === "ru"
            ? "Выбор папки отменён."
            : "Folder selection cancelled.";
        }
      })
      .catch(function (err) {
        if (statusEl) {
          statusEl.textContent = (store.lang === "ru" ? "Не удалось открыть диалог: " : "Folder dialog failed: ") + (err && err.message ? err.message : String(err));
        }
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function revealProjectFolder(pathValue, statusId) {
    var target = String(pathValue || "").trim();
    var statusEl = el(statusId);
    fetch("/api/os/reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: target })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d && d.opened) {
          if (statusEl) statusEl.textContent = (store.lang === "ru" ? "Открыта папка: " : "Opened folder: ") + (d.path || target);
        } else {
          var browseTarget = (d && d.path) || target;
          if (statusEl) {
            statusEl.textContent = (store.lang === "ru" ? "Просмотр папки в проводнике студии: " : "Opened folder in studio browser: ") + browseTarget;
          }
          openFolderPickerModal(browseTarget, "browse", function (pickedPath) {
            syncProjectPathDisplay(pickedPath);
            if (store.draft) store.draft.output_dir = pickedPath;
            if (statusEl) {
              statusEl.textContent = (store.lang === "ru" ? "Выбрана папка: " : "Selected folder: ") + pickedPath;
            }
          });
        }
      })
      .catch(function (err) {
        if (statusEl) {
          statusEl.textContent = (store.lang === "ru" ? "Ошибка открытия папки: " : "Open folder error: ") + (err && err.message ? err.message : String(err));
        }
      });
  }

  function stopStarterPreloader(ctrlRef) {
    if (ctrlRef && store.starterAbort !== ctrlRef) return;
    clearInterval(store.starterTimer);
    store.starterTimer = null;
    if (el("starter-preloader")) el("starter-preloader").hidden = true;
  }

  function runRandomStarterTemplate(useLlm) {
    if (store.starterAbort) {
      try { store.starterAbort.abort(); } catch (e) {}
    }
    clearInterval(store.starterTimer);
    var ctrl = new AbortController();
    store.starterAbort = ctrl;
    var overlay = el("starter-preloader");
    if (overlay) overlay.hidden = false;
    var startedAt = Date.now();
    if (el("starter-timer")) el("starter-timer").textContent = "00:00";
    if (el("starter-status")) {
      el("starter-status").textContent = useLlm
        ? (store.lang === "ru"
            ? "SmartLLM придумывает бренд, логотип-промпт, стиль и страницы под шаги 2–5…"
            : "SmartLLM is crafting brand brief, logo cue, style & pages for Steps 2–5…")
        : (store.lang === "ru"
            ? "Применяем связный быстрый шаблон…"
            : "Applying cohesive instant template…");
    }
    var pills = document.querySelectorAll("#starter-preloader [data-starter-pill]");
    var tickCount = 0;
    store.starterTimer = setInterval(function () {
      if (store.starterAbort !== ctrl) return;
      if (el("starter-timer")) el("starter-timer").textContent = formatElapsed(Date.now() - startedAt);
      tickCount += 1;
      var activeIdx = tickCount % Math.max(1, pills.length);
      for (var i = 0; i < pills.length; i++) {
        pills[i].classList.toggle("is-active", i <= activeIdx);
      }
    }, 350);

    var reqLang = el("s1-lang") ? el("s1-lang").value : store.lang;
    fetch("/api/orchestrator/random-template", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      body: JSON.stringify({
        lang: reqLang || "ru",
        use_llm: Boolean(useLlm),
        exclude_names: store.starterHistory.slice(-8)
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (store.starterAbort !== ctrl) return;
        stopStarterPreloader(ctrl);
        if (!data || data.error || !data.template) return;
        var tpl = data.template;
        if (tpl.name) store.starterHistory.push(tpl.name);

        store.logoVariants = [];
        if (el("s2-logo-grid")) el("s2-logo-grid").innerHTML = "";
        if (el("s2-logo-status")) {
          el("s2-logo-status").textContent = store.lang === "ru"
            ? "Промпт логотипа подготовлен. При желании нажмите «Сгенерировать 6 вариантов 512×512»."
            : "Logo prompt is ready. Click 'Generate 6 Logo Variants' when you want Z-Image logos.";
        }

        store.draft = Object.assign({}, store.draft || {}, {
          id: "starter",
          revision: 1,
          name: tpl.name,
          brief: tpl.brief,
          goal: tpl.brief,
          logo_prompt: tpl.logo_prompt || "",
          languages: tpl.languages || "ru",
          canon_id: tpl.canon_id || "01_bento_grid",
          polarity: tpl.polarity || "auto",
          landing_preset: tpl.landing_preset || "gsap_scrollytelling",
          motion: tpl.motion || "motion",
          site_type: tpl.site_type || "multi",
          selected_pages: (tpl.selected_pages || ["index"]).slice(),
          page_blocks: tpl.page_blocks || {},
          selected_blocks: (tpl.selected_blocks || []).slice(),
          page_block_prompts: tpl.page_block_prompts || {},
          block_prompts: tpl.block_prompts || {},
          company: tpl.company || {},
          output_dir: tpl.output_dir || "",
          selected_logo_path: "",
          routes: tpl.selected_pages
            ? tpl.selected_pages.map(function (s) {
                var pp = presetPage(s);
                return {
                  slug: s,
                  filename: s === "index" ? "index.html" : s + ".html",
                  title: pp ? (store.lang === "ru" ? pp.title_ru : pp.title_en) : s
                };
              })
            : []
        });

        if (el("s1-lang") && (tpl.languages === "ru" || tpl.languages === "en" || tpl.languages === "en+ru")) {
          el("s1-lang").value = tpl.languages;
        }
        if (tpl.output_dir) syncProjectPathDisplay(tpl.output_dir);
        if (el("s2-name")) el("s2-name").value = tpl.name || "";
        if (el("s2-desc")) el("s2-desc").value = tpl.brief || "";
        if (el("s2-logo-prompt")) el("s2-logo-prompt").value = tpl.logo_prompt || "";

        setPolarity(tpl.polarity || "auto", false);
        setLandingPreset(tpl.landing_preset || "gsap_scrollytelling", false);
        setMotion(tpl.motion || "motion", false);
        renderCanons();

        store.siteType = tpl.site_type === "single" ? "single" : "multi";
        store.selectedPages = (tpl.selected_pages || ["index"]).slice();
        store.pageBlocks = tpl.page_blocks || {};
        store.pageBlockPrompts = tpl.page_block_prompts || {};
        store.blockPrompts = tpl.block_prompts || {};
        store.company = tpl.company || {};
        renderCompanyFields();
        renderPagesAndBlocksChecklists();
        syncRouteSelectFromDraft(store.draft);

        var sumBox = el("s5-starter-summary");
        if (sumBox) {
          sumBox.hidden = false;
          var badgeEl = el("s5-starter-badge");
          if (badgeEl) {
            badgeEl.textContent = data.source === "llm"
              ? (store.lang === "ru" ? "SmartLLM ИИ" : "SmartLLM AI")
              : (store.lang === "ru" ? "Быстрый шаблон" : "Quick Preset");
          }
          var bodyEl = el("s5-starter-summary-body");
          if (bodyEl) {
            var canonObj = (store.catalog.canons || []).filter(function (c) { return c.id === tpl.canon_id; })[0];
            var canonTitle = canonObj ? canonName(canonObj) : tpl.canon_id;
            var lpObj = getLandingPresetsList().filter(function (p) { return p.id === store.landingPreset; })[0];
            var lpTitle = lpObj ? (store.lang === "ru" ? lpObj.name_ru : lpObj.name_en) : store.landingPreset;
            bodyEl.textContent = tpl.name + " · " + canonTitle + " · " + lpTitle + " → " + (tpl.output_dir || "");
          }
        }

        if (data.preview_url && el("live-stage-iframe")) {
          var sep = data.preview_url.indexOf("?") === -1 ? "?" : "&";
          el("live-stage-iframe").src = data.preview_url + sep + "t=" + Date.now();
          setStageOpen(true);
        }
        setStep(5);
        var sumTarget = el("s5-starter-summary") || el("s5-autofill-btn");
        if (sumTarget && typeof sumTarget.scrollIntoView === "function") {
          sumTarget.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") return;
        stopStarterPreloader(ctrl);
      });
  }

  function translateDOM(lang) {
    store.lang = lang === "ru" ? "ru" : "en";
    document.documentElement.lang = store.lang;
    var dict = store.i18n[store.lang] || {};
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var k = nodes[i].getAttribute("data-i18n");
      if (dict[k]) nodes[i].textContent = dict[k];
    }
    var attrNodes = document.querySelectorAll("[data-i18n-attr]");
    for (var j = 0; j < attrNodes.length; j++) {
      var spec = attrNodes[j].getAttribute("data-i18n-attr") || "";
      var pairs = spec.split(";");
      for (var p = 0; p < pairs.length; p++) {
        var kv = pairs[p].split(":");
        if (kv.length === 2 && dict[kv[1]]) {
          attrNodes[j].setAttribute(kv[0].trim(), dict[kv[1]].trim());
        }
      }
    }
    var ind = el("lang-indicator");
    if (ind) ind.textContent = store.lang === "ru" ? "RU | EN" : "EN | RU";
    renderCanons();
    renderMotionSelects();
    renderLandingPresets();
    renderPagesAndBlocksChecklists();
    renderBlockDescriptionInputs();
    if (el("s1-folder-input")) syncProjectPathDisplay(el("s1-folder-input").value);
  }

  function setMode(mode) {
    store.mode = mode === "express" ? "express" : "constructor";
    el("mode-btn-constructor").setAttribute("aria-selected", store.mode === "constructor" ? "true" : "false");
    el("mode-btn-express").setAttribute("aria-selected", store.mode === "express" ? "true" : "false");
    el("view-constructor").hidden = store.mode !== "constructor";
    el("view-express").hidden = store.mode !== "express";
  }

  function setStep(stepNum) {
    var n = Math.max(1, Math.min(5, parseInt(stepNum, 10) || 1));
    store.step = n;
    setMode("constructor");
    for (var i = 1; i <= 5; i++) {
      var pane = el("ctor-step-" + i);
      if (pane) pane.hidden = i !== n;
      var navBtn = el("nav-step-" + i);
      if (navBtn) {
        if (i === n) navBtn.setAttribute("aria-current", "step");
        else navBtn.removeAttribute("aria-current");
      }
    }
    if (n === 5) renderBlockDescriptionInputs();
  }

  function markOrchStages(stateStr) {
    var items = document.querySelectorAll("#orch-sidebar-list .orch-item");
    for (var i = 0; i < items.length; i++) {
      items[i].setAttribute("data-state", stateStr);
    }
  }

  function setBusy(busy) {
    ["exp-generate-btn", "s5-build-site-btn", "s5-autofill-btn", "s2-gen-logos-btn"].forEach(function (id) {
      var btn = el(id);
      if (btn) btn.disabled = Boolean(busy);
    });
  }

  function formatElapsed(ms) {
    var total = Math.max(0, Math.floor(ms / 1000));
    var m = Math.floor(total / 60);
    var s = total % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }

  function updateLogoProgress(percent, text) {
    var box = el("s2-logo-progress");
    if (!box) return;
    box.hidden = false;
    var pct = Math.max(3, Math.min(100, Number(percent) || 0));
    var fill = el("s2-logo-progress-fill");
    if (fill) fill.style.width = pct + "%";
    if (text) el("s2-logo-progress-text").textContent = text;
  }

  function startLogoProgress() {
    store.logoBusy = true;
    var box = el("s2-logo-progress");
    if (box) box.hidden = false;
    updateLogoProgress(5, store.lang === "ru" ? "Запуск: анализ бренда..." : "Starting: analyzing the brand...");
    var started = Date.now();
    var timer = setInterval(function () {
      var timeEl = el("s2-logo-progress-time");
      if (timeEl) timeEl.textContent = formatElapsed(Date.now() - started);
    }, 500);
    return function stopLogoProgress(doneText) {
      store.logoBusy = false;
      clearInterval(timer);
      updateLogoProgress(100, doneText || (store.lang === "ru" ? "Готово" : "Done"));
      setTimeout(function () {
        var b = el("s2-logo-progress");
        if (b) b.hidden = true;
      }, 1600);
    };
  }

  function updateSidebarOrchFromTasks(tasks) {
    if (!tasks || !tasks.length) return;
    var items = document.querySelectorAll("#orch-sidebar-list .orch-item");
    tasks.forEach(function (t, idx) {
      var node = document.querySelector('#orch-sidebar-list [data-orch="' + t.id + '"]') || items[idx];
      if (node && t.status) node.setAttribute("data-state", t.status);
    });
  }

  function updateAutofillProgress(percent, text) {
    var box = el("s5-autofill-progress");
    if (!box) return;
    box.hidden = false;
    var pct = Math.max(3, Math.min(100, Number(percent) || 0));
    var fill = el("s5-autofill-progress-fill");
    if (fill) fill.style.width = pct + "%";
    if (text) el("s5-autofill-progress-text").textContent = text;
  }

  function startAutofillProgress() {
    store.autofillBusy = true;
    var box = el("s5-autofill-progress");
    if (box) box.hidden = false;
    updateAutofillProgress(5, store.lang === "ru" ? "Запуск: анализ бренда..." : "Starting: analyzing the brand...");
    var started = Date.now();
    var timer = setInterval(function () {
      var timeEl = el("s5-autofill-progress-time");
      if (timeEl) timeEl.textContent = formatElapsed(Date.now() - started);
    }, 500);
    return function stopAutofillProgress(doneText) {
      store.autofillBusy = false;
      clearInterval(timer);
      updateAutofillProgress(100, doneText || (store.lang === "ru" ? "Готово" : "Done"));
      setTimeout(function () {
        var b = el("s5-autofill-progress");
        if (b) b.hidden = true;
      }, 1600);
    };
  }

  function startProgressPolling(statusEl) {
    var timer = null;
    var stopped = false;
    function tick() {
      if (stopped) return;
      fetch("/api/orchestrator/progress")
        .then(function (r) { return r.json(); })
        .then(function (prog) {
          if (stopped || !prog) return;
          if (prog.tasks) updateSidebarOrchFromTasks(prog.tasks);
          if (store.logoBusy && typeof prog.progress === "number") {
            updateLogoProgress(prog.progress, store.lang === "ru" ? (prog.message_ru || "") : (prog.message_en || ""));
          }
          if (store.autofillBusy && typeof prog.progress === "number") {
            updateAutofillProgress(prog.progress, store.lang === "ru" ? (prog.message_ru || "") : (prog.message_en || ""));
          }
          if (statusEl && prog.running) {
            var msg = store.lang === "ru" ? (prog.message_ru || prog.stage) : (prog.message_en || prog.stage);
            if (msg) statusEl.textContent = msg;
          }
          refreshEngineHUD();
        })
        .catch(function () {});
    }
    tick();
    timer = setInterval(tick, 1000);
    return function stopPolling() {
      stopped = true;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };
  }

  function renderLogoVariantsGrid() {
    var grid = el("s2-logo-grid");
    if (!grid) return;
    grid.innerHTML = "";
    store.logoVariants.forEach(function (v) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "logo-variant-card";
      var isSel = store.draft && store.draft.selected_logo_path === v.path;
      btn.setAttribute("aria-pressed", isSel ? "true" : "false");
      var img = document.createElement("img");
      img.src = v.url + (v.url.indexOf("?") === -1 ? "?" : "&") + "t=" + Date.now();
      img.width = 140;
      img.alt = v.label_en;
      var cap = document.createElement("span");
      cap.textContent = store.lang === "ru" ? v.label_ru : v.label_en;
      btn.appendChild(img);
      btn.appendChild(cap);
      btn.addEventListener("click", function () {
        if (store.draft) store.draft.selected_logo_path = v.path;
        renderLogoVariantsGrid();
        fetch("/api/logo/select", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: (store.draft && store.draft.id) || "default",
            path: v.path,
            output_dir: el("s1-folder-input").value
          })
        })
          .then(function (r) { return r.json(); })
          .then(function (res) {
            if (res.preview_url) el("live-stage-iframe").src = res.preview_url;
            el("s2-logo-status").textContent = (store.lang === "ru" ? "Выбран логотип: " : "Selected logo: ") + (store.lang === "ru" ? v.label_ru : v.label_en);
          });
      });
      grid.appendChild(btn);
    });
  }

  function generateSixLogos() {
    var bname = el("s2-name").value.trim() || "SmartLLM";
    var desc = el("s2-desc").value.trim() || "";
    var logoPrompt = el("s2-logo-prompt") ? el("s2-logo-prompt").value.trim() : "";
    var statusEl = el("s2-logo-status");
    if (statusEl) {
      statusEl.textContent = store.lang === "ru"
        ? "SmartLLM составляет промпт и запускает рендер 6 вариантов логотипа 512×512..."
        : "SmartLLM is composing the prompt and rendering 6 logo variants (512x512)...";
    }
    setBusy(true);
    var stopLogoProgress = startLogoProgress();
    var stopPolling = startProgressPolling(statusEl);
    fetch("/api/logo/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: bname, description: desc, logo_prompt: logoPrompt, lang: store.lang })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        stopPolling();
        stopLogoProgress(store.lang === "ru" ? "Логотипы готовы" : "Logos ready");
        setBusy(false);
        refreshEngineHUD();
        if (data.error) {
          if (statusEl) statusEl.textContent = (store.lang === "ru" ? "Ошибка: " : "Error: ") + data.error;
          return;
        }
        store.logoVariants = data.variants || [];
        if (store.logoVariants.length > 0 && store.draft) {
          store.draft.selected_logo_path = store.logoVariants[0].path;
        }
        renderLogoVariantsGrid();
        if (statusEl) {
          var src = String(data.prompt_source || "").indexOf("llm") === 0
            ? (store.lang === "ru" ? "Промпт расширен ИИ-моделью. " : "Prompt expanded by SmartLLM. ")
            : "";
          statusEl.textContent = src + (store.lang === "ru"
            ? "Готово! Кликните на любой из 6 вариантов 512×512 для применения."
            : "Ready! Click any of the 6 variants (512x512) to apply.");
        }
      })
      .catch(function (err) {
        stopPolling();
        stopLogoProgress(store.lang === "ru" ? "Ошибка" : "Error");
        setBusy(false);
        refreshEngineHUD();
        if (statusEl) {
          statusEl.textContent = (store.lang === "ru" ? "Ошибка генерации логотипов: " : "Logo generation failed: ") + (err && err.message ? err.message : String(err));
        }
      });
  }

  function canonName(c) {
    return store.lang === "ru" ? (c.name_ru || c.name) : c.name;
  }

  function canonDescription(c) {
    return store.lang === "ru" ? (c.description_ru || c.description_en || "") : (c.description_en || "");
  }

  function renderCanonCategories() {
    var catSel = el("s3-canon-cat");
    if (!catSel) return;
    var current = catSel.value || "all";
    var total = store.catalog.canons_count || (store.catalog.canons || []).length;
    catSel.innerHTML = "";
    var allOpt = document.createElement("option");
    allOpt.value = "all";
    allOpt.textContent = store.lang === "ru" ? "Все стили (" + total + ")" : "All Styles (" + total + ")";
    catSel.appendChild(allOpt);
    (store.catalog.canon_categories || []).forEach(function (cat) {
      var opt = document.createElement("option");
      opt.value = cat.id;
      opt.textContent = (store.lang === "ru" ? cat.label_ru : cat.label_en) + " (" + (cat.count || 0) + ")";
      catSel.appendChild(opt);
    });
    var exists = false;
    for (var i = 0; i < catSel.options.length; i++) if (catSel.options[i].value === current) exists = true;
    catSel.value = exists ? current : "all";
  }

  function renderCanons() {
    var canons = store.catalog.canons || [];
    var search = (el("s3-canon-search") ? el("s3-canon-search").value : "").toLowerCase().trim();
    var cat = el("s3-canon-cat") ? el("s3-canon-cat").value : "all";

    renderCanonCategories();

    var expSel = el("exp-canon-select");
    if (expSel) {
      var prev = expSel.value || "";
      expSel.innerHTML = "";
      var autoOpt = document.createElement("option");
      autoOpt.value = "";
      autoOpt.textContent = store.lang === "ru" ? "Автоматический подбор под тему промпта" : "Automatic style selection from the brief";
      expSel.appendChild(autoOpt);
      canons.forEach(function (c) {
        var opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = canonName(c);
        expSel.appendChild(opt);
      });
      expSel.value = prev;
    }

    var gal = el("s3-canon-gallery");
    if (!gal) return;
    gal.innerHTML = "";
    canons
      .filter(function (c) {
        var haystack = [
          c.id, c.name, c.name_ru, c.description_en, c.description_ru,
          (c.search_terms || []).join(" "), (c.best_for || []).join(" "), c.category
        ].join(" ").toLowerCase();
        var matchText = !search || haystack.indexOf(search) !== -1;
        var matchCat = cat === "all" || c.category === cat;
        return matchText && matchCat;
      })
      .forEach(function (c) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "canon-card";
        btn.setAttribute("aria-pressed", store.draft && store.draft.canon_id === c.id ? "true" : "false");
        var thumb = document.createElement("img");
        thumb.className = "canon-preview-img";
        thumb.loading = "lazy";
        thumb.width = 640;
        thumb.height = 400;
        thumb.alt = "";
        thumb.src = c.preview_image || ("/static/art/canons/" + c.id + ".webp");
        var head = document.createElement("div");
        head.className = "canon-card-head";
        var title = document.createElement("strong");
        title.textContent = canonName(c);
        var activePol = (store.polarity === "light" || store.polarity === "dark") ? store.polarity : (c.default_polarity || "light");
        var polBadge = document.createElement("span");
        polBadge.className = "canon-polarity-badge";
        polBadge.textContent = store.lang === "ru" ? (activePol === "dark" ? "Тёмная" : "Светлая") : (activePol === "dark" ? "Dark" : "Light");
        head.appendChild(title);
        head.appendChild(polBadge);
        var desc = document.createElement("span");
        desc.className = "canon-desc";
        desc.textContent = canonDescription(c);
        var dots = document.createElement("div");
        dots.className = "oklch-dots";
        var pal = (c.palettes && c.palettes[activePol]) || c.palette || {};
        [pal.bg, pal.surface, pal.text, pal.accent, pal.accent_2, pal.muted || pal.accent_3].forEach(function (col) {
          var d = document.createElement("span");
          d.className = "oklch-dot";
          d.style.background = col || "#c084fc";
          dots.appendChild(d);
        });
        var tags = document.createElement("div");
        tags.className = "canon-tags";
        (c.best_for || []).slice(0, 3).forEach(function (tag) {
          var chip = document.createElement("span");
          chip.className = "canon-tag";
          chip.textContent = tag;
          tags.appendChild(chip);
        });
        btn.appendChild(thumb);
        btn.appendChild(head);
        btn.appendChild(desc);
        btn.appendChild(tags);
        btn.appendChild(dots);
        btn.addEventListener("click", function () {
          if (store.draft) store.draft.canon_id = c.id;
          renderCanons();
          scheduleLivePreviewRefresh(true);
        });
        gal.appendChild(btn);
      });
  }

  function presetPage(slug) {
    var pages = store.catalog.preset_pages || [];
    for (var i = 0; i < pages.length; i++) if (pages[i].slug === slug) return pages[i];
    return null;
  }

  function ensurePageBlocks() {
    if (!store.pageBlocks) store.pageBlocks = {};
    (store.catalog.preset_pages || []).forEach(function (p) {
      if (!store.pageBlocks[p.slug] || !store.pageBlocks[p.slug].length) {
        store.pageBlocks[p.slug] = (p.default_blocks || ["hero", "contact", "footer"]).slice();
      }
    });
  }

  function activePageSlugs() {
    if (store.siteType === "single") return ["index"];
    var list = (store.selectedPages || []).slice();
    if (list.indexOf("index") === -1) list.unshift("index");
    return list;
  }

  function syncSelectedBlocks() {
    var union = [];
    activePageSlugs().forEach(function (slug) {
      (store.pageBlocks[slug] || []).forEach(function (bid) {
        if (bid !== "footer" && union.indexOf(bid) === -1) union.push(bid);
      });
    });
    if (!union.length) union = ["hero", "contact"];
    store.selectedBlocks = union;
    if (store.draft) store.draft.page_blocks = store.pageBlocks;
  }

  function renderCompanyFields() {
    var c = store.company || {};
    var setVal = function (id, val) { var e = el(id); if (e) e.value = val || ""; };
    setVal("s5-tagline", c.tagline);
    setVal("s5-positioning", c.positioning);
    setVal("s5-values", Array.isArray(c.values) ? c.values.join(" | ") : c.values);
    setVal("s5-priorities", Array.isArray(c.priorities) ? c.priorities.join(", ") : c.priorities);
    setVal("s5-cities", Array.isArray(c.cities) ? c.cities.join(", ") : c.cities);
    setVal("s5-address", c.address);
    setVal("s5-phone", c.phone);
    setVal("s5-email", c.email);
    setVal("s5-hours", c.hours);
  }

  function syncCompanyFromInputs() {
    var val = function (id) { var e = el(id); return e ? e.value.trim() : ""; };
    var splitList = function (raw, sep) { return raw.split(sep).map(function (x) { return x.trim(); }).filter(Boolean); };
    store.company = Object.assign({}, store.company || {}, {
      tagline: val("s5-tagline"),
      positioning: val("s5-positioning"),
      values: splitList(val("s5-values"), /[|\n]+/),
      priorities: splitList(val("s5-priorities"), /,/),
      cities: splitList(val("s5-cities"), /,/),
      address: val("s5-address"),
      phone: val("s5-phone"),
      email: val("s5-email"),
      hours: val("s5-hours")
    });
  }

  function initializeCompanyState() {
    store.company = (store.draft && store.draft.company) || {};
    store.pageBlockPrompts = (store.draft && store.draft.page_block_prompts) || {};
    renderCompanyFields();
  }

  function initializePageState() {
    var presets = store.catalog.preset_pages || [];
    var valid = presets.map(function (p) { return p.slug; });
    ensurePageBlocks();
    if (store.draft && store.draft.page_blocks && typeof store.draft.page_blocks === "object") {
      valid.forEach(function (slug) {
        var arr = store.draft.page_blocks[slug];
        if (Array.isArray(arr) && arr.length) {
          store.pageBlocks[slug] = arr.filter(function (bid) {
            return bid === "footer" || (store.catalog.available_blocks || []).some(function (b) { return b.id === bid; });
          });
        }
      });
    }
    var fromDraft = [];
    if (store.draft && Array.isArray(store.draft.selected_pages)) {
      fromDraft = store.draft.selected_pages.slice();
    } else if (store.draft && Array.isArray(store.draft.routes)) {
      fromDraft = store.draft.routes.map(function (r) { return r.slug; });
    }
    fromDraft = fromDraft.filter(function (slug) { return valid.indexOf(slug) !== -1; });
    var explicitType = store.draft && store.draft.site_type;
    if (!fromDraft.length || (!explicitType && fromDraft.length <= 1)) {
      fromDraft = ["index", "about", "services", "portfolio", "pricing", "contact"].filter(function (s) { return valid.indexOf(s) !== -1; });
    }
    if (fromDraft.indexOf("index") === -1) fromDraft.unshift("index");
    store.selectedPages = fromDraft;
    store.siteType = explicitType === "single" ? "single" : "multi";
    syncSelectedBlocks();
  }

  function renderPagesAndBlocksChecklists() {
    ensurePageBlocks();
    var pagesBox = el("s4-pages-box");
    if (pagesBox) pagesBox.hidden = store.siteType !== "multi";
    el("s4-type-single-btn").setAttribute("aria-pressed", store.siteType === "single" ? "true" : "false");
    el("s4-type-single-btn").className = store.siteType === "single" ? "btn btn-primary" : "btn";
    el("s4-type-multi-btn").setAttribute("aria-pressed", store.siteType === "multi" ? "true" : "false");
    el("s4-type-multi-btn").className = store.siteType === "multi" ? "btn btn-primary" : "btn";

    var pagesList = el("s4-pages-checklist");
    if (pagesList) {
      pagesList.innerHTML = "";
      (store.catalog.preset_pages || []).forEach(function (p) {
        var lbl = document.createElement("label");
        lbl.className = "check-card";
        var chk = document.createElement("input");
        chk.type = "checkbox";
        chk.checked = store.selectedPages.indexOf(p.slug) !== -1;
        chk.addEventListener("change", function () {
          if (chk.checked) {
            if (store.selectedPages.indexOf(p.slug) === -1) store.selectedPages.push(p.slug);
            if (!store.pageBlocks[p.slug]) store.pageBlocks[p.slug] = (p.default_blocks || ["hero", "contact", "footer"]).slice();
          } else if (p.slug !== "index") {
            store.selectedPages = store.selectedPages.filter(function (x) { return x !== p.slug; });
          } else {
            chk.checked = true;
          }
          syncSelectedBlocks();
          renderPagesAndBlocksChecklists();
          renderBlockDescriptionInputs();
        });
        var sp = document.createElement("span");
        sp.textContent = store.lang === "ru" ? p.title_ru : p.title_en;
        lbl.appendChild(chk);
        lbl.appendChild(sp);
        pagesList.appendChild(lbl);
      });
    }

    var blockList = el("s4-page-blocks-list");
    if (!blockList) return;
    blockList.innerHTML = "";
    var blockMap = {};
    (store.catalog.available_blocks || []).forEach(function (b) { blockMap[b.id] = b; });
    var allBlocks = (store.catalog.available_blocks || []).map(function (b) { return b.id; });

    activePageSlugs().forEach(function (slug) {
      var preset = presetPage(slug);
      if (!preset) {
        preset = { slug: slug, title_ru: slug, title_en: slug, purpose_ru: "", purpose_en: "", default_blocks: ["hero", "contact", "footer"] };
        (store.catalog.preset_pages || []).push(preset);
      }
      var card = document.createElement("section");
      card.className = "page-block-card";
      var head = document.createElement("div");
      head.className = "page-block-head";
      var h3 = document.createElement("h3");
      h3.textContent = (store.lang === "ru" ? preset.title_ru : preset.title_en) + (store.lang === "en" ? " · " + slug + ".html" : "");
      var count = document.createElement("span");
      count.className = "page-block-count";
      var current = store.pageBlocks[slug] || [];
      count.textContent = current.filter(function (b) { return b !== "footer"; }).length + " " + (store.lang === "ru" ? "блоков" : "blocks");
      head.appendChild(h3);
      head.appendChild(count);
      card.appendChild(head);
      var purpose = document.createElement("p");
      purpose.className = "page-block-purpose";
      purpose.textContent = store.lang === "ru" ? (preset.purpose_ru || "") : (preset.purpose_en || "");
      if (purpose.textContent) card.appendChild(purpose);

      var grid = document.createElement("div");
      grid.className = "check-grid";
      var available = preset.available_blocks || allBlocks;
      available.forEach(function (bid) {
        if (bid === "footer") return;
        var meta = blockMap[bid] || { id: bid, title_ru: bid, title_en: bid };
        var lbl = document.createElement("label");
        lbl.className = "check-card";
        var chk = document.createElement("input");
        chk.type = "checkbox";
        chk.checked = (store.pageBlocks[slug] || []).indexOf(bid) !== -1;
        chk.addEventListener("change", function () {
          var arr = store.pageBlocks[slug] || [];
          if (chk.checked) {
            if (arr.indexOf(bid) === -1) arr.push(bid);
          } else if (arr.length > 1) {
            arr = arr.filter(function (x) { return x !== bid; });
          } else {
            chk.checked = true;
          }
          if (arr.indexOf("footer") === -1) arr.push("footer");
          store.pageBlocks[slug] = arr;
          syncSelectedBlocks();
          count.textContent = arr.filter(function (b) { return b !== "footer"; }).length + " " + (store.lang === "ru" ? "блоков" : "blocks");
          renderBlockDescriptionInputs();
        });
        var sp = document.createElement("span");
        sp.textContent = store.lang === "ru" ? meta.title_ru : meta.title_en;
        lbl.appendChild(chk);
        lbl.appendChild(sp);
        grid.appendChild(lbl);
      });
      card.appendChild(grid);
      blockList.appendChild(card);
    });
    syncSelectedBlocks();
  }

  function orderedBlocksForStep5(blocks) {
    var foundation = ["manifesto", "values", "priorities", "locations", "contact"];
    var head = [];
    var tail = [];
    blocks.forEach(function (bid) {
      if (bid === "footer") return;
      if (foundation.indexOf(bid) !== -1) head.push(bid);
      else tail.push(bid);
    });
    head.sort(function (a, b) { return foundation.indexOf(a) - foundation.indexOf(b); });
    return head.concat(tail);
  }

  function renderBlockDescriptionInputs() {
    var container = el("s5-block-descriptions-list");
    if (!container) return;
    container.innerHTML = "";
    ensurePageBlocks();
    var availMap = {};
    (store.catalog.available_blocks || []).forEach(function (b) { availMap[b.id] = b; });
    activePageSlugs().forEach(function (slug) {
      var blocks = orderedBlocksForStep5(store.pageBlocks[slug] || []);
      if (!blocks.length) return;
      var preset = presetPage(slug) || { title_ru: slug, title_en: slug };
      var group = document.createElement("section");
      group.className = "page-desc-group";
      var head = document.createElement("div");
      head.className = "page-desc-head";
      var h4 = document.createElement("h4");
      h4.textContent = store.lang === "ru" ? preset.title_ru : preset.title_en;
      var cnt = document.createElement("span");
      cnt.textContent = blocks.length + " " + (store.lang === "ru" ? "блоков" : "blocks");
      head.appendChild(h4);
      head.appendChild(cnt);
      group.appendChild(head);
      var list = document.createElement("div");
      list.className = "block-desc-list";
      blocks.forEach(function (bid) {
        var meta = availMap[bid] || { id: bid, title_ru: bid, title_en: bid };
        var card = document.createElement("div");
        card.className = "block-desc-card";
        var lbl = document.createElement("label");
        var inpId = "blk-desc-" + slug + "-" + bid;
        lbl.setAttribute("for", inpId);
        lbl.textContent = store.lang === "ru" ? meta.title_ru : meta.title_en;
        var ta = document.createElement("textarea");
        ta.id = inpId;
        ta.name = "studio_blk_" + slug + "_" + bid;
        ta.rows = 2;
        ta.setAttribute("autocomplete", "off");
        ta.setAttribute("data-lpignore", "true");
        ta.setAttribute("data-1p-ignore", "true");
        ta.setAttribute("data-bwignore", "true");
        ta.setAttribute("data-form-type", "other");
        ta.value = ((store.pageBlockPrompts[slug] || {})[bid]) || "";
        ta.placeholder = store.lang === "ru"
          ? "Опишите своими словами, что должно быть в этом блоке (пункты можно разделять точкой с запятой ; или |)..."
          : "Describe what you want inside this block (separate multiple items with ; or |)...";
        ta.addEventListener("input", function () {
          if (!store.pageBlockPrompts[slug]) store.pageBlockPrompts[slug] = {};
          store.pageBlockPrompts[slug][bid] = ta.value;
        });
        card.appendChild(lbl);
        card.appendChild(ta);
        list.appendChild(card);
      });
      group.appendChild(list);
      container.appendChild(group);
    });
  }

  function autofillBlockDescriptions() {
    var statusEl = el("s5-build-status");
    syncCompanyFromInputs();
    if (statusEl) {
      statusEl.textContent = store.lang === "ru"
        ? "Запуск ИИ: бренд-основа и описания блоков по страницам..."
        : "Running AI: brand foundation and per-page block copy...";
    }
    setBusy(true);
    var stopAutofillProgress = startAutofillProgress();
    var stopPolling = startProgressPolling(statusEl);
    var activePages = {};
    activePageSlugs().forEach(function (slug) {
      activePages[slug] = store.pageBlocks[slug] || [];
    });
    fetch("/api/orchestrator/autofill-blocks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: el("s2-name").value,
        brief: el("s2-desc").value,
        selected_blocks: store.selectedBlocks,
        page_blocks: activePages,
        company: store.company,
        lang: el("s1-lang").value
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        stopPolling();
        var hasWarnings = Array.isArray(res.warnings) && res.warnings.length > 0;
        if (res.error) {
          stopAutofillProgress(store.lang === "ru" ? "Ошибка" : "Error");
          setBusy(false);
          refreshEngineHUD();
          if (statusEl) statusEl.textContent = (store.lang === "ru" ? "Ошибка: " : "Error: ") + res.error;
          return;
        }
        stopAutofillProgress(
          hasWarnings
            ? (store.lang === "ru" ? "Заполнено с предупреждениями" : "Completed with warnings")
            : (store.lang === "ru" ? "Бренд-основа и блоки готовы" : "Foundation and blocks ready")
        );
        setBusy(false);
        refreshEngineHUD();
        if (res.company) {
          store.company = res.company;
          renderCompanyFields();
        }
        if (res.page_block_prompts) store.pageBlockPrompts = res.page_block_prompts;
        if (res.block_prompts) store.blockPrompts = res.block_prompts;
        renderBlockDescriptionInputs();
        if (statusEl) {
          if (hasWarnings) {
            statusEl.textContent = res.warnings.join(" | ");
          } else {
            statusEl.textContent = store.lang === "ru"
              ? "Бренд-основа и тексты по страницам заполнены. Проверьте и нажмите «Собрать сайт через Оркестратор»."
              : "Brand foundation and per-page copy filled. Review and click Build Site via Orchestrator.";
          }
        }
      })
      .catch(function (err) {
        stopPolling();
        stopAutofillProgress(store.lang === "ru" ? "Ошибка" : "Error");
        setBusy(false);
        refreshEngineHUD();
        if (statusEl) {
          statusEl.textContent = (store.lang === "ru" ? "Ошибка заполнения: " : "Autofill error: ") + (err && err.message ? err.message : String(err));
        }
      });
  }

  function syncRouteSelectFromDraft(draft) {
    var stageSel = el("stage-route-select");
    if (!stageSel || !draft || !draft.routes) return;
    stageSel.innerHTML = "";
    draft.routes.forEach(function (r, idx) {
      var opt = document.createElement("option");
      opt.value = String(idx);
      opt.textContent = r.title + " (" + r.filename + ")";
      stageSel.appendChild(opt);
    });
  }

  function runOrchestratorBuild(mode) {
    syncCompanyFromInputs();
    markOrchStages("queued");
    var isAuto = mode === "auto";
    var statusEl = isAuto ? el("exp-status-readout") : el("s5-build-status");
    if (statusEl) {
      statusEl.textContent = store.lang === "ru"
        ? "Запуск оркестратора: подготовка этапов генерации..."
        : "Starting orchestrator: preparing build stages...";
    }
    setBusy(true);
    var stopPolling = startProgressPolling(statusEl);

    var payload = isAuto
      ? {
          orchestrator_mode: "auto",
          auto_prompt: el("exp-brief-input").value,
          output_dir: el("exp-folder-input").value,
          languages: el("exp-lang-select").value,
          canon_id: el("exp-canon-select").value || undefined,
          polarity: store.polarity,
          motion: store.motion,
          landing_preset: store.landingPreset,
          render_images: true
        }
      : {
          orchestrator_mode: "constructor",
          output_dir: el("s1-folder-input").value,
          languages: el("s1-lang").value,
          name: el("s2-name").value,
          brief: el("s2-desc").value,
          goal: el("s2-desc").value,
          logo_prompt: el("s2-logo-prompt") ? el("s2-logo-prompt").value.trim() : "",
          selected_logo_path: store.draft ? store.draft.selected_logo_path : undefined,
          canon_id: store.draft ? store.draft.canon_id : "01_bento_grid",
          polarity: store.polarity,
          motion: store.motion,
          landing_preset: store.landingPreset,
          site_type: store.siteType,
          selected_pages: activePageSlugs(),
          page_blocks: store.pageBlocks,
          page_block_prompts: store.pageBlockPrompts,
          company: store.company,
          selected_blocks: store.selectedBlocks,
          block_prompts: store.blockPrompts,
          render_images: el("s5-render-visuals") ? el("s5-render-visuals").checked : true
        };

    fetch("/api/orchestrator/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(function (r) { return r.json(); })
      .then(function (bp) {
        stopPolling();
        setBusy(false);
        refreshEngineHUD();
        if (bp.error) {
          markOrchStages("error");
          if (statusEl) statusEl.textContent = (store.lang === "ru" ? "Ошибка сборки: " : "Build error: ") + bp.error;
          return;
        }
        markOrchStages("done");
        if (bp.orchestrator && bp.orchestrator.draft) {
          store.draft = bp.orchestrator.draft;
          syncRouteSelectFromDraft(store.draft);
        }
        if (bp.preview_url) {
          var sep = bp.preview_url.indexOf("?") === -1 ? "?" : "&";
          el("live-stage-iframe").src = bp.preview_url + sep + "t=" + Date.now();
          setStageOpen(true);
        }
        if (bp.project_dir) {
          syncProjectPathDisplay(bp.project_dir);
          if (store.draft) store.draft.output_dir = bp.project_dir;
        }
        if (statusEl) {
          var orch = bp.orchestrator || {};
          var aiTag = orch.ai_used
            ? (store.lang === "ru" ? "ИИ-текст" : "AI copy")
            : (store.lang === "ru" ? "базовый текст" : "fallback copy");
          var imgTag = orch.zimage_used
            ? (store.lang === "ru" ? "Z-Image графика" : "Z-Image art")
            : (store.lang === "ru" ? "без Z-Image" : "no Z-Image");
          statusEl.textContent = (store.lang === "ru" ? "Готово (" + aiTag + " + " + imgTag + ")! Сайт собран в: " : "Done (" + aiTag + " + " + imgTag + ")! Site built in: ") + (bp.project_dir || "");
        }
      })
      .catch(function (err) {
        stopPolling();
        setBusy(false);
        refreshEngineHUD();
        markOrchStages("error");
        if (statusEl) {
          statusEl.textContent = (store.lang === "ru" ? "Ошибка соединения со студией: " : "Studio request failed: ") + (err && err.message ? err.message : String(err));
        }
      });
  }

  var RU_TRANSLIT_MAP = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
    "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"
  };

  function slugifyPageTitle(raw) {
    var lower = String(raw || "").trim().toLowerCase();
    var out = "";
    for (var i = 0; i < lower.length; i++) {
      var ch = lower.charAt(i);
      out += Object.prototype.hasOwnProperty.call(RU_TRANSLIT_MAP, ch) ? RU_TRANSLIT_MAP[ch] : ch;
    }
    return out.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "page";
  }

  function renderPathDiagnostics(paths) {
    if (!paths) return;
    el("set-model-input").value = paths.gguf_model_path || "";
    el("set-llama-input").value = paths.llama_server_bin || "";
    el("set-sd-input").value = paths.sd_cli_bin || "";
    el("set-mmproj-input").value = paths.mmproj_path || "";
    el("set-dit-input").value = paths.dit_model_path || "";
    el("set-te-input").value = paths.te_model_path || "";
    el("set-vae-input").value = paths.vae_model_path || "";
    var flagMap = {
      gguf_model_path: "gguf_model_exists",
      llama_server_bin: "llama_server_exists",
      sd_cli_bin: "sd_cli_exists",
      mmproj_path: "mmproj_exists",
      dit_model_path: "dit_model_exists",
      te_model_path: "te_model_exists",
      vae_model_path: "vae_model_exists"
    };
    var diag = Object.keys(flagMap).map(function (k) {
      return (paths[flagMap[k]] ? "OK   " : "MISS ") + k + " = " + (paths[k] || "");
    });
    el("set-paths-status").textContent = diag.join("\n");
    var missing = (paths.missing_required || []).concat(paths.missing_visuals || []);
    var banner = el("setup-banner");
    if (banner) {
      banner.hidden = missing.length === 0;
      if (missing.length) {
        el("setup-banner-text").textContent = (store.lang === "ru" ? "Не найдены компоненты: " : "Missing components: ") + missing.join(", ");
      }
    }
  }

  function handleLogoUpload(file) {
    if (!file || !store.draft) return;
    var reader = new FileReader();
    reader.onload = function () {
      var resStr = String(reader.result || "");
      var b64 = resStr.indexOf(",") !== -1 ? resStr.split(",")[1] : resStr;
      fetch("/api/assets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          data_b64: b64,
          project_id: store.draft.id || "default",
          project_dir: el("s1-folder-input").value
        })
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.logo) {
            store.draft.logo = data.logo;
            store.draft.selected_logo_path = data.selected_logo_path || store.draft.selected_logo_path;
            if (data.preview_url) {
              el("live-stage-iframe").src = data.preview_url + (data.preview_url.indexOf("?") === -1 ? "?" : "&") + "t=" + Date.now();
            }
            el("s2-logo-status").textContent = (store.lang === "ru" ? "Загружен свой логотип: " : "Uploaded custom logo: ") + file.name;
          }
        });
    };
    reader.readAsDataURL(file);
  }

  function bindAllControls() {
    document.addEventListener("submit", function (ev) { ev.preventDefault(); });
    el("mode-btn-constructor").addEventListener("click", function () { setMode("constructor"); });
    el("mode-btn-express").addEventListener("click", function () { setMode("express"); });
    el("btn-lang-switch").addEventListener("click", function () {
      var nextLang = store.lang === "en" ? "ru" : "en";
      translateDOM(nextLang);
      fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: nextLang })
      }).catch(function () {});
    });
    el("btn-open-support").addEventListener("click", function () { el("modal-support").hidden = false; });
    el("hud-support-link-btn").addEventListener("click", function () { el("modal-support").hidden = false; });
    el("btn-close-support").addEventListener("click", function () { el("modal-support").hidden = true; });
    el("btn-open-settings").addEventListener("click", function () { el("modal-settings").hidden = false; });
    el("btn-close-settings").addEventListener("click", function () { el("modal-settings").hidden = true; });
    el("btn-toggle-stage-drawer").addEventListener("click", function () {
      setStageOpen(!store.stageOpen);
    });
    if (el("btn-topbar-random-template")) {
      el("btn-topbar-random-template").addEventListener("click", function () { runRandomStarterTemplate(true); });
    }
    if (el("s2-random-template-btn")) {
      el("s2-random-template-btn").addEventListener("click", function () { runRandomStarterTemplate(true); });
    }
    if (el("s5-reroll-starter-btn")) {
      el("s5-reroll-starter-btn").addEventListener("click", function () { runRandomStarterTemplate(true); });
    }
    if (el("s5-goto-step2-btn")) {
      el("s5-goto-step2-btn").addEventListener("click", function () { setStep(2); });
    }
    if (el("s5-goto-step3-btn")) {
      el("s5-goto-step3-btn").addEventListener("click", function () { setStep(3); });
    }
    if (el("starter-instant-btn")) {
      el("starter-instant-btn").addEventListener("click", function () { runRandomStarterTemplate(false); });
    }
    if (el("starter-skip-btn")) {
      el("starter-skip-btn").addEventListener("click", function () {
        if (store.starterAbort) {
          try { store.starterAbort.abort(); } catch (e) {}
        }
        stopStarterPreloader(store.starterAbort);
      });
    }
    if (el("fp-up-btn")) {
      el("fp-up-btn").addEventListener("click", function () {
        if (fpState.parentDir) loadDirectoryIntoPicker(fpState.parentDir);
      });
    }
    if (el("fp-mkdir-btn")) {
      el("fp-mkdir-btn").addEventListener("click", function () {
        var inp = el("fp-new-name");
        var fname = inp ? inp.value.trim() : "";
        if (!fname || !fpState.currentDir) return;
        fetch("/api/fs/mkdir", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ parent_dir: fpState.currentDir, name: fname })
        })
          .then(function (r) { return r.json(); })
          .then(function (res) {
            if (res && res.path) {
              if (inp) inp.value = "";
              loadDirectoryIntoPicker(res.path);
            } else if (el("fp-status")) {
              el("fp-status").textContent = (res && res.message) || (res && res.error) || "Error";
            }
          });
      });
    }
    if (el("fp-new-name")) {
      el("fp-new-name").addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && el("fp-mkdir-btn")) {
          ev.preventDefault();
          el("fp-mkdir-btn").click();
        }
      });
    }
    if (el("fp-copy-btn")) {
      el("fp-copy-btn").addEventListener("click", function () {
        if (fpState.currentDir && navigator.clipboard) {
          navigator.clipboard.writeText(fpState.currentDir).catch(function () {});
        }
        if (el("fp-status")) el("fp-status").textContent = (store.lang === "ru" ? "Скопировано: " : "Copied: ") + fpState.currentDir;
      });
    }
    if (el("fp-select-btn")) {
      el("fp-select-btn").addEventListener("click", function () {
        if (fpState.onPicked && fpState.currentDir) fpState.onPicked(fpState.currentDir);
        if (el("modal-folder-picker")) el("modal-folder-picker").hidden = true;
      });
    }
    if (el("fp-close-btn")) {
      el("fp-close-btn").addEventListener("click", function () {
        if (el("modal-folder-picker")) el("modal-folder-picker").hidden = true;
      });
    }

    for (var s = 1; s <= 5; s++) {
      (function (stepIdx) {
        el("nav-step-" + stepIdx).addEventListener("click", function () { setStep(stepIdx); });
      })(s);
    }
    ["s1-next-btn", "s2-prev-btn", "s2-next-btn", "s3-prev-btn", "s3-next-btn", "s4-prev-btn", "s4-next-btn", "s5-prev-btn"].forEach(function (id) {
      el(id).addEventListener("click", function (ev) { setStep(ev.currentTarget.getAttribute("data-target")); });
    });

    el("btn-reset-draft").addEventListener("click", function () {
      fetch("/api/projects/default").then(function (r) { return r.json(); }).then(function (d) {
        store.draft = d;
        initializePageState();
        initializeCompanyState();
        renderPagesAndBlocksChecklists();
        renderBlockDescriptionInputs();
        setStep(1);
      });
    });

    // Automatic mode controls
    el("exp-folder-input").addEventListener("input", function () { syncProjectPathDisplay(el("exp-folder-input").value); });
    el("exp-pick-folder-btn").addEventListener("click", function () {
      pickProjectFolder("exp-pick-folder-btn", "exp-status-readout", "exp-folder-input");
    });
    el("exp-brief-input").addEventListener("input", function () {});
    el("exp-lang-select").addEventListener("change", function () {});
    if (el("exp-canon-select")) el("exp-canon-select").addEventListener("change", function () {});
    if (el("exp-landing-preset")) el("exp-landing-preset").addEventListener("change", function (ev) { setLandingPreset(ev.target.value, false); });
    if (el("exp-motion-select")) el("exp-motion-select").addEventListener("change", function (ev) { setMotion(ev.target.value); });
    el("exp-generate-btn").addEventListener("click", function () { runOrchestratorBuild("auto"); });
    el("exp-open-folder-btn").addEventListener("click", function () {
      revealProjectFolder(el("exp-folder-input").value || (store.draft && store.draft.output_dir) || "", "exp-status-readout");
    });

    // Step 1 controls
    el("s1-folder-input").addEventListener("input", function () { syncProjectPathDisplay(el("s1-folder-input").value); });
    el("setup-auto-btn").addEventListener("click", function () {
      var btn = el("setup-auto-btn");
      btn.disabled = true;
      el("setup-progress").textContent = store.lang === "ru" ? "Запуск загрузки..." : "Starting download...";
      fetch("/api/setup/auto", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.status === "nothing_to_do") { el("setup-banner").hidden = true; btn.disabled = false; return; }
          if (d.error) { el("setup-progress").textContent = d.error + (d.message ? ": " + d.message : ""); btn.disabled = false; return; }
          var timer = setInterval(function () {
            fetch("/api/setup/progress").then(function (r) { return r.json(); }).then(function (p) {
              el("setup-progress").textContent = p.line || "";
              if (p.done) {
                clearInterval(timer);
                btn.disabled = false;
                if (p.error) {
                  el("setup-progress").textContent = (store.lang === "ru" ? "Ошибка: " : "Error: ") + p.error;
                } else {
                  el("setup-progress").textContent = store.lang === "ru" ? "Готово! Перезагружаю интерфейс..." : "Done! Reloading UI...";
                  setTimeout(function () { location.reload(); }, 1200);
                }
              }
            }).catch(function () {});
          }, 2000);
        })
        .catch(function (e) { el("setup-progress").textContent = String(e); btn.disabled = false; });
    });
    el("s1-pick-folder-btn").addEventListener("click", function () {
      pickProjectFolder("s1-pick-folder-btn", "s1-folder-status", "s1-folder-input");
    });
    el("s1-open-folder-btn").addEventListener("click", function () {
      revealProjectFolder(el("s1-folder-input").value, "s1-folder-status");
    });
    el("s1-lang").addEventListener("change", function () {});

    // Step 2 controls
    el("s2-name").addEventListener("input", function () {});
    el("s2-desc").addEventListener("input", function () {});
    el("s2-logo-prompt").addEventListener("input", function () {});
    el("s2-gen-logos-btn").addEventListener("click", generateSixLogos);
    el("s2-upload-logo-btn").addEventListener("click", function () { el("s2-logo-file").click(); });
    el("s2-logo-file").addEventListener("change", function (ev) { if (ev.target.files && ev.target.files[0]) handleLogoUpload(ev.target.files[0]); });

    // Step 3 controls
    el("s3-canon-search").addEventListener("input", renderCanons);
    el("s3-canon-cat").addEventListener("change", renderCanons);
    if (el("s3-motion-select")) el("s3-motion-select").addEventListener("change", function (ev) { setMotion(ev.target.value, true); });
    ["auto", "light", "dark"].forEach(function (mode) {
      var btn = el("s3-polarity-" + mode);
      if (btn) btn.addEventListener("click", function () { setPolarity(mode, true); });
    });

    // Step 4 controls
    el("s4-type-single-btn").addEventListener("click", function () {
      store.siteType = "single";
      renderPagesAndBlocksChecklists();
    });
    el("s4-type-multi-btn").addEventListener("click", function () {
      store.siteType = "multi";
      renderPagesAndBlocksChecklists();
    });
    el("s4-custom-page-input").addEventListener("input", function () {});
    el("s4-add-page-btn").addEventListener("click", function () {
      var raw = el("s4-custom-page-input").value.trim();
      if (!raw) return;
      var slug = slugifyPageTitle(raw);
      var allBlocks = (store.catalog.available_blocks || []).map(function (b) { return b.id; });
      store.catalog.preset_pages.push({
        slug: slug,
        title_ru: raw,
        title_en: raw,
        purpose_ru: "Пользовательская страница проекта.",
        purpose_en: "Custom project page.",
        default_blocks: ["hero", "contact", "footer"],
        available_blocks: allBlocks
      });
      store.pageBlocks[slug] = ["hero", "contact", "footer"];
      if (store.selectedPages.indexOf(slug) === -1) store.selectedPages.push(slug);
      el("s4-custom-page-input").value = "";
      renderPagesAndBlocksChecklists();
    });

    // Step 5 controls
    ["s5-tagline", "s5-positioning", "s5-values", "s5-priorities", "s5-cities", "s5-address", "s5-phone", "s5-email", "s5-hours"].forEach(function (id) {
      el(id).addEventListener("input", syncCompanyFromInputs);
    });
    el("s5-autofill-btn").addEventListener("click", autofillBlockDescriptions);
    el("s5-build-site-btn").addEventListener("click", function () { runOrchestratorBuild("constructor"); });
    var rvToggle = el("s5-render-visuals");
    if (rvToggle) rvToggle.addEventListener("change", function () {
      var st = el("s5-build-status");
      if (st) st.textContent = rvToggle.checked
        ? (store.lang === "ru" ? "Визуалы Z-Image будут отрендерены при сборке." : "Z-Image visuals will be rendered during the build.")
        : (store.lang === "ru" ? "Сборка без рендера визуалов (быстрее)." : "Build without visual rendering (faster).");
    });
    el("s5-export-zip-btn").addEventListener("click", function () {
      var zipBtn = el("s5-export-zip-btn");
      var statusEl = el("s5-build-status");
      var pid = (store.draft && store.draft.id) || "default";
      if (zipBtn) zipBtn.disabled = true;
      if (statusEl) statusEl.textContent = store.lang === "ru" ? "Создаём ZIP-архив..." : "Building ZIP archive...";
      fetch("/api/export/" + encodeURIComponent(pid), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_dir: el("s1-folder-input").value || (store.draft && store.draft.output_dir) || "", as_zip: true })
      })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
        .then(function (resp) {
          var res = resp.data || {};
          if (!resp.ok || res.error) {
            if (statusEl) statusEl.textContent = (store.lang === "ru" ? "Ошибка экспорта ZIP: " : "ZIP export error: ") + (res.message || res.error || "failed");
            return;
          }
          var dlName = res.filename || "site_bundle.zip";
          if (!res.download_url) {
            if (statusEl) statusEl.textContent = store.lang === "ru" ? "Ошибка экспорта ZIP: нет ссылки скачивания." : "ZIP export error: missing download URL.";
            return;
          }
          return fetch(res.download_url)
            .then(function (dlResp) {
              if (!dlResp.ok) throw new Error("HTTP " + dlResp.status);
              return dlResp.blob();
            })
            .then(function (blob) {
              var objUrl = URL.createObjectURL(blob);
              var a = document.createElement("a");
              a.href = objUrl;
              a.download = dlName;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              setTimeout(function () { URL.revokeObjectURL(objUrl); }, 2000);
              if (statusEl) {
                statusEl.textContent = store.lang === "ru"
                  ? ("ZIP-архив «" + dlName + "» скачан в папку «Загрузки» браузера.")
                  : ('ZIP archive "' + dlName + '" downloaded to your browser\'s Downloads folder.');
              }
              if (res.show_support_card) el("pwyw-post-export-card").hidden = false;
            });
        })
        .catch(function (err) {
          if (statusEl) statusEl.textContent = (store.lang === "ru" ? "Ошибка скачивания ZIP: " : "ZIP download failed: ") + (err && err.message ? err.message : String(err));
        })
        .finally(function () {
          if (zipBtn) zipBtn.disabled = false;
        });
    });
    el("s5-reveal-folder-btn").addEventListener("click", function () {
      revealProjectFolder(el("s1-folder-input").value || (store.draft && store.draft.output_dir) || "", "s5-build-status");
    });

    // Support & PWYW VKVstudio buttons + direct crypto wallet copy controls
    ["pwyw-card-donate-btn", "btn-support-donate"].forEach(function (id) {
      el(id).addEventListener("click", function () {
        el("pwyw-post-export-card").hidden = true;
        window.open("https://github.com/VKVstudio/.github/blob/main/DONATE.md", "_blank", "noopener");
      });
    });
    ["pwyw-card-vkv-btn", "btn-support-vkv"].forEach(function (id) {
      el(id).addEventListener("click", function () {
        el("pwyw-post-export-card").hidden = true;
        window.open("https://github.com/VKVstudio", "_blank", "noopener");
      });
    });
    ["btn-copy-wallet-trc20", "btn-copy-wallet-ton", "btn-copy-wallet-evm", "btn-copy-wallet-btc"].forEach(function (id) {
      el(id).addEventListener("click", function (ev) {
        var btn = ev.currentTarget;
        var addr = btn.getAttribute("data-address") || "";
        var dict = store.i18n[store.lang] || {};
        if (addr && navigator.clipboard) navigator.clipboard.writeText(addr).catch(function () {});
        btn.textContent = dict.msg_wallet_copied || "Copied";
        setTimeout(function () {
          var curDict = store.i18n[store.lang] || {};
          btn.textContent = curDict.btn_copy_wallet || "Copy";
        }, 1600);
      });
    });
    el("pwyw-card-not-now-btn").addEventListener("click", function () { el("pwyw-post-export-card").hidden = true; });
    el("pwyw-card-dismiss-btn").addEventListener("click", function () {
      el("pwyw-post-export-card").hidden = true;
      fetch("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ support_card_dismissed: true }) });
    });

    // Live Stage toolbar controls
    ["vp-btn-1440", "vp-btn-834", "vp-btn-390"].forEach(function (id) {
      el(id).addEventListener("click", function (ev) {
        el("live-stage-iframe").style.width = ev.currentTarget.getAttribute("data-vp");
      });
    });
    el("stage-route-select").addEventListener("change", function () {
      var idx = parseInt(el("stage-route-select").value || "0", 10) || 0;
      var route = (store.draft && store.draft.routes && store.draft.routes[idx]) || { filename: "index.html" };
      var pid = (store.draft && store.draft.id) || "default";
      el("live-stage-iframe").src = "/preview/" + encodeURIComponent(pid) + "/" + route.filename;
    });
    el("stage-reload-btn").addEventListener("click", function () {
      var ifr = el("live-stage-iframe");
      ifr.src = ifr.src;
    });
    el("stage-browser-btn").addEventListener("click", function () {
      window.open(el("live-stage-iframe").src, "_blank", "noopener");
    });
    el("stage-audit-btn").addEventListener("click", function () {
      var ov = el("stage-audit-overlay");
      ov.hidden = !ov.hidden;
    });

    // HUD & Settings controls
    el("hud-start-llm-btn").addEventListener("click", function () {
      fetch("/api/engine/llm/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then(function () { refreshEngineHUD(); });
    });
    el("hud-stop-llm-btn").addEventListener("click", function () {
      fetch("/api/engine/llm/stop", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then(function () { refreshEngineHUD(); });
    });
    el("hud-quit-studio-btn").addEventListener("click", function () {
      el("hud-quit-studio-btn").disabled = true;
      fetch("/api/studio/shutdown", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
        .then(function () { el("hud-engine-state").textContent = "stopped"; })
        .catch(function () { el("hud-engine-state").textContent = "stopped"; });
    });
    ["set-model-input", "set-llama-input", "set-sd-input", "set-mmproj-input", "set-dit-input", "set-te-input", "set-vae-input", "set-support-mode"].forEach(function (id) {
      el(id).addEventListener("input", function () {});
      el(id).addEventListener("change", function () {});
    });
    el("btn-save-settings").addEventListener("click", function () {
      fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          support_mode: el("set-support-mode").value,
          paths: {
            gguf_model_path: el("set-model-input").value,
            llama_server_bin: el("set-llama-input").value,
            sd_cli_bin: el("set-sd-input").value,
            mmproj_path: el("set-mmproj-input").value,
            dit_model_path: el("set-dit-input").value,
            te_model_path: el("set-te-input").value,
            vae_model_path: el("set-vae-input").value
          }
        })
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (res && res.settings && res.settings.paths) {
            renderPathDiagnostics(res.settings.paths);
          }
          el("modal-settings").hidden = true;
        });
    });

    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") {
        el("modal-settings").hidden = true;
        el("modal-support").hidden = true;
        if (el("modal-folder-picker")) el("modal-folder-picker").hidden = true;
        if (el("starter-preloader") && !el("starter-preloader").hidden) {
          if (store.starterAbort) {
            try { store.starterAbort.abort(); } catch (e) {}
          }
          stopStarterPreloader(store.starterAbort);
        }
      }
    });
  }

  function refreshEngineHUD() {
    fetch("/api/engine")
      .then(function (r) { return r.json(); })
      .then(function (eng) {
        el("hud-engine-state").textContent = eng.state || "idle";
        var vramEl = el("hud-vram-val");
        if (vramEl && eng.telemetry && eng.telemetry.gpu) {
          vramEl.textContent = (eng.telemetry.gpu.vram_used_mib || 0) + " MiB";
        }
        var dotEl = el("hud-dot");
        if (dotEl) {
          dotEl.setAttribute("data-state", eng.gpu_busy ? "busy" : "idle");
        }
        el("hud-lock-val").textContent = eng.gpu_busy ? ("GPU busy: " + (eng.lock_owner || "self")) : (eng.lock_owner || "free");
        el("hud-start-llm-btn").disabled = Boolean(eng.gpu_busy);
        el("hud-speed-val").textContent = (eng.tok_per_sec || 0) + " tok/s";
        if (eng.telemetry) {
          el("hud-ram-val").textContent = eng.telemetry.mem_avail_gib + " GiB";
        }
      })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindAllControls();

    Promise.all([
      fetch("/static/i18n/en.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
      fetch("/static/i18n/ru.json", { cache: "no-store" }).then(function (r) { return r.json(); }),
      fetch("/api/catalog").then(function (r) { return r.json(); }),
      fetch("/api/projects/default").then(function (r) { return r.json(); }),
      fetch("/api/status").then(function (r) { return r.json(); })
    ])
      .then(function (res) {
        store.i18n.en = res[0];
        store.i18n.ru = res[1];
        store.catalog = res[2];
        store.draft = res[3];
        if (store.draft) {
          if (store.draft.name && String(store.draft.name).trim()) {
            el("s2-name").value = String(store.draft.name).trim();
          }
          var draftBrief = store.draft.brief || store.draft.goal;
          if (draftBrief && String(draftBrief).trim()) {
            el("s2-desc").value = String(draftBrief).trim();
          }
          var draftLang = String(store.draft.languages || "").toLowerCase();
          if (draftLang === "ru" || draftLang === "en" || draftLang === "en+ru") {
            el("s1-lang").value = draftLang;
          }
          if (store.draft.logo_prompt && el("s2-logo-prompt")) {
            el("s2-logo-prompt").value = String(store.draft.logo_prompt);
          }
        }
        initializePageState();
        initializeCompanyState();
        var st = res[4];
        if (st && st.version) {
          var vBadge = el("app-version-badge");
          if (vBadge) vBadge.textContent = "v" + st.version;
          document.title = "SmartLLM Studio v" + st.version;
        }
        var initLang = (st && st.settings && st.settings.language) || "ru";
        setStageOpen(false);
        setPolarity((store.draft && store.draft.polarity) || "auto");
        setLandingPreset((store.draft && store.draft.landing_preset) || "gsap_scrollytelling", false);
        var initMotion = (store.draft && store.draft.motion) || "motion";
        if (store.draft && store.draft.name === "Quartz-Field Atelier" && (store.draft.revision || 1) <= 1 && initMotion === "css_scroll_driven") {
          initMotion = "motion";
        }
        setMotion(initMotion);
        syncRouteSelectFromDraft(store.draft);
        translateDOM(initLang);
        if (st && st.paths) {
          var pathSep = String(st.paths.projects_root || "").indexOf("\\") !== -1 ? "\\" : "/";
          var defDir = store.draft.output_dir || (st.paths.projects_root + pathSep + "default");
          syncProjectPathDisplay(defDir);
          renderPathDiagnostics(st.paths);
        }
        refreshEngineHUD();
        setInterval(refreshEngineHUD, 2500);

        var skipStarter = window.location.search.indexOf("skip_starter=1") !== -1;
        var alreadyInited = false;
        try { alreadyInited = window.sessionStorage.getItem("smartllm_starter_init") === "1"; } catch (e0) {}
        if (!skipStarter && !alreadyInited) {
          try { window.sessionStorage.setItem("smartllm_starter_init", "1"); } catch (e1) {}
          runRandomStarterTemplate(true);
        }
      })
      .catch(function () {});
  });
})();
