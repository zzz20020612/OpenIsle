# Paper Platform Technical Development Plan

## 1. Project Positioning

本项目是在 OpenIsle 基础上二次开发的英文论文发布与评价平台。它不是传统期刊系统，而是一个更接近内容社区、论文数据库和评价平台结合体的系统。

核心流程是：作者提交论文，平台调用 AI initial screening，初筛通过后直接公开发布；公开后由读者和后续专家评价体系持续产生论文分数、作者排名、机构排名和主题推荐。

OpenIsle 已经提供用户、登录、帖子、草稿、分类标签、评论、互动、后台管理、通知和基础搜索能力。第一版不重写这些底座，而是在其上新增 `Paper Business Extension`。

开发规则：

- 平台界面、按钮、表单、提示语和演示数据使用英文。
- 代码命名、API、数据库实体和字段使用英文。
- 我和你讨论时继续使用中文。

## 2. Recommended Architecture

推荐采用 `OpenIsle Core + Paper Business Extension`。

`OpenIsle Core` 继续负责通用社区能力：

- `User`
- `Role`
- `Auth`
- `Post`
- `Draft`（仅指 OpenIsle 通用 post draft，不承载论文投稿表单）
- `Category`
- `Tag`
- `Comment`
- `Reaction`
- `Notification`
- `Admin`

`Paper Business Extension` 负责论文平台业务：

- `PaperProfile`
- `PaperSubmissionDraft`
- `PaperSubmissionFile`
- `PaperAuthor`
- `PaperAuthorAffiliation`
- `Institution`
- `PaperFundingRecord`
- `PaperFile`
- `PaperRating`
- `PaperScoreSnapshot`
- `AiScreeningResult`
- `ExpertProfile`
- `KnowledgeEntry`

核心设计原则是：不要把 `Post` 直接改成复杂论文总表。`Post` 继续承载最终论文的评论、reaction、subscription、notification 和 moderation；`PaperProfile` 保存正式完成投稿后的论文元数据与 publication state，并与 `Post` 一对一关联；`PaperSubmissionDraft` 只保存未完成、私有、owner-scoped 的交互式表单状态。

部分保存和 autosave 只能写入 `PaperSubmissionDraft` 及其 draft-scoped files，不能提前创建不完整的 `Post` 或 `PaperProfile`。

推荐关系：

```text
Post
  -> finalized content, comments, reactions, subscriptions, notifications, moderation

PaperProfile
  -> linked to Post
  -> formal finalized metadata, subject area, publication status, screening status

PaperSubmissionDraft
  -> incomplete private owner-scoped form state only
  -> no Post or PaperProfile before final submission

PaperRating
  -> linked to PaperProfile
  -> reader rating records

PaperScoreSnapshot
  -> linked to PaperProfile
  -> calculated paper score

Institution
  -> PaperAuthorAffiliation
  -> PaperAuthor
  -> each PaperAuthor may have multiple affiliations with exactly one primary
  -> used for institution ranking

AiScreeningResult
  -> linked to PaperProfile
  -> stores algorithm API result
```

## 3. Complete Platform Modules

完整平台最终包括以下模块。

### 3.1 Paper Database

论文数据库保存论文元数据、正文、作者、机构、关键词、主题、评分、知识条目和公开状态。

第一版中，正文和评论复用 `Post`，论文属性保存在 `PaperProfile`。

### 3.2 AI Screening

AI 初筛用于判断论文是否满足平台公开发布的基本条件。它不是学术质量裁决，而是基础准入检查。

第一版只做接口占位和 mock 结果，后续由算法团队提供 API。

建议状态：

- `PASSED`
- `NEEDS_REVISION`
- `REJECTED_BY_POLICY`

### 3.3 Rating System

评价系统是平台核心特色。读者注册并满足平台门槛后，可以对论文进行评分。评分结果进入论文分数计算，并进一步影响作者排名和机构排名。

