# OpenIsle v2.1.0 中文交接说明

交接日期：2026-10-19。本版本是阶段性源码快照，供同事了解、运行和继续维护；不代表所有外部服务已配置或所有业务流程均完成验收。

## 1. 从哪里开始

- 仓库：<https://github.com/zzz20020612/OpenIsle>
- 固定版本：`v2.1.0`，以 GitHub Release 和对应标签为准。
- 核心功能源码基线：`9a138e570240be468e1e72cbc2436b2f610599da`；标签还包含本交接文档。
- 本项目的 `main` 保留旧代码，接手时应使用本标签，而非直接下载默认分支。
- 已部署域名：<https://zsgxpt.online>。本次源码发布没有更新线上服务，也没有重新检查线上现状。

建议阅读顺序：本文件 → `AGENTS.md` → `scholarheng-business-rules.md` → 需要维护的模块代码和 README。

## 2. 项目是什么

本项目从 OpenIsle 社区平台扩展而来，当前包含学术论文投稿与修订、AI 初筛、研究评价/排名、审稿任务、文献采集与知识处理，以及账号、讨论、消息和通知。源码仍保留部分上游命名与基础模块。

| 目录 | 职责与入口 |
| --- | --- |
| `frontend_nuxt/` | Nuxt/Vue 前端；`pages/papers/` 为论文页面，`pages/literature/` 为文献页面 |
| `backend/` | Spring Boot 主服务：账号、投稿、评价、业务 API、数据库 |
| `websocket_service/` | 独立 WebSocket/STOMP 通知服务，消费 RabbitMQ 消息 |
| `literature_system/` | Python 文献采集、PDF/参考文献解析、知识提炼、检索与可视化；先看其 README |
| `ai-screening/` | 稿件 AI 初筛，依赖外部模型配置 |
| `mcp/` | Python MCP 接口，封装平台操作 |
| `docker/` | Compose、Dockerfile、服务端口和数据卷定义 |
| `deploy/` | 原有部署脚本；使用前必须阅读下文限制 |
| `docs/` | 文档站和 OpenAPI 相关源码 |
| `scripts/` | Windows 本地启动、后端热重载等辅助脚本 |

主链路为：浏览器 → Nuxt/后端 API → MySQL；后端通过内部接口调用文献和初筛服务，通过 RabbitMQ/WebSocket 推送通知。文献库单独保存在 SQLite 和文件卷中。

## 3. 在新电脑运行

准备 Git、Docker Desktop（Linux containers + Compose v2）和 PowerShell。使用容器运行时，Java、Maven、Node 和 Python 由镜像提供；首次启动需要下载镜像、依赖并构建，时间较长。

```powershell
git clone --branch v2.1.0 https://github.com/zzz20020612/OpenIsle.git
cd OpenIsle
Copy-Item .env.example .env
# 先编辑 .env，参考下方配置说明
$env:COMPOSE_PROJECT_NAME = 'openisle-local'
./scripts/dev-start.ps1
```

`COMPOSE_PROJECT_NAME` 决定容器名和数据卷名。这里使用独立的本地名称；在已有数据的电脑上必须沿用原名称，改名会连接到另一个新卷。

配置说明：

- `.env.example` 是变量基线；`.env` 留在本机，不提交到 Git。
- 本地数据库使用示例的 `MYSQL_HOST=mysql`，宿主机映射端口默认为 `3307`；容器内部后端使用 MySQL `3306`。
- 修改示例数据库密码、JWT 系列密钥、内部服务令牌；将前端公开地址设为本地地址。
- `AI_SCREENING_API_KEY/BASE_URL/MODEL` 用于初筛和文献提炼；向量检索另需 `EMBEDDING_*`。MinerU、OAuth、邮件和 COS 也需相应凭据才能使用；同事通过私下授权渠道获取，不在仓库中查找真实密码。
- 默认 `REGISTER_MODE=WHITELIST`，不能假设任意邮箱都能注册。空 MySQL 数据卷的初始化脚本包含示例账号，参见 `backend/src/main/resources/db/init/02_seed_data.sql`；其密码为公开测试值，仅供本地使用。
- GitHub 源码不附带原来的 17 个账号或 102 篇采集文献，需要使用已有的非公开备份另行恢复。

启动后访问：

| 服务 | 本地入口 |
| --- | --- |
| 前端 | <http://localhost:3000> |
| 主后端 | <http://localhost:8080> |
| WebSocket | <http://localhost:8082> |
| 文献独立工作台 | <http://localhost:8088> |

