# cleanup.ps1 — Remove global i18n-agent-skill installations

$SKILL_NAME = "i18n-agent-skill"

$target_paths = @(
    "$env:USERPROFILE\.claude\skills\$SKILL_NAME",
    "$env:USERPROFILE\.cursor\rules\$SKILL_NAME",
    "$env:USERPROFILE\.gemini\skills\$SKILL_NAME",
    "$env:USERPROFILE\.agents\skills\$SKILL_NAME"
)

Write-Host "[INFO]  Cleaning up global installations..." -ForegroundColor Cyan

foreach ($p in $target_paths) {
    if (Test-Path $p) {
        Write-Host "[INFO]  Removing: $p" -ForegroundColor Cyan
        Remove-Item $p -Recurse -Force
    }
}

Write-Host "[OK]    Cleanup complete." -ForegroundColor Green
