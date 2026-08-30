<#
.SYNOPSIS
    Creates the list views and applies the column / view formatting JSON.
    Run after provision_lists.ps1.

.DESCRIPTION
    The views in .\views\_views.json are the shop-floor user interface. There is no
    app behind them - the "auto-updating allotted list" is a view whose filter is
    Task_Status ne 'Completed'. When a checklist submission flips that field, the
    row leaves the technician's list on his next refresh. That is the entire
    mechanism, and it costs nothing to run.

    Formatting JSON lives in .\formatting\*.json. Each file may contain:
        ViewFormat     - applied to the view (row formatter / additionalRowClass)
        ColumnFormats  - a map of column internal name -> column formatting JSON

.PARAMETER SiteUrl
    Target site, e.g. https://contoso.sharepoint.com/sites/Maintenance

.EXAMPLE
    .\apply_views.ps1 -SiteUrl https://contoso.sharepoint.com/sites/Maintenance -WhatIf

.EXAMPLE
    .\apply_views.ps1 -SiteUrl https://contoso.sharepoint.com/sites/Maintenance
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$SiteUrl,

    [string]$ViewsFile      = (Join-Path $PSScriptRoot 'views\_views.json'),
    [string]$FormattingPath = (Join-Path $PSScriptRoot 'formatting')
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

Write-Head 'EPQPL PM System - views and formatting'
Write-Host "  Site : $SiteUrl"
if ($WhatIfPreference) { Write-Host '  Mode : WHAT-IF (dry run)' -ForegroundColor Yellow }

# Normalise the path separator so this runs on Windows and on a Linux build agent.
$ViewsFile      = $ViewsFile      -replace '\\', [IO.Path]::DirectorySeparatorChar
$FormattingPath = $FormattingPath -replace '\\', [IO.Path]::DirectorySeparatorChar

if (-not (Test-Path $ViewsFile)) { throw "Views file not found: $ViewsFile" }
$viewDef = Get-Content $ViewsFile -Raw -Encoding UTF8 | ConvertFrom-Json

if (-not $WhatIfPreference) {
    if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
        throw 'PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser'
    }
    Import-Module PnP.PowerShell -ErrorAction Stop
    Connect-PnPOnline -Url $SiteUrl -Interactive -ErrorAction Stop
    Write-Ok 'connected'
}

# Cache formatting files so a file shared by two views is read once.
$formatCache = @{}
function Get-FormatFile {
    param([string]$FileName)
    if (-not $FileName) { return $null }
    if ($formatCache.ContainsKey($FileName)) { return $formatCache[$FileName] }
    $path = Join-Path $FormattingPath $FileName
    if (-not (Test-Path $path)) {
        Write-Warn2 "formatting file not found: $FileName"
        $formatCache[$FileName] = $null
        return $null
    }
    $obj = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
    $formatCache[$FileName] = $obj
    return $obj
}

function Remove-CommentKeys {
    <#
        Strips the _comment documentation keys before the JSON is sent to
        SharePoint. They are there for whoever maintains this next; SharePoint
        does not need them and silently ignores unknown keys anyway, but a
        formatting payload has a size limit and the comments are not free.
    #>
    param($Node)
    if ($null -eq $Node) { return $null }
    if ($Node -is [System.Management.Automation.PSCustomObject]) {
        $clean = [ordered]@{}
        foreach ($p in $Node.PSObject.Properties) {
            if ($p.Name -eq '_comment') { continue }
            $clean[$p.Name] = Remove-CommentKeys $p.Value
        }
        return [PSCustomObject]$clean
    }
    if ($Node -is [System.Object[]]) {
        return @($Node | ForEach-Object { Remove-CommentKeys $_ })
    }
    return $Node
}

Write-Head "Views  ($($viewDef.Views.Count))"

$viewsDone = 0
$colsDone  = 0

foreach ($v in $viewDef.Views) {

    Write-Step "$($v.List)  /  $($v.Title)"

    $existing = $null
    if (-not $WhatIfPreference) {
        $existing = Get-PnPView -List $v.List -Identity $v.Title -ErrorAction SilentlyContinue
    }

    if ($existing) {
        if ($PSCmdlet.ShouldProcess("$($v.List)/$($v.Title)", 'Update existing view')) {
            Set-PnPView -List $v.List -Identity $v.Title -Values @{
                ViewQuery = $v.Query
                RowLimit  = $v.RowLimit
                Paged     = [bool]$v.Paged
            } | Out-Null
            Write-Ok 'view updated'
        }
    }
    else {
        if ($PSCmdlet.ShouldProcess("$($v.List)/$($v.Title)", "Create view ($($v.Fields.Count) columns)")) {
            Add-PnPView -List $v.List -Title $v.Title -Fields $v.Fields `
                        -Query $v.Query -RowLimit $v.RowLimit -Paged:([bool]$v.Paged) `
                        -SetAsDefault:([bool]$v.SetAsDefault) | Out-Null
            Write-Ok "view created ($($v.Fields.Count) columns, row limit $($v.RowLimit))"
        }
    }
    $viewsDone++

    $fmtFileName = $null
    if ($v.PSObject.Properties.Name -contains 'FormatFile') { $fmtFileName = $v.FormatFile }
    $fmt = Get-FormatFile $fmtFileName
    if (-not $fmt) { continue }

    # View-level formatting (row formatter / additionalRowClass)
    if ($fmt.PSObject.Properties.Name -contains 'ViewFormat') {
        $payload = (Remove-CommentKeys $fmt.ViewFormat) | ConvertTo-Json -Depth 30 -Compress
        if ($PSCmdlet.ShouldProcess("$($v.List)/$($v.Title)", "Apply view formatting ($($payload.Length) bytes)")) {
            Set-PnPView -List $v.List -Identity $v.Title `
                        -Values @{ CustomFormatter = $payload } | Out-Null
            Write-Ok "view formatting applied ($($payload.Length) bytes)"
        }
    }

    # Column-level formatting
    if ($fmt.PSObject.Properties.Name -contains 'ColumnFormats') {
        foreach ($p in $fmt.ColumnFormats.PSObject.Properties) {
            $payload = (Remove-CommentKeys $p.Value) | ConvertTo-Json -Depth 30 -Compress
            if ($PSCmdlet.ShouldProcess("$($v.List)/$($p.Name)", 'Apply column formatting')) {
                try {
                    Set-PnPField -List $v.List -Identity $p.Name `
                                 -Values @{ CustomFormatter = $payload } | Out-Null
                    Write-Ok "column formatting on $($p.Name)"
                    $colsDone++
                }
                catch { Write-Warn2 "column formatting on $($p.Name) failed: $($_.Exception.Message)" }
            }
            else { $colsDone++ }
        }
    }
}

Write-Head 'Summary'
Write-Host "  Views processed             : $viewsDone"
Write-Host "  Column formats applied      : $colsDone"

$hub = $viewDef.Views | Where-Object { $_.Title -eq 'Machine Hub' } | Select-Object -First 1
if ($hub) {
    Write-Host ''
    Write-Host '  QR payload pattern - put this in Machine_Master.QR_Payload_URL:' -ForegroundColor White
    Write-Host "    $($hub.QrTargetPattern)" -ForegroundColor Yellow
    Write-Host '  Substitute {SiteUrl}, {ViewUrlName} (the view page name SharePoint created,'
    Write-Host '  usually "Machine Hub.aspx" URL-encoded) and {Machine_ID}, then regenerate the'
    Write-Host '  labels with:  python qr/generate_qr_labels.py --test'
}
Write-Host ''
