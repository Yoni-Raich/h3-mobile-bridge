param(
    [string]$Range = '',
    [string]$Branch = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$repo = Get-RepoRoot
$types = 'feat|fix|perf|refactor|docs|test|build|ci|chore|revert'
$scopes = 'app|backend|ui|bootstrap|comfy|models|tailscale|docs|tests|ci|deps|release'
$subjectPattern = "^($types)\(($scopes)\)!?: [a-z0-9][^.]{0,70}$"
$branchName = if ($Branch) { $Branch } else { (@(git -C $repo branch --show-current) -join '').Trim() }
if (-not $branchName -and $env:GITHUB_HEAD_REF) { $branchName = $env:GITHUB_HEAD_REF }
# Actions checks out a shallow synthetic merge in detached HEAD mode.
# Validate the real PR commits and branch without depending on that merge subject.
$commitRange = $Range
if ($Range -eq 'HEAD' -and $env:GITHUB_EVENT_NAME -eq 'pull_request' -and $env:GITHUB_EVENT_PATH) {
    $event = Get-Content -LiteralPath $env:GITHUB_EVENT_PATH -Raw | ConvertFrom-Json
    $baseSha = [string]$event.pull_request.base.sha
    $headSha = [string]$event.pull_request.head.sha
    if ($baseSha -notmatch '^[0-9a-f]{40}$' -or $headSha -notmatch '^[0-9a-f]{40}$') {
        throw 'Pull request commit identifiers are invalid'
    }
    & git -C $repo fetch --no-tags origin $baseSha $headSha
    if ($LASTEXITCODE -ne 0) { throw 'Could not fetch pull request commits for validation' }
    $commitRange = "$baseSha..$headSha"
}
if ($branchName -and $branchName -ne 'main' -and $branchName -notmatch "^($types)/[0-9]+-[a-z0-9]+(?:-[a-z0-9]+)*$") {
    throw "Branch does not follow <type>/<issue-number>-<short-slug>: $branchName"
}
$subjects = if ($commitRange) { @(git -C $repo log --no-merges $commitRange --format=%s) } else { @(git -C $repo log -1 --format=%s) }
if ($LASTEXITCODE -ne 0 -or $subjects.Count -eq 0) { throw "No commits available for Git validation" }
foreach ($subject in $subjects) {
    if ($subject.Length -gt 72 -or $subject -notmatch $subjectPattern) {
        throw "Commit subject violates Git standards: $subject"
    }
}
foreach ($candidate in @('.runtime\probe.part', 'state\probe.log', 'config.local.json', 'models\probe.safetensors', 'logs\probe.log')) {
    git -C $repo check-ignore -q --no-index -- $candidate
    if ($LASTEXITCODE -ne 0) { throw "Required ignored path is not ignored: $candidate" }
}
Write-Host 'Git standards and ignore policy passed.'
exit 0
