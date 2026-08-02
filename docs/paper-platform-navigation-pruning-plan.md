# Paper Platform Navigation Pruning Plan

## Goal

Turn the current OpenIsle community UI into a focused academic paper and knowledge-service platform while keeping the useful infrastructure from the source system.

## Product Direction

The source system is a community base. The target product should not feel like a general forum. It should feel like:

- a paper database,
- an academic evaluation community,
- an expert database foundation,
- a future enterprise knowledge-service portal.

## Keep As Core Entry Points

These pages should stay visible in the main navigation.

| Route | Decision | Reason |
| --- | --- | --- |
| `/papers` | Keep | Main public paper database and discovery page. |
| `/papers/submit` | Keep | Core author submission workflow. |
| `/papers/:id` | Keep | Paper detail, files, comments, ratings, and future knowledge extraction. |
| `/papers/rankings` | Keep | Paper, author, and institution ranking entrance. |
| `/login` | Keep | Required authentication entry. |
| `/signup` | Keep | Required author and reader onboarding. |
| `/users/:id` | Keep, refactor later | User profiles become author/expert profiles. |
| `/settings` | Keep | Account and profile settings. |
| `/message-box` | Keep | Direct messaging supports author, expert, and enterprise communication. |
| `/admin/papers` | Keep | Paper moderation and publication operations. |

## Keep But Refactor Into Academic Platform Features

These pages/components are useful, but their product meaning should change.

| Current Feature | Current Route/Area | Future Meaning |
| --- | --- | --- |
| User profile | `/users/:id` | Expert/author profile with papers, institutions, fields, ratings, and verified expertise. |
| Notifications | `/message` | Academic notifications: comments, paper status, review/rating reminders, expert contact events. |
| Search | `SearchDropdown.vue` | Paper/expert/knowledge search, not generic post search. |
| Comments | paper detail via reused post comments | Public academic discussion under papers. |
| Reactions | `ReactionsGroup.vue` | Keep lightly, but do not make it the main quality signal. Ratings should dominate. |
| Admin | admin endpoints/pages | Paper admission, risk control, taxonomy, expert verification, knowledge curation. |

## Hide From Main Navigation Now

These source-system pages can remain technically accessible during transition, but should disappear from primary navigation.

| Route | Decision | Reason |
| --- | --- | --- |
| `/` | Replace or redirect later | Current home is generic post feed. It should become paper feed, dashboard, or enterprise knowledge entry. |
| `/new-post` | Hide | Generic forum posting is not part of the target MVP. |
| `/posts/:id` | Hide, keep as internal dependency | Paper comments still reuse `Post`, but users should enter through `/papers/:id`. |
| `/posts/:id/edit` | Hide | Generic post edit should not be a visible product flow. |
| `/points` | Hide | Points/goods economy is not core to academic credibility. |
| `/activities` | Hide | Activity/campaign mechanics do not fit the current paper platform positioning. |
| `/about/stats` | Hide | Source community stats are not useful as primary product UI. |
| `/about` | Replace later | Needs paper-platform About, terms, data policy, and enterprise service intro. |

## Candidate For Later Removal

Do not delete these immediately. First confirm no paper workflow depends on them.

| Area | Candidate Files | Removal Condition |
| --- | --- | --- |
| Lottery / poll posts | `LotteryForm.vue`, `PostLottery.vue`, `PollForm.vue`, `PostPoll.vue` | Remove after generic `/new-post` and post type creation are retired. |
| Activity system UI | `activities.vue`, `ActivityPopup.vue`, `MilkTeaActivityComponent.vue`, `InviteCodeActivityComponent.vue` | Remove after no active platform campaigns depend on them. |
| Points mall UI | `points.vue`, `RedeemPopup.vue` | Remove or repurpose after deciding whether points are part of academic reputation. |
| Generic feed UI | `index.vue`, `TimelinePostItem.vue`, generic post feed logic | Remove after `/papers` becomes the default landing route. |
| Generic post editor | `PostEditor.vue`, `PostTypeSelect.vue`, `/new-post` | Remove after paper submission is the only creation flow. |

## Main Navigation Target

Primary navigation should be reduced to:

1. Papers
2. Submit
3. Rankings
4. Experts
5. Knowledge
6. Messages
7. Profile / Settings
8. Admin, only for admins

MVP can ship with Experts and Knowledge as disabled or placeholder routes only if they explain future structure without fake functionality.

## Recommended Implementation Phases

### Phase 1: Navigation Cleanup

- Make `/papers` the default product entry.
- Remove `/new-post`, `/activities`, `/points`, `/about/stats` from `MenuComponent.vue`.
- Keep hidden routes accessible only by direct URL during transition.
- Keep admin paper entry visible only for admins.

### Phase 2: Home Page Conversion

- Convert `/` from generic post feed into a paper-platform landing dashboard.
- Prioritize latest papers, top ranked papers, subject areas, and submission CTA.
- Do not build a marketing hero as the primary experience.

### Phase 3: Profile Refactor

- Refactor `/users/:id` into academic profile layout.
- Keep old user activity tabs only if useful.
- Add paper list, author identity, institution, research areas, and future expert-verification fields.

### Phase 4: Search Refactor

- Change search categories from generic posts/users/comments to papers/authors/experts/knowledge.
- Keep post search internally only for paper discussion comments.

### Phase 5: Retire Generic Community Creation

- Disable or remove `/new-post`.
- Keep `Post` backend model as infrastructure for paper discussion and feed mechanics.
- Remove lottery/poll/proposal creation UI unless deliberately repurposed.

## Backend Guidance

Do not delete backend services first. The paper platform still reuses:

- `Post`
- `Comment`
- `Reaction`
- `Notification`
- `Message`
- `User`
- `Admin`

Frontend pruning should happen before backend deletion. Backend deletion should only happen after route, component, and API dependency checks.

## Immediate Next Step

Start with `MenuComponent.vue` and `HeaderComponent.vue` only:

- keep Papers,
- keep Submit,
- add Rankings,
- keep Messages,
- keep Profile/Settings,
- keep Admin Papers for admins,
- hide generic Forum/New Post/Points/Activities/Stats.

This gives the product an academic-platform shape without risking backend regressions.
