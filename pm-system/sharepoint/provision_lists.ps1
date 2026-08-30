<#
.SYNOPSIS
    Provisions the EPQPL preventive-maintenance SharePoint Online site: 15 lists,
    5 document libraries, every column with the correct type, and the indexes the
    flows and views depend on.

.DESCRIPTION
    Column definitions are NOT held in this script. They are read from
    .\schema\*.json, which is generated from the data dictionary. That is
    deliberate: the schema and the provisioning script cannot drift apart.

    Every column is created from Field XML with Name, StaticName and DisplayName
    all set to the dictionary name. This matters more than it looks. If you let
    SharePoint derive the internal name from a display name containing an
    underscore, you get Cell_x005f_ID as the internal name, and every Power Query
    step, every Power Automate expression and every Power BI column reference
    then has to use that mangled name. Creating from XML keeps the name exactly
    as the dictionary states it, character for character.

.PARAMETER SiteUrl
    Target site, e.g. https://contoso.sharepoint.com/sites/Maintenance

.PARAMETER SchemaPath
    Folder holding the schema JSON files. Defaults to .\schema next to this script.

.PARAMETER SkipLibraries
    Provision lists only, no document libraries.

.PARAMETER Force
    Recreate a list that already exists. This DELETES the list and all its data.

.EXAMPLE
    # Dry run first - always. Prints every action, changes nothing.
    .\provision_lists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/Maintenance -WhatIf

.EXAMPLE
    .\provision_lists.ps1 -SiteUrl https://contoso.sharepoint.com/sites/Maintenance

.NOTES
    Requires PnP.PowerShell 2.x:  Install-Module PnP.PowerShell -Scope CurrentUser
    You need Site Owner rights on the target site.

    If your tenant blocks the default PnP app registration, register your own once:
        Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "EPQPL PM Provisioning" -Tenant contoso.onmicrosoft.com
    then pass the resulting client id with -ClientId on Connect-PnPOnline.
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$SiteUrl,

    [string]$SchemaPath = (Join-Path $PSScriptRoot 'schema'),

    [switch]$SkipLibraries,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Created = [System.Collections.Generic.List[string]]::new()
$script:Skipped = [System.Collections.Generic.List[string]]::new()
$script:Failed  = [System.Collections.Generic.List[string]]::new()

function Write-Step   { param([string]$m) Write-Host "  -> $m" -ForegroundColor Cyan }
function Write-Ok     { param([string]$m) Write-Host "     OK   $m" -ForegroundColor Green }
function Write-Skip   { param([string]$m) Write-Host "     SKIP $m" -ForegroundColor DarkGray }
function Write-Warn2  { param([string]$m) Write-Host "     WARN $m" -ForegroundColor Yellow }
function Write-Head   {
    param([string]$m)
    Write-Host ''
    Write-Host ('=' * 72) -ForegroundColor DarkCyan
    Write-Host "  $m" -ForegroundColor White
    Write-Host ('=' * 72) -ForegroundColor DarkCyan
}

# ---------------------------------------------------------------------------
# Field XML builders. One per SharePoint field type.
# ---------------------------------------------------------------------------
function ConvertTo-XmlSafe {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    return [System.Security.SecurityElement]::Escape($Value)
}

