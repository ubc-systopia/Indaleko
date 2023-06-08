$machineName = $env:COMPUTERNAME
$domainName = $env:USERDOMAIN
$pageSize = [System.Environment]::SystemPageSize
$osVersion = [Environment]::OSVersion.Version
$os = $null
$sid = $null
$domainSid = $null
$systemGuid = $null

if([Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([Runtime.InteropServices.OSPlatform]::Windows)) {
    $os = "Windows"

    $account = New-Object System.Security.Principal.NTAccount($machineName)
    $sid = $account.Translate([System.Security.Principal.SecurityIdentifier]).Value

    $windowsIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $domainSid = $windowsIdentity.User.Value.Substring(0, $windowsIdentity.User.Value.LastIndexOf('-'))

    $systemGuid = Get-ItemPropertyValue 'HKLM:\SOFTWARE\Microsoft\Cryptography' -Name 'MachineGuid'
}
else {
    $os = "Unsupported OS platform"
}

Write-Output "MachineName:$machineName"
Write-Output "DomainName:$domainName"
Write-Output "PageSize:$pageSize"
Write-Output "OSVersion:$osVersion"
Write-Output "OS:$os"
Write-Output "SystemSID:$sid"
Write-Output "DomainSID:$domainSid"
Write-Output "SystemGuid:$systemGuid"
