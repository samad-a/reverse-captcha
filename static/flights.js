// Haarline mock search: no challenge. Pressing Search sends the silent telemetry to /api/flights/route,
// which sends humans to normal results and obvious agents to the agent lane.
(async () => {
  const $ = (id) => document.getElementById(id);
  const airports = await (await fetch("/api/airports")).json();
  const opts = Object.entries(airports).map(([code, name]) => `<option value="${code}">${name} (${code})</option>`).join("");
  $("from").innerHTML = opts; $("to").innerHTML = opts;
  $("from").value = "EDI"; $("to").value = "BCN";
  const d = new Date(); d.setDate(d.getDate() + 21);
  $("depart").value = d.toISOString().slice(0, 10);
  d.setDate(d.getDate() + 4); $("ret").value = d.toISOString().slice(0, 10);

  $("searchForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = { from: $("from").value, to: $("to").value, depart: $("depart").value, return: $("ret").value, pax: $("pax").value };
    $("overlay").classList.remove("hidden");
    let r;
    try {
      const res = await fetch("/api/flights/route", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, telemetry: window.RCTelemetry }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      r = await res.json();
    } catch (_) { // routing check failed: fail open to the human results page
      location.href = "/flights/results?" + new URLSearchParams(query);
      return;
    }
    try { sessionStorage.setItem("rc_route", JSON.stringify(r)); } catch (_) {}
    $("spin").classList.add("hidden");
    $("laneText").className = "lane " + r.lane;
    $("laneText").textContent = r.lane === "agent" ? "🤖 Agent detected → agent lane" : "Finding flights…";
    $("laneWhy").textContent = r.lane === "agent" ? r.reason : "";
    setTimeout(() => { location.href = r.redirect; }, r.lane === "agent" ? 1400 : 500);
  });
})();
