<#
.SYNOPSIS
    Loads the prepared CSVs from .\data into the SharePoint lists created by
    provision_lists.ps1.

.DESCRIPTION
    Uses PnP batching. This is not a micro-optimisation: Checklist_Response alone
    is ~1,000 rows, and one web request per row against SharePoint Online takes
    the better part of an hour and will trip throttling. Batched, the whole load
    is a couple of minutes.

    Type conversion happens here, once, in one place:
      Yes / No          -> [bool]
      yyyy-MM-dd        -> [datetime], parsed with InvariantCulture so a machine
                           set to en-IN does not read 2026-03-04 as 3 April
      URL columns       -> "url, description" - the shape PnP expects for a
                           Hyperlink field
      empty string      -> skipped entirely, so an optional column stays genuinely
                           empty rather than becoming the string ""

    Title is set from each list's primary key. SharePoint always has a Title
    column; leaving it blank gives you a list of items all called "Item", which
    makes search and every "Send an email with a link" step useless. Matching is
    always done on the real key column, never on Title.

.PARAMETER SiteUrl
    Target site.

.PARAMETER Only
    Load just these lists, e.g. -Only Cell_Master,Machine_Master

.PARAMETER Truncate
    Delete all existing items in each target list first. Destructive; prompts.

.PARAMETER BatchSize
    Items per batch. 100 is a good compromise between speed and a readable
    failure when one row is bad.

.EXAMPLE
    .\load_data.ps1 -SiteUrl https://contoso.sharepoint.com/sites/Maintenance -WhatIf

.EXAMPLE
    .\load_data.ps1 -SiteUrl https://contoso.sharepoint.com/sites/Maintenance -Only Cell_Master
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$SiteUrl,

    [string]$DataPath   = (Join-Path $PSScriptRoot 'data'),
    [string]$SchemaPath = (Join-Path $PSScriptRoot 'schema'),

    [string[]]$Only,
    [switch]$Truncate,

    [ValidateRange(1, 200)]
    [int]$BatchSize = 100
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step { param([string]$m) Write-Host "  -> $m" -ForegroundColor Cyan }
function Write-Ok   { param([string]$m) Write-Host "     OK   $m" -ForegroundColor Green }
function Write-Warn2{ param([string]$m) Write-Host "     WARN $m" -ForegroundColor Yellow }
function Write-Head {
    param([string]$m)
    Write-Host ''
    Write-Host ('=' * 72) -ForegroundColor DarkCyan
    Write-Host "  $m" -ForegroundColor White
    Write-Host ('=' * 72) -ForegroundColor DarkCyan
}

$DataPath   = $DataPath   -replace '\\', [IO.Path]::DirectorySeparatorChar
$SchemaPath = $SchemaPath -replace '\\', [IO.Path]::DirectorySeparatorChar

Write-Head 'EPQPL PM System - data load'
Write-Host "  Site : $SiteUrl"
Write-Host "  Data : $DataPath"
if ($WhatIfPreference) { Write-Host '  Mode : WHAT-IF (dry run)' -ForegroundColor Yellow }

$manifestPath = Join-Path $SchemaPath '_manifest.json'
if (-not (Test-Path $manifestPath)) { throw "Manifest not found: $manifestPath" }
$manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$order = $manifest.ProvisioningOrder
if ($Only) {
    $order = $order | Where-Object { $Only -contains $_ }
    if (-not $order) { throw "None of -Only [$($Only -join ', ')] matched a known list." }
}

if (-not $WhatIfPreference) {
    if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
        throw 'PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser'
    }
    Import-Module PnP.PowerShell -ErrorAction Stop
    Connect-PnPOnline -Url $SiteUrl -Interactive -ErrorAction Stop
    Write-Ok 'connected'
}

$invariant = [System.Globalization.CultureInfo]::InvariantCulture

function Convert-CellValue {
    <#
        Turns one CSV string into the CLR type the SharePoint column expects.
        Returns a marker of $null for "leave this column alone".
    #>
    param(
        [AllowNull()][AllowEmptyString()][string]$Raw,
        [Parameter(Mandatory)][string]$Type
    )

    if ([string]::IsNullOrWhiteSpace($Raw)) { return $null }

    switch ($Type) {
        'Boolean' {
            return ($Raw.Trim() -ieq 'Yes' -or $Raw.Trim() -eq '1' -or $Raw.Trim() -ieq 'true')
        }
        'Number' {
            [double]$d = 0
            if ([double]::TryParse($Raw, [System.Globalization.NumberStyles]::Float, $invariant, [ref]$d)) {
                return $d
            }
            throw "'$Raw' is not a number"
        }
        'DateTime' {
            # The CSVs are written as yyyy-MM-dd or yyyy-MM-ddTHH:mm:ss by
            # prepare_sharepoint_data.py. Parsing with an explicit format list and
            # InvariantCulture is what stops a machine set to a day-first locale
            # from silently reading 2026-03-04 as the 3rd of April.
            # [string[]] is load-bearing. A bare @(...) is an Object[], which makes
            # PowerShell bind to the single-format TryParseExact overload and join the
            # array into one nonsense format string - every date then fails to parse.
            [string[]]$formats = @('yyyy-MM-ddTHH:mm:ss', 'yyyy-MM-dd HH:mm:ss', 'yyyy-MM-dd')
            [datetime]$dt = [datetime]::MinValue
            if ([datetime]::TryParseExact($Raw, $formats, $invariant,
                    [System.Globalization.DateTimeStyles]::None, [ref]$dt)) {
                return $dt
            }
            throw "'$Raw' is not a recognised date"
        }
        'URL' {
            # PnP takes a Hyperlink field as "url, description".
            return "$Raw, Open"
        }
        default {
            return $Raw
        }
    }
}

