// Shared silent telemetry recorder. Exposes window.RCTelemetry (sent with form submissions).
(() => {
  const T0 = performance.now();
  const now = () => Math.round(performance.now() - T0);
  const MAX = 6000;
  const tel = {
    webdriver: !!navigator.webdriver, ua: navigator.userAgent,
    viewport: { w: innerWidth, h: innerHeight }, moves: [], clicks: [], keys: [],
    pastes: 0, scrolls: 0, focus: 0, blur: 0, first_interaction_ms: null,
    events_total: 0, untrusted_total: 0, touch: false,
  };
  const count = (e) => {
    tel.events_total++;
    if (!e.isTrusted) tel.untrusted_total++;
    if (tel.first_interaction_ms === null) tel.first_interaction_ms = now();
  };

  addEventListener("pointermove", (e) => {
    count(e);
    if (e.pointerType === "touch") tel.touch = true;
    if (tel.moves.length < MAX) tel.moves.push([Math.round(e.clientX), Math.round(e.clientY), now(), e.pointerType || "mouse"]);
  }, { passive: true, capture: true });
  addEventListener("touchstart", (e) => { count(e); tel.touch = true; }, { passive: true, capture: true });
  addEventListener("click", (e) => {
    count(e);
    const btn = e.target.closest && e.target.closest("button");
    const c = { x: Math.round(e.clientX), y: Math.round(e.clientY), t: now(), trusted: e.isTrusted, target: btn ? btn.id : e.target.tagName };
    if (btn && e.detail !== 0) { // detail 0 = keyboard-activated click, no position
      const r = btn.getBoundingClientRect();
      c.rel = { dx: e.clientX - (r.left + r.width / 2), dy: e.clientY - (r.top + r.height / 2), w: r.width, h: r.height };
    }
    if (tel.clicks.length < 200) tel.clicks.push(c);
  }, { capture: true });
  addEventListener("keydown", (e) => { count(e); if (tel.keys.length < 500) tel.keys.push({ t: now(), type: "down", trusted: e.isTrusted }); }, true);
  addEventListener("keyup", (e) => { count(e); if (tel.keys.length < 500) tel.keys.push({ t: now(), type: "up", trusted: e.isTrusted }); }, true);
  addEventListener("paste", (e) => { count(e); tel.pastes++; }, true);
  addEventListener("scroll", (e) => { tel.events_total++; tel.scrolls++; }, { passive: true, capture: true });
  addEventListener("wheel", (e) => { count(e); }, { passive: true, capture: true });
  addEventListener("focus", () => tel.focus++, true);
  addEventListener("blur", () => tel.blur++, true);
  window.RCTelemetry = tel;
})();
