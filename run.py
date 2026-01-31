#!/usr/bin/env python3
"""Quick run script for Expert Analyst"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from src.cli.main import app
    app()