第一版评分维度建议：

- `Originality`
- `Methodological Rigor`
- `Practical Value`
- `Clarity`
- `Overall Score`

### 3.4 Ranking System

排名系统由评分数据派生。

第一版至少包含：

- `Paper Ranking`
- `Author Ranking`
- `Institution Ranking`
- `Topic Ranking`

### 3.5 Expert Database

专家数据库用于后续专家身份识别、专家评价、专家推荐和企业服务。第一版只预留基础表和管理入口。

### 3.6 Institution Database

机构数据库用于作者归属、机构排名和企业知识服务。第一版需要支持论文作者绑定机构。

### 3.7 Knowledge Base

知识库用于把论文内容转化为结构化知识。它不只是搜索论文，而是回答“某个问题有哪些方法、创新点、贡献点、局限性和应用场景”。

第一版只预留 `KnowledgeEntry`，后续由算法团队写入结构化结果。

### 3.8 Recommendation System

推荐系统用于首页论文流、主题页、相似论文和企业知识服务。第一版先使用规则排序：latest、top rated、trending、subject filter。

### 3.9 Search Strategy

MVP 阶段默认关闭 OpenSearch，原因是本地样品部署要尽量轻量，避免搜索服务占用资源或阻塞启动。当前 OpenIsle 的搜索配置实际由 `SEARCH_ENABLED` 控制，因此本地 `.env` 应设置：

```ini
SEARCH_ENABLED=false
SEARCH_REINDEX_ON_STARTUP=false
```

关闭 OpenSearch 后，MVP 搜索采用 MySQL 实现。

基础方案：

- 对 `PaperProfile.title`、`abstractText`、`keywords` 建立 MySQL `FULLTEXT INDEX`。
- 作者名搜索可通过 `PaperAuthor.displayName` 做 `LIKE` 或单独建立索引。
- 主题筛选通过 `subjectArea` 精确匹配。
- 排序先支持 `latest`、`top_rated`、`trending`。

MVP API：

```text
GET /api/papers/search?q=xxx&subject=xxx&sort=latest|top_rated|trending
```

OpenSearch / Elasticsearch 的引入时机：

- 论文数据量超过 100,000 篇。
- 需要更复杂的全文检索、同义词、相关性排序、高亮摘要。
- 知识库检索和推荐系统进入正式开发阶段。

## 4. MVP Scope

第一版样品目标是跑通最小闭环：

```text
User login
  -> Paper submission
  -> AI screening placeholder
  -> Direct publication
  -> Reader rating
  -> Paper score
  -> Author ranking
  -> Institution ranking
  -> Basic admin management
```

第一版必须完成：

- 用户可以登录和注册。
- 作者可以提交 paper。
- Paper 可以保存 title、abstract、keywords、subject area、authors、institutions、content。
- 系统可以调用 mock AI screening。
- AI screening 通过后 paper 直接公开。
- 首页显示公开 paper feed。
- 读者可以评分和评价。
- Paper detail 展示评分和评价。
- Ranking 页面展示 paper、author、institution ranking。
- Admin 可以查看 paper list 和 screening status。

第一版暂不做：

- 完整专家认证。
- 真实推荐算法。
- 复杂知识图谱。
- 企业服务后台。
- 复杂论文版本管理。
- 传统审稿工作流。

## 5. Backend Design

后端继续使用 Spring Boot，新增论文业务实体、Repository、Service 和 Controller。

### 5.1 PaperProfile

作用：正式完成投稿后的论文业务主表，与 `Post` 一对一关联。未完成表单不写入该表。

建议字段：

- `id`
- `postId`
- `title`
- `abstractText`
- `keywords`
- `subjectArea`
- `paperType`
- `publicationStatus`
- `screeningStatus`
- `publishedAt`
- `primaryInstitutionId`
- `correspondingAuthorContactConfirmed`
- `correspondingAuthorContactConfirmedAt`
- `correspondingAuthorContactConfirmedBy`
- `createdBy`
- `createdAt`
- `updatedAt`

