<template>
  <div v-if="show" class="cropper-modal">
    <div class="cropper-body">
      <div class="cropper-wrapper">
        <img ref="image" :src="src" alt="to crop" />
      </div>
      <div class="cropper-actions">
        <button class="cropper-btn" type="button" @click="$emit('close')">Cancel</button>
        <button class="cropper-btn primary" type="button" @click="onConfirm">Apply photo</button>
      </div>
    </div>
  </div>
</template>

<script>
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'

export default {
  name: 'AvatarCropper',
  props: {
    src: {
      type: String,
      required: true,
    },
    show: {
      type: Boolean,
      default: false,
    },
  },
  emits: ['close', 'crop'],
  data() {
    return { cropper: null }
  },
  watch: {
    show(val) {
      if (val) {
        this.$nextTick(() => this.init())
      } else {
        this.destroy()
      }
    },
  },
  mounted() {
    if (this.show) {
      this.init()
    }
  },
  methods: {
    init() {
      const image = this.$refs.image
      this.cropper = new Cropper(image, {
        aspectRatio: 1,
        viewMode: 1,
        autoCropArea: 1,
        responsive: true,
      })
    },
    destroy() {
      if (this.cropper) {
        this.cropper.destroy()
        this.cropper = null
      }
    },
    onConfirm() {
      if (!this.cropper) return
      this.cropper.getCroppedCanvas({ width: 256, height: 256 }).toBlob((blob) => {
        const file = new File([blob], 'avatar.png', { type: 'image/png' })
        const url = URL.createObjectURL(blob)
        this.$emit('crop', { file, url })
        this.$emit('close')
        this.destroy()
      })
    },
  },
}
</script>

<style scoped>
.cropper-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  opacity: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.cropper-body {
  background: #fff;
  padding: 18px;
  border: 1px solid #9eafb7;
  border-top: 5px solid #009edb;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.cropper-wrapper {
  width: 80vw;
  height: 80vw;
  max-width: 400px;
  max-height: 400px;
}

.cropper-wrapper img {
  max-width: 100%;
}

.cropper-actions {
  width: 100%;
  justify-content: flex-end;
  margin-top: 14px;
  display: flex;
  gap: 10px;
}

.cropper-btn {
  padding: 6px 12px;
  min-height: 40px;
  padding: 8px 14px;
  border-radius: 0;
  color: #0065a8;
  border: 1px solid #0065a8;
  background: #fff;
  cursor: pointer;
}

.cropper-btn.primary {
  background: #0065a8;
  color: #ffff;
  border-color: var(--primary-color);
}

@media (min-width: 768px) {
  .cropper-wrapper {
    width: 400px;
    height: 400px;
  }
}
</style>
