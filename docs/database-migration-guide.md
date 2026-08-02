# Database Migration Guide

## 1. 这件事解决什么问题

之前论文相关表主要依赖：

```properties
spring.jpa.hibernate.ddl-auto=update
```

这表示 Spring Boot 启动时，Hibernate 会根据 Java Entity 自动尝试修改数据库表。

开发早期这样很方便，但它有三个问题：

1. 不可审查：别人不知道这次启动到底改了哪些表。
2. 不可复现：你的本地数据库和别人的数据库可能慢慢不一样。
3. 不适合回滚：线上出问题时，很难知道该撤销哪一次表结构变化。

正式项目通常使用 SQL migration：

```text
V12__create_paper_platform_tables.sql
V13__backfill_paper_post_type.sql
```

每个文件代表一次明确的数据库结构或数据变更。

## 2. 可以把 migration 理解成什么

把数据库想成一个共享 Excel 文件。

`ddl-auto=update` 像是程序打开 Excel 后自动加列、改列。速度快，但你不知道它具体做了什么。

SQL migration 像是每次改表前写一张变更单：

```sql
CREATE TABLE paper_profiles (...);
ALTER TABLE posts MODIFY COLUMN type ...;
```

团队所有人按相同顺序执行这些变更单，数据库结构就能保持一致。

## 3. 本次新增了什么

本次新增论文平台专用 migration：

```text
backend/src/main/resources/db/migration/V12__create_paper_platform_tables.sql
backend/src/main/resources/db/migration/V13__backfill_paper_post_type.sql
```

`V12` 创建论文平台核心表：

- `institutions`
- `expert_profiles`
- `paper_profiles`
- `paper_authors`
- `ai_screening_results`
- `paper_ratings`
- `paper_score_snapshots`

`V13` 做数据修正：

- 如果某个 `post` 已经被 `paper_profiles` 引用，就把它的 `posts.type` 修正为 `PAPER`。

同时调整了：

```text
backend/src/main/resources/db/migration/V11__add_paper_post_type.sql
```

原因是旧的 `V11` 同时做了两件事：

1. 给 `posts.type` 枚举加入 `PAPER`。
2. 立刻 join `paper_profiles` 回填数据。

但 `paper_profiles` 当时还没有对应 migration。未来如果按顺序执行 migration，`V11` 会因为找不到 `paper_profiles` 表而失败。所以现在把它拆开：

- `V11`：只修改 `posts.type` 枚举。
- `V12`：创建论文表。
- `V13`：回填已有 paper post 类型。

## 4. 为什么还没有直接启用 Flyway

仓库里已经有 `db/migration` 目录，但当前后端还没有启用 Flyway 依赖。

另外，原有 migration 文件里存在一个历史问题：两个文件都使用了 `V6` 版本号。Flyway 要求版本号唯一，否则启动会失败。

本次已经把其中一个文件改成：

```text
V6_1__add_visible_scope_to_posts.sql
```

这样版本顺序变成：

```text
V6
V6_1
V7
...
V13
```

这一步是在为后续正式启用 Flyway 做准备。

## 5. 现在如何使用

当前阶段：

- 本地开发仍默认使用 `ddl-auto=update`。
- 论文模块已有明确 SQL migration，可用于审查和部署准备。
- 如果要手动在数据库执行，可以按版本顺序执行 `db/migration` 下的 SQL。

配置已改成可通过环境变量控制：

```properties
spring.jpa.hibernate.ddl-auto=${SPRING_JPA_HIBERNATE_DDL_AUTO:update}
```

开发环境可以继续：

```env
SPRING_JPA_HIBERNATE_DDL_AUTO=update
```

正式环境最终应改成：

```env
SPRING_JPA_HIBERNATE_DDL_AUTO=validate
```

`validate` 的意思是：Hibernate 只检查 Entity 和数据库是否匹配，不再自动改表。

## 6. 后续正式启用 Flyway 的步骤

后续要真正让应用自动执行 migration，需要再做这些事：

1. 在 `backend/pom.xml` 添加 Flyway 依赖。
2. 配置 Flyway 读取 `classpath:db/migration`。
3. 对已有数据库做 baseline，避免 Flyway 误以为空库。
4. 把生产环境 `ddl-auto` 改为 `validate`。
5. 每次表结构变化只新增 migration 文件，不直接依赖 Hibernate 自动改表。

推荐生产配置方向：

```properties
spring.jpa.hibernate.ddl-auto=validate
spring.flyway.enabled=true
spring.flyway.locations=classpath:db/migration
spring.flyway.baseline-on-migrate=true
```

注意：这一步应该在完整验证后再做，不能在旧库没有 baseline 的情况下直接开启。

## 7. 面试时怎么解释

可以这样说：

> 早期 MVP 为了快速验证业务，我使用 Hibernate ddl-auto=update 自动同步表结构。但我知道这不适合正式项目，因为它不可审查、不可复现、不可回滚。所以我开始把论文平台核心表固化成版本化 SQL migration。当前已经补了 `V12` 创建论文核心表，`V13` 做 paper post 类型回填，并把 `ddl-auto` 改成环境变量控制。后续生产化会接入 Flyway，并把 ddl-auto 切到 validate。

如果面试官问为什么没有一步到位启用 Flyway：

> 因为这是基于开源项目二次开发，原仓库已有历史 migration 文件，但还没有真正启用 Flyway，而且存在旧版本号冲突。贸然启用会影响启动。我先做了低风险整理：补全论文模块 SQL migration，修复版本冲突，为后续 Flyway baseline 做准备。

## 8. 后续每次改表的规则

以后不要只改 Entity。

如果新增字段，例如给 `paper_profiles` 加 `doi`：

1. 修改 Java Entity。
2. 新增 migration 文件，例如：

```text
V14__add_doi_to_paper_profiles.sql
```

3. SQL 内容：

```sql
ALTER TABLE paper_profiles
  ADD COLUMN doi VARCHAR(255) DEFAULT NULL;
```

4. 本地执行测试。
5. 代码和 migration 一起提交。

这就是标准后端项目的数据库协作方式。