最终文件元数据以 normalized `PaperFile` rows 为权威来源。若为兼容现有消费者保留 `PaperProfile.manuscriptFiles` 或 `PaperProfile.supplementaryFiles`，它们只能是由 `PaperFile` 派生的 compatibility summaries，不得用于 visibility 或 access-control 判断。

建议状态：

- `SCREENING`
- `PUBLISHED`
- `NEEDS_REVISION`
- `REJECTED`
- `WITHDRAWN`
- `RETRACTED`

`PaperProfile` 在 final submission 事务中直接以 `SCREENING` 状态创建。`IN_PROGRESS` 属于 `PaperSubmissionDraft.status`，不是新的 `PaperProfile` 或 `Post` 记录。

状态含义：

- `WITHDRAWN`：公开前作者取消/放弃投稿，或公开后经 Admin 审核批准的撤稿结果。撤回后论文不在公开 feed 中展示，但历史记录和已有评分保留。
- `RETRACTED`：平台管理员强制下架。用于学术不端、违规内容或严重风险场景，只有 Admin 可以操作。

### 5.2 PaperAuthor

作用：保存论文作者列表。作者不一定都是平台注册用户。

建议字段：

- `id`
- `paperId`
- `userId`
- `givenName`
- `middleName`（optional）
- `familyName`
- `displayName`（derived compatibility/search field）
- `email`
- `authorRole`
- `authorOrder`
- `isCorrespondingAuthor`

最终提交要求每位作者都有 email、given name、family name、author role、至少一个 `PaperAuthorAffiliation`，且其中恰好一个为 primary affiliation。整篇投稿必须恰好有一位 corresponding author。

`givenName` 和 `familyName` 是权威姓名字段。`displayName` 由 `givenName`、可选 `middleName` 和 `familyName` 计算生成，仅用于兼容现有实现与搜索，不作为独立可编辑的数据源。

### 5.2.1 PaperAuthorAffiliation

作用：连接 `PaperAuthor` 与 normalized `Institution`，允许每位作者拥有多个 affiliations，并要求恰好一个 primary affiliation。

建议字段：

- `id`
- `paperAuthorId`
- `institutionId`
- `department`
- `city`
- `regionOrState`
- `country`
- `streetOrAddressLines`
- `postalCode`
- `isPrimary`
- `displayOrder`

公开 `organization` 值来自关联的 normalized `Institution.name`；如保留 author-specific organization snapshot，也必须由该 normalized institution 关系派生。

公开 affiliation 字段仅包括 organization、department、city、region/state 和 country。`streetOrAddressLines` 与 `postalCode` 始终私有，不得进入公开 API、搜索索引或页面元数据。

### 5.3 Institution

作用：保存机构信息，支撑机构排名。

建议字段：

- `id`
- `name`
- `country`
- `type`
- `website`
- `verified`
- `createdAt`
- `updatedAt`

### 5.4 PaperRating

作用：保存读者对论文的一次评分。

建议字段：

- `id`
- `paperId`
- `raterUserId`
- `originalityScore`
- `rigorScore`
- `practicalValueScore`
- `clarityScore`
- `overallScore`
- `commentText`
- `createdAt`
- `updatedAt`

第一版规则：一个用户对一篇论文只保留一条有效评分，可以更新。

### 5.5 PaperScoreSnapshot

作用：保存论文聚合分数，避免列表页每次实时计算。

建议字段：

- `id`
- `paperId`
- `ratingCount`
- `averageOverallScore`
- `weightedScore`
- `originalityAverage`
- `rigorAverage`
- `practicalValueAverage`
- `clarityAverage`
- `calculatedAt`

第一版可使用简单平均分，后续再加入用户权重、专家权重、时间衰减和反作弊规则。

### 5.6 AiScreeningResult

作用：保存 AI 初筛结果。

