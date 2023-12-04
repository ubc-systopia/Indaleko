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
    VolumeInfo     =  @()
    OperatingSystem = @{
        Caption        = (Get-WmiObject -Class Win32_OperatingSystem).Caption
        OSArchitecture = (Get-WmiObject -Class Win32_OperatingSystem).OSArchitecture
        Version        = (Get-WmiObject -Class Win32_OperatingSystem).Version
    }
    NetworkAdapters = @()
    MachineGuid     = ""
}

# Fetch Storage information
$volumeInfo = Get-Volume | Select-Object OperationalStatus, HealthStatus, DriveType, DriveLetter, FileSystemType, UniqueId, AllocationUnitSize, FileSystem, FileSystemLabel, Size, SizeRemaining
foreach ($volume in $volumeInfo) {
    $volinfo = [PSCustomObject]@{
        'OperationalStatus' = $volume.OperationalStatus
        'HealthStatus'      = $volume.HealthStatus
        'DriveType'         = $volume.DriveType
        'DriveLetter' = $volume.DriveLetter
        'FileSystemType'    = $volume.FileSystemType
        'UniqueId'    = $volume.UniqueId
        'AllocationUnitSize'    = $volume.AllocationUnitSize
        'FileSystem'    = $volume.FileSystem
        'FileSystemLabel' = $volume.FileSystemLabel
        'Size' = $volume.Size
        'SizeRemaining' = $volume.SizeRemaining
    }
    $hardwareData.VolumeInfo += $volinfo
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

# let's generate a timestamp

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH-mm-ss.fffffffZ")


# if the output file is not specified, output to a default name
if ($outputFile -eq "") {
    if (-not $hardwareData.MachineGuid -eq "") {
        $outputFile = ".\config\windows-hardware-info-$($hardwareData["MachineGuid"])-$timestamp.json"
    }
    else {
        $outputFile = ".\config\windows-hardware-info-unknown-$timestamp.json"
    }
}

# Output the JSON data
# Write-Output $jsonData
$jsonData | Out-File -FilePath $outputFile -Encoding utf8

