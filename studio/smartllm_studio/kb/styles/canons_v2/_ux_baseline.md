# UX baseline (all canons)

- Always loaded with the canon spec and `_engineering_baseline.md`. It says how the page must work; the canon says how it looks. If they conflict, keep the look but change it until the rule holds: UX wins.

<!-- section:navigation -->
## Navigation
- The visitor must always know where they are and how to go on:
  - the same nav in the same place on every page;
  - the current page is marked (weight, underline or accent bar), not by colour alone;
  - labels are words; icon-only items need an `aria-label` and a visible text label on desktop.
- Keep the top nav short: 3–6 items plus one CTA. More items go to a footer or a "More" menu.
- Mobile: a menu button (≥44×44px) with a clear label ("Menu"); the menu closes with a close button, the Escape key and a tap outside.
- Links are `<a href>` (they open in new tabs and work with middle-click); actions are `<button>`. Never a clickable `<div>`.
- Every important state has a URL (tabs, filters, pages), so Back works and links can be shared.
- Sticky headers must not cover anchored headings or the focused element: use `scroll-margin-top` on anchors.
- Deep pages (3+ levels): add breadcrumbs.

<!-- section:layout -->
## Layout and mobile
- Design mobile-first, then widen. Test at 360/375px, 768px, 1024px and 1440px, and in landscape.
- `<meta name="viewport" content="width=device-width, initial-scale=1">`. Never disable zoom.
- No horizontal scroll on the page. Only tables or galleries may scroll sideways, inside their own box, with a visible hint.
- Use `min-height: 100dvh` instead of `100vh` for full-screen sections on mobile.
- Respect safe areas on notched phones: `env(safe-area-inset-*)` for fixed bars and full-bleed sections.
- Show the core content first on mobile. Do not hide key facts (price, contact, main action) behind tabs or hover.
- Spacing on a 4/8px scale; related items closer together than unrelated ones.
- Fixed bars (header, bottom CTA) reserve space so they never hide content.

<!-- section:readability -->
## Readability
- Body text at least 16px; line-height 1.5–1.7; line length 45–75 characters (mobile 35–60).
- Contrast: body text ≥ 4.5:1, large text (≥24px, or ≥19px bold) ≥ 3:1, UI borders and icons ≥ 3:1. Check dark mode separately.
- Never grey text on grey backgrounds for important content.
- Headings in order (h1 → h2 → h3), one h1 per page. Use `text-wrap: balance` on headings.
- Uppercase, very thin weights and wide display faces only for short text, never for paragraphs.
- Prefer wrapping over truncation. If you truncate, give a way to see the full text.
- Use `tabular-nums` for prices, tables and counters.

<!-- section:interaction -->
## Interaction
- Touch targets ≥ 44×44px (a small icon can have a bigger padded hit area), with ≥ 8px between targets.
- Every control has 4 visible states: rest, hover (fine pointers only), focus, active/pressed. Disabled looks disabled and uses the `disabled` attribute.
- Focus: `:focus-visible` ring 2–4px with offset, never removed without a replacement.
- Feedback within 100ms of a tap or click (pressed state, spinner, change).
- Hover is a bonus, never the only way to reveal content or actions. Touch users have no hover.
- Gestures (swipe, drag) always have a button alternative.
- Keyboard: everything works with Tab, Enter, Space, Escape and arrows where expected. Tab order follows the visual order.
- Modals: focus moves into the modal, stays there, returns to the trigger on close; Escape closes; background has a scrim. Prefer native `<dialog>`.

<!-- section:cta -->
## Calls to action
- One primary action per screen or section. Secondary actions look clearly weaker (outline or text link).
- CTA labels say what happens: "Book a call", "Download the guide", not "Submit" or "Click here".
- The main CTA is visible without scrolling on mobile and repeats at the end of the page.
- Destructive actions (delete, cancel plan) use danger styling, sit apart from normal actions and need a confirm step or undo.

<!-- section:forms -->
## Forms
- Visible label above every field. Placeholder is only an example, never the label.
- Ask only for what is needed. Mark required (or optional) fields clearly.
- Right input types and keyboards: `type="email"`, `tel`, `url`, `number`, plus `inputmode` and `autocomplete` (name, email, tel, street-address).
- Never block paste. Turn off spellcheck on emails and codes.
- Inputs at least 44px tall and 16px font (smaller fonts make iOS zoom in).
- Validate on blur or on submit, not on every keystroke. Errors appear next to the field, say what is wrong and how to fix it, and are announced (`aria-live` or `role="alert"`).
- On a failed submit, move focus to the first invalid field; for many errors show a short summary at the top with links.
- Submit button: enabled until the request starts, then shows "Sending…" and is disabled; after that a clear success or error message. Keep the user's input on error.
- Group related fields with `<fieldset>`/`<legend>`; long forms are split into steps with a progress indicator and a Back button.

<!-- section:states -->
## Loading, empty, error, success
- Loading: if it takes more than ~300ms, show a skeleton or progress, not a blank area. Reserve the final size to avoid layout shift.
- Empty: explain why it is empty and offer the next action ("No projects yet — Create your first project").
- Error: say what happened in plain words, give a way out (Retry, Edit, Contact). Never a raw error code alone.
- Offline or backend down: the static page still works; dynamic parts show a short notice instead of breaking.
- Success: short confirmation near the action (inline message or toast). Toasts do not steal focus, use `aria-live="polite"` and stay 3–5s or until dismissed.
- Colour is never the only signal: add an icon or a word ("Error", "Saved").

<!-- section:motion -->
## Motion that never blocks
- Content is visible without animation. Animation only adds polish; if scripts fail, everything is still there.
- UI transitions 150–300ms; bigger transitions ≤ 400ms; exits faster than entries. Nothing that the user waits for lasts over 500ms.
- Never block input during an animation; animations can be interrupted.
- Animate only `transform` and `opacity`; never `transition: all`; never animate width, height, top or left.
- Animate 1–2 key things per view; stagger lists by 30–50ms.
- No scroll hijacking: native scroll speed and direction stay under the user's control.
- Loops longer than 5 seconds need a visible Pause button. Nothing flashes more than 3 times per second.
- `prefers-reduced-motion: reduce` gives the final state at once; parallax, auto-play and tilt switch off.

<!-- section:content -->
## Content and copy
- Lead with the answer: what it is, who it is for, what to do next, in the first screen.
- Short sentences, active voice, second person ("You get…").
- Specific numbers and facts beat adjectives ("Delivered in 10 days", not "Super fast").
- Use real typography: "…" not "...", curly quotes, non-breaking spaces between numbers and units (`10&nbsp;MB`).
- Format dates, numbers and money with `Intl.DateTimeFormat` and `Intl.NumberFormat` for the page language.
- Images that carry meaning have `alt` text; decorative images use `alt=""`.

<!-- section:checklist -->
## Pre-delivery checklist
- 360px phone: no sideways scroll, CTA visible, menu works.
- Keyboard only: all reachable, focus visible, modals trap and release focus.
- Screen reader: one h1, landmarks, labelled controls. Contrast checked in both themes. Reduced motion: page complete. Slow network: no layout jumps.

<!-- section:hard_limits -->
## Hard limits
- Never disable zoom or remove focus outlines without a replacement.
- Never use placeholder-only labels, hover-only content or gesture-only actions.
- Never hijack scroll or block input with animation.
- Touch targets ≥ 44×44px; body text ≥ 16px; contrast ≥ 4.5:1.
- One primary CTA per section; destructive actions need confirm or undo.
