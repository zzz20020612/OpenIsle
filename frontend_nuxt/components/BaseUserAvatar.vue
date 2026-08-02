<template>
  <div
    class="base-user-avatar"
    :class="wrapperClass"
    :style="wrapperStyle"
    v-bind="wrapperAttrs"
    @click="handleClick"
  >
    <BaseImage :src="props.src" :alt="altText" class="base-user-avatar-img" />
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useAttrs } from 'vue'
import BaseImage from './BaseImage.vue'

const props = defineProps({
  userId: {
    type: [String, Number],
    default: null,
  },
  src: {
    type: String,
    default: '',
  },
  alt: {
    type: String,
    default: '',
  },
  width: {
    type: [Number, String],
    default: null,
  },
  rounded: {
    type: Boolean,
    default: true,
  },
  disableLink: {
    type: Boolean,
    default: false,
  },
  to: {
    type: String,
    default: '',
  },
})

const attrs = useAttrs()

const resolvedLink = computed(() => {
  if (props.to) return props.to
  if (props.userId !== null && props.userId !== undefined && props.userId !== '') {
    return `/users/${props.userId}`
  }
  return null
})

const altText = computed(() => props.alt || 'User avatar')

const sizeStyle = computed(() => {
  var style = {}

  if (props.width > 0) {
    style.width = `${props.width}px`
  }
  if (props.height > 0) {
    style.height = `${props.height}px`
  }

  return style
})

const wrapperStyle = computed(() => {
  const attrStyle = attrs.style
  return [sizeStyle.value, attrStyle]
})

const wrapperClass = computed(() => [attrs.class, { 'is-rounded': props.rounded }])

const wrapperAttrs = computed(() => {
  const { class: _class, style: _style, ...rest } = attrs
  return rest
})

const handleClick = () => {
  if (props.disableLink) return
  if (!resolvedLink.value || resolvedLink.value === useRoute().path) return
  navigateTo(resolvedLink.value)
}
</script>

<style scoped>
.base-user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background-color: var(--avatar-placeholder-color, #f0f0f0);
  /* 先用box-sizing: border-box，保证加border后宽高不变，圆形不变形 */
  box-sizing: border-box;
  border: 1.5px solid var(--normal-border-color);
  transition: all 0.6s ease;
}

.base-user-avatar:hover {
  box-shadow: 0 4px 24px rgba(251, 138, 138, 0.1);
  transform: scale(1.05);
}

.base-user-avatar:active {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
}

.base-user-avatar.is-rounded {
  border-radius: 50%;
}

.base-user-avatar:not(.is-rounded) {
  border-radius: 0;
}

.base-user-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
