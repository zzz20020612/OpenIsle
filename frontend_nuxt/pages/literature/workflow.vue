<template>
  <main class="paper-shell">
    <div class="paper-container literature-workflow-container">
      <header class="paper-workspace-header workflow-header">
        <div>
          <div class="paper-page-eyebrow">Knowledge Base · Processing</div>
          <h1 class="paper-page-title">Literature processing workflow</h1>
          <p class="paper-page-description">
            Collect literature metadata, obtain open PDFs, parse full text, and extract reusable knowledge.
          </p>
        </div>
        <div class="workflow-header-actions">
          <NuxtLink class="paper-button" to="/literature">View knowledge base</NuxtLink>
          <a class="paper-button" :href="workspaceUrl" target="_blank" rel="noopener">Open full screen</a>
        </div>
      </header>

      <ol class="workflow-stages" aria-label="Literature processing stages">
        <li><span>1</span><strong>Collect metadata</strong></li>
        <li><span>2</span><strong>Download open PDF</strong></li>
        <li><span>3</span><strong>Parse full text</strong></li>
        <li><span>4</span><strong>Extract knowledge</strong></li>
      </ol>

      <section class="paper-panel workflow-frame-shell">
        <div class="workflow-frame-note">
          This is the original literature-system workspace. Its pipeline, settings, job history, retries,
          quality checks, and knowledge tools are preserved here.
        </div>
        <iframe
          class="workflow-frame"
          :src="workspaceUrl"
          title="Literature system workflow"
          loading="eager"
        />
      </section>
    </div>
  </main>
</template>

<script setup>
import '~/assets/paper-platform.css'

definePageMeta({ middleware: 'auth-client', keepalive: false })

const config = useRuntimeConfig()
const workspaceUrl = computed(() => {
  const base = String(config.public.literatureWorkspaceUrl || 'http://localhost:8088').replace(/\/$/, '')
  return `${base}/#/workflow`
})

useHead({ title: 'Knowledge Workflow - OpenIsle' })
</script>

<style scoped>
.literature-workflow-container {
  max-width: 1320px;
}

.workflow-header {
  align-items: end;
}

.workflow-header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workflow-stages {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin: 0 0 14px;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--paper-line);
  border-radius: 10px;
  background: var(--paper-line);
  list-style: none;
}

.workflow-stages li {
  display: flex;
  gap: 9px;
  align-items: center;
  min-height: 52px;
  padding: 10px 14px;
  background: var(--paper-panel);
  color: var(--paper-muted);
  font-size: 12px;
}

.workflow-stages span {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: color-mix(in srgb, var(--paper-teal) 12%, transparent);
  color: var(--paper-teal);
  font-weight: 800;
}

.workflow-stages strong {
  color: var(--paper-ink);
}

.workflow-frame-shell {
  padding: 0;
  overflow: hidden;
}

.workflow-frame-note {
  padding: 11px 14px;
  border-bottom: 1px solid var(--paper-line);
  color: var(--paper-muted);
  font-size: 12px;
  line-height: 1.5;
}

.workflow-frame {
  display: block;
  width: 100%;
  min-height: 820px;
  border: 0;
  background: #fff;
}

@media (max-width: 840px) {
  .workflow-stages {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workflow-frame {
    min-height: 720px;
  }
}
</style>
