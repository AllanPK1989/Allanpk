<#
.SYNOPSIS
    Proves the SharePoint side of the PM system is correctly provisioned and loaded.

.DESCRIPTION
    Run this after provision_lists.ps1, apply_views.ps1 and load_data.ps1.

    It checks the things that go wrong quietly - a list short by one row, a column
    whose internal name SharePoint mangled, a filtered column with no index, a
    missing view - each of which works fine on day one and fails months later in a
    way nobody connects back to provisioning day.

    Everything it needs is read from the site itself and from the schema files, so
    it needs no other tooling.

.EXAMPLE
    .\verify_load.ps1 -SiteUrl "https://yourcompany.sharepoint.com/sites/Maintenance"

.EXAMPLE
    .\verify_load.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Maintenance" -ClientId "<id>"

.NOTES
    Requires PnP.PowerShell 2.x:  Install-Module PnP.PowerShell -Scope CurrentUser
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$SiteUrl,

    # Entra application id, if your tenant blocks the default PnP application.
    # Same value you passed to the other three scripts.
    [string]$ClientId,

    [string]$SchemaPath = (Join-Path $PSScriptRoot 'schema'),
    [string]$DataPath   = (Join-Path $PSScriptRoot 'data'),
    [string]$ViewsFile  = (Join-Path $PSScriptRoot 'views\_views.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Head ($t) { Write-Host ''; Write-Host $t -ForegroundColor Cyan;
                           Write-Host ('-' * 74) -ForegroundColor DarkGray }
function Write-Ok   ($t) { Write-Host "  PASS  $t" -ForegroundColor Green }
function Write-Fail ($t) { Write-Host "  FAIL  $t" -ForegroundColor Red }
function Write-Warn ($t) { Write-Host "  WARN  $t" -ForegroundColor Yellow }

$script:Failures = 0
function Check ($label, $ok, $detail) {
    if ($ok) { Write-Ok "$label$(if ($detail) { "   $detail" })" }
    else     { Write-Fail "$label$(if ($detail) { "   $detail" })"; $script:Failures++ }
}

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host '  PM system - post-load verification' -ForegroundColor Cyan
Write-Host "  $SiteUrl" -ForegroundColor DarkGray
Write-Host '======================================================================' -ForegroundColor Cyan

Import-Module PnP.PowerShell -ErrorAction Stop
$connect = @{ Url = $SiteUrl; Interactive = $true; ErrorAction = 'Stop' }
if ($ClientId) { $connect.ClientId = $ClientId; Write-Ok "using registered application $ClientId" }
Connect-PnPOnline @connect

$manifest = Get-Content (Join-Path $SchemaPath '_manifest.json') -Raw | ConvertFrom-Json
$order    = $manifest.ProvisioningOrder

