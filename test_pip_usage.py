"""Test file that uses pip directly - should trigger our hook."""

import os
import subprocess
import sys


def install_package(package_name):
    """Install a package using pip (BAD!)."""
    # This should trigger our check-no-pip-usage hook
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def another_bad_example():
    """Another example of direct pip usage (BAD!)."""
    # This should also trigger our hook
    os.system("pip install some-package")


if __name__ == "__main__":
    install_package("requests")
