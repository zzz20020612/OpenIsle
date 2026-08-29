<template>
  <main class="about-page">
    <header class="about-hero">
      <p class="eyebrow">OPEN RESEARCH INFRASTRUCTURE</p>
      <h1>About OpenIsle</h1>
      <p class="lead">
        OpenIsle connects manuscript submission, literature knowledge processing and transparent
        research evaluation in one scholarly platform.
      </p>
    </header>

    <nav class="about-nav" aria-label="About OpenIsle sections">
      <a href="#purpose">Purpose</a>
      <a href="#services">Services</a>
      <a href="#principles">Principles</a>
      <a href="#trial">Trial programme</a>
    </nav>

    <div class="about-layout">
      <article class="about-content">
        <section id="purpose">
          <p class="section-number">01</p>
          <div>
            <h2>Purpose</h2>
            <p>
              Research workflows are often fragmented across submission systems, literature
              databases and evaluation tools. OpenIsle brings these stages together while keeping
              the evidence, status and responsible participant visible at every step.
            </p>
          </div>
        </section>

        <section id="services">
          <p class="section-number">02</p>
          <div>
            <h2>Research services</h2>
            <dl class="service-list">
              <div><dt>Submission</dt><dd>Author-managed drafts, document parsing, preview, screening and revision tracking.</dd></div>
              <div><dt>Knowledge</dt><dd>Online literature collection, open-PDF processing, structured sections and knowledge extraction.</dd></div>
              <div><dt>Evaluation</dt><dd>Registered-user assessment, review tasks and transparent research rankings.</dd></div>
              <div><dt>Discussion</dt><dd>Comments, replies, notifications and direct messages connected to scholarly records.</dd></div>
            </dl>
          </div>
        </section>

        <section id="principles">
          <p class="section-number">03</p>
          <div>
            <h2>Platform principles</h2>
            <ul>
              <li>Research records and processing status should be understandable without technical knowledge.</li>
              <li>Automated extraction supports researchers but never replaces author review or human evaluation.</li>
              <li>Public browsing and registered participation use clear, consistent access boundaries.</li>
              <li>Open-source and third-party processing components remain identifiable and auditable.</li>
            </ul>
          </div>
        </section>

        <section id="trial">
          <p class="section-number">04</p>
          <div>
            <h2>Trial programme</h2>
            <p>
              OpenIsle is currently prepared for controlled functional testing. Trial users can
              submit manuscripts, inspect processed literature, complete assigned evaluations and
              report workflow or display problems to the project team.
            </p>
            <div class="trial-actions">
              <NuxtLink to="/papers">Browse papers</NuxtLink>
              <NuxtLink to="/literature">Explore the knowledge base</NuxtLink>
            </div>
          </div>
        </section>
      </article>

      <aside class="about-aside">
        <h2>Platform scope</h2>
        <p>Submission · Knowledge · Evaluation · Scholarly discussion</p>
        <hr />
        <strong>Access</strong>
        <p>Reading is public where source rights allow. Submission, download and evaluation require an account.</p>
        <strong>Document processing</strong>
        <p>Automated results may require author correction, especially for equations, complex tables and scanned files.</p>
      </aside>
    </div>
  </main>
</template>

<script setup>
useHead({ title: 'About OpenIsle - Open Research Infrastructure' })
</script>

<style scoped>
.about-page { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 52px 0 78px; color: #263b45; }
.about-hero { max-width: 820px; padding-bottom: 30px; border-bottom: 1px solid #bfcbd0; }
.eyebrow { margin: 0 0 10px; color: #176582; font-size: 12px; font-weight: 800; letter-spacing: .11em; }
.about-hero h1 { margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: clamp(40px, 6vw, 62px); font-weight: 400; line-height: 1.06; }
.lead { margin: 20px 0 0; color: #52656e; font-family: Georgia, 'Times New Roman', serif; font-size: 21px; line-height: 1.55; }
.about-nav { display: flex; flex-wrap: wrap; gap: 2px; margin: 24px 0 42px; border-bottom: 4px solid #009edb; }
.about-nav a { padding: 10px 16px; color: #fff; background: #0065a8; font-size: 13px; font-weight: 750; text-decoration: none; }
.about-nav a:hover, .about-nav a:focus-visible { background: #004f85; }
.about-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 58px; align-items: start; }
.about-content { display: grid; gap: 0; }
.about-content section { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 18px; padding: 0 0 38px; scroll-margin-top: 30px; }
.section-number { margin: 3px 0 0; color: #1687a7; font-size: 12px; font-weight: 800; letter-spacing: .08em; }
.about-content h2, .about-aside h2 { margin: 0 0 13px; font-family: Georgia, 'Times New Roman', serif; font-size: 28px; font-weight: 400; }
.about-content p, .about-content li, .service-list dd, .about-aside p { color: #52636c; font-size: 15px; line-height: 1.72; }
.about-content section p:not(.section-number) { margin: 0; }
.service-list { margin: 0; border-top: 1px solid #ced7da; }
.service-list div { display: grid; grid-template-columns: 130px 1fr; gap: 22px; padding: 15px 0; border-bottom: 1px solid #ced7da; }
.service-list dt { color: #273e49; font-weight: 800; }
.service-list dd { margin: 0; }
.about-content ul { margin: 0; padding-left: 20px; }
.about-content li + li { margin-top: 8px; }
.trial-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; }
.trial-actions a { padding: 10px 14px; border: 1px solid #0065a8; color: #0065a8; font-size: 13px; font-weight: 750; text-decoration: none; }
.trial-actions a:first-child { color: #fff; background: #0065a8; }
.about-aside { padding: 26px; border-top: 5px solid #009edb; background: #edf2f3; }
.about-aside h2 { font-size: 23px; }
.about-aside p { margin: 7px 0 18px; font-size: 13px; }
.about-aside strong { color: #314a55; font-size: 12px; letter-spacing: .07em; text-transform: uppercase; }
.about-aside hr { margin: 22px 0; border: 0; border-top: 1px solid #bdcbd0; }
@media (max-width: 820px) { .about-layout { grid-template-columns: 1fr; gap: 20px; } .about-aside { order: -1; } }
@media (max-width: 560px) { .about-page { width: min(100% - 28px, 1180px); padding-top: 30px; } .about-content section { grid-template-columns: 1fr; gap: 7px; } .service-list div { grid-template-columns: 1fr; gap: 4px; } }
</style>