# ---------------------------------------------------------------- lists exist
Write-Head '1. Every list exists, with every column'
$totalCols = 0
foreach ($name in $order) {
    $schema = Get-Content (Join-Path $SchemaPath "$name.json") -Raw | ConvertFrom-Json
    $list = Get-PnPList -Identity $name -ErrorAction SilentlyContinue
    if (-not $list) { Check "$name exists" $false ''; continue }

    $fields = Get-PnPField -List $name | Select-Object -ExpandProperty InternalName
    $want   = $schema.Fields | Select-Object -ExpandProperty InternalName
    $missing = @($want | Where-Object { $_ -notin $fields })
    $totalCols += $want.Count
    Check "$name" ($missing.Count -eq 0) `
          $(if ($missing.Count) { "missing column(s): $($missing -join ', ')" }
            else { "$($want.Count) columns" })
}
Write-Host "        $($order.Count) lists, $totalCols columns expected" -ForegroundColor DarkGray

# ------------------------------------------------------- internal names intact
# SharePoint rewrites a column name containing an underscore to Cell_x005f_ID if
# it is created the wrong way. Everything still looks fine in the browser; Power
# BI then loads blank columns and nothing says why.
Write-Head '2. Column internal names were not mangled'
$mangled = @()
foreach ($name in $order) {
    Get-PnPField -List $name |
        Where-Object { $_.InternalName -like '*_x005f_*' -or $_.InternalName -like '*_x0020_*' } |
        ForEach-Object { $mangled += "$name.$($_.InternalName)" }
}
Check 'no column name contains an escape sequence' ($mangled.Count -eq 0) `
      $(if ($mangled.Count) { $mangled -join ', ' } else { 'internal names match display names' })

# ------------------------------------------------------------------ row counts
Write-Head '3. Row counts reconcile against the exported data'
$countsFile = Join-Path $DataPath '_ROW_COUNTS.csv'
if (Test-Path $countsFile) {
    foreach ($row in Import-Csv $countsFile) {
        $listName = $row.List_Name
        $expected = [int]$row.Row_Count
        $list = Get-PnPList -Identity $listName -ErrorAction SilentlyContinue
        if (-not $list) { Check "$listName" $false 'list not found'; continue }
        $actual = $list.ItemCount
        Check "$listName" ($actual -eq $expected) "$actual of $expected"
    }
} else {
    Write-Warn "no _ROW_COUNTS.csv at $countsFile - skipping"
}

# --------------------------------------------------------------------- indexes
# An unindexed filter works perfectly until the list passes 5,000 items. Then it
# throws, the flow reading it stops, and it happens years after anyone remembers
# how the system was built.
Write-Head '4. Every column a view filters on is indexed'
$views = (Get-Content $ViewsFile -Raw | ConvertFrom-Json).Views
$gaps = @()
foreach ($name in $order) {
    $schema  = Get-Content (Join-Path $SchemaPath "$name.json") -Raw | ConvertFrom-Json
    $indexed = @($schema.IndexedColumns)
    $cols    = $schema.Fields | Select-Object -ExpandProperty InternalName
    foreach ($v in ($views | Where-Object { $_.List -eq $name })) {
        if (-not $v.Query) { continue }
        foreach ($m in [regex]::Matches($v.Query, "<FieldRef Name='([^']+)'")) {
            $col = $m.Groups[1].Value
            if ($col -in $cols -and $col -notin $indexed) { $gaps += "$name.$col (view '$($v.Title)')" }
        }
    }
}
Check 'no view filters on an unindexed column' ($gaps.Count -eq 0) `
      $(if ($gaps.Count) { $gaps -join '; ' } else { 'no 5,000-item threshold risk' })

# ----------------------------------------------------------------------- views
Write-Head '5. Every view was created'
foreach ($v in $views) {
    $found = Get-PnPView -List $v.List -Identity $v.Title -ErrorAction SilentlyContinue
    Check "$($v.List) / $($v.Title)" ($null -ne $found) ''
}

# ------------------------------------------------------------------- libraries
Write-Head '6. Every document library was created'
foreach ($lib in $manifest.DocumentLibraries) {
    $found = Get-PnPList -Identity $lib.Title -ErrorAction SilentlyContinue
    Check $lib.Title ($null -ne $found) ''
}

# ------------------------------------------------------- the counter is sane
# The reset rule in one query: a completed work order must have zeroed its cell.
# This is the failure that costs most and announces itself least.
Write-Head '7. No completed work order left its counter unreset'
try {
    $bad = Get-PnPListItem -List 'PM_WorkOrder' -PageSize 500 |
           Where-Object { $_.FieldValues.WO_Status -eq 'Completed' -and
                          -not $_.FieldValues.Reset_Applied }
    Check 'every completed work order has Reset_Applied = Yes' ($bad.Count -eq 0) `
          $(if ($bad.Count) { "$($bad.Count) work order(s): $(($bad | ForEach-Object { $_.FieldValues.WO_No }) -join ', ')" }
            else { 'integrity rule 3 holds' })
} catch {
    Write-Warn "could not read PM_WorkOrder - $($_.Exception.Message)"
}

# ----------------------------------------------------------------------- done
Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
if ($script:Failures -eq 0) {
    Write-Host '  Everything checks out. SharePoint is provisioned and loaded correctly.' -ForegroundColor Green
    Write-Host '======================================================================' -ForegroundColor Cyan
    exit 0
}
Write-Host "  $($script:Failures) CHECK(S) FAILED - read them above before going on." -ForegroundColor Red
Write-Host '======================================================================' -ForegroundColor Cyan
exit 1
