<#
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


Write-Host ""
Write-Host "PM_WorkOrders" -ForegroundColor Cyan
New-PmList -Title "PM_WorkOrders" -Description "The core transactional list."

New-PmField -List "PM_WorkOrders" -Name "WOID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_WorkOrders" -Name "CycleID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_WorkOrders" -Name "CellName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "Area" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_WorkOrders" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "MachineType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "Criticality" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "PMType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "TriggerType" -Type "Choice" -Choices @("Std Hours","Calendar Backstop") -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "TriggerStdHrs" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "PlanMonth" -Type "Text" -Choices @() -Required $false -Indexed $true
New-PmField -List "PM_WorkOrders" -Name "PlannedDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "DueDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "AssignedTechID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_WorkOrders" -Name "AssignedTechName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "Shift" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "Status" -Type "Choice" -Choices @("Scheduled","In Progress","Completed","Overdue","Deferred") -Required $true -Indexed $true
New-PmField -List "PM_WorkOrders" -Name "ActualStartDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "ActualEndDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "DurationMin" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "ChecklistTotalTasks" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "ChecklistDoneTasks" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "ChecklistFailTasks" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "ChecklistCompletionPct" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "MachineQRScanned" -Type "Choice" -Choices @("Yes","No") -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "PMResult" -Type "Choice" -Choices @("Pass","Pass with observation","Fail - follow-up raised") -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "OnTimeFlag" -Type "Boolean" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "StdMinutes" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_WorkOrders" -Name "Remarks" -Type "Note" -Choices @() -Required $false -Indexed $false

Write-Host ""
Write-Host "PM_ChecklistResults" -ForegroundColor Cyan
New-PmList -Title "PM_ChecklistResults" -Description "One row per checklist task per work order."

New-PmField -List "PM_ChecklistResults" -Name "ResultID" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "WOID" -Type "Text" -Choices @() -Required $false -Indexed $true
New-PmField -List "PM_ChecklistResults" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_ChecklistResults" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "ChecklistID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "TaskNo" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "TaskDescription" -Type "Note" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "TaskType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "AcceptanceStandard" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "Mandatory" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "SafetyCritical" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "Result" -Type "Choice" -Choices @("OK","Not OK","Not Applicable") -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "MeasuredValue" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "Observation" -Type "Note" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "TechID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_ChecklistResults" -Name "RecordedDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_ChecklistResults" -Name "AbnormalityRaised" -Type "Choice" -Choices @("Yes","No") -Required $false -Indexed $false

Write-Host ""
Write-Host "Breakdown_Reports" -ForegroundColor Cyan
New-PmList -Title "Breakdown_Reports" -Description "Unplanned stoppages, raised from the machine QR by an operator or technician."

New-PmField -List "Breakdown_Reports" -Name "BreakdownID" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "Breakdown_Reports" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "Breakdown_Reports" -Name "CellName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "Area" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "MachineType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "Criticality" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "ReportedDateTime" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "RestoredDateTime" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "DowntimeMinutes" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "ResponseMinutes" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "FailureMode" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "FailureCategory" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "RootCause" -Type "Note" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "ActionTaken" -Type "Note" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "ReportedBy" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "AttendedTechID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "AttendedTechName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "Status" -Type "Choice" -Choices @("Open","In Progress","Pending Spare","Closed") -Required $true -Indexed $true
New-PmField -List "Breakdown_Reports" -Name "SpareUsed" -Type "Choice" -Choices @("Yes","No") -Required $false -Indexed $false
New-PmField -List "Breakdown_Reports" -Name "Severity" -Type "Choice" -Choices @("High","Medium","Low") -Required $false -Indexed $false

Write-Host ""
Write-Host "SparePart_Requests" -ForegroundColor Cyan
New-PmList -Title "SparePart_Requests" -Description "Requests raised from the machine QR, either during a PM or against a breakdown."

New-PmField -List "SparePart_Requests" -Name "RequestID" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "SparePart_Requests" -Name "SourceType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "SourceID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "SparePart_Requests" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "SparePart_Requests" -Name "PartNo" -Type "Number" -Choices @() -Required $true -Indexed $true
New-PmField -List "SparePart_Requests" -Name "PartName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "Category" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "UOM" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "QtyRequested" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "UnitCostINR" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "TotalCostINR" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "RequestedByTechID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "RequestedByName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "RequestDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "Urgency" -Type "Choice" -Choices @("Planned","Urgent","Emergency") -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "Status" -Type "Choice" -Choices @("Pending Approval","Approved","Issued","Purchase Raised","Rejected") -Required $true -Indexed $true
New-PmField -List "SparePart_Requests" -Name "ApprovedDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "ApprovedBy" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "IssuedDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "LeadTimeDays" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "StoreBin" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Requests" -Name "RejectionReason" -Type "Text" -Choices @() -Required $false -Indexed $false

