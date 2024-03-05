#!/usr/bin/env python3

import sys
import subprocess
import argparse
import os

# Check if Python version is >= 3.12
def check_python_version():
    if sys.version_info < (3, 12):
        print("Python 3.12 or later is required.")
        sys.exit(1)

def run_commands(user_provided_path):
    # Create necessary folders
    folders_to_create = ['./config', './data', './logs']
    for folder in folders_to_create:
        os.makedirs(folder, exist_ok=True)

    # Run the commands
    commands = [
        ['python', 'dbsetup.py' ],
        ['python', 'MacHardwareInfoGenerator.py', '-d', './config'],
        ['sleep', '1'],
        ['python', 'IndalekoMacLocalIndexer.py', '--path', user_provided_path],
        ['python', 'IndalekoMacLocalIngester.py']
    ]
    for command in commands:
        try:
            print('>>> running', ' '.join(command))
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running command: {' '.join(command)}")
            print(e)
            sys.exit(1)

def main():
    # Check Python version
    check_python_version()

    # Set up arguments parser
    parser = argparse.ArgumentParser(description="Runs Indaleko on MacOS")
    parser.add_argument("--path", help="Path provided by the user to index")
    args = parser.parse_args()

    # Run the commands
    run_commands(args.path)

if __name__ == "__main__":
    main()