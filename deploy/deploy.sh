#!/usr/bin/env bash
set -euo pipefail

# 可用法：
#   ./deploy.sh
#   ./deploy.sh feature/docker
deploy_branch="${1:-main}"

repo_dir="/opt/openisle/OpenIsle"
compose_file="${repo_dir}/docker/docker-compose.yaml"
env_file="${repo_dir}/.env"
project="openisle"

echo "👉 Enter repo..."
cd "$repo_dir"

echo "👉 Syncing code & switching to branch: $deploy_branch"
git fetch --all --prune
git checkout -B "$deploy_branch" "origin/$deploy_branch"
git reset --hard "origin/$deploy_branch"

echo "👉 Ensuring env file: $env_file"
if [ ! -f "$env_file" ]; then
  echo "❌ ${env_file} not found. Create it based on .env.example (with domains)."
  exit 1
fi

export COMPOSE_PROJECT_NAME="$project"
# 供 compose 内各 service 的 env_file 使用
export ENV_FILE="$env_file"

echo "👉 Validate compose..."
docker compose -f "$compose_file" --env-file "$env_file" config >/dev/null

echo "👉 Pull base images (for image-based services)..."
docker compose -f "$compose_file" --env-file "$env_file" pull --ignore-pull-failures

echo "👉 Build images ..."
# 前端 + OpenSearch 都是自建镜像；--pull 更新其基础镜像
docker compose -f "$compose_file" --env-file "$env_file" \
  build --pull \
  --build-arg NUXT_ENV=production \
  frontend_service mcp ai-screening

echo "👉 Recreate & start all target services (no dev profile)..."
docker compose -f "$compose_file" --env-file "$env_file" \
  up -d --force-recreate --remove-orphans --no-deps \
  mysql redis rabbitmq websocket-service ai-screening springboot frontend_service mcp

echo "👉 Current status:"
docker compose -f "$compose_file" --env-file "$env_file" ps

echo "👉 Pruning dangling images..."
docker image prune -f

echo "✅ Stack deployed at $(date)"
