<template>
  <div class="dropdown" ref="wrapper">
    <div class="dropdown-display" @click="toggle">
      <slot
        name="display"
        :selected="selectedLabels"
        :toggle="toggle"
        :search="search"
        :setSearch="setSearch"
      >
        <template v-if="multiple">
          <span v-if="selectedLabels.length">
            <template v-for="(label, idx) in selectedLabels" :key="label.id">
              <div class="selected-label">
                <template v-if="label.icon">
                  <BaseImage
                    v-if="isImageIcon(label.icon)"
                    :src="label.icon"
                    class="option-icon"
                    :alt="label.name"
                  />
                  <component v-else :is="label.icon" class="option-icon" :size="16" />
                </template>
                <span>{{ label.name }}</span>
              </div>
              <span v-if="idx !== selectedLabels.length - 1">, </span>
            </template>
          </span>
          <span v-else class="placeholder">{{ placeholder }}</span>
        </template>
        <template v-else>
          <span v-if="selectedLabels.length">
            <div class="selected-label">
              <template v-if="selectedLabels[0].icon">
                <BaseImage
                  v-if="isImageIcon(selectedLabels[0].icon)"
                  :src="selectedLabels[0].icon"
                  class="option-icon"
                  :alt="selectedLabels[0].name"
                />
                <component v-else :is="selectedLabels[0].icon" class="option-icon" :size="16" />
              </template>
              <span>{{ selectedLabels[0].name }}</span>
            </div>
          </span>
          <span v-else class="placeholder">{{ placeholder }}</span>
        </template>
        <down class="dropdown-caret" />
      </slot>
    </div>
    <div
      v-if="
        open &&
        !isMobile &&
        (loading || filteredOptions.length > 0 || showSearch || (remote && search))
      "
      :class="['dropdown-menu', menuClass]"
      v-click-outside="close"
      ref="menuRef"
    >
      <div v-if="showSearch" class="dropdown-search">
        <search-icon class="search-icon" />
        <input type="text" v-model="search" placeholder="Search options" />
      </div>
      <div v-if="loading" class="dropdown-loading">
        <l-hatch size="20" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
      </div>
      <template v-else>
        <div v-if="filteredOptions.length === 0" class="dropdown-empty">No matching options</div>
        <template v-else>
          <div
            v-for="o in filteredOptions"
            :key="o.id"
            @click="select(o.id)"
            :class="['dropdown-option', optionClass, { selected: isSelected(o.id) }]"
          >
            <slot name="option" :option="o" :isSelected="isSelected(o.id)">
              <template v-if="o.icon">
                <BaseImage
                  v-if="isImageIcon(o.icon)"
                  :src="o.icon"
                  class="option-icon"
                  :alt="o.name"
                />
                <component v-else :is="o.icon" class="option-icon" :size="16" />
              </template>
              <span>{{ o.name }}</span>
            </slot>
          </div>
          <slot name="footer" :close="close" :loading="loading" />
        </template>
      </template>
    </div>
    <Teleport to="body">
      <div v-if="open && isMobile" class="dropdown-mobile-page">
        <div class="dropdown-mobile-header">
          <next class="back-icon" @click="close" />
          <span class="mobile-title">{{ placeholder }}</span>
        </div>
        <div class="dropdown-mobile-menu" ref="mobileMenuRef">
          <div v-if="showSearch" class="dropdown-search">
            <search-icon class="search-icon" />
            <input type="text" v-model="search" placeholder="Search options" />
          </div>
          <div v-if="loading" class="dropdown-loading">
            <l-hatch size="20" stroke="4" speed="3.5" color="var(--primary-color)"></l-hatch>
          </div>
          <template v-else>
            <div v-if="filteredOptions.length === 0" class="dropdown-empty">No matching options</div>
            <template v-else>
              <div
                v-for="o in filteredOptions"
                :key="o.id"
                @click="select(o.id)"
                :class="['dropdown-option', optionClass, { selected: isSelected(o.id) }]"
              >
                <slot name="option" :option="o" :isSelected="isSelected(o.id)">
                  <template v-if="o.icon">
                    <BaseImage
                      v-if="isImageIcon(o.icon)"
                      :src="o.icon"
                      class="option-icon"
                      :alt="o.name"
                    />
                    <component v-else :is="o.icon" class="option-icon" :size="16" />
                  </template>
                  <span>{{ o.name }}</span>
                </slot>
              </div>
              <slot name="footer" :close="close" :loading="loading" />
            </template>
          </template>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { computed, onMounted, ref, watch } from 'vue'
import { useIsMobile } from '~/utils/screen'