$totalLoaded = 0
$totalFailed = 0

foreach ($listName in $order) {

    $csv = Join-Path $DataPath "$listName.csv"
    if (-not (Test-Path $csv)) {
        Write-Warn2 "no CSV for '$listName' - skipped"
        continue
    }

    $schema = Get-Content (Join-Path $SchemaPath "$listName.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $typeOf = @{}
    foreach ($f in $schema.Fields) { $typeOf[$f.InternalName] = $f.Type }
    $pk = $schema.PrimaryKey

    $rows = @(Import-Csv -Path $csv -Encoding UTF8)
    Write-Step "$listName  ($($rows.Count) rows)"

    if ($Truncate) {
        if ($PSCmdlet.ShouldProcess($listName, "DELETE ALL existing items")) {
            $existing = Get-PnPListItem -List $listName -PageSize 2000 -Fields 'ID'
            if ($existing.Count) {
                $b = New-PnPBatch
                foreach ($it in $existing) {
                    Remove-PnPListItem -List $listName -Identity $it.Id -Recycle -Batch $b | Out-Null
                }
                Invoke-PnPBatch -Batch $b -Details
                Write-Warn2 "removed $($existing.Count) existing item(s)"
            }
        }
    }

    $loaded = 0
    $failed = 0
    $batch = $null
    $inBatch = 0

    for ($i = 0; $i -lt $rows.Count; $i++) {

        $row = $rows[$i]
        $values = @{}

        foreach ($col in $row.PSObject.Properties.Name) {
            if (-not $typeOf.ContainsKey($col)) { continue }
            try {
                $v = Convert-CellValue -Raw $row.$col -Type $typeOf[$col]
                if ($null -ne $v) { $values[$col] = $v }
            }
            catch {
                Write-Warn2 "row $($i + 2), column ${col}: $($_.Exception.Message)"
                $failed++
            }
        }

        # Give the item a readable display name.
        if ($pk -and $row.PSObject.Properties.Name -contains $pk -and $row.$pk) {
            $values['Title'] = [string]$row.$pk
        }
        elseif ($listName -eq 'StdHours_Monthly') {
            $values['Title'] = "$($row.Upload_Month) $($row.Cell_ID)"
        }
        elseif ($listName -eq 'Checklist_Master') {
            $values['Title'] = "$($row.Checklist_ID) #$($row.Item_No)"
        }

        if ($WhatIfPreference) {
            if ($i -eq 0) {
                Write-Host "     sample payload: $((($values.GetEnumerator() | Sort-Object Name | Select-Object -First 6 | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '; '))" -ForegroundColor DarkGray
            }
            $loaded++
            continue
        }

        if ($null -eq $batch) { $batch = New-PnPBatch }
        Add-PnPListItem -List $listName -Values $values -Batch $batch | Out-Null
        $inBatch++
        $loaded++

        if ($inBatch -ge $BatchSize) {
            Invoke-PnPBatch -Batch $batch
            Write-Host "     ... $loaded / $($rows.Count)" -ForegroundColor DarkGray
            $batch = $null
            $inBatch = 0
        }
    }

    if (-not $WhatIfPreference -and $null -ne $batch -and $inBatch -gt 0) {
        Invoke-PnPBatch -Batch $batch
    }

    if ($WhatIfPreference) {
        Write-Host "What if: Performing the operation `"Add $loaded item(s)`" on target `"$listName`"."
    }
    Write-Ok "$loaded row(s)$(if ($failed) { ", $failed conversion problem(s)" })"
    $totalLoaded += $loaded
    $totalFailed += $failed
}

Write-Head 'Summary'
Write-Host "  Rows loaded            : $totalLoaded"
Write-Host "  Conversion problems    : $totalFailed" -ForegroundColor $(if ($totalFailed) { 'Red' } else { 'Green' })
Write-Host ''
Write-Host '  Reconcile against sharepoint\data\_ROW_COUNTS.csv before you go further.' -ForegroundColor White
Write-Host '  A short list here is a silently dropped row, and it will not announce itself later.'
Write-Host ''
