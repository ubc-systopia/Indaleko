import os

def count_files_and_directories(path):
    total_files = 0
    total_dirs = 0

    for root, dirs, files in os.walk(path):
        total_dirs += len(dirs)
        total_files += len(files)

    return total_files, total_dirs

# Change the root path to the directory you want to start the enumeration from
root_path = "C:\\"

file_count, dir_count = count_files_and_directories(root_path)

print("Total files:", file_count)
print("Total directories:", dir_count)

'''
Results from May 24, 2023

PS C:\Users\TonyMason\source\repos\arangodb> python .\enumerate-volume.py
Total files: 3540073
Total directories: 472693
PS C:\Users\TonyMason\source\repos\arangodb>

'''
