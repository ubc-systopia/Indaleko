#Requires -RunAsAdministrator

# The file name where we will save the ouput:
param(
    [string]$outputFile = ""
)



# Define an object to store hardware data
$hardwareData = @{
    CPU             = @{
        Name              = (Get-WmiObject -Class Win32_Processor).Name
        Cores             = (Get-WmiObject -Class Win32_Processor).NumberOfCores
        LogicalProcessors = (Get-WmiObject -Class Win32_Processor).ThreadCount
    }
    RAM             = @{
        TotalPhysicalMemory = (Get-WmiObject -Class Win32_ComputerSystem).TotalPhysicalMemory / 1MB
    }
    Disks           = @()
    OperatingSystem = @{
        Caption        = (Get-WmiObject -Class Win32_OperatingSystem).Caption
        OSArchitecture = (Get-WmiObject -Class Win32_OperatingSystem).OSArchitecture
        Version        = (Get-WmiObject -Class Win32_OperatingSystem).Version
    }
    NetworkAdapters = @()
    MachineGuid     = ""
}

# Fetch Storage information
$disks = Get-WmiObject -Class Win32_LogicalDisk -Filter "DriveType = 3"
foreach ($disk in $disks) {
    $diskData = @{
        DeviceID  = $disk.DeviceID
        Size      = $disk.Size / 1GB
        FreeSpace = $disk.FreeSpace / 1GB
    }
    $hardwareData.Disks += $diskData
}

# Fetch Network Adapter Configuration
$networkAdapters = Get-WmiObject -Class Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True"
foreach ($adapter in $networkAdapters) {
    $adapterData = @{
        Description = $adapter.Description
        IPAddress   = $adapter.IPAddress
        MACAddress  = $adapter.MACAddress
    }
    $hardwareData.NetworkAdapters += $adapterData
}

# Fetch MachineGuid
$registryPath = "HKLM:\SOFTWARE\Microsoft\Cryptography"
$valueName = "MachineGuid"
try {
    $hardwareData.MachineGuid = (Get-ItemProperty -Path $registryPath -Name $valueName).$valueName
}
catch {
    Write-Host "Error retrieving MachineGuid: $_"
}


# Convert the object to JSON format
$jsonData = ConvertTo-Json -InputObject $hardwareData

# if the output file is not specified, output to a default name
if ($outputFile -eq "") {
    if (-not $hardwareData.MachineGuid -eq "") {
        $outputFile = ".\config\windows-hardware-info-$($hardwareData["MachineGuid"]).json"
    }
    else {
        $outputFile = ".\config\windows-hardware-info.json"
    }
}

# Output the JSON data
# Write-Output $jsonData
$jsonData | Out-File -FilePath $outputFile -Encoding utf8

