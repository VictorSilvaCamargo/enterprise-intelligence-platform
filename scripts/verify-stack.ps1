<#
.SYNOPSIS
    Verify the running Stage 1 Enterprise Intelligence Platform Docker Compose stack.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$backendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
$frontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }

if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*BACKEND_PORT=(\d+)\s*$") { $backendPort = $Matches[1] }
        if ($_ -match "^\s*FRONTEND_PORT=(\d+)\s*$") { $frontendPort = $Matches[1] }
    }
}

Write-Host "==> Checking Docker Compose service status..."
docker compose ps
if ($LASTEXITCODE -ne 0) { throw "docker compose ps failed." }

Write-Host "==> Verifying backend liveness: http://localhost:$backendPort/health"
$health = Invoke-RestMethod -Uri "http://localhost:$backendPort/health" -Method Get -TimeoutSec 5
if ($health.status -ne "ok") { throw "Unexpected /health status: $($health.status)" }
Write-Host ("    OK: {0} v{1} ({2})" -f $health.service, $health.version, $health.environment)

Write-Host "==> Verifying backend readiness: http://localhost:$backendPort/health/ready"
$ready = Invoke-RestMethod -Uri "http://localhost:$backendPort/health/ready" -Method Get -TimeoutSec 5
if ($ready.status -ne "ready") { throw "Unexpected /health/ready status: $($ready.status)" }
if ($ready.dependencies.postgresql.status -ne "up") { throw "PostgreSQL dependency is not up." }
if ($ready.dependencies.redis.status -ne "up") { throw "Redis dependency is not up." }
Write-Host ("    OK: postgresql={0} ({1}ms), redis={2} ({3}ms)" -f `
    $ready.dependencies.postgresql.status, $ready.dependencies.postgresql.latency_ms, `
    $ready.dependencies.redis.status, $ready.dependencies.redis.latency_ms)

Write-Host "==> Verifying OpenAPI specification: http://localhost:$backendPort/openapi.json"
$openapi = Invoke-RestMethod -Uri "http://localhost:$backendPort/openapi.json" -Method Get -TimeoutSec 5
if (-not $openapi.paths."/health" -or -not $openapi.paths."/health/ready") {
    throw "OpenAPI specification missing required health endpoints."
}
Write-Host "    OK: OpenAPI schema exposes /health and /health/ready"

Write-Host "==> Verifying frontend HTTP response: http://localhost:$frontendPort/"
$frontendResp = Invoke-WebRequest -Uri "http://localhost:$frontendPort/" -Method Get -TimeoutSec 5 -UseBasicParsing
if ($frontendResp.StatusCode -ne 200) { throw "Frontend returned HTTP $($frontendResp.StatusCode)" }
Write-Host "    OK: Frontend returned HTTP 200"

Write-Host "All Stage 1 stack checks passed."