建议字段：

- `id`
- `paperId`
- `status`
- `riskLevel`
- `detectedSubjectArea`
- `detectedPaperType`
- `summary`
- `issuesJson`
- `rawResponseJson`
- `screenedAt`

### 5.7 AiScreeningLog

作用：保存每次 AI 初筛请求和响应，便于审计、调试和算法团队排查问题。

建议字段：

- `id`
- `paperId`
- `requestJson`
- `responseJson`
- `statusCode`
- `errorMessage`
- `durationMs`
- `createdAt`

### 5.8 ExpertProfile

作用：专家数据库预留。

建议字段：

- `id`
- `userId`
- `displayName`
- `institutionId`
- `degree`
- `title`
- `researchAreas`
- `verified`
- `externalProfileUrl`

### 5.9 KnowledgeEntry

作用：知识库预留。

建议字段：

- `id`
- `paperId`
- `entryType`
- `title`
- `content`
- `subjectArea`
- `keywords`
- `sourceQuote`
- `confidence`
- `createdAt`

`entryType` 建议：

- `PROBLEM`
- `METHOD`
- `INNOVATION`
- `CONTRIBUTION`
- `LIMITATION`
- `APPLICATION`

## 6. API Design

前端调用论文平台业务 API，不直接依赖复杂内部实现。

### 6.1 Submission Draft and Finalized Paper APIs

浏览器投稿工作区使用 owner-scoped draft APIs：

```text
POST /api/paper-submission-drafts
GET /api/paper-submission-drafts/current
GET /api/paper-submission-drafts/{draftId}
PATCH /api/paper-submission-drafts/{draftId}
DELETE /api/paper-submission-drafts/{draftId}
POST /api/paper-submission-drafts/{draftId}/files/presign
PATCH /api/paper-submission-drafts/{draftId}/files/{fileId}
DELETE /api/paper-submission-drafts/{draftId}/files/{fileId}
POST /api/paper-submission-drafts/{draftId}/validate
POST /api/paper-submission-drafts/{draftId}/submit
```

`GET /api/paper-submission-drafts/current` 返回当前用户最近更新的 `IN_PROGRESS` draft；没有可恢复草稿时返回 `204 No Content`。可通过 `kind=ORIGINAL|REVISION|ANY` 限定草稿用途，其中不传参数时保持 `ANY` 兼容行为。全局 Submit 入口必须请求 `ORIGINAL`，修订工作流必须通过明确的 revision draft ID 进入，避免普通投稿与修订稿互相恢复。

这些 draft endpoints 是交互式、owner-scoped 的浏览器工作流，因此有意不暴露为 MCP tools。未来 MCP 集成边界是 finalized paper APIs，而不是部分草稿的 autosave、恢复或文件编排接口。

正式论文 API 继续服务 final submission 之后的资源：

```text
GET /api/papers
GET /api/papers/{paperId}
PUT /api/papers/{paperId}
POST /api/papers/{paperId}/publish
```

### 6.2 AI Screening APIs

```text
POST /api/papers/{paperId}/screening
GET /api/papers/{paperId}/screening
```

第一版由后端 mock screening result。后续替换为算法团队 API，不改变前端接口。

### 6.3 Rating APIs

```text
POST /api/papers/{paperId}/ratings
GET /api/papers/{paperId}/ratings
GET /api/papers/{paperId}/my-rating
```

### 6.4 Ranking APIs

```text
GET /api/rankings/papers
GET /api/rankings/authors
GET /api/rankings/institutions
GET /api/rankings/topics/{topic}
```

### 6.5 Admin APIs

```text
GET /api/admin/papers
GET /api/admin/papers/{paperId}
POST /api/admin/papers/{paperId}/screening/override
POST /api/admin/institutions
POST /api/admin/experts
```

### 6.6 API Documentation

OpenIsle 已经包含 SpringDoc/OpenAPI 相关依赖。MVP 开发阶段需要把 API 文档作为前后端协作契约。

