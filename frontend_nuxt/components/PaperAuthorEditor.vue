<template>
  <div class="author-editor">
    <div class="author-list" role="list">
      <article
        v-for="(author, index) in localAuthors"
        :key="author._key"
        class="author-list-row"
        :class="{ expanded: expandedIndex === index }"
        role="listitem"
      >
        <div class="author-order">{{ index + 1 }}</div>
        <button class="author-summary" type="button" @click="toggleEditor(index)">
          <span class="author-summary-name">{{ authorName(author, index) }}</span>
          <span class="author-summary-meta">
            {{ author.correspondingAuthor ? 'Corresponding Author' : 'Author' }}
            <template v-if="primaryAffiliation(author)">
              · {{ primaryAffiliation(author).organizationName || 'Affiliation incomplete' }}
            </template>
          </span>
        </button>
        <div class="author-actions">
          <button
            class="author-icon-button"
            type="button"
            title="Edit author"
            aria-label="Edit author"
            @click="toggleEditor(index)"
          ><Edit :size="17" /></button>
          <button
            class="author-icon-button"
            type="button"
            title="Move author up"
            aria-label="Move author up"
            :disabled="index === 0"
            @click="moveAuthor(index, -1)"
          ><ArrowUp :size="17" /></button>
          <button
            class="author-icon-button"
            type="button"
            title="Move author down"
            aria-label="Move author down"
            :disabled="index === localAuthors.length - 1"
            @click="moveAuthor(index, 1)"
          ><ArrowDown :size="17" /></button>
          <button
            class="author-icon-button danger"
            type="button"
            title="Remove author"
            aria-label="Remove author"
            :disabled="localAuthors.length === 1"
            @click="removeAuthor(index)"
          ><Delete :size="17" /></button>
        </div>

        <div v-if="expandedIndex === index" class="author-detail">
          <div class="author-detail-heading">
            <div>
              <strong>Author {{ index + 1 }}</strong>
              <span>Required identity, role, and affiliation details</span>
            </div>
            <button
              class="author-icon-button"
              type="button"
              title="Close author editor"
              aria-label="Close author editor"
              @click="expandedIndex = -1"
            ><CloseOne :size="17" /></button>
          </div>

          <div class="author-fields three">
            <label class="author-field">
              <span>Given name *</span>
              <input v-model.trim="author.givenName" autocomplete="given-name" />
            </label>
            <label class="author-field">
              <span>Middle name</span>
              <input v-model.trim="author.middleName" autocomplete="additional-name" />
            </label>
            <label class="author-field">
              <span>Family name *</span>
              <input v-model.trim="author.familyName" autocomplete="family-name" />
            </label>
          </div>

          <div class="author-fields two">
            <label class="author-field">
              <span>Email *</span>
              <input v-model.trim="author.email" type="email" autocomplete="email" />
            </label>
            <label class="author-field">
              <span>ORCID</span>
              <input v-model.trim="author.orcid" placeholder="0000-0000-0000-0000" />
            </label>
          </div>

          <div class="author-flags">
            <label>
              <input
                :checked="author.correspondingAuthor"
                type="checkbox"
                @change="setCorrespondingAuthor(index, $event.target.checked)"
              />
              <span>Corresponding author</span>
            </label>
            <label>
              <input v-model="author.equalContribution" type="checkbox" />
              <span>Co-first author</span>
            </label>
          </div>

          <fieldset class="author-contributions">
            <legend>CRediT contribution roles</legend>
            <div>
              <label v-for="role in CONTRIBUTION_ROLES" :key="role">
                <input v-model="author.contributionRoles" type="checkbox" :value="role" />
                <span>{{ role }}</span>
              </label>
            </div>
          </fieldset>

          <div class="affiliation-disclosure">
            <div>
              <strong>Affiliations</strong>
              <span>{{ affiliationSummary(author) }}</span>
            </div>
            <button class="author-command-button" type="button" @click="toggleAffiliations(author)">
              <Edit :size="17" />
              {{ affiliationsExpanded(author) ? 'Hide affiliations' : 'Add / Edit affiliations' }}
            </button>
          </div>

          <div
            v-if="affiliationsExpanded(author)"
            class="affiliation-backdrop"
            aria-hidden="true"
            @click="closeAffiliations"
          />
          <aside
            v-if="affiliationsExpanded(author)"
            class="affiliation-panel"
            role="dialog"
            aria-modal="true"
            :aria-label="`Affiliations for ${authorName(author, index)}`"
          >
            <div class="affiliation-heading">
              <div>
                <strong>{{ authorName(author, index) }}</strong>
                <span>Each author needs at least one affiliation and exactly one primary affiliation.</span>
              </div>
              <button
                class="author-icon-button"
                type="button"
                title="Close affiliations"
                aria-label="Close affiliations"
                @click="closeAffiliations"
              >
                <CloseOne :size="17" />
              </button>
            </div>

            <div class="affiliation-list">
              <article
                v-for="(affiliation, affiliationIndex) in author.affiliations"
                :key="affiliation._key"
                class="affiliation-editor"
              >
              <div class="affiliation-editor-head">
                <strong>Affiliation {{ affiliationIndex + 1 }}</strong>
                <div>
                  <label class="primary-radio">
                    <input
                      :checked="affiliation.primaryAffiliation"
                      type="radio"
                      :name="`primary-affiliation-${author._key}`"
                      @change="setPrimaryAffiliation(index, affiliationIndex)"
                    />
                    Primary
                  </label>
                  <button
                    class="author-icon-button danger"
                    type="button"
                    title="Remove affiliation"
                    aria-label="Remove affiliation"
                    :disabled="author.affiliations.length === 1"
                    @click="removeAffiliation(index, affiliationIndex)"
                  ><Delete :size="16" /></button>
                </div>
              </div>
              <div class="author-fields two">
                <label class="author-field">
                  <span>Organization *</span>
                  <input v-model.trim="affiliation.organizationName" />
                </label>
                <label class="author-field">
                  <span>Department</span>
                  <input v-model.trim="affiliation.department" />
                </label>
              </div>
              <div class="author-fields three">
                <label class="author-field">
                  <span>Country / Region *</span>
                  <select v-model="affiliation.country">
                    <option value="">Select</option>
                    <option v-for="country in COUNTRY_OPTIONS" :key="country" :value="country">
                      {{ country }}
                    </option>
                  </select>
                </label>
                <label class="author-field">
                  <span>State / Region</span>
                  <input v-model.trim="affiliation.region" />
                </label>
                <label class="author-field">
                  <span>City *</span>
                  <input v-model.trim="affiliation.city" />
                </label>
              </div>
              <details class="affiliation-address">
                <summary>Postal address</summary>
                <div class="author-fields two">
                  <label class="author-field">
                    <span>Address line 1</span>
                    <input v-model.trim="affiliation.addressLine1" />
                  </label>
                  <label class="author-field">
                    <span>Address line 2</span>
                    <input v-model.trim="affiliation.addressLine2" />
                  </label>
                  <label class="author-field">
                    <span>Postal code</span>
                    <input v-model.trim="affiliation.postalCode" />
                  </label>
                </div>
              </details>
              </article>
            </div>
            <button class="author-command-button" type="button" @click="addAffiliation(index)">
              <AddOne :size="17" /> Add affiliation
            </button>
          </aside>
        </div>
      </article>
    </div>

    <button class="author-command-button" type="button" @click="addAuthor">
      <AddOne :size="18" /> Add author
    </button>
  </div>
