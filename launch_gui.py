#!/usr/bin/env python3
"""
Hedwig GUI Launcher

Standalone launcher for the Hedwig desktop application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Launch the Hedwig GUI application."""
    try:
        # Import and run GUI
        from hedwig.gui import HedwigGUI
        
        print("🦉 Starting Hedwig AI Desktop Application...")
        app = HedwigGUI()
        app.run()
        
    except ImportError as e:
        print(f"❌ Failed to import GUI components: {e}")
        print("\n💡 Make sure you have installed the required dependencies:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n👋 Hedwig GUI interrupted by user")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Failed to start Hedwig GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()