# Powershell script to collect hardware data

# Fetch CPU information
$CPU = Get-WmiObject -Class Win32_Processor
Write-Host "CPU: " $CPU.Name
Write-Host "Cores: " $CPU.NumberOfCores
Write-Host "Logical Processors: " $CPU.ThreadCount

# Fetch Memory information
$RAM = Get-WmiObject -Class Win32_ComputerSystem
Write-Host "Total Physical Memory (MB): " ($RAM.TotalPhysicalMemory / 1MB)

# Fetch Storage information
$Disks = Get-WmiObject -Class Win32_LogicalDisk -Filter "DriveType = 3"
foreach ($Disk in $Disks) {
    Write-Host "Disk: " $Disk.DeviceID
    Write-Host "   Size (GB): " ($Disk.Size / 1GB)
    Write-Host "   Free Space (GB): " ($Disk.FreeSpace / 1GB)
}

# Fetch Operating System information
$OS = Get-WmiObject -Class Win32_OperatingSystem
Write-Host "Operating System: " $OS.Caption
Write-Host "OS Architecture: " $OS.OSArchitecture
Write-Host "Version: " $OS.Version

# Fetch Network Adapter Configuration
$NetworkAdapters = Get-WmiObject -Class Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True"
foreach ($Adapter in $NetworkAdapters) {
    Write-Host "Network Adapter: " $Adapter.Description
    Write-Host "   IP Address(es): " $Adapter.IPAddress
    Write-Host "   MAC Address: " $Adapter.MACAddress
}