</template>

<script setup>
import { AddOne, ArrowDown, ArrowUp, CloseOne, Delete, Edit } from '@icon-park/vue-next'
import {
  CONTRIBUTION_ROLES,
  COUNTRY_OPTIONS,
  createEmptyAffiliation,
  createEmptyAuthor,
} from '~/config/paperSubmissionConfig'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const makeKey = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`
const withKeys = (authors) => authors.map((author) => ({
  ...author,
  _key: author._key || makeKey(),
  contributionRoles: Array.isArray(author.contributionRoles) ? author.contributionRoles : [],
  affiliations: (author.affiliations?.length ? author.affiliations : [createEmptyAffiliation()]).map((item) => ({
    ...createEmptyAffiliation(),
    ...item,
    _key: item._key || makeKey(),
  })),
}))

const localAuthors = ref(withKeys(props.modelValue.length ? props.modelValue : [createEmptyAuthor(true)]))
const expandedIndex = ref(0)
const expandedAffiliations = ref({})
let syncingFromParent = false

watch(
  () => props.modelValue,
  (value) => {
    const incoming = JSON.stringify(value || [])
    const current = JSON.stringify(localAuthors.value.map(stripKeys))
    if (incoming === current) return
    syncingFromParent = true
    localAuthors.value = withKeys(value?.length ? value : [createEmptyAuthor(true)])
    nextTick(() => { syncingFromParent = false })
  },
  { deep: true },
)

watch(
  localAuthors,
  (value) => {
    if (syncingFromParent) return
    emit('update:modelValue', value.map((author) => {
      const primary = author.affiliations.find((item) => item.primaryAffiliation)
      author.displayName = [author.givenName, author.middleName, author.familyName]
        .map((part) => part?.trim())
        .filter(Boolean)
        .join(' ')
      author.authorRole = author.correspondingAuthor ? 'Corresponding Author' : 'Author'
      author.institutionName = primary?.organizationName || ''
      author.country = primary?.country || ''
      return stripKeys(author)
    }))
  },
  { deep: true },
)

function stripKeys(value) {
  const clone = JSON.parse(JSON.stringify(value))
  delete clone._key
  if (clone.affiliations) clone.affiliations.forEach((item) => delete item._key)
  return clone
}

const authorName = (author, index) => {
  const name = [author.givenName, author.middleName, author.familyName]
    .map((part) => part?.trim())
    .filter(Boolean)
    .join(' ')
  return name || `Author ${index + 1}`
}

const primaryAffiliation = (author) =>
  author.affiliations?.find((item) => item.primaryAffiliation) || author.affiliations?.[0]

const affiliationsExpanded = (author) => Boolean(expandedAffiliations.value[author._key])

const toggleAffiliations = (author) => {
  expandedAffiliations.value = affiliationsExpanded(author) ? {} : { [author._key]: true }
}

const closeAffiliations = () => {
  expandedAffiliations.value = {}
}

const handleKeydown = (event) => {
  if (event.key === 'Escape' && Object.keys(expandedAffiliations.value).length) {
    closeAffiliations()
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))

const affiliationSummary = (author) => {
  const affiliation = primaryAffiliation(author)
  if (!affiliation?.organizationName) return 'Institution details are required before submission.'
  return [affiliation.organizationName, affiliation.city, affiliation.country].filter(Boolean).join(', ')
}

const toggleEditor = (index) => {
  expandedIndex.value = expandedIndex.value === index ? -1 : index
}

const addAuthor = () => {
  localAuthors.value.push(withKeys([createEmptyAuthor(false)])[0])
  expandedIndex.value = localAuthors.value.length - 1
}

const removeAuthor = (index) => {
  if (localAuthors.value.length === 1) return
  localAuthors.value.splice(index, 1)
  if (!localAuthors.value.some((author) => author.correspondingAuthor)) {
    setCorrespondingAuthor(0, true)
  }
  expandedIndex.value = Math.min(expandedIndex.value, localAuthors.value.length - 1)
}

const moveAuthor = (index, direction) => {
  const target = index + direction
  if (target < 0 || target >= localAuthors.value.length) return
  const [author] = localAuthors.value.splice(index, 1)
  localAuthors.value.splice(target, 0, author)
  expandedIndex.value = target
}

const setCorrespondingAuthor = (index, checked) => {
  localAuthors.value.forEach((author, authorIndex) => {
    author.correspondingAuthor = checked ? authorIndex === index : authorIndex === index ? false : author.correspondingAuthor
  })
}

const addAffiliation = (authorIndex) => {
  const author = localAuthors.value[authorIndex]
  author.affiliations.push({
    ...createEmptyAffiliation(),
    primaryAffiliation: false,
    _key: makeKey(),
  })
}

const removeAffiliation = (authorIndex, affiliationIndex) => {
  const author = localAuthors.value[authorIndex]
  if (author.affiliations.length === 1) return
  const wasPrimary = author.affiliations[affiliationIndex].primaryAffiliation
  author.affiliations.splice(affiliationIndex, 1)
  if (wasPrimary) setPrimaryAffiliation(authorIndex, 0)
}

const setPrimaryAffiliation = (authorIndex, affiliationIndex) => {
  localAuthors.value[authorIndex].affiliations.forEach((item, index) => {
    item.primaryAffiliation = index === affiliationIndex
  })
}
</script>

<style scoped>
.author-editor { display: grid; gap: 14px; }
.author-list { border: 1px solid #d5dce1; border-bottom: 0; }
.author-list-row { display: grid; grid-template-columns: 44px minmax(0, 1fr) 176px; align-items: center; min-height: 68px; border-bottom: 1px solid #d5dce1; background: #fff; }
.author-list-row.expanded { background: #fbfcfc; }
.author-order { display: grid; place-items: center; align-self: stretch; border-right: 1px solid #e0e5e8; color: #61707a; font-weight: 700; }
.author-summary { display: grid; gap: 3px; min-width: 0; padding: 12px 14px; border: 0; background: transparent; text-align: left; cursor: pointer; }
.author-summary-name { color: #18242c; font-weight: 700; overflow-wrap: anywhere; }
.author-summary-meta { color: #68747c; font-size: 12px; overflow-wrap: anywhere; }
.author-actions { width: 176px; display: grid; grid-template-columns: repeat(4, 36px); gap: 6px; justify-content: end; padding-right: 12px; }
.author-icon-button { width: 36px; height: 36px; display: inline-grid; place-items: center; border: 1px solid #c8d0d5; background: #fff; color: #34444e; cursor: pointer; }
.author-icon-button:hover:not(:disabled) { background: #edf2f4; }
.author-icon-button:disabled { opacity: .35; cursor: not-allowed; }
.author-icon-button.danger { color: #a33d34; }
.author-detail { grid-column: 1 / -1; display: grid; gap: 18px; padding: 18px; border-top: 1px solid #d5dce1; background: #f7f9fa; }
.author-detail-heading, .affiliation-heading, .affiliation-editor-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.author-detail-heading > div, .affiliation-heading > div { display: grid; gap: 3px; }
.author-detail-heading span, .affiliation-heading span { color: #65727b; font-size: 12px; }
.author-fields { display: grid; gap: 12px; }
.author-fields.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.author-fields.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.author-field { display: grid; gap: 6px; min-width: 0; }
.author-field span { color: #36454f; font-size: 12px; font-weight: 700; }
.author-field input, .author-field select { width: 100%; min-height: 42px; padding: 8px 10px; border: 1px solid #bbc5cb; background: #fff; color: #18242c; }
.author-flags { display: flex; flex-wrap: wrap; gap: 20px; padding: 12px 14px; border: 1px solid #d6dde1; background: #fff; }
.author-flags label, .primary-radio { display: inline-flex; align-items: center; gap: 8px; color: #2f3d46; font-size: 13px; font-weight: 600; }
.author-contributions { margin: 0; padding: 14px; border: 1px solid #d6dde1; background: #fff; }
.author-contributions legend { padding: 0 6px; font-size: 13px; font-weight: 700; color: #34434d; }
.author-contributions > div { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px 14px; }
.author-contributions label { display: flex; gap: 7px; align-items: flex-start; color: #4b5962; font-size: 12px; line-height: 1.35; }
.author-command-button { min-height: 40px; width: fit-content; display: inline-flex; align-items: center; gap: 8px; padding: 8px 13px; border: 1px solid #1f5b78; background: #fff; color: #174b64; font-weight: 700; cursor: pointer; }
.affiliation-disclosure { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px; border: 1px solid #d6dde1; background: #fff; }
.affiliation-disclosure > div { display: grid; gap: 3px; min-width: 0; }
.affiliation-disclosure span { color: #65727b; font-size: 12px; overflow-wrap: anywhere; }
.affiliation-backdrop { position: fixed; inset: 0; z-index: 1200; background: rgba(18, 31, 39, .38); }
.affiliation-panel { position: fixed; z-index: 1201; top: 0; right: 0; bottom: 0; width: min(560px, 92vw); display: flex; flex-direction: column; gap: 16px; padding: 20px; overflow-y: auto; border-left: 1px solid #c8d1d6; background: #f4f6f7; box-shadow: -12px 0 28px rgba(18, 31, 39, .18); }
.affiliation-panel > .affiliation-heading { position: sticky; top: -20px; z-index: 1; margin: -20px -20px 0; padding: 18px 20px; border-bottom: 1px solid #d3dade; background: #fff; }
.affiliation-panel > .author-command-button { flex: 0 0 auto; }
.affiliation-list { display: grid; gap: 12px; }
.affiliation-editor { display: grid; gap: 12px; padding: 14px; border: 1px solid #d3dade; background: #fff; }
.affiliation-editor-head > div { display: flex; align-items: center; gap: 12px; }
.affiliation-address summary { color: #315c72; font-size: 13px; font-weight: 700; cursor: pointer; }
.affiliation-address[open] summary { margin-bottom: 12px; }
input:focus-visible, select:focus-visible, button:focus-visible, summary:focus-visible { outline: 3px solid rgba(38, 117, 158, .25); outline-offset: 1px; }
@media (max-width: 760px) {
  .author-list-row { grid-template-columns: 38px minmax(0, 1fr); }
  .author-actions { grid-column: 2; width: 100%; justify-content: start; padding: 0 12px 12px; }
  .author-fields.two, .author-fields.three, .author-contributions > div { grid-template-columns: 1fr; }
  .author-detail { padding: 14px; }
  .affiliation-heading { align-items: flex-start; flex-direction: column; }
  .affiliation-disclosure { align-items: flex-start; flex-direction: column; }
  .affiliation-disclosure .author-command-button { width: 100%; justify-content: center; }
  .affiliation-panel { width: 100vw; padding: 14px; }
  .affiliation-panel > .affiliation-heading { top: -14px; margin: -14px -14px 0; padding: 14px; }
}
</style>
