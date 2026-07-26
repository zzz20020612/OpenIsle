param(
  [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $root 'docker\docker-compose.yaml'
$envFile = Join-Path $root '.env'

Push-Location $root
try {
  $containerId = (& docker compose --env-file $envFile -f $composeFile --profile dev ps -q springboot).Trim()
  if (-not $containerId) {
    throw 'The Spring Boot container is not running. Run scripts\dev-start.ps1 first.'
  }

  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  Write-Host 'Compiling changed backend sources...'
  & docker exec $containerId mvn -q -DskipTests compile
  if ($LASTEXITCODE -ne 0) {
    throw "Backend compilation failed with exit code $LASTEXITCODE"
  }

  Write-Host 'Waiting for Spring Boot DevTools restart...'
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      $health = Invoke-RestMethod -Uri 'http://localhost:8080/actuator/health' -TimeoutSec 5
      if ($health.status -eq 'UP') {
        $watch.Stop()
        Write-Host "Backend is healthy after $([Math]::Round($watch.Elapsed.TotalSeconds, 1)) seconds."
        return
      }
    } catch {
      # The endpoint is expected to be briefly unavailable during restart.
    }
    Start-Sleep -Seconds 3
  } while ((Get-Date) -lt $deadline)

  & docker logs --tail 80 $containerId
  throw "Backend did not become healthy within $TimeoutSeconds seconds."
} finally {
  Pop-Location
}