function New-FieldXml {
    <#
        Builds the CAML <Field/> element for one column.
        Name / StaticName / DisplayName are all set to the same value so the
        internal name matches the data dictionary exactly.
    #>
    param(
        [Parameter(Mandatory)] $Field,
        [Parameter(Mandatory)] [string]$ListTitle
    )

    $name     = ConvertTo-XmlSafe $Field.InternalName
    $display  = ConvertTo-XmlSafe $Field.DisplayName
    $required = if ($Field.Required) { 'TRUE' } else { 'FALSE' }
    $guid     = [guid]::NewGuid().ToString('B').ToUpper()

    $common = "ID=`"$guid`" Name=`"$name`" StaticName=`"$name`" DisplayName=`"$display`" Required=`"$required`""

    switch ($Field.Type) {

        'Text' {
            $max = if ($Field.PSObject.Properties.Name -contains 'MaxLength') { $Field.MaxLength } else { 255 }
            return "<Field $common Type=`"Text`" MaxLength=`"$max`" />"
        }

        'Note' {
            $lines = if ($Field.PSObject.Properties.Name -contains 'NumberOfLines') { $Field.NumberOfLines } else { 4 }
            return "<Field $common Type=`"Note`" NumLines=`"$lines`" RichText=`"FALSE`" RichTextMode=`"Compatible`" AppendOnly=`"FALSE`" />"
        }

        'Number' {
            $dec = if ($Field.PSObject.Properties.Name -contains 'Decimals') { $Field.Decimals } else { 2 }
            # Decimals="0" alone is not enough - without Percentage="FALSE" a
            # tenant with a non-English locale can render whole numbers oddly.
            return "<Field $common Type=`"Number`" Decimals=`"$dec`" Percentage=`"FALSE`" />"
        }

        'Boolean' {
            return "<Field $common Type=`"Boolean`"><Default>0</Default></Field>"
        }

        'DateTime' {
            $fmt = if ($Field.PSObject.Properties.Name -contains 'DisplayFormat') { $Field.DisplayFormat } else { 'DateOnly' }
            # Calendar="1" = Gregorian. FriendlyDisplayFormat="Disabled" stops
            # SharePoint showing "2 days ago" instead of the date, which makes
            # exported views and Power Automate output unreadable.
            return "<Field $common Type=`"DateTime`" Format=`"$fmt`" Calendar=`"1`" FriendlyDisplayFormat=`"Disabled`" />"
        }

        'URL' {
            return "<Field $common Type=`"URL`" Format=`"Hyperlink`" />"
        }

        'Choice' {
            $fill = if ($Field.FillInChoice) { 'TRUE' } else { 'FALSE' }
            $sb = [System.Text.StringBuilder]::new()
            [void]$sb.Append("<Field $common Type=`"Choice`" Format=`"Dropdown`" FillInChoice=`"$fill`"><CHOICES>")
            foreach ($c in $Field.Choices) {
                [void]$sb.Append("<CHOICE>$(ConvertTo-XmlSafe $c)</CHOICE>")
            }
            [void]$sb.Append('</CHOICES></Field>')
            return $sb.ToString()
        }

        default {
            throw "List '$ListTitle', column '$($Field.InternalName)': unsupported type '$($Field.Type)'"
        }
    }
}

# ---------------------------------------------------------------------------
function New-PmList {
    param([Parameter(Mandatory)] $Schema)

    $title = $Schema.ListTitle
    Write-Step "List: $title  ($($Schema.Fields.Count) columns, $($Schema.IndexedColumns.Count) indexes)"

    $existing = $null
    if (-not $WhatIfPreference) {
        $existing = Get-PnPList -Identity $title -ErrorAction SilentlyContinue
    }

    if ($existing) {
        if ($Force) {
            if ($PSCmdlet.ShouldProcess($title, 'DELETE list and all its data, then recreate')) {
                Remove-PnPList -Identity $title -Force
                Write-Warn2 "deleted existing list '$title'"
                $existing = $null
            }
        }
        else {
            Write-Skip "'$title' already exists. Re-run with -Force to recreate it (this deletes its data)."
            $script:Skipped.Add($title)
            # Still top up any missing columns - safe and idempotent.
        }
    }

    if (-not $existing) {
        if ($PSCmdlet.ShouldProcess($title, "Create list at $($Schema.ListUrl)")) {
            New-PnPList -Title $title -Template GenericList -Url $Schema.ListUrl `
                        -OnQuickLaunch:$false | Out-Null
            Set-PnPList -Identity $title -Description $Schema.Description `
                        -EnableVersioning:$Schema.EnableVersioning `
                        -MajorVersions $Schema.MajorVersionLimit `
                        -EnableAttachments:$Schema.EnableAttachments | Out-Null
            Write-Ok "created list '$title'"
            $script:Created.Add($title)
        }
    }

    # Title column: not required, because the primary key column is the real key.
    # load_data.ps1 fills Title from the primary key so items have a readable name.
    if ($PSCmdlet.ShouldProcess("$title/Title", 'Set Title column to not-required')) {
        try {
            Set-PnPField -List $title -Identity 'Title' -Values @{ Required = $false } | Out-Null
        }
        catch { Write-Warn2 "could not relax Title on '$title': $($_.Exception.Message)" }
    }

    foreach ($f in $Schema.Fields) {
        $fname = $f.InternalName
        $already = $null
        if (-not $WhatIfPreference) {
            $already = Get-PnPField -List $title -Identity $fname -ErrorAction SilentlyContinue
        }
        if ($already) { Write-Skip "column $fname exists"; continue }

        $xml = New-FieldXml -Field $f -ListTitle $title
        if ($PSCmdlet.ShouldProcess("$title/$fname", "Add $($f.Type) column")) {
            try {
                Add-PnPFieldFromXml -List $title -FieldXml $xml | Out-Null
                Write-Ok "column $fname ($($f.Type)$(if($f.Required){', required'}))"
            }
            catch {
                Write-Warn2 "column $fname FAILED: $($_.Exception.Message)"
                $script:Failed.Add("$title/$fname")
            }
        }
        else {
            Write-Verbose $xml
        }
    }

    # Indexes. Without these, a list over 5,000 items throws the list view
    # threshold error and the flow that reads it stops working - usually about
    # eight months after go-live, with no warning.
    foreach ($idx in $Schema.IndexedColumns) {
        if ($PSCmdlet.ShouldProcess("$title/$idx", 'Add column index')) {
            try {
                Set-PnPField -List $title -Identity $idx -Values @{ Indexed = $true } | Out-Null
                Write-Ok "index on $idx"
            }
            catch { Write-Warn2 "index on $idx failed: $($_.Exception.Message)" }
        }
    }
}

