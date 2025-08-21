import argparse
import datetime
import os


def count_files_and_directories(path: str, getstats: bool = False) -> tuple:
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
        if getstats:
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    stat_data = os.stat(file_path)
                    timestamp = datetime.datetime.fromtimestamp(
                        stat_data.stat_info.st_ctime,
                    )
                    oldest_file = min(oldest_file, timestamp)
                    newest_file = max(newest_file, timestamp)
                    file_sizes += stat_data.st_size
                    file_count += 1
                except:
                    continue
            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    stat_data = os.stat(dir_path)
                    timestamp = datetime.datetime.fromtimestamp(
                        stat_data.stat_info.st_ctime,
                    )
                    oldest_dir = min(oldest_dir, timestamp)
                    newest_dir = max(newest_dir, timestamp)
                    dir_sizes += stat_data.st_size
                    dir_count += 1
                except:
                    continue
    return total_files, total_dirs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("topdir")
    parser.add_argument(
        "--label",
        type=str,
        help="Add a descriptive label to the output",
        default="",
    )
    parser.add_argument(
        "--dostat",
        action="store_true",
        default=False,
        help="Perform file stat while enumerating",
    )
    args = parser.parse_args()
    start = datetime.datetime.utcnow()
    file_count, dir_count = count_files_and_directories(args.topdir, args.dostat)
    if type(args.label) is str and len(args.label) > 0:
        pass
    count = file_count + dir_count
    end = datetime.datetime.utcnow()
    end - start
    if count > 0:
        pass
    # TODO: write this to a json file


if __name__ == "__main__":
    main()


def scratch() -> None:
    # old code
    root_path = "C:\\Users\\TonyMason"

    start = datetime.datetime.utcnow()

    file_count, dir_count = count_files_and_directories(root_path)


    count = file_count + dir_count

    end = datetime.datetime.utcnow()
    end - start
    if count > 0:
        pass