```powershell
# 查看状态和日志
docker compose --env-file .env -f docker/docker-compose.yaml --profile dev ps
docker compose --env-file .env -f docker/docker-compose.yaml --profile dev logs --tail 100 springboot literature-system
# Java 代码改动后编译并等待重启
./scripts/backend-reload.ps1
# 需要 MCP 时启用
./scripts/dev-start.ps1 -IncludeMcp
```

前端源码绑定到开发容器，日常修改可热更新。首次启动失败时，先查看失败服务的日志，检查镜像下载、端口占用、配置和外部服务凭据。

## 4. 数据和备份

| 数据 | 保存位置 |
| --- | --- |
| 账号、论文业务、评论、评分、通知等 | MySQL，Compose 卷 `${COMPOSE_PROJECT_NAME}_mysql-data` |
| 采集文献、全文、知识卡片、向量、解析任务 | 文献卷 `${COMPOSE_PROJECT_NAME}_literature-data` 中的 `/app/data/literature.db` |
| 文献 PDF/解析文件 | 同一文献卷的 `/app/data/` 目录 |
| 上传文件/对象存储 | 依据后端配置；需额外核对本地 uploads 或 COS，不能仅备份数据库 |

2026-09-14 迁移时核对过的数据为：MySQL 17 个账号、11 篇帖子、15 条评论、62 条通知、24 条投稿草稿；文献库 102 篇文献、422 位作者、457 个解析任务。这是历史快照数量，不是对今天线上数据的实时统计。

当时服务器代码目录为 `/opt/openisle/OpenIsle`，MySQL 与文献卷的迁移前备份位于 `/opt/openisle/db-backups/`，服务器项目名为 `openisle`。接手时先由负责人提供服务器访问权限，再核对备份是否仍存在并获取新备份。

日常发布代码保留数据卷；不要用本地旧库覆盖线上新数据。`docker compose down -v` 会删除卷，不能作为普通更新步骤。SQLite 应在停写状态下归档整个文献卷，或者使用 SQLite 一致性备份接口；MySQL 使用逻辑备份并验证可恢复性。

## 5. 已知部署差异与限制

本节记录已有证据，未在此次发布中修改生产系统：

1. 2026-09 的服务器运行 OpenCloudOS、Docker、Nginx、HTTPS；服务健康不代表 OAuth、邮件、模型 API 等外部功能均已配置。证书续期、资源和备份状态需要接手人重新检查。
2. 上次部署在服务器上将 `mcp/pyproject.toml` 的依赖改为 `mcp>=1.19.0,<2`，仓库当前仍是 `mcp>=1.19.0`，重新构建可能拉到不兼容的大版本。
3. 上次部署在服务器上将前端健康检查改成 TCP 端口检查，并做过镜像下载相关调整。这些不保证全部存在于本标签；重新部署前应对比服务器文件与 Git 源码。
4. `deploy/deploy.sh` 当前从 `origin/<分支>` 获取代码并执行强制重置，而本地原 `origin` 指向上游 `nagisa77/OpenIsle`；其构建/启动列表也未包含完整的文献服务。不要直接将此脚本作为本版本的一键上线方式。先核实远端、目标提交、服务列表和线上未提交调整，再执行部署。
5. OpenSearch 在当前 Compose 中被注释，示例配置默认关闭搜索；不要把该服务视为已启用。
6. 本版本保留现有架构和依赖，并未完成依赖升级或全系统安全审计。

## 6. 此次验证范围

2026-10-19，对功能源码提交 `9a138e570` 执行：

```powershell
python -m pytest literature_system/tests -q
# 70 passed
cd frontend_nuxt
npm run test:reader
# 21 passed
npm run build
# 成功，退出码 0
```

构建有浏览器兼容数据过期、依赖 exports 弃用、JS 包体偏大、Windows sharp 二进制缺失警告。检查了常见密钥格式、Git diff 格式和远端提交一致性。未在本次重新运行全部 Java/MCP/文档站测试，也未做全流程业务验收或重新部署。

## 7. 同事接手的第一轮工作

1. 下载标签，读业务规则并在本地启动；先看论文、文献、投稿/修订、后台处理几个入口。
2. 从负责人处获取测试账号、必要的 API 凭据和经过授权的数据备份；保持测试环境与生产隔离。
3. 整理服务器与源码的差异，优先收敛 MCP 依赖、健康检查及部署脚本。
4. 实测一次投稿 → 初筛 → 审稿/评价，以及文献采集 → PDF 解析 → 知识提炼 → 阅读/检索链路，记录当前可用和待办项。
5. 后续从此标签新建开发分支。更新线上前先备份，并明确更新哪些服务及回滚提交。

独立的 `paper-workbench` 仓库、临时预览文件、压缩包、私有配置和运行数据不属于本次 OpenIsle 源码发布。
