<template>
  <Dropdown
    v-model="selected"
    :fetch-options="fetchTypes"
    placeholder="Select discussion visibility"
  />
</template>

<script>
import { computed, ref, watch } from 'vue'
import Dropdown from '~/components/Dropdown.vue'

export default {
  name: 'PostVisibleScopeSelect',
  components: { Dropdown },
  props: {
    modelValue: { type: String, default: 'ALL' },
    // options: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {

    const fetchTypes = async () => {
      return [
        { id: 'ALL', name: 'Public', icon: 'communication' },
        { id: 'ONLY_ME', name: 'Private', icon: 'user-icon' },
        { id: 'ONLY_REGISTER', name: 'Registered users', icon: 'peoples-two' },
      ]
    }

    const selected = computed({
      get: () => props.modelValue,
      set: (v) => emit('update:modelValue', v),
    })

    return { fetchTypes, selected }
  },
}
</script>

<style scoped></style>
