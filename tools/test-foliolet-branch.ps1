$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'foliolet-desktop-common.ps1')
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('foliolet-branch-' + [guid]::NewGuid().ToString('N'))
# An empty disposable repository exercises Git's actual branch lookup, without
# checking out or changing any branch in the application repository.
& git init --quiet $fixture
if ($LASTEXITCODE -ne 0) { throw 'Could not create branch test fixture.' }
$folioletRoot = $fixture
foreach ($case in @(
    @{branch='feature/ps32-final-winning-audit-20261016-1645';allowed=$true},
    @{branch='feature/digilocker-assisted-intake';allowed=$true},
    @{branch='feature/digilocker-assisted-intake-test';allowed=$true},
    @{branch='main';allowed=$false},
    @{branch='cf';allowed=$false},
    @{branch='feature/unrelated';allowed=$false}
)) {
    & git -C $fixture symbolic-ref HEAD ('refs/heads/' + $case.branch)
    if ($LASTEXITCODE -ne 0) { throw 'Could not select fixture branch.' }
    $accepted=$true
    try { Assert-FolioletBranch } catch { $accepted=$false }
    if ($accepted -ne $case.allowed) { throw ('Wrong branch decision: ' + $case.branch) }
    Write-Output ('PASS branch guard: ' + $case.branch)
}
