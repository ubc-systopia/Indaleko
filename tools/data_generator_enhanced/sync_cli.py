#!/usr/bin/env python3
"""
Utility script to synchronize CLI interfaces between the main entry point
and the agents module entry point.
"""

import os
import shutil
import logging
from pathlib import Path

def main():
    """Copy CLI files to ensure consistency."""
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Get paths
    root_dir = Path(__file__).parent.resolve()
    handler_mixin_src = root_dir / "handler_mixin.py"
    handler_mixin_dest = root_dir / "agents" / "handler_mixin.py"

    cli_src = root_dir / "cli.py"
    cli_dest = root_dir / "agents" / "cli.py"

    # Copy handler_mixin.py
    logging.info(f"Copying {handler_mixin_src} to {handler_mixin_dest}")
    shutil.copy2(handler_mixin_src, handler_mixin_dest)

    # Copy cli.py
    logging.info(f"Copying {cli_src} to {cli_dest}")
    shutil.copy2(cli_src, cli_dest)

    logging.info("Synchronization complete!")

if __name__ == "__main__":
    main()
