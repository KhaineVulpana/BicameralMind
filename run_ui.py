"""Launch BicameralMind Testing UI"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and launch
from api.main import launch_ui

if __name__ == "__main__":
    print("=" * 60)
    print(" BicameralMind Testing UI")
    print("=" * 60)
    print()
    print("Starting server on http://localhost:8000")
    print("Browser will open automatically...")
    print()
    print("Press Ctrl+C to stop")
    print()

    try:
        launch_ui()
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down...")
        sys.exit(0)
