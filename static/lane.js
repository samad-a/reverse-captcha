// Shared passive routing for the demo sites. Call RCRoute(site, query) when the visitor presses the main button.
// Humans: resolves with {lane:"human", result}. Agents: shows the reroute overlay and navigates to the agent lane.
(() => {
  const overlay = document.createElement("div");
  overlay.className = "overlay hidden";
  overlay.innerHTML = `<div class="box"><div class="spinner"></div><div class="lane">Checking…</div><div class="why"></div></div>`;
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(overlay));

  window.RCRoute = async (site, query) => {
    overlay.classList.remove("hidden");
    const spin = overlay.querySelector(".spinner"), lane = overlay.querySelector(".lane"), why = overlay.querySelector(".why");
    spin.classList.remove("hidden"); lane.className = "lane"; lane.textContent = "Checking…"; why.textContent = "";
    const r = await (await fetch(`/api/route/${site}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, telemetry: window.RCTelemetry }),
    })).json();
    try { sessionStorage.setItem("rc_route", JSON.stringify(r)); } catch (_) {}
    if (r.lane === "agent") {
      spin.classList.add("hidden");
      lane.className = "lane agent"; lane.textContent = "🤖 Agent detected → agent lane"; why.textContent = r.reason;
      setTimeout(() => { location.href = r.redirect; }, 1400);
      return null;
    }
    overlay.classList.add("hidden");
    return r;
  };
})();
