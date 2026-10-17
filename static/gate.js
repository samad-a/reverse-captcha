// Reverse CAPTCHA gate: silent telemetry, challenge fetch, submission, verdict rendering.
(() => {
  const tel = window.RCTelemetry;

  const $ = (id) => document.getElementById(id);
  let challengeId = null, timerRAF = null;
  const params = new URLSearchParams(location.search);

  $("enterBtn").addEventListener("click", async () => {
    $("enterBtn").disabled = true;
    $("tickbox").textContent = "⟳";
    const res = await fetch("/api/challenge", { method: "POST" });
    const c = await res.json();
    challengeId = c.challenge_id;
    $("question").textContent = c.question;
    $("doc").innerHTML = c.document_html;
    $("landing").classList.add("hidden");
    $("challenge").classList.remove("hidden");
    $("answer").focus({ preventScroll: true });
    startTimer(c.time_limit_s);
  });

  function startTimer(limit) {
    const start = performance.now();
    const tick = () => {
      const s = (performance.now() - start) / 1000;
      const left = Math.max(0, limit - s);
      $("timerBar").style.transform = `scaleX(${left / limit})`;
      $("timerText").textContent = left > 0 ? `${left.toFixed(1)}s: machines only past this point` : `+${(s - limit).toFixed(1)}s over. Still human, then?`;
      $("timerBar").classList.toggle("late", left < limit * 0.3);
      timerRAF = requestAnimationFrame(tick);
    };
    tick();
  }

  $("answerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!challengeId) return;
    $("submitBtn").disabled = true;
    cancelAnimationFrame(timerRAF);
    const payload = { challenge_id: challengeId, answer: $("answer").value, telemetry: tel };
    if (params.get("label")) payload.true_label = params.get("label");
    challengeId = null;
    const res = await fetch("/api/submit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const v = await res.json();
    render(v);
  });

  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const list = (items) => items.length ? `<ul>${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : "<p class='fine'>nothing notable</p>";

  function render(v) {
    $("challenge").classList.add("hidden");
    const el = $("result");
    el.classList.remove("hidden");
    const r = v.reasons;
    const meter = `<div class="meterbar"><i style="left:0%"></i></div><div class="meter-ends"><span>HUMAN</span><span>MACHINE</span></div>`;
    const pills = `<div class="score-row">
        <div class="pill">machine score<b>${v.machine_score}/100</b></div>
        <div class="pill">time<b>${v.elapsed}s</b></div>
        <div class="pill">confidence<b>${Math.round(v.confidence * 100)}%</b></div>
        <div class="pill">classifier<b>${esc(v.model)}</b></div></div>`;
    const labelText = v.label === "UNCERTAIN" ? `UNCERTAIN <small>likely ${esc(v.likely)}</small>` : esc(v.label);
    if (!v.passed) {
      const detected = [...r.human, ...r.challenge].slice(0, 4).join(", ");
      el.innerHTML = `
        <div class="stamp denied">ACCESS DENIED</div>
        <div class="verdict-label denied">${labelText}</div>
        <p class="lede"><b>Suspiciously human.</b> Detected: ${esc(detected || "general carbon-based vibes")}.</p>
        ${meter}${pills}
        <div class="reasons">
          <div><h4>🧠 Human tells</h4>${list(r.human)}</div>
          <div><h4>📄 The challenge</h4>${list(r.challenge)}
            <p class="fine">Correct answer: £${v.solution.answer} (${esc(v.solution.working)})</p></div>
          <div><h4>🤖 Robot-ish bits</h4>${list(r.robotic)}</div>
        </div>
        <form class="namebox" id="nameForm"><input id="nameInput" maxlength="24" placeholder="Name for the Hall of Humans">
          <button class="big-btn small yellow">Immortalise my humanity</button></form>
        <p><button class="big-btn small" onclick="location.reload()">Try again ⟲</button></p>`;
      $("nameForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = $("nameInput").value.trim();
        if (!name) return;
        await fetch("/api/name", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ attempt_id: v.attempt_id, name }) });
        $("nameForm").innerHTML = `<p class="lede">🏛️ <b>${esc(name)}</b> has been added to the Hall of Humans. Congratulations on being made of meat.</p>`;
      });
    } else {
      el.innerHTML = `
        <div class="stamp welcome">ACCESS GRANTED</div>
        <div class="verdict-label welcome">Welcome, agent.</div>
        <p class="lede">Classified as <b>${labelText}</b>. Here's your private entrance: no cookie banners, just structured data.</p>
        ${meter}${pills}
        <div class="reasons">
          <div><h4>🤖 Machine tells</h4>${list(r.robotic)}</div>
          <div><h4>📄 The challenge</h4>${list(r.challenge)}</div>
          <div><h4>🧠 Human-ish bits</h4>${list(r.human)}</div>
        </div>
        <h4>GET ${esc(v.agent_entrance)}</h4><pre class="json" id="agentJson">loading…</pre>`;
      fetch(v.agent_entrance).then((x) => x.json()).then((j) => { $("agentJson").textContent = JSON.stringify(j, null, 2); });
    }
    requestAnimationFrame(() => setTimeout(() => { el.querySelector(".meterbar i").style.left = `calc(${v.machine_score}% - 3px)`; }, 50));
    window.__verdict = v; // handy for agents and debugging
  }
})();