Write-Host ""
Write-Host "SparePart_Replacements" -ForegroundColor Cyan
New-PmList -Title "SparePart_Replacements" -Description "What was actually fitted to the machine."

New-PmField -List "SparePart_Replacements" -Name "ReplacementID" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "SourceType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "SourceID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "RequestID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "SparePart_Replacements" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "SparePart_Replacements" -Name "MachineType" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "PartNo" -Type "Number" -Choices @() -Required $true -Indexed $true
New-PmField -List "SparePart_Replacements" -Name "PartName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "Category" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "UOM" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "QtyReplaced" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "UnitCostINR" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "TotalCostINR" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "ReplacedByTechID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "ReplacedByName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "ReplacedDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "OldPartCondition" -Type "Choice" -Choices @("Worn out","Broken","Leaking","Seized","End of life","Preventive replacement") -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "WarrantyClaim" -Type "Choice" -Choices @("Yes","No") -Required $false -Indexed $false
New-PmField -List "SparePart_Replacements" -Name "Remarks" -Type "Note" -Choices @() -Required $false -Indexed $false

Write-Host ""
Write-Host "Abnormality_Log" -ForegroundColor Cyan
New-PmList -Title "Abnormality_Log" -Description "Anything not right that is not yet a breakdown."

New-PmField -List "Abnormality_Log" -Name "AbnormalityID" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "Abnormality_Log" -Name "Source" -Type "Choice" -Choices @("PM Checklist","QR Walk-by","Breakdown","Audit") -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "SourceRefID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "Abnormality_Log" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "Abnormality_Log" -Name "CellName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "Area" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "Category" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "Severity" -Type "Choice" -Choices @("High","Medium","Low") -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "Description" -Type "Note" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "ReportedByTechID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "ReportedByName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "ReportedDate" -Type "DateTime" -Choices @() -Required $true -Indexed $true
New-PmField -List "Abnormality_Log" -Name "Status" -Type "Choice" -Choices @("Open","In Progress","Closed") -Required $true -Indexed $true
New-PmField -List "Abnormality_Log" -Name "ClosedDate" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "CorrectiveAction" -Type "Note" -Choices @() -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "OwnerFunction" -Type "Choice" -Choices @("Maintenance","Production","Safety","Quality") -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "EscalationRequired" -Type "Choice" -Choices @("Yes","No") -Required $false -Indexed $false
New-PmField -List "Abnormality_Log" -Name "PhotoURL" -Type "URL" -Choices @() -Required $false -Indexed $false

Write-Host ""
Write-Host "PM_Hour_Ledger" -ForegroundColor Cyan
New-PmList -Title "PM_Hour_Ledger" -Description "The audit trail of the scheduling rule."

New-PmField -List "PM_Hour_Ledger" -Name "MonthKey" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "PM_Hour_Ledger" -Name "CellName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "OpeningStdHrs" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "StdHoursAdded" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "ClosingStdHrs" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "PMIntervalStdHrs" -Type "Number" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "PMTriggered" -Type "Choice" -Choices @("Yes","No") -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "TriggerType" -Type "Choice" -Choices @("Std Hours","Calendar Backstop") -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "CarryOverAfterPM" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "MonthsSinceLastPM" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "PM_Hour_Ledger" -Name "Scenario" -Type "Choice" -Choices @("Actual","Forecast") -Required $false -Indexed $false

Write-Host ""
Write-Host "QR_Scan_Log" -ForegroundColor Cyan
New-PmList -Title "QR_Scan_Log" -Description "Audit trail of every QR scan."

New-PmField -List "QR_Scan_Log" -Name "ScanID" -Type "Text" -Choices @() -Required $true -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "QRType" -Type "Choice" -Choices @("Machine QR","Technician QR") -Required $false -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "MachineID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "QR_Scan_Log" -Name "MachineName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "TechID" -Type "Text" -Choices @() -Required $true -Indexed $true
New-PmField -List "QR_Scan_Log" -Name "TechName" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "ScanDateTime" -Type "DateTime" -Choices @() -Required $false -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "LinkedWOID" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "Action" -Type "Text" -Choices @() -Required $false -Indexed $false
New-PmField -List "QR_Scan_Log" -Name "CellID" -Type "Text" -Choices @() -Required $true -Indexed $true


Write-Host ""
Write-Host "Done. Next steps:" -ForegroundColor Green
Write-Host "  1. Check each list in Site contents - the columns should match"
Write-Host "     00-reference\SharePoint_List_Schemas.xlsx exactly."
Write-Host "  2. Set item-level permissions on PM_WorkOrders: read all, edit own."
Write-Host "  3. If this site is shared with other teams, break permission"
Write-Host "     inheritance on all eight lists now, before any real data goes in."
Disconnect-PnPOnline
