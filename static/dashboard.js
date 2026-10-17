(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const cls = (label) => (label || "").split(" ")[0];
  const params = new URLSearchParams(location.search);
  if (params.get("demo")) document.body.classList.add("demo");
  let lastId = null, lastSig = "";

  const topReasons = (v, n) => {
    const r = v.reasons || {};
    const pool = v.passed ? [...(r.robotic || []), ...(r.challenge || [])] : [...(r.human || []), ...(r.challenge || [])];
    return pool.slice(0, n);
  };
  const ago = (ts) => { const s = Math.round(Date.now() / 1000 - ts); return s < 60 ? `${s}s ago` : `${Math.round(s / 60)}m ago`; };

  const SITE_ICON = { gate: "⟲", flights: "✈️", contracts: "✍️", tickets: "🎟️", shop: "👟" };
  const siteLabel = (r) => {
    const q = r.query || {}, s = r.site || "flights";
    const what = s === "gate" ? "gate checkbox" : s === "flights" ? `${q.from} → ${q.to}` : s === "contracts" ? "sign contract" : s === "tickets" ? `${q.qty || ""}× ${q.tier || "tickets"}` : `size ${q.size || "?"}`;
    return `${SITE_ICON[s] || ""} ${esc(what)}`;
  };

  function renderLanes(L) {
    if (!L) return;
    $("laneH").textContent = L.human; $("laneA").textContent = L.agent;
    const tot = L.human + L.agent || 1;
    $("splitH").style.width = `${100 * L.human / tot}%`; $("splitA").style.width = `${100 * L.agent / tot}%`;
    $("routes").innerHTML = L.recent.length ? L.recent.map((r) => `<li><span class="chip ${r.lane === "agent" ? "SCRAPER" : "HUMAN"}">${r.lane === "agent" ? "REROUTED" : "HUMAN"}</span>
      <span>${siteLabel(r)}</span><span class="why">${esc(r.reason)}</span></li>`).join("")
      : `<li class="empty">No traffic yet. Try /sites</li>`;
  }

  function render(d) {
    renderLanes(d.lanes);
    const L = d.latest;
    if (L && L.id !== lastId) {
      lastId = L.id;
      const v = L.verdict;
      $("needle").style.transform = `rotate(${-90 + 180 * v.machine_score / 100}deg)`;
      $("scoreTxt").textContent = v.machine_score;
      $("bigLabel").className = "big-label " + cls(v.label);
      $("bigLabel").textContent = v.label === "UNCERTAIN" ? `UNCERTAIN (likely ${v.likely})` : v.label;
      $("latestSub").textContent = `${v.passed ? "✅ let in" : "⛔ blocked"} · ${v.elapsed}s · ${Math.round(v.confidence * 100)}% confident · ${v.model}` + (L.name ? ` · ${L.name}` : "");
      $("latestReasons").innerHTML = topReasons(v, 5).map((x) => `<li>${esc(x)}</li>`).join("");
    } else if (L && L.name) {
      $("latestSub").textContent = $("latestSub").textContent.replace(/ · [^·]*$/, (m) => m.includes(L.name) ? m : m + ` · ${L.name}`);
    }
    if (!L) { $("bigLabel").textContent = "–"; $("latestReasons").innerHTML = ""; $("latestSub").textContent = ""; $("needle").style.transform = "rotate(-90deg)"; $("scoreTxt").textContent = "–"; lastId = null; }

    const sig = JSON.stringify([d.recent.map((a) => [a.id, a.name]), d.hall.map((a) => a.id), d.stats]);
    $("liveText").textContent = L ? `last visitor ${ago(L.ts)} · time limit ${d.time_limit_s}s` : "waiting for visitors…";
    if (sig === lastSig) return renderImp(d);
    lastSig = sig;
    $("feed").innerHTML = d.recent.length ? d.recent.map((a) => `
      <li><span class="chip ${cls(a.label)}">${esc(a.label === "UNCERTAIN" ? "UNSURE" : a.label)}</span>
      <span class="score">${a.machine_score}</span>
      <span class="why">${esc(a.name ? a.name + ": " : "")}${esc(topReasons(a.verdict, 2).join(" · "))}</span></li>`).join("")
      : `<li class="empty">No one yet. Go on, try it.</li>`;
    $("hall").innerHTML = d.hall.length ? d.hall.map((a) => `
      <li><span class="nm">${esc(a.name)}</span><span class="st">${a.correct ? "✓ correct but" : a.given == null ? "no answer," : "off by £" + Math.abs(a.given - a.expected).toFixed(2) + ","} ${a.elapsed.toFixed(1)}s</span></li>`).join("")
      : `<li class="empty">Nobody has admitted to being human yet.</li>`;
    $("counts").innerHTML = Object.entries(d.stats).map(([k, n]) => `<span class="chip ${cls(k)}">${esc(k)} × ${n}</span>`).join("");
    renderImp(d);
  }

  function renderImp(d) {

    if (d.importances && d.importances.features) {
      $("impWrap").classList.remove("hidden");
      const top = d.importances.features.slice(0, 8), mx = top[0][1] || 1;
      $("imp").innerHTML = `<p class="sub" style="font-size:13px;margin:0 0 6px">${esc(d.importances.model)} · trained on ${d.importances.n} attempts · CV accuracy ${Math.round(d.importances.accuracy * 100)}%</p>` +
        top.map(([f, w]) => `<div class="imp-row"><span>${esc(f)}</span><div class="imp-bar" style="width:${100 * w / mx}%"></div><span>${w.toFixed(2)}</span></div>`).join("");
    }
  }

  async function poll() {
    try { render(await (await fetch("/api/dashboard", { cache: "no-store" })).json()); } catch (e) { $("liveText").textContent = "reconnecting…"; }
    setTimeout(poll, 1000);
  }
  $("resetBtn").addEventListener("click", async () => {
    if (!confirm("Archive all attempts? (They're kept for training.)")) return;
    const res = await fetch("/api/reset", { method: "POST" });
    if (!res.ok) alert("Reset only works on the demo machine itself (http://localhost:8000/dashboard).");
  });
  poll();
})();
