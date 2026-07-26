param(
  [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $root 'docker\docker-compose.yaml'
$envFile = Join-Path $root '.env'
$buildContainer = 'openisle-frontend-build'
$frontendWasRunning = $false

Push-Location $root
try {
  $frontendId = (& docker compose --env-file $envFile -f $composeFile --profile dev ps -q frontend_dev).Trim()
  if ($frontendId) {
    $frontendWasRunning = $true
    Write-Host 'Stopping Nuxt dev server so it cannot modify .nuxt during the build...'
    & docker compose --env-file $envFile -f $composeFile --profile dev stop frontend_dev | Out-Host
  }

  $existing = & docker ps -aq --filter "name=^/$buildContainer$"
  if ($existing) {
    & docker rm -f $buildContainer | Out-Null
  }

  Write-Host "Starting isolated Nuxt build (timeout: $TimeoutSeconds seconds)..."
  $containerId = (& docker compose --env-file $envFile -f $composeFile --profile dev run -d --name $buildContainer --no-deps frontend_dev sh -c 'npm run build:verbose').Trim()
  if (-not $containerId) {
    throw 'Could not start the frontend build container.'
  }

  $watch = [System.Diagnostics.Stopwatch]::StartNew()
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $nextUpdate = [TimeSpan]::Zero
  do {
    $running = (& docker inspect -f '{{.State.Running}}' $buildContainer).Trim()
    if ($running -ne 'true') {
      $exitCode = [int]((& docker inspect -f '{{.State.ExitCode}}' $buildContainer).Trim())
      & docker logs $buildContainer
      if ($exitCode -ne 0) {
        throw "Nuxt build failed with exit code $exitCode."
      }
      $watch.Stop()
      Write-Host "Nuxt build completed in $([Math]::Round($watch.Elapsed.TotalSeconds, 1)) seconds."
      return
    }

    if ($watch.Elapsed -ge $nextUpdate) {
      Write-Host "Build still running: $([Math]::Round($watch.Elapsed.TotalSeconds)) seconds elapsed."
      & docker logs --tail 12 $buildContainer
      $nextUpdate = $watch.Elapsed.Add([TimeSpan]::FromSeconds(30))
    }
    Start-Sleep -Seconds 5
  } while ((Get-Date) -lt $deadline)

  & docker logs --tail 80 $buildContainer
  & docker stop -t 5 $buildContainer | Out-Null
  throw "Nuxt build timed out after $TimeoutSeconds seconds."
} finally {
  & docker rm -f $buildContainer 2>$null | Out-Null
  if ($frontendWasRunning) {
    Write-Host 'Restarting Nuxt dev server...'
    & docker compose --env-file $envFile -f $composeFile --profile dev up -d --no-deps frontend_dev | Out-Host
  }
  Pop-Location
}
