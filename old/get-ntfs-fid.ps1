# Powershell script to get the FID for an NTFS file or process_directory

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Path
)

if (Test-Path -Path $Path) {
    $fsutilOutput = fsutil file queryfileid $Path
    Write-Host "File Identifier for '$Path': " $fsutilOutput.Split(":")[1].Trim()
} else {
    Write-Error "File or directory does not exist"
}
