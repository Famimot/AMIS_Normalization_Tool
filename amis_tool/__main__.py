"""
Main entry point for AMIS Normalization Tool package.
This file allows running the tool via: python -m amis_tool
"""

import sys
import os

# Add the parent directory to Python path so we can import run_amis
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from run_amis import main
except ImportError:
    print("Error: Cannot find run_amis.py in the project root directory.")
    print("Make sure run_amis.py exists in the same directory as amis_tool/ folder.")
    sys.exit(1)

if __name__ == "__main__":
    main()