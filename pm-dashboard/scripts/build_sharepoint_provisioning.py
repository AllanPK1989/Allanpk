"""Emit a PnP PowerShell script that provisions all eight PM lists.

Columns, types, choices, required and indexed flags come from the same LISTS
spec and infer_type() that produce SharePoint_List_Schemas.xlsx, so the script
and the schema workbook cannot disagree.

This has not been run against a tenant - there is no SharePoint here to run it
against. It is ordinary PowerShell rather than a binary package on purpose: it
fails one visible line at a time, and a line you do not like can be commented
out, which is not true of an import that either takes or does not.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_sharepoint_templates as S

OUT = os.path.join(ROOT, "sharepoint-templates", "Provision_PM_Lists.ps1")

# SharePoint column type as written in the schema workbook -> PnP -Type value.
PNP_TYPE = {
    "Single line of text": "Text",
    "Multiple lines of text": "Note",
    "Number": "Number",
    "Choice": "Choice",
    "Date and Time (date only)": "DateTime",
    "Date and Time (with time)": "DateTime",
    "Hyperlink": "URL",
    "Yes/No (choice)": "Boolean",
}

HEADER = r'''<#
    Provisions the eight SharePoint lists for the PM system.

    WHAT IT DOES
      Creates each list, adds every column with the right type, choice values,
      required and indexed settings, turns on versioning, and stops the unused
      Title column being mandatory.

    WHAT IT DOES NOT DO
      Nothing destructive. It never deletes a list and never deletes a column.
      Re-running it is safe: existing lists and columns are skipped, not reset.

    BEFORE YOU RUN IT
      1. Install the module (once, per machine):
             Install-Module PnP.PowerShell -Scope CurrentUser
      2. PnP.PowerShell 2.x and later need an Entra app registration of your own
         to sign in. If your tenant has one for PnP, put its client ID in
         $ClientId below. If it does not, and you cannot get one, use the manual
         route instead - see the import procedure document, section 2.
      3. Run it against a TEST site first. Read what it prints. Then run it
         against the real site.

    HOW TO RUN
         .\Provision_PM_Lists.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/YourSite"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SiteUrl,

    # Your tenant's PnP Entra app registration. Leave as-is only if your tenant
    # still allows the legacy multi-tenant app.
    [string] $ClientId = "",

    # Prints what would happen without changing anything.
    [switch] $WhatIfOnly
)

$ErrorActionPreference = "Stop"

if ($ClientId) {
    Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
} else {
    Connect-PnPOnline -Url $SiteUrl -Interactive
}
Write-Host "Connected to $SiteUrl" -ForegroundColor Green

function New-PmList {
    param([string] $Title, [string] $Description)
    $existing = Get-PnPList -Identity $Title -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "  list $Title already exists - leaving it alone" -ForegroundColor Yellow
        return
    }
    if ($WhatIfOnly) { Write-Host "  WOULD create list $Title"; return }
    New-PnPList -Title $Title -Template GenericList -OnQuickLaunch | Out-Null
    Set-PnPList -Identity $Title -Description $Description `
                -EnableVersioning $true -MajorVersions 50 | Out-Null
    # The Title column is unused by this system; leaving it mandatory blocks
    # every write from the app and the flows.
    Set-PnPField -List $Title -Identity "Title" -Values @{ Required = $false } | Out-Null
    Write-Host "  created list $Title" -ForegroundColor Green
}

function New-PmField {
    param([string] $List, [string] $Name, [string] $Type,
          [string[]] $Choices, [bool] $Required, [bool] $Indexed)
    $existing = Get-PnPField -List $List -Identity $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "    column $Name already exists - skipped" -ForegroundColor Yellow
        return
    }
    if ($WhatIfOnly) { Write-Host "    WOULD add $Name ($Type)"; return }
    if ($Type -eq "Choice") {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name `
                     -Type Choice -Choices $Choices -AddToDefaultView | Out-Null
    } else {
        Add-PnPField -List $List -DisplayName $Name -InternalName $Name `
                     -Type $Type -AddToDefaultView | Out-Null
    }
    $values = @{}
    if ($Required) { $values["Required"] = $true }
    if ($Indexed)  { $values["Indexed"]  = $true }
    if ($values.Count -gt 0) {
        Set-PnPField -List $List -Identity $Name -Values $values | Out-Null
    }
    Write-Host "    added $Name ($Type)"
}

'''

FOOTER = r'''
Write-Host ""
Write-Host "Done. Next steps:" -ForegroundColor Green
Write-Host "  1. Check each list in Site contents - the columns should match"
Write-Host "     00-reference\SharePoint_List_Schemas.xlsx exactly."
Write-Host "  2. Set item-level permissions on PM_WorkOrders: read all, edit own."
Write-Host "  3. If this site is shared with other teams, break permission"
Write-Host "     inheritance on all eight lists now, before any real data goes in."
Disconnect-PnPOnline
'''


def ps_str(s: str) -> str:
    return '"' + s.replace('"', '`"') + '"'


def build() -> str:
    out = [HEADER]
    for csv_name, xlsx_name, table, title, purpose, rules, validations in S.LISTS:
        header, _ = S.read_csv(csv_name)
        list_name = xlsx_name.replace(".xlsx", "")
        desc = purpose.split(".")[0].strip() + "."
        out.append(f'Write-Host ""')
        out.append(f'Write-Host "{list_name}" -ForegroundColor Cyan')
        out.append(f"New-PmList -Title {ps_str(list_name)} -Description {ps_str(desc)}")
        out.append("")
        for i, col in enumerate(header):
            t, choices = S.infer_type(col)
            if validations and col in validations:
                t, choices = "Choice", "; ".join(validations[col])
            if col.lower().endswith("description") or col.lower() in (
                    "remarks", "observation", "correctiveaction",
                    "actiontaken", "rootcause"):
                t = "Multiple lines of text"
            required = i == 0 or col in (
                "MachineID", "CellID", "Status", "TechID", "AssignedTechID",
                "ReportedDate", "PartNo")
            indexed = col in ("MachineID", "CellID", "WOID", "TechID",
                              "AssignedTechID", "PartNo", "PlanMonth",
                              "Status", "ReportedDate")
            pnp = PNP_TYPE[t]
            if t == "Yes/No (choice)":
                choice_list = "@()"
            elif choices:
                choice_list = ",".join(
                    ps_str(c.strip()) for c in choices.split(";") if c.strip())
                choice_list = f"@({choice_list})"
            else:
                choice_list = "@()"
            out.append(
                f"New-PmField -List {ps_str(list_name)} -Name {ps_str(col)} "
                f"-Type {ps_str(pnp)} -Choices {choice_list} "
                f"-Required ${str(required).lower()} -Indexed ${str(indexed).lower()}")
        out.append("")
    out.append(FOOTER)
    return "\n".join(out)


def main() -> None:
    script = build()
    open(OUT, "w", encoding="utf-8-sig", newline="\r\n").write(script)
    n_lists = len(S.LISTS)
    n_cols = script.count("\nNew-PmField -List ")
    print(f"  sharepoint-templates/Provision_PM_Lists.ps1  "
          f"({n_lists} lists, {n_cols} columns, {len(script.splitlines())} lines)")


if __name__ == "__main__":
    main()
