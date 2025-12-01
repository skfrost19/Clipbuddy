#!/usr/bin/env python3
"""
Build script for creating SmartClip executables for Windows and Linux.

Usage:
    python build.py          # Build for current platform
    python build.py --clean  # Clean build artifacts before building
"""

import subprocess
import sys
import platform
import shutil
from pathlib import Path


def clean_build():
    """Remove previous build artifacts."""
    dirs_to_remove = ["build", "dist", "__pycache__"]
    files_to_remove = ["*.spec"]

    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Removing {dir_path}...")
            shutil.rmtree(dir_path)

    for pattern in files_to_remove:
        for file_path in Path(".").glob(pattern):
            print(f"Removing {file_path}...")
            file_path.unlink()


def build_executable():
    """Build the executable using PyInstaller."""

    system = platform.system()

    # Base PyInstaller arguments
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=SmartClip",
        "--onefile",  # Single executable file
        "--windowed",  # No console window (GUI app)
        "--clean",  # Clean cache before building
        "main.py",
    ]

    # Platform-specific options
    if system == "Windows":
        # Add Windows-specific options
        args.insert(-1, "--add-data=README.md;.")  # Windows uses semicolon
        args.insert(-1, "--add-data=icon.png;.")  # Include icon
        # Use icon for executable
        if Path("icon.ico").exists():
            args.insert(-1, "--icon=icon.ico")
        elif Path("icon.png").exists():
            args.insert(-1, "--icon=icon.png")
    else:
        # Linux/Mac specific options
        args.insert(-1, "--add-data=README.md:.")  # Linux/Mac uses colon
        args.insert(-1, "--add-data=icon.png:.")  # Include icon
        if Path("icon.png").exists():
            args.insert(-1, "--icon=icon.png")

    print(f"Building SmartClip for {system}...")
    print(f"Command: {' '.join(args)}")
    print("-" * 50)

    # Run PyInstaller
    result = subprocess.run(args, cwd=Path(__file__).parent)

    if result.returncode == 0:
        print("-" * 50)
        print("✅ Build successful!")

        # Show output location
        if system == "Windows":
            exe_path = Path("dist") / "SmartClip.exe"
        else:
            exe_path = Path("dist") / "SmartClip"

        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📦 Executable: {exe_path.absolute()}")
            print(f"📏 Size: {size_mb:.2f} MB")
    else:
        print("-" * 50)
        print("❌ Build failed!")
        sys.exit(1)


def main():
    # Change to script directory
    script_dir = Path(__file__).parent

    # Check for --clean flag
    if "--clean" in sys.argv:
        clean_build()

    # Build the executable
    build_executable()


if __name__ == "__main__":
    main()
