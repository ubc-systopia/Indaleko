import subprocess
import platform
import multiprocessing
import time
import ctypes

'''
This is just a scratch script for figuring out how to do certain things.
'''


def main():
    import argparse
    import re
    import os
    import datetime
    import uuid

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', '-c', help='Path to the config files', default='./config')
    args = parser.parse_args()
    print(args)

    win_machine_info = [x for x in os.listdir(args.config) if x.startswith('windows-hardware-info')]
    print(win_machine_info)
    if len(win_machine_info) == 1:
        print(f'default to {win_machine_info[0]}')
        # Regular expression to match the GUID and timestamp
        pattern = r"windows-hardware-info-(?P<guid>[a-fA-F0-9\-]+)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z)\.json"
        match = re.match(pattern, win_machine_info[0])
        if match:
            guid = match.group("guid")
            timestamp = match.group("timestamp").replace("-", ":")
            print(f"GUID: {guid}")
            print(f"Timestamp: {timestamp}")
            guid = uuid.UUID(guid)
            # %f can only handle up to 6 digits and it seems Windows gives back
            # more sometimes. Note this truncates, it doesn't round.  I doubt
            # it matters.
            decimal_position = timestamp.rindex('.')
            if len(timestamp) - decimal_position - 2 > 6:
                timestamp = timestamp[:decimal_position + 7] + "Z"
            timestamp = datetime.datetime.strptime(timestamp, "%Y:%m:%dT%H:%M:%S.%fZ")
            print('Post conversion:')
            print(f"\tGUID: {guid}")
            print(f"\tTimestamp: {timestamp}")
        else:
            print("Filename format not recognized.")


if __name__ == "__main__":
    main()
