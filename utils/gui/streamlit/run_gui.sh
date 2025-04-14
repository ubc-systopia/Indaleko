#!/bin/bash
# Script to launch Indaleko Streamlit GUI on Linux/macOS

# Set the Indaleko root directory (this assumes run_gui.sh is in utils/gui/streamlit)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export INDALEKO_ROOT="$(cd "$SCRIPT_DIR/../../.." >/dev/null 2>&1 && pwd)"

echo "Setting INDALEKO_ROOT to $INDALEKO_ROOT"

# Check if we have an active virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "No active virtual environment detected. Activating..."
    
    # Try to find and activate a virtual environment
    if [ -f "$INDALEKO_ROOT/.venv-linux-python3.13/bin/activate" ]; then
        echo "Found .venv-linux-python3.13, activating..."
        source "$INDALEKO_ROOT/.venv-linux-python3.13/bin/activate"
    elif [ -f "$INDALEKO_ROOT/.venv-macos-python3.12/bin/activate" ]; then
        echo "Found .venv-macos-python3.12, activating..."
        source "$INDALEKO_ROOT/.venv-macos-python3.12/bin/activate"
    elif [ -f "$INDALEKO_ROOT/.venv/bin/activate" ]; then
        echo "Found .venv, activating..."
        source "$INDALEKO_ROOT/.venv/bin/activate"
    else
        echo "No virtual environment found at expected locations."
        echo "Please create and activate a virtual environment and install dependencies:"
        echo "  uv venv"
        echo "  source .venv/bin/activate"
        echo "  uv pip install -e ."
        exit 1
    fi
else
    echo "Using active virtual environment: $VIRTUAL_ENV"
fi

# Check if streamlit is installed
if ! pip show streamlit > /dev/null 2>&1; then
    echo "Streamlit is not installed. Installing required packages..."
    pip install streamlit plotly pydeck pillow
fi

# Launch the Streamlit app
echo "Launching Indaleko GUI..."
cd "$INDALEKO_ROOT/utils/gui/streamlit"
streamlit run app.py
