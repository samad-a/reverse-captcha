// "Send an agent" buttons: start a real agent script on the demo laptop and stream its output into a panel.
// Only the demo machine (localhost or X-Admin-Key) gets buttons; everyone else sees nothing.
(() => {
  const css = `
  .rc-run { position: fixed; right: 16px; bottom: 16px; z-index: 60; width: min(460px, calc(100vw - 32px)); background: #111; color: #eee;
    border: 3px solid #111; border-radius: 14px; box-shadow: 6px 6px 0 #000; font: 13px/1.45 "JetBrains Mono", ui-monospace, Consolas, monospace; overflow: hidden; }
  .rc-run header { display: flex; align-items: center; gap: 10px; padding: 8px 10px 8px 14px; background: #ffd400; color: #111; font: 400 14px "Archivo Black", Inter, sans-serif; }
  .rc-run header .st { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .rc-run header .st i { font: 700 12px Inter, sans-serif; font-style: normal; opacity: .75; margin-left: 6px; }
  .rc-run header button { font: 700 12px Inter, sans-serif; background: #111; color: #fff; border: 0; border-radius: 6px; padding: 5px 10px; cursor: pointer; }
  .rc-run.done header { background: #6fe39a; } .rc-run.failed header { background: #ff6b5e; }
  .rc-run pre { margin: 0; padding: 10px 14px 12px; max-height: min(46vh, 420px); overflow: auto; white-space: pre-wrap; word-break: break-word; }
  .rc-run pre .ok { color: #6fe39a; } .rc-run pre .no { color: #ff8a80; } .rc-run pre .hi { color: #ffd400; font-weight: 700; } .rc-run pre .dim { color: #888; }
  .rc-run .dots::after { content: "…"; animation: rc-dots 1s steps(3) infinite; display: inline-block; width: 1em; overflow: hidden; vertical-align: bottom; }
  @keyframes rc-dots { from { width: 0; } }
  .rc-send { font: 600 12px/1 Inter, system-ui, sans-serif; background: #e2231a; color: #fff; border: 0; border-radius: 6px; padding: 5px 10px; cursor: pointer; white-space: nowrap; }
  .rc-send:hover { background: #fff; color: #e2231a; } .rc-send:disabled { opacity: .5; cursor: progress; }
  .hub .tile { position: relative; display: flex; transition: transform .1s; } .hub .tile > a { flex: 1; padding-bottom: 58px; }
  .hub .tile:hover { transform: translate(-2px, -2px); } .hub .tile > a:hover { transform: none; }
  .hub .tile:hover > a { box-shadow: 8px 8px 0 #111; }
  .tile-send { position: absolute; left: 50%; transform: translateX(-50%); bottom: 18px; white-space: nowrap; font: 400 13px "Archivo Black", Inter, sans-serif; background: #111; color: #fff; border: 2px solid #111;
    border-radius: 10px; padding: 6px 12px; cursor: pointer; }
  .tile-send:hover { background: #e2231a; border-color: #e2231a; } .tile-send:disabled { opacity: .45; cursor: progress; }`;
  document.head.insertAdjacentHTML("beforeend", `<style>${css}</style>`);

  const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  const tone = (l) => /^\[agent\]/.test(l) ? "dim" : /→ (4\d\d)|Traceback|Error|wrong answer|blocked/i.test(l) ? "no"
    : /VERDICT|rerouted|landed in the AGENT|picked|decided|summary|review/i.test(l) ? "hi"
    : /→ 2\d\d|correct answer/.test(l) ? "ok" : /^\s+(why|robotic|human|challenge)\b/.test(l) ? "dim" : "";

  let panel, pre, st, stopBtn, since = 0, run = 0, timer = null;
  const buttons = new Set();
  const setBusy = (busy) => buttons.forEach((b) => { b.disabled = busy; });

  function ensurePanel() {
    if (panel) return;
    panel = document.createElement("section");
    panel.className = "rc-run";
    panel.setAttribute("aria-live", "polite");
    panel.innerHTML = `<header><span class="st"></span><button type="button" class="stop">Stop</button><button type="button" class="x" aria-label="Close">✕</button></header><pre></pre>`;
    document.body.appendChild(panel);
    pre = panel.querySelector("pre"); st = panel.querySelector(".st"); stopBtn = panel.querySelector(".stop");
    stopBtn.addEventListener("click", () => fetch("/api/demo/stop", { method: "POST" }));
    panel.querySelector(".x").addEventListener("click", () => { panel.remove(); panel = null; });
  }

  async function poll() {
    clearTimeout(timer);
    let s;
    try { s = await (await fetch(`/api/demo/run?since=${since}`, { cache: "no-store" })).json(); }
    catch (_) { timer = setTimeout(poll, 1500); return; }
    if (s.run !== run) { run = s.run; since = 0; if (pre) pre.innerHTML = ""; return poll(); }
    since = s.next;
    if (panel) {
      const stick = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 30;
      pre.insertAdjacentHTML("beforeend", s.lines.map((l) => `<span class="${tone(l)}">${esc(l)}</span>\n`).join(""));
      if (stick) pre.scrollTop = pre.scrollHeight;
      panel.classList.toggle("done", s.holding || (!s.running && (s.returncode === 0 || s.stopped)));
      panel.classList.toggle("failed", !s.running && !s.stopped && s.returncode !== null && s.returncode !== 0);
      st.innerHTML = s.holding ? `🤖 ${esc(s.label)} <i>finished · its window is still open to explore</i>`
        : s.running ? `🤖 ${esc(s.label)} <i class="dots">running</i>` : `🤖 ${esc(s.label)} <i>${s.stopped ? "closed" : s.returncode === 0 ? "finished" : "stopped with an error"}</i>`;
      stopBtn.hidden = !s.running;
      stopBtn.textContent = s.holding ? "Close window" : "Stop";
    }
    setBusy(s.running && !s.holding);
    if (s.running) timer = setTimeout(poll, s.holding ? 1500 : 400);
  }

  async function start(name) {
    ensurePanel();
    st.innerHTML = `🤖 Starting <i class="dots">agent</i>`; pre.innerHTML = ""; since = 0;
    setBusy(true);
    const res = await fetch(`/api/demo/run/${encodeURIComponent(name)}`, { method: "POST" });
    if (!res.ok && res.status !== 409) { // 409: one is already running, so just show that one
      const msg = (await res.json().catch(() => ({}))).detail || `HTTP ${res.status}`;
      st.textContent = "🤖 Couldn't start the agent"; pre.textContent = msg; panel.classList.add("failed"); setBusy(false);
      return;
    }
    if (res.ok) run = (await res.json()).run;
    poll();
  }

  let enabled = null;
  window.RCAgentRun = {
    // Resolves with {key: label} on the demo machine, or null elsewhere.
    agents: async () => {
      if (enabled === null) {
        try { const d = await (await fetch("/api/demo/agents", { cache: "no-store" })).json(); enabled = d.enabled ? d.agents : false; }
        catch (_) { enabled = false; }
      }
      return enabled || null;
    },
    button(name, text, cls = "rc-send") {
      const b = document.createElement("button");
      b.type = "button"; b.className = cls; b.textContent = text;
      b.addEventListener("click", () => start(name));
      buttons.add(b);
      return b;
    },
    start,
    // Give every site tile in a .hub grid its own "send this site's agent" button (demo laptop only).
    async decorateHub(hub) {
      const agents = await window.RCAgentRun.agents();
      if (!agents || !hub) return;
      for (const a of [...hub.querySelectorAll(":scope > a[href]")]) {
        const key = new URL(a.href).pathname.split("/")[1];
        if (!agents[key]) continue;
        const tile = document.createElement("div");
        tile.className = "tile has-agent";
        a.replaceWith(tile);
        tile.append(a, window.RCAgentRun.button(key, "🤖 Send agent", "tile-send"));
        tile.lastChild.title = `Run ${agents[key]} against this site in its own browser window`;
      }
    },
  };
})();