export default {
  name: 'BaseDropdown',
  props: {
    modelValue: { type: [Array, String, Number], default: () => [] },
    placeholder: { type: String, default: 'Select an option' },
    multiple: { type: Boolean, default: false },
    fetchOptions: { type: Function, required: true },
    remote: { type: Boolean, default: false },
    menuClass: { type: String, default: '' },
    optionClass: { type: String, default: '' },
    showSearch: { type: Boolean, default: true },
    initialOptions: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue', 'update:search', 'close'],
  setup(props, { emit, expose }) {
    const open = ref(false)
    const search = ref('')
    const setSearch = (val) => {
      search.value = val
    }
    const options = ref(Array.isArray(props.initialOptions) ? [...props.initialOptions] : [])
    const loaded = ref(false)
    const loading = ref(false)
    const wrapper = ref(null)
    const menuRef = ref(null)
    const mobileMenuRef = ref(null)
    const isMobile = useIsMobile()

    const openMenu = () => {
      if (!open.value) {
        open.value = true
      }
    }

    const toggle = () => {
      if (open.value) {
        open.value = false
        emit('close')
      } else {
        open.value = true
      }
    }

    const close = () => {
      open.value = false
      emit('close')
    }

    const select = (id) => {
      if (props.multiple) {
        const arr = Array.isArray(props.modelValue) ? [...props.modelValue] : []
        const idx = arr.indexOf(id)
        if (idx > -1) {
          arr.splice(idx, 1)
        } else {
          arr.push(id)
        }
        emit('update:modelValue', arr)
      } else {
        emit('update:modelValue', id)
        close()
      }
      search.value = ''
    }

    const filteredOptions = computed(() => {
      if (props.remote) return options.value
      if (!search.value) return options.value
      return options.value.filter((o) => o.name.toLowerCase().includes(search.value.toLowerCase()))
    })

    const loadOptions = async (kw = '') => {
      if (!props.remote && loaded.value) return
      try {
        loading.value = true
        const res = await props.fetchOptions(props.remote ? kw : undefined)
        options.value = Array.isArray(res) ? res : []
        if (!props.remote) loaded.value = true
      } catch {
        options.value = []
      } finally {
        loading.value = false
      }
    }

    const scrollToBottom = () => {
      const el = isMobile.value ? mobileMenuRef.value : menuRef.value
      if (el) {
        el.scrollTop = el.scrollHeight
      }
    }

    const reload = async () => {
      await loadOptions(props.remote ? search.value : undefined)
    }

    watch(
      () => props.initialOptions,
      (val) => {
        if (Array.isArray(val)) {
          options.value = [...val]
        }
      },
    )

    watch(open, async (val) => {
      if (val) {
        if (props.remote) {
          await loadOptions(search.value)
        } else if (!loaded.value) {
          await loadOptions()
        }
      }
    })

    watch(search, async (val) => {
      emit('update:search', val)
      if (props.remote && open.value) {
        await loadOptions(val)
      }
    })

    onMounted(async () => {
      if (!props.remote) {
        loadOptions()
      }
    })

    const selectedLabels = computed(() => {
      if (props.multiple) {
        return options.value.filter((o) => (props.modelValue || []).includes(o.id))
      }
      const match = options.value.find((o) => o.id === props.modelValue)
      return match ? [match] : []
    })

    const isSelected = (id) => {
      return selectedLabels.value.some((label) => label.id === id)
    }

    const isImageIcon = (icon) => {
      if (!icon) return false
      return /^https?:\/\//.test(icon) || icon.startsWith('/')
    }

    expose({ toggle, close, reload, scrollToBottom, openMenu })

    return {
      open,
      toggle,
      close,
      select,
      search,
      filteredOptions,
      wrapper,
      menuRef,
      mobileMenuRef,
      selectedLabels,
      isSelected,
      loading,
      isImageIcon,
      setSearch,
      isMobile,
      remote: props.remote,
    }
  },
}
</script>

<style>
.dropdown {
  position: relative;
}

.dropdown-display {
  min-height: 42px;
  box-sizing: border-box;
  border: 1px solid #aebdc3;
  border-radius: 0;
  padding: 8px 11px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-width: 100px;
}
.dropdown-display:hover { border-color: #39758d; }
.dropdown-display:focus-within { outline: 3px solid rgba(0,101,168,.16); outline-offset: 1px; border-color: #0065a8; }

.placeholder {
  color: gray;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #9eb0b8;
  border-top: 4px solid #009edb;
  border-radius: 0;
  box-shadow: 0 10px 24px rgba(34,57,68,.12);
  z-index: 10000;
  max-height: 300px;
  min-width: 350px;
  margin-top: 4px;
  overflow-y: auto;
}

.dropdown-caret {
  margin-left: 5px;
}

.selected-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-right: 5px;
}

.dropdown-search {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #ced7da;
}

.dropdown-search input {
  flex: 1;
  border: none;
  outline: none;
  margin-left: 5px;
  background: transparent;
  color: #2d424c;
  font-size: 13px;
}

.search-icon {
  font-size: 14px;
}

.dropdown-option {
  display: flex;
  align-items: center;
  min-height: 40px;
  padding: 9px 14px;
  gap: 5px;
  cursor: pointer;
}

.dropdown-option.selected {
  background: #e5f1f5;
  color: #184f68;
}

.dropdown-option:hover {
  background: #eef4f5;
}

.option-icon {
  width: 16px;
  height: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.dropdown-loading {
  display: flex;
  justify-content: center;
  padding: 10px 0;
}

.dropdown-empty {
  padding: 20px;
  text-align: center;
  color: var(--muted-text-color, #8c8c8c);
  font-size: 14px;
}

.dropdown-mobile-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--app-menu-background-color);
  z-index: 1300;
  display: flex;
  flex-direction: column;
}

.dropdown-mobile-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-bottom: 1px solid var(--normal-border-color);
}

.back-icon {
  transform: rotate(180deg);
  cursor: pointer;
}

.dropdown-mobile-menu {
  flex: 1;
  overflow-y: auto;
}
</style>
