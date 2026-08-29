<template>
  <main class="callback-page" aria-labelledby="callback-title">
    <section class="callback-panel">
      <p class="callback-eyebrow">SECURE ACCOUNT CONNECTION</p>
      <h1 id="callback-title">Completing sign in</h1>
      <div class="callback-progress">
        <l-hatch size="24" stroke="4" speed="3.5" color="#0065a8" />
        <p>OpenIsle is verifying the identity provider response. You will be redirected automatically.</p>
      </div>
    </section>
  </main>
</template>

<script>
export default {
  name: 'CallbackPage',
}
</script>

<style scoped>
.callback-page {
  min-height: 600px;
  display: grid;
  place-items: center;
  padding: 48px 20px 70px;
  color: #293f4a;
  background: #f4f6f6;
}
.callback-panel { width: min(540px, 100%); padding: 36px 40px; border: 1px solid #bdcbd0; border-top: 5px solid #009edb; background: #fff; }
.callback-eyebrow { margin: 0 0 8px; color: #176582; font-size: 11px; font-weight: 800; letter-spacing: .1em; }
h1 { margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: 34px; font-weight: 400; }
.callback-progress { display: flex; align-items: flex-start; gap: 14px; margin-top: 22px; padding-top: 18px; border-top: 1px solid #d2dade; }
.callback-progress p { margin: 0; color: #5c6d75; font-size: 14px; line-height: 1.6; }
</style>
