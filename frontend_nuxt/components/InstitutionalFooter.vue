<template>
  <footer class="site-footer">
    <div class="footer-primary">
      <div class="footer-inner footer-grid">
        <section><h2>OpenIsle</h2><p>An integrated public platform for scholarly submission, literature knowledge processing, and transparent research evaluation.</p></section>
        <nav aria-label="Research services"><h3>Research services</h3><NuxtLink to="/papers">Papers</NuxtLink><NuxtLink to="/literature">Knowledge Base</NuxtLink><NuxtLink to="/papers/review-tasks">Review Tasks</NuxtLink></nav>
        <nav aria-label="Platform information"><h3>Platform</h3><NuxtLink to="/papers/rankings">Rankings</NuxtLink><NuxtLink to="/papers/submit">Submit research</NuxtLink><NuxtLink to="/about">About OpenIsle</NuxtLink></nav>
      </div>
    </div>
    <div class="footer-legal"><div class="footer-inner"><span>OpenIsle Research Infrastructure</span><span>Submission · Knowledge · Evaluation</span></div></div>
  </footer>
</template>

<style scoped>
.site-footer{flex:0 0 auto;color:#fff;background:#1f1f1f}.footer-inner{width:min(1180px,calc(100% - 40px));margin:0 auto}.footer-primary{padding:42px 0;border-top:5px solid #009edb}.footer-grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:64px}h2{margin:0 0 12px;font-family:Georgia,'Times New Roman',serif;font-size:30px;font-weight:400}h3{margin:0 0 13px;font-size:13px;letter-spacing:.08em;text-transform:uppercase}p{max-width:560px;margin:0;color:#d0d0d0;font-size:14px;line-height:1.7}nav{display:flex;flex-direction:column;align-items:flex-start;gap:9px}a{color:#fff;font-size:14px;text-decoration:none}a:hover,a:focus-visible{text-decoration:underline}.footer-legal{padding:15px 0;border-top:1px solid #4a4a4a;color:#bdbdbd;font-size:12px}.footer-legal .footer-inner{display:flex;justify-content:space-between;gap:20px}@media(max-width:720px){.footer-grid{grid-template-columns:1fr;gap:30px}.footer-legal .footer-inner{flex-direction:column;gap:6px}}
</style>
