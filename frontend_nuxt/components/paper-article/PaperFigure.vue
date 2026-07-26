<template>
  <figure class="article-figure">
    <img v-if="src" :src="src" :alt="block.altText || block.caption || 'Article figure'" loading="lazy" />
    <div v-else class="figure-placeholder">Figure file is not available in this preview.</div>
    <figcaption>
      <strong v-if="label">{{ label }}. </strong>{{ block.caption }}
      <small v-if="block.sourceNote">{{ block.sourceNote }}</small>
    </figcaption>
  </figure>
</template>

<script setup>
const props = defineProps({
  block: { type: Object, required: true },
  src: { type: String, default: '' },
  label: { type: String, default: 'Figure' },
})
</script>

<style scoped>
.article-figure { margin: 28px auto; max-width: 100%; text-align: center; }
.article-figure img { display: block; max-width: 100%; max-height: 720px; margin: 0 auto; object-fit: contain; }
.article-figure figcaption { max-width: 760px; margin: 12px auto 0; color: #35454f; font-size: 14px; line-height: 1.55; text-align: left; }
.article-figure figcaption small { display: block; margin-top: 4px; color: #68747c; }
.figure-placeholder { display: grid; place-items: center; min-height: 180px; border: 1px dashed #aab7be; color: #68747c; }
</style>
