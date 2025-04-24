import argparse
import os
import platform
import subprocess
import sys

# Check if Python version is >= 3.12


def check_python_version():
    if sys.version_info < (3, 12):
        print("Python 3.12 or later is required.")
        sys.exit(1)


"""
Command represents a command object
"""


class Command:
    def __init__(self, command_name):
        self.command_name = command_name
        self.args = []

    """
    arg = [key, value] if both key and value exits
    arg = [key] if only key exits
    """

    def add_arg(self, arg):
        self.args.extend(arg)

    """
    returns a list consisting of the command and all of its arguments.
    e.g: For the command 'docker ps -a', it will return ['docker', 'ps', '-a']
    """

    def to_list(self):
        return [self.command_name] + self.args

    """
    returns a string of the command
    """

    def __str__(self):
        return " ".join([self.command_name] + self.args)


class CommandBuilder:
    def __init__(self, command_name):
        self.command = Command(command_name=command_name)

    def add_arg(self, arg, value: str = ""):
        arg = [arg]
        if value:
            arg.append(value)
        self.command.add_arg(arg)

        return self

    def build(self):
        return self.command


def run_commands(commands: list[Command]):
    # Create necessary folders
    folders_to_create = ["./config", "./data", "./logs"]
    for folder in folders_to_create:
        os.makedirs(folder, exist_ok=True)

    for command in commands:
        try:
            print(">> running", command.build())
            subprocess.run(command.build().to_list(), check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running command: '{command}'")
            print(f"Err: {e}")
            sys.exit(1)


def main():
    # Check Python version
    check_python_version()

    if platform.system() != "Darwin":
        print("Only supports MacOS for now")
        exit(1)

    # Set up arguments parser
    parser = argparse.ArgumentParser(description="Runs Indaleko on MacOS")
    parser.add_argument("--path", help="Path provided by the user to index")
    parser.add_argument(
        "--reset",
        help="Drops the old collections before ingesting data",
        action="store_true",
    )
    args = parser.parse_args()

    prereq_commands = [
        CommandBuilder("docker").add_arg("ps"),
        CommandBuilder("pip").add_arg("install").add_arg("-r", "requirements.txt"),
    ]
    build_db_commands = [CommandBuilder("python").add_arg("dbsetup.py")]

    build_machine_config_commands = [
        CommandBuilder("python").add_arg("MacHardwareInfoGenerator.py").add_arg("-d", "./config").add_arg("--skip"),
        CommandBuilder("sleep").add_arg("10"),
        CommandBuilder("python").add_arg("IndalekoMacMachineConfig.py").add_arg("--add"),
    ]

    index_commands = [
        CommandBuilder("python").add_arg("IndalekoMacLocalIndexer.py").add_arg("--path", args.path),
        CommandBuilder("sleep").add_arg("10"),
    ]

    ingest_commands = [CommandBuilder("python").add_arg("IndalekoMacLocalIngester.py")]
    if args.reset:
        ingest_commands[0].add_arg("--reset")

    # Run the commands
    run_commands(prereq_commands)
    run_commands(build_db_commands)
    run_commands(build_machine_config_commands)
    run_commands(index_commands)
    run_commands(ingest_commands)


if __name__ == "__main__":
    main()