要求：

- 所有新增 Controller 增加 `@Tag`。
- 所有核心接口增加 `@Operation`。
- 重要响应增加 `@ApiResponse`。
- 本地开发时确认 OpenAPI JSON 可访问。
- 如果项目启用 Swagger UI，优先使用 Swagger UI 作为接口调试入口；如果只启用 API docs，则以前端请求代码和 OpenAPI JSON 作为契约。

## 7. Frontend Design

前端继续使用 Nuxt / Vue 3。第一版优先保证业务闭环，界面文案全部英文。

### 7.1 Home Page

首页从社区帖子流改成 paper feed。

区块：

- `Latest Papers`
- `Trending Papers`
- `Top Rated Papers`
- `Subject Filters`

论文卡片展示：

- Paper title
- Authors
- Institution
- Abstract snippet
- Subject area
- Score
- Rating count
- Published date

### 7.2 Submit Paper Page

使用独立的连续投稿工作区，并以 `PaperSubmissionDraft` autosave；打开或保存页面时不得创建 `Post` 或 `PaperProfile`。

字段：

- Title
- Abstract
- Keywords
- Subject Area
- Paper Type
- Exactly one DOCX Manuscript
- Exactly one Cover Letter
- Exactly one TOC Graphic
- Authors with Email, Given Name, Family Name, and Author Role
- At least one Affiliation and exactly one Primary Affiliation per Author
- Exactly one Corresponding Author
- Corresponding Author Public Contact Confirmation
- Structured Funding and Declarations
- Optional Supporting, Review Only, and Other Files

Final review 必须写入 `correspondingAuthorContactConfirmed = true`。Finalization 将该值连同 `correspondingAuthorContactConfirmedAt` 和 `correspondingAuthorContactConfirmedBy` 保存到 finalized metadata；公开后仅 corresponding author email 可公开。非 corresponding author email、street/address lines、postal code、Cover Letter、Review Only files 和 Comments to the Platform 始终私有。

### 7.3 Paper Detail Page

基于现有 `posts/[id]/index.vue` 改造。

内容：

- Paper metadata
- Structured public metadata and downloadable DOCX manuscript
- Score panel
- Rating distribution
- Reader reviews
- AI screening summary
- Knowledge entries placeholder

### 7.4 Rating Dialog

读者登录后可评分。

字段：

- Originality
- Methodological Rigor
- Practical Value
- Clarity
- Overall Score
- Comment

### 7.5 Ranking Page

新增 ranking 页面，第一版可以用 tabs：

- `Paper Ranking`
- `Author Ranking`
- `Institution Ranking`

### 7.6 Admin Pages

第一版后台只做必要功能：

- Paper list
- Screening status
- Manual override
- Institution management
- Basic rating monitoring

## 8. AI Integration Boundary

算法团队负责具体算法，平台负责流程、接口调用、结果存储和展示。

第一版定义统一 client：

```java
public interface AiScreeningClient {
    AiScreeningResponse screen(AiScreeningRequest request)
        throws AiServiceException, AiTimeoutException;
}
```

平台发送：

- Title
- Abstract
- Keywords
- Subject Area
- DOCX manuscript file reference or extracted text when available
- Authors
- Institutions

算法返回：

- Screening status
- Risk level
- Detected subject area
- Detected paper type
- Summary
- Issues
- Raw metadata

原则：

- AI 不直接修改论文正文。
- AI 不直接决定作者排名和机构排名。
- AI screening 只控制是否进入公开发布流程。
- Admin 可以 override AI screening result。
- 所有 AI 原始结果需要保存，便于审计和调试。

错误处理策略：

- Timeout: 30 seconds.
- Retry: no automatic retry in MVP, to avoid duplicate cost and duplicate side effects.
- Fallback: if AI service is unavailable, keep `PaperProfile.publicationStatus = SCREENING`.
- Admin handling: Admin can manually approve, reject, or request revision.
- Logging: every request and response must be persisted into `AiScreeningLog`.

## 9. Core Data Flow

第一版主流程：

```text
Author fills submit form
  -> System creates and autosaves PaperSubmissionDraft only
  -> Author reviews and confirms final submission
  -> correspondingAuthorContactConfirmed must equal true
  -> Idempotent transaction creates Post + PaperProfile
  -> Same transaction stores contact-confirmation audit metadata
  -> Same transaction creates authors + affiliations + funding + files + screening state
  -> Draft is locked and marked submitted
  -> Existing AI screening runs
  -> If PASSED, PaperProfile becomes PUBLISHED
  -> Paper appears in public feed
  -> Reader submits PaperRating
  -> PaperScoreSnapshot recalculated
  -> Author ranking updated
  -> Institution ranking updated
```

AI 初筛不通过：

```text
PaperProfile becomes NEEDS_REVISION or REJECTED
  -> Author sees issues
  -> Author can revise and resubmit
  -> Admin can manually override if needed
```

创建规则：

- `Post.title` 同步论文标题。
- `Post.content` 存储由正式元数据生成的公开可读正文或结构化摘要；当前阶段不解析 DOCX 全文。
- `PaperProfile` 存储摘要、关键词、主题、类型、发布状态和初筛状态。
- `PaperAuthor` 与 `PaperAuthorAffiliation` 存储作者顺序、多机构关系和 primary affiliation。
- Normalized `PaperFile` rows 是 final file metadata、role、visibility 和 access control 的权威来源；legacy `PaperProfile` file summaries 仅用于兼容。
- Public contact 只允许 exactly-one corresponding author email，且 final submission 必须验证并审计 `correspondingAuthorContactConfirmed = true`。
- Affiliation 公开字段为 organization、department、city、region/state、country；street/address lines 和 postal code 始终私有。
- Partial save 只更新 `PaperSubmissionDraft`，不创建 `Post`、`PaperProfile` 或其他正式论文记录。
- Final submission 必须幂等，并在同一个事务中创建 `Post`、`PaperProfile`、authors、affiliations、funding、final files 和 initial screening state。
- 相同 idempotency key 的重试返回同一篇正式论文，不得重复创建任何记录。
- `PaperSubmissionDraft.status = IN_PROGRESS` 表示私有草稿仍在编辑；取消时设置为 `ABANDONED`，且不创建或转换任何 `PaperProfile`。
- AI screening 在 finalization 后执行；调用失败时，已完成投稿的论文保持 `SCREENING`。

论文详情页聚合规则：

```text
GET /api/papers/{paperId}
  -> PaperProfile metadata
  -> Post content
  -> Post comments
  -> PaperRating list and summary
  -> PaperScoreSnapshot
  -> AiScreeningResult summary
```

取消、撤稿和下架流程：

```text
Private draft abandonment:
PaperSubmissionDraft IN_PROGRESS -> ABANDONED (no PaperProfile)

Finalized pre-publication cancellation:
SCREENING | NEEDS_REVISION | REJECTED -> WITHDRAWN

Post-publication withdrawal request:
PUBLISHED -> withdrawal request -> Admin review -> WITHDRAWN or RETRACTED

Admin retraction:
PUBLISHED -> RETRACTED
```

权限规则：

- 作者可以在公开发表前取消或放弃自己的投稿。
- AI 通过并公开发表后，作者不能自行撤回论文。
- 公开发表后的撤稿只能由作者提交 withdrawal request，由 Admin 审核处理。
- Admin 审核后可以将论文标记为 `WITHDRAWN`，如涉及违规或平台风险则标记为 `RETRACTED`。
- Admin 可以下架任意论文。
- `WITHDRAWN` 和 `RETRACTED` 不进入公开 feed 和 ranking。
- 已有评分和评论保留，用于审计和历史记录。

## 10. Score, Concurrency, and Ranking Rules

