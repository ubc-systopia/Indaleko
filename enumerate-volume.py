import os
import datetime

def count_files_and_directories(path):
    total_files = 0
    total_dirs = 0
    file_sizes = 0
    dir_sizes = 0
    file_count = 0
    dir_count = 0
    newest_file = datetime.datetime.fromtimestamp(0)
    oldest_file = datetime.datetime.now()
    oldest_dir = datetime.datetime.now()
    newest_dir = datetime.datetime.fromtimestamp(0)
    for root, dirs, files in os.walk(path):
        total_dirs += len(dirs)
        total_files += len(files)
        for name in files:
            file_path = os.path.join(root, name)
            try:
                stat_data = os.stat(file_path)
                timestamp = datetime.datetime.fromtimestamp(
                    stat_data.stat_info.st_ctime)
                if timestamp < oldest_file:
                    oldest_file = timestamp
                if timestamp > newest_file:
                    newest_file = timestamp
                file_sizes += stat_data.st_size
                file_count += 1
            except:
                continue
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                stat_data = os.stat(dir_path)
                timestamp = datetime.datetime.fromtimestamp(
                    stat_data.stat_info.st_ctime)
                if timestamp < oldest_dir:
                    oldest_dir = timestamp
                if timestamp > newest_dir:
                    newest_dir = timestamp
                dir_sizes += stat_data.st_size
                dir_count += 1
            except:
                continue
    return total_files, total_dirs

# Change the root path to the directory you want to start the enumeration from
root_path = "C:\\Users\TonyMason"

start = datetime.datetime.utcnow()

file_count, dir_count = count_files_and_directories(root_path)

print("Total files:", file_count)
print("Total directories:", dir_count)

count = file_count + dir_count

end = datetime.datetime.utcnow()
execution_time = end - start
if count > 0:
    print('Enumerated {} in {} time ({} seconds per entry)'.format(
        count, execution_time, execution_time.total_seconds() / count))


def unused():
    '''
    Results from May 24, 2023

    PS C:\\Users\\TonyMason\\source\\repos\\arangodb> python .\enumerate-volume.py
    Total files: 3540073
    Total directories: 472693
    PS C:\\Users\\TonyMason\\source\\repos\\arangodb>
    '''
