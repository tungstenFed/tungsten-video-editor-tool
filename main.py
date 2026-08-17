#!/usr/bin/env python3
"""
Tungsten Video Editor - Main Entry Point
"""
import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Add tools to path
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

# Import after path setup
from src.app import main

if __name__ == "__main__":
    main()