### 10.1 Score Snapshot Update

`PaperScoreSnapshot` 的更新时机必须明确，否则列表页、详情页和排名页会出现分数不一致。

MVP 推荐策略：

```text
PaperRatingService.saveOrUpdate()
  -> upsert PaperRating
  -> call PaperScoreSnapshotService.recalculate(paperId)
```

如果评分量较大，再改为异步：

```text
PaperRating saved
  -> publish PaperRatingChangedEvent
  -> @Async listener recalculates snapshot
```

或批量任务：

```text
@Scheduled every 5 minutes
  -> find papers with rating changes
  -> recalculate snapshots
```

### 10.2 Concurrency Control

评分去重：

```sql
UNIQUE(paper_id, rater_user_id)
```

含义：一个用户对一篇论文只有一条有效评分，重复评分时更新原记录。

快照更新：

- MVP 可以在事务中重新计算平均分并写入 `PaperScoreSnapshot`。
- 如果出现并发写冲突，使用 `SELECT ... FOR UPDATE` 锁定 snapshot row。
- 或在 `PaperScoreSnapshot` 增加 `version` 字段，使用 optimistic locking。

排名更新：

- Paper ranking 可以读取 `PaperScoreSnapshot`。
- Author ranking 和 institution ranking 不要求实时。
- MVP 使用定时任务周期性生成排名结果，避免每次评分都重算全站榜单。

### 10.3 Search Fallback

OpenSearch 关闭时，搜索能力由 MySQL 承担。

MVP 搜索范围：

- Paper title
- Abstract
- Keywords
- Author display name
- Subject area

MVP 不实现复杂语义搜索、向量检索和知识库问答。这些能力放到后续 AI/knowledge base 阶段。

## 11. MVP Testing Strategy

样品阶段不追求高覆盖率，但必须覆盖核心闭环。

最低测试要求：

- Integration test: partial autosave creates only `PaperSubmissionDraft`, with no `Post` or `PaperProfile` rows.
- Integration test: final submission validates exactly one corresponding author, required author fields and affiliations, and the three required file roles.
- Integration test: final submission is transactional and idempotent across paper metadata, authors, affiliations, funding, files, and screening state.
- Security test: draft ownership and private-file/public-field visibility rules.
- Integration test: `paper submission -> mock AI screening -> publication`.
- Integration test: `rating -> score snapshot update -> ranking data changes`.
- Service test: `PaperRatingService` must enforce one user, one rating.
- Service test: `AiScreeningClient` timeout and fallback behavior.

建议测试工具：

- Spring Boot Test。
- H2 or test MySQL container。
- Mock AI screening client。

## 12. Development Phases

### Phase 1: Environment Stabilization

- 保持 Docker Compose 可启动。
- 默认关闭 OpenSearch，并设置 `SEARCH_ENABLED=false`。
- 使用 MySQL `FULLTEXT INDEX` 作为 MVP 搜索替代方案。
- 保留 MySQL、Redis、RabbitMQ、Spring Boot、Nuxt。
- 确认默认账号可登录。
- 确认 SpringDoc OpenAPI 可用，并暴露本地 API 文档入口。

### Phase 2: Paper Data Layer

- 新增 `PaperSubmissionDraft` 和 draft-scoped file records。
- 新增 `PaperProfile`。
- 新增 `PaperAuthor`。
- 新增 `PaperAuthorAffiliation`、`PaperFundingRecord` 和 final `PaperFile`。
- 新增 `Institution`。
- 建立 `Post -> PaperProfile` 关联。
- 建立基础 repository 和 service。
- 为 `PaperProfile.title`、`abstractText`、`keywords` 建立 MySQL `FULLTEXT INDEX`。
- 为 Controller 补充 `@Tag`、`@Operation`、`@ApiResponse` 注解，保持前后端 API 契约清晰。

### Phase 3: Paper Submission and Publication