function New-PmLibrary {
    param([Parameter(Mandatory)] $Library)

    $title = $Library.Title
    Write-Step "Library: $title"

    $existing = $null
    if (-not $WhatIfPreference) {
        $existing = Get-PnPList -Identity $title -ErrorAction SilentlyContinue
    }
    if ($existing) { Write-Skip "'$title' already exists"; return }

    if ($PSCmdlet.ShouldProcess($title, 'Create document library')) {
        New-PnPList -Title $title -Template DocumentLibrary -Url $title `
                    -OnQuickLaunch:$false | Out-Null
        Set-PnPList -Identity $title -Description $Library.Description | Out-Null
        Write-Ok "created library '$title'"
        $script:Created.Add("$title (library)")
    }
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
Write-Head 'EPQPL PM System - SharePoint provisioning'
Write-Host "  Site   : $SiteUrl"
Write-Host "  Schema : $SchemaPath"
if ($WhatIfPreference) {
    Write-Host '  Mode   : WHAT-IF (dry run - nothing will be changed)' -ForegroundColor Yellow
}

if (-not (Test-Path $SchemaPath)) {
    throw "Schema folder not found: $SchemaPath"
}

$manifestPath = Join-Path $SchemaPath '_manifest.json'
if (-not (Test-Path $manifestPath)) {
    throw "Manifest not found: $manifestPath. Run tools/generate_sharepoint_schema.py first."
}
$manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

# In -WhatIf mode nothing touches the tenant, so neither the PnP module nor a
# connection is needed. That is deliberate: it means the whole schema can be
# validated on a laptop with no site access and no module installed, which is
# how you check a change before you are anywhere near production.
if (-not $WhatIfPreference) {
    if (-not (Get-Module -ListAvailable -Name PnP.PowerShell)) {
        throw 'PnP.PowerShell is not installed. Run: Install-Module PnP.PowerShell -Scope CurrentUser'
    }
    Import-Module PnP.PowerShell -ErrorAction Stop

    Write-Step 'Connecting'
    Connect-PnPOnline -Url $SiteUrl -Interactive -ErrorAction Stop
    $web = Get-PnPWeb
    Write-Ok "connected to '$($web.Title)'"
}
else {
    Write-Skip 'PnP module and connection skipped in -WhatIf mode'
}

Write-Head "Lists  ($($manifest.ProvisioningOrder.Count))"
foreach ($listName in $manifest.ProvisioningOrder) {
    $schemaFile = Join-Path $SchemaPath "$listName.json"
    if (-not (Test-Path $schemaFile)) {
        Write-Warn2 "schema file missing for '$listName' - skipped"
        $script:Failed.Add($listName)
        continue
    }
    $schema = Get-Content $schemaFile -Raw -Encoding UTF8 | ConvertFrom-Json
    New-PmList -Schema $schema
}

if (-not $SkipLibraries) {
    Write-Head "Document libraries  ($($manifest.DocumentLibraries.Count))"
    foreach ($lib in $manifest.DocumentLibraries) { New-PmLibrary -Library $lib }
}

Write-Head 'Summary'
Write-Host "  Created : $($script:Created.Count)"
Write-Host "  Skipped : $($script:Skipped.Count)  (already existed)"
Write-Host "  Failed  : $($script:Failed.Count)" -ForegroundColor $(if ($script:Failed.Count) { 'Red' } else { 'Green' })
if ($script:Failed.Count) { $script:Failed | ForEach-Object { Write-Host "            $_" -ForegroundColor Red } }

Write-Host ''
Write-Host '  Next steps:' -ForegroundColor White
Write-Host '    1.  .\apply_views.ps1     -SiteUrl <url>    # views + formatting'
Write-Host '    2.  .\load_data.ps1       -SiteUrl <url>    # load the CSVs'
Write-Host '    3.  docs\IMPLEMENTATION_RUNBOOK.md step 4   # build the Forms'
Write-Host ''
