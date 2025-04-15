#Requires -RunAsAdministrator

# The file name where we will save the ouput:
param(
    [string]$outputDir = "."
)

#$VerbosePreference = "Continue"
#$DebugPreference = "Continue"
#$ErrorActionPreference = "Stop"

#Write-Host "Capturing Windows Hardware Information"
#Write-Host "Output Directory: $outputDir"

# Define an object to store hardware data
$hardwareData = @{
    Hostname = [System.Net.Dns]::GetHostByName($env:COMPUTERNAME).HostName
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

#Write-Host "hardwareData: $hardwareData"

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
    Write-Host "Added Volume: $volinfo"
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
#Write-Host "Network Information: $networkAdapters"

# Fetch MachineGuid
$registryPath = "HKLM:\SOFTWARE\Microsoft\Cryptography"
$valueName = "MachineGuid"
try {
    $hardwareData.MachineGuid = (Get-ItemProperty -Path $registryPath -Name $valueName).$valueName
}
catch {
    Write-Host "Error retrieving MachineGuid: $_"
}
#Write-Host "MachineGuid: $($hardwareData.MachineGuid)"

# Convert the object to JSON format
$jsonData = ConvertTo-Json -InputObject $hardwareData

# let's generate a timestamp

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy_MM_ddTHH#mm#ss.fffffffZ")

#Write-Host "Timestamp: $timestamp"

# if the output file is not specified, output to a default name
if (-not $hardwareData.MachineGuid -eq "") {
    $outputFile = Join-Path -Path $outputDir -childPath "windows_hardware_info-plt=Windows-svc=windows_machine_config-machine=$($hardwareData["MachineGuid"])-ts=$timestamp.json"
}
else {
    $outputFile = Join-Path -Path $outputDir -childPath "windows_hardware_info-plt=Windows-svc=windows_machine_config-machine=unknown-ts=$timestamp.json"
}

# Output the JSON data
# Write-Output $jsonData
$jsonData | Out-File -FilePath $outputFile -Encoding utf8

#   Indaleko Windows Hardware Information Gathering Powershell script
#    Copyright (C) 2024 Tony Mason
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
# Write-Host "Data written to: $outputFile"
