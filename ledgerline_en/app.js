(function () {
  "use strict";
  var root = document.documentElement;
  root.setAttribute("data-stack", "html5_esm");
  root.setAttribute("data-motion", "motion");
  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.setAttribute("data-reduced-motion", reduced ? "reduce" : "no-preference");
  var I18N = {};
  var BILINGUAL = false;
  var PRIMARY = "en";
  var MOTION_MODE = "motion";
  var STAGGER_MS = 25;
  var PARALLAX_ON = true;
  var MAGNETIC_ON = true;
  var TILT_ON = false;
  function applyLang(l) {
    if (!BILINGUAL) return;
    root.lang = l;
    var nodes = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < nodes.length; i++) {
      var e = I18N[nodes[i].getAttribute("data-i18n")];
      if (e && e[l] && nodes[i].children.length === 0) nodes[i].textContent = e[l];
    }
    var alts = document.querySelectorAll("[data-i18n-alt]");
    for (var j = 0; j < alts.length; j++) {
      var ea = I18N[alts[j].getAttribute("data-i18n-alt")];
      if (ea && ea[l]) alts[j].setAttribute("alt", ea[l]);
    }
    var arias = document.querySelectorAll("[data-i18n-aria]");
    for (var a = 0; a < arias.length; a++) {
      var ear = I18N[arias[a].getAttribute("data-i18n-aria")];
      if (ear && ear[l]) arias[a].setAttribute("aria-label", ear[l]);
    }
    var metas = document.querySelectorAll("[data-i18n-content]");
    for (var k = 0; k < metas.length; k++) {
      var em = I18N[metas[k].getAttribute("data-i18n-content")];
      if (em && em[l]) metas[k].setAttribute("content", em[l]);
    }
    var btns = document.querySelectorAll(".lang-switch button");
    for (var b = 0; b < btns.length; b++) btns[b].setAttribute("aria-pressed", btns[b].getAttribute("data-lang") === l ? "true" : "false");
    try { localStorage.setItem("slm-lang", l); } catch (err) {}
  }
  if (BILINGUAL) {
    var saved = null;
    try { saved = localStorage.getItem("slm-lang"); } catch (err) {}
    var switcher = document.querySelector(".lang-switch");
    if (switcher) switcher.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-lang]");
      if (btn) applyLang(btn.getAttribute("data-lang"));
    });
    if (saved && saved !== PRIMARY) applyLang(saved);
  }
  var navToggle = document.getElementById("mobile-nav-toggle");
  var navList = document.getElementById("primary-nav-list");
  if (navToggle && navList) {
    navToggle.addEventListener("click", function () {
      var expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      navList.setAttribute("data-open", expanded ? "false" : "true");
    });
  }
  var mqToggle = document.querySelector(".marquee-toggle");
  if (mqToggle) {
    mqToggle.addEventListener("click", function () {
      var wrap = mqToggle.closest(".marquee");
      if (!wrap) return;
      var paused = wrap.getAttribute("data-paused") === "true";
      wrap.setAttribute("data-paused", paused ? "false" : "true");
      mqToggle.setAttribute("aria-pressed", paused ? "false" : "true");
    });
  }
  document.querySelectorAll(".carousel-btn[data-dir]").forEach(function (cbtn) {
    cbtn.addEventListener("click", function () {
      var sec = cbtn.closest(".section-block");
      var grid = sec ? sec.querySelector(".canon-grid") : null;
      if (!grid) return;
      var dir = parseInt(cbtn.getAttribute("data-dir") || "1", 10) || 1;
      grid.scrollBy({ left: dir * 340, behavior: reduced ? "auto" : "smooth" });
    });
  });
  function animateStatCounters() {
    if (reduced || MOTION_MODE === "reduced_motion_instant") return;
    var stats = Array.prototype.slice.call(document.querySelectorAll(".stat-value"));
    if (!stats.length) return;
    function runCounter(el) {
      if (el.getAttribute("data-counted") === "1") return;
      el.setAttribute("data-counted", "1");
      var raw = (el.textContent || "").trim();
      var m = raw.match(/^([^0-9-]*)(-?[0-9][0-9., ]*)(.*)$/);
      if (!m || /^[/:-]/.test(m[3]) || (/[-/:.]/.test(m[2]) && !/[.,][0-9]{1,2}$/.test(m[2]))) return;
      var numStr = m[2].replace(/\s+/g, "").replace(",", ".");
      var target = parseFloat(numStr);
      if (!isFinite(target) || target <= 0 || (target >= 1900 && target <= 2100 && !m[3])) return;
      var decimals = (numStr.split(".")[1] || "").length;
      var prefix = m[1] || "";
      var suffix = m[3] || "";
      var start = null;
      var dur = 760;
      function step(ts) {
        if (!start) start = ts;
        var p = Math.min(1, (ts - start) / dur);
        var eased = 1 - Math.pow(1 - p, 3);
        var val = (target * eased).toFixed(decimals);
        if (decimals === 0 && target >= 1000 && m[2].indexOf(" ") !== -1) {
          val = val.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
        }
        el.textContent = prefix + val + suffix;
        if (p < 1) window.requestAnimationFrame(step);
        else el.textContent = raw;
      }
      window.requestAnimationFrame(step);
    }
    if ("IntersectionObserver" in window) {
      var so = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            runCounter(en.target);
            so.unobserve(en.target);
          }
        });
      }, { threshold: 0.2 });
      stats.forEach(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top <= (window.innerHeight || 900)) runCounter(el);
        else so.observe(el);
      });
    }
  }
  function setupPointerInteractions() {
    if (reduced || !window.matchMedia || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    if (MAGNETIC_ON) {
      document.querySelectorAll(".hero-shell .cta-row .btn, .cta-banner .btn").forEach(function (btn) {
        btn.addEventListener("pointermove", function (ev) {
          var r = btn.getBoundingClientRect();
          var dx = ((ev.clientX - r.left) / Math.max(1, r.width) - 0.5) * 10;
          var dy = ((ev.clientY - r.top) / Math.max(1, r.height) - 0.5) * 7;
          btn.style.transform = "translate3d(" + dx.toFixed(1) + "px," + dy.toFixed(1) + "px,0)";
        });
        btn.addEventListener("pointerleave", function () {
          btn.style.transform = "";
        });
      });
    }
    if (TILT_ON) {
      var heroFig = document.querySelector(".hero-shell .hero-figure");
      if (heroFig) {
        heroFig.addEventListener("pointermove", function (ev) {
          var r = heroFig.getBoundingClientRect();
          var rx = ((ev.clientY - r.top) / Math.max(1, r.height) - 0.5) * -4;
          var ry = ((ev.clientX - r.left) / Math.max(1, r.width) - 0.5) * 5;
          heroFig.style.transform = "perspective(1100px) rotateX(" + rx.toFixed(2) + "deg) rotateY(" + ry.toFixed(2) + "deg)";
        });
        heroFig.addEventListener("pointerleave", function () {
          heroFig.style.transform = "";
        });
      }
    }
  }
  if (!reduced && MOTION_MODE !== "reduced_motion_instant") {
    var revealEls = Array.prototype.slice.call(document.querySelectorAll(".section-block [data-reveal]"));
    var markRevealed = function (el) {
      el.classList.remove("slm-pending");
      el.classList.add("is-revealed");
    };
    if (revealEls.length) {
      var groups = {};
      var vhInit = window.innerHeight || root.clientHeight || 900;
      revealEls.forEach(function (el) {
        var sec = el.closest("section") || root;
        var key = sec.id || "root";
        groups[key] = groups[key] || 0;
        el.style.setProperty("--rd", (groups[key]++ * 25) + "ms");
        if (el.getBoundingClientRect().top <= vhInit * 0.92) {
          markRevealed(el);
        } else {
          el.classList.add("slm-pending");
        }
      });
      var io = null;
      var cleanupReveal = function () {
        window.removeEventListener("scroll", revealVisible);
        window.removeEventListener("resize", revealVisible);
      };
      var revealVisible = function () {
        var vh = window.innerHeight || root.clientHeight || 900;
        var remaining = 0;
        for (var idx = 0; idx < revealEls.length; idx++) {
          var el = revealEls[idx];
          if (el.classList.contains("is-revealed")) continue;
          if (el.getBoundingClientRect().top <= vh + 80) {
            markRevealed(el);
            if (io) io.unobserve(el);
          } else {
            remaining++;
          }
        }
        if (remaining === 0) cleanupReveal();
      };
      if ("IntersectionObserver" in window) {
        revealVisible();
        root.classList.add("js");
        io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (en.isIntersecting) {
              markRevealed(en.target);
              io.unobserve(en.target);
            }
          });
        }, { threshold: 0.01, rootMargin: "0px 0px 40px 0px" });
        var pendingReveal = 0;
        revealEls.forEach(function (el) {
          if (!el.classList.contains("is-revealed")) {
            io.observe(el);
            pendingReveal++;
          }
        });
        if (pendingReveal > 0) {
          window.requestAnimationFrame(revealVisible);
          window.setTimeout(revealVisible, 550);
          window.addEventListener("scroll", revealVisible, { passive: true });
          window.addEventListener("resize", revealVisible, { passive: true });
        }
      } else {
        revealEls.forEach(function (el) { markRevealed(el); });
        root.classList.add("js");
      }
    } else {
      root.classList.add("js");
    }
    var scrollySteps = Array.prototype.slice.call(document.querySelectorAll(".scrolly-stage .scrolly-step"));
    if (scrollySteps.length) {
      var scCounter = document.getElementById("scrolly-counter");
      var scCaption = document.getElementById("scrolly-caption");
      var scPinImg = document.querySelector(".scrolly-pin img");
      var activateStep = function (stepEl, idx) {
        scrollySteps.forEach(function (st, j) {
          st.classList.toggle("is-active", j === idx);
        });
        var total = String(scrollySteps.length).padStart(2, "0");
        var curNum = String(idx + 1).padStart(2, "0");
        if (scCounter) scCounter.textContent = curNum + " / " + total;
        var ttl = stepEl.getAttribute("data-step-title");
        if (scCaption && ttl) scCaption.textContent = ttl;
        if (scPinImg) {
          var scScale = 1 + (idx * 0.018);
          if (window.Motion && typeof window.Motion.animate === "function") {
            window.Motion.animate(scPinImg, { scale: scScale }, { duration: 0.45, ease: [0.22, 1, 0.36, 1] });
          } else {
            scPinImg.style.transform = "scale(" + scScale.toFixed(3) + ")";
          }
        }
      };
      if ("IntersectionObserver" in window) {
        var stepIo = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (!en.isIntersecting) return;
            var idx = scrollySteps.indexOf(en.target);
            if (idx >= 0) activateStep(en.target, idx);
          });
        }, { rootMargin: "-30% 0px -30% 0px", threshold: 0.05 });
        scrollySteps.forEach(function (st) { stepIo.observe(st); });
      }
      scrollySteps.forEach(function (st, idx) {
        st.addEventListener("pointerenter", function () { activateStep(st, idx); });
      });
    }
    var bar = document.querySelector(".scroll-progress");
    var heroImg = document.querySelector(".hero-figure img");
    var ticking = false;
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        ticking = false;
        var max = root.scrollHeight - window.innerHeight;
        if (bar && MOTION_MODE !== "css_scroll_driven") bar.style.transform = "scaleX(" + (max > 0 ? Math.min(1, window.scrollY / max) : 0) + ")";
        if (PARALLAX_ON && heroImg) {
          var r = heroImg.getBoundingClientRect();
          if (r.bottom > 0 && r.top < window.innerHeight) heroImg.style.transform = "translateY(" + Math.min(28, window.scrollY * 0.055).toFixed(1) + "px) scale(1.03)";
        }
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    animateStatCounters();
    setupPointerInteractions();
  } else {
    document.querySelectorAll("[data-reveal]").forEach(function (el) { el.classList.remove("slm-pending"); el.classList.add("is-revealed"); });
    root.classList.add("js");
    root.setAttribute("data-motion-active", "reduced");
  }
  function bootVendorMotion() {
    if (reduced || MOTION_MODE === "reduced_motion_instant") return;
    var activeParts = [];
    if (typeof window.Lenis === "function" && (MOTION_MODE === "motion" || MOTION_MODE === "animejs" || MOTION_MODE === "lenis" || MOTION_MODE === "three")) {
      try {
        window.__slmLenis = new window.Lenis({
          autoRaf: true,
          lerp: 0.088,
          wheelMultiplier: 1.0,
          smoothWheel: true,
          anchors: true,
          respectReducedMotion: true
        });
        activeParts.push("lenis");
      } catch (err) {}
    }
    var M = window.Motion;
    if (MOTION_MODE === "motion" && M && typeof M.animate === "function") {
      activeParts.unshift("motion");
      try {
        var heroNodes = Array.prototype.slice.call(document.querySelectorAll(".hero-shell .eyebrow, .hero-shell h1, .hero-shell .lead-copy, .hero-shell .cta-row"));
        if (heroNodes.length && typeof M.stagger === "function") {
          M.animate(heroNodes, { opacity: [0.001, 1], y: [22, 0] }, { duration: 0.56, delay: M.stagger(0.065), ease: [0.22, 1, 0.36, 1] });
        }
        var hFig = document.querySelector(".hero-shell .hero-figure");
        if (hFig) {
          M.animate(hFig, { opacity: [0.001, 1], scale: [0.96, 1] }, { duration: 0.68, ease: [0.16, 1, 0.3, 1] });
        }
        var barEl = document.querySelector(".scroll-progress");
        if (barEl && typeof M.scroll === "function") {
          M.scroll(function (prog) {
            if (typeof prog === "number") barEl.style.transform = "scaleX(" + Math.max(0, Math.min(1, prog)).toFixed(4) + ")";
          });
        }
        if (typeof M.inView === "function" && typeof M.stagger === "function") {
          document.querySelectorAll(".section-block").forEach(function (sec) {
            var pendingCards = Array.prototype.slice.call(sec.querySelectorAll("[data-reveal].slm-pending"));
            if (!pendingCards.length) return;
            M.inView(sec, function () {
              var allCards = Array.prototype.slice.call(sec.querySelectorAll("[data-reveal]"));
              allCards.forEach(function (c) {
                c.classList.remove("slm-pending");
                c.classList.add("is-revealed");
              });
              M.animate(allCards, { opacity: [0.001, 1], y: [32, 0], scale: [0.975, 1] }, { duration: 0.56, delay: M.stagger(Math.max(0.035, STAGGER_MS / 1000)), ease: [0.22, 1, 0.36, 1] });
            }, { amount: 0.12 });
          });
        }
        if (PARALLAX_ON) {
          document.querySelectorAll(".gallery-card").forEach(function (card) {
            var img = card.querySelector("img");
            if (!img || typeof M.scroll !== "function") return;
            try {
              M.scroll(M.animate(img, { y: [-14, 14], scale: [1.06, 1.01] }, { ease: "linear" }), { target: card, offset: ["start end", "end start"] });
            } catch (e1) {}
          });
        }
      } catch (err) {}
    } else if (MOTION_MODE === "animejs" && window.anime && typeof window.anime.animate === "function") {
      activeParts.unshift("animejs");
      try {
        var A = window.anime;
        var aHero = document.querySelectorAll(".hero-shell .eyebrow, .hero-shell h1, .hero-shell .lead-copy, .hero-shell .cta-row, .hero-shell .hero-figure");
        if (aHero.length && typeof A.createTimeline === "function") {
          var tl = A.createTimeline({ defaults: { ease: "outExpo", duration: 640 } });
          tl.add(aHero, { opacity: [0.001, 1], translateY: [22, 0], delay: typeof A.stagger === "function" ? A.stagger(65) : 0 });
        } else if (aHero.length) {
          A.animate(aHero, { opacity: [0.001, 1], translateY: [22, 0], duration: 640, delay: typeof A.stagger === "function" ? A.stagger(65) : 0, ease: "outExpo" });
        }
        if ("IntersectionObserver" in window) {
          var aio = new IntersectionObserver(function (entries) {
            entries.forEach(function (en) {
              if (!en.isIntersecting) return;
              var items = en.target.querySelectorAll("[data-reveal]");
              if (items.length) {
                items.forEach(function (it) {
                  it.classList.remove("slm-pending");
                  it.classList.add("is-revealed");
                });
                A.animate(items, { opacity: [0.001, 1], translateY: [32, 0], scale: [0.975, 1], duration: 560, delay: typeof A.stagger === "function" ? A.stagger(Math.max(35, STAGGER_MS)) : 0, ease: "outExpo" });
              }
              aio.unobserve(en.target);
            });
          }, { threshold: 0.12 });
          document.querySelectorAll(".section-block").forEach(function (sec) { aio.observe(sec); });
        }
      } catch (err) {}
    } else if (activeParts.length === 0) {
      activeParts.push(MOTION_MODE);
    }
    root.setAttribute("data-motion-active", activeParts.join("+"));
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootVendorMotion, { once: true });
  } else {
    window.setTimeout(bootVendorMotion, 0);
  }
  var form = document.querySelector(".intake-form");
  if (form) form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var trap = form.querySelector(".hp-trap input, input.hp-trap");
    if (trap && trap.value) return;
    var btn = form.querySelector("button[type=submit]");
    var status = form.querySelector(".form-status");
    if (btn) btn.disabled = true;
    if (status) status.textContent = "Request sent — we will get back to you.";
    window.setTimeout(function () {
      if (btn) btn.disabled = false;
      if (status) status.textContent = "";
      form.reset();
    }, 4000);
  });
})();
