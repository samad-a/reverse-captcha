// Reverse CAPTCHA demo bar: a thin strip above every mock site, so visitors can get back to the hub and dashboard.
(() => {
  document.body.insertAdjacentHTML("afterbegin", `
    <div class="rc-bar" role="navigation" aria-label="Reverse CAPTCHA demo">
      <a class="rc-logo" href="/"><span>⟲</span> REVERSE<b>CAPTCHA</b></a>
      <span class="rc-tag">demo site · you're on the <b>human lane</b></span>
      <nav><a href="/sites"><i>All demo </i>sites</a><a href="/dashboard" target="_blank"><i>Live </i>dashboard ↗</a></nav>
    </div>`);

  // On the demo laptop only: a button that sends this site's real agent script at the page.
  const site = location.pathname.split("/")[1];
  const s = document.createElement("script");
  s.src = "/static/agentrun.js";
  s.onload = async () => {
    const agents = await window.RCAgentRun.agents();
    if (!agents || !agents[site]) return;
    const b = window.RCAgentRun.button(site, "🤖 Send an agent");
    b.title = `Runs ${agents[site]} in its own browser window on this laptop`;
    document.querySelector(".rc-bar nav").prepend(b);
  };
  document.head.appendChild(s);
})();