- 实现 EST-style continuous submission workspace 和 owner-scoped autosave。
- 新增 draft create/read/update/delete、file、validate 和 submit API。
- 实现幂等 finalization transaction，正式创建 `Post`、paper metadata、authors、affiliations、funding、files 和 screening state。
- 保持 browser draft APIs 不进入 MCP；finalized paper APIs 作为未来 MCP 集成边界。
- 新增 mock AI screening。
- AI passed 后自动发布。
- 首页展示 paper feed。

### Phase 4: Rating System

- 新增 `PaperRating`。
- 新增 `PaperScoreSnapshot`。
- 新增评分 API。
- 新增评分弹窗。
- 论文详情页展示分数和评价。
- 在 `PaperRating` 增加唯一约束 `UNIQUE(paperId, raterUserId)`，实现 one user, one rating。
- 在评分创建或更新后触发 `PaperScoreSnapshotService.recalculate(paperId)`。
- MVP 可先使用同步更新；如果性能不足，再改为 Spring Event + `@Async` 或 `@Scheduled` 批量任务。

### Phase 5: Ranking System

- 实现 paper ranking。
- 实现 author ranking。
- 实现 institution ranking。
- 前端新增 ranking page。
- 排名不要求实时更新，MVP 可通过定时任务周期性刷新，降低并发复杂度。

### Phase 6: Admin Management

- Admin paper list。
- AI screening result view。
- Manual override。
- Institution management。

### Phase 7: Knowledge and Expert Placeholders

- 新增 `ExpertProfile` 基础结构。
- 新增 `KnowledgeEntry` 基础结构。
- 新增知识库查询 API 占位。
- 新增专家库管理 API 占位。

## 13. MVP Acceptance Criteria

第一版样品完成标准：

- 用户可以登录平台。
- 作者可以提交 paper。
- Paper 经过 mock AI screening 后可以公开发布。
- 首页可以看到 public paper feed。
- 论文详情页可以查看 metadata、正文、分数和评价。
- 登录读者可以提交 rating。
- Paper score 可以更新。
- Author ranking 可以根据 paper score 显示。
- Institution ranking 可以根据 paper score 显示。
- Admin 可以查看 paper list 和 screening status。

完成以上能力后，平台就具备“论文发布 + 评价打分 + 排名”的最小可演示样品。

## 14. Three-System Local Integration

The current local integration combines three team deliverables without duplicating identity or paper records:

```text
OpenIsle
  -> registration, login, navigation, submission, screening, and public paper pages

Literature knowledge service
  -> online metadata collection, open-PDF acquisition, parsing, and structured knowledge extraction

Scholar衡 evaluation model
  -> six-dimensional human ratings, score snapshots, evaluated-paper rankings, and scholar rankings
```

Integration boundary:

- Existing-literature metadata and extracted knowledge remain authoritative in the literature service.
- OpenIsle proxies public literature reads and stores registered-user rating records in its own MySQL database.
- Ratings refer to the stable external `literaturePaperId`; PDF/full-text data is not duplicated into OpenIsle.
- The active ranking page reads `LiteratureScoreSnapshot`, not the legacy submitted-paper score snapshot.
- Paper and author ranking responses merge rating snapshots with current literature metadata at read time.
- The original Scholar衡 credit, task matching, appeals, and governance screens remain prototype concepts until
  their identity, moderation, conflict-of-interest, and audit rules are implemented.

Active APIs:

```text
POST /api/literature/papers/{paperId}/ratings
GET  /api/literature/papers/{paperId}/ratings
GET  /api/literature/papers/{paperId}/ratings/me
GET  /api/literature/papers/{paperId}/score
GET  /api/literature/rankings/papers
GET  /api/literature/rankings/authors
```

Browser draft and human-rating APIs remain user-interactive authenticated workflows and are not exposed as MCP
tools. Public finalized literature and ranking reads can be considered for MCP only after a stable cross-system
resource contract is approved.
