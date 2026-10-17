// Reverse CAPTCHA demo bar: a thin strip above every mock site, so visitors can get back to the hub and dashboard.
(() => {
  document.body.insertAdjacentHTML("afterbegin", `
    <div class="rc-bar" role="navigation" aria-label="Reverse CAPTCHA demo">
      <a class="rc-logo" href="/"><span>⟲</span> REVERSE<b>CAPTCHA</b></a>
      <span class="rc-tag">demo site · you're on the <b>human lane</b></span>
      <nav><a href="/sites"><i>All demo </i>sites</a><a href="/dashboard" target="_blank"><i>Live </i>dashboard ↗</a></nav>
    </div>`);
})();
