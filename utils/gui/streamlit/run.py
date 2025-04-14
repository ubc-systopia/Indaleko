#!/usr/bin/env python
"""
Indaleko Streamlit GUI runner script

This script provides a convenient way to launch the Streamlit GUI.

Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys
import subprocess
import argparse

# Set up path to include Indaleko modules
# Find the Indaleko root directory
current_path = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
    current_path = os.path.dirname(current_path)

# Set environment variable if not already set
if os.environ.get("INDALEKO_ROOT") is None:
    os.environ["INDALEKO_ROOT"] = current_path
else:
    # Use the value from the environment if set
    current_path = os.environ["INDALEKO_ROOT"]

# Clean up sys.path to ensure a clean import environment
# This helps prevent module lookup conflicts
new_path = []
for p in sys.path:
    if p not in new_path:
        new_path.append(p)
sys.path = new_path

# Ensure the project root is FIRST in the Python path
if current_path in sys.path:
    sys.path.remove(current_path)
sys.path.insert(0, current_path)
    
print(f"INDALEKO_ROOT set to: {os.environ['INDALEKO_ROOT']}")
print(f"Python path first entry: {sys.path[0]}")
print(f"Full Python path: {sys.path}")

def main():
    """Main function to run the Streamlit app"""
    parser = argparse.ArgumentParser(description="Run the Indaleko Streamlit GUI")
    parser.add_argument("--port", type=int, default=8501, help="Port to run Streamlit on")
    parser.add_argument("--browser", action="store_true", help="Open browser automatically")
    args = parser.parse_args()
    
    # Get the path to app.py
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    
    # Check that we can find the app
    if not os.path.exists(app_path):
        print(f"Error: Could not find app.py at {app_path}")
        sys.exit(1)
    
    # Build the command
    cmd = [
        "streamlit", "run", app_path, 
        "--server.port", str(args.port)
    ]
    
    if not args.browser:
        cmd.extend(["--server.headless", "true"])
    
    try:
        # Run Streamlit
        print(f"Starting Indaleko GUI on port {args.port}...")
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nShutting down Indaleko GUI...")
    except Exception as e:
        print(f"Error running Streamlit: {e}")
        
        # Check if streamlit is installed
        try:
            subprocess.run(["streamlit", "--version"], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
        except:
            print("\nStreamlit does not appear to be installed. Please install it with:")
            print("\nuv pip install -e \".[gui]\"")
            
        sys.exit(1)

if __name__ == "__main__":
    main()