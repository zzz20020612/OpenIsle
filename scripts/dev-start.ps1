param(
  [int]$TimeoutSeconds = 360,
  [switch]$IncludeMcp
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $root 'docker\docker-compose.yaml'
$envFile = Join-Path $root '.env'
$services = @(
  'mysql',
  'redis',
  'rabbitmq',
  'websocket-service',
  'ai-screening',
  'springboot',
  'frontend_dev',
  'loopback_8080',
  'loopback_8082'
)
if ($IncludeMcp) {
  $services += 'mcp'
}

$watch = [System.Diagnostics.Stopwatch]::StartNew()
Push-Location $root
try {
  & docker compose --env-file $envFile -f $composeFile --profile dev up -d --wait --wait-timeout $TimeoutSeconds @services
  if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed with exit code $LASTEXITCODE"
  }
} finally {
  Pop-Location
}
$watch.Stop()

Write-Host "OpenIsle is ready in $([Math]::Round($watch.Elapsed.TotalSeconds, 1)) seconds."
Write-Host 'Frontend: http://localhost:3000'
Write-Host 'Backend:  http://localhost:8080/actuator/health'
Write-Host 'Tip: run scripts\backend-reload.ps1 after changing Java files.'
