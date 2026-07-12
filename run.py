#!/usr/bin/env python3
"""
PyInstaller entry point.
Uses absolute imports so the packaged binary can locate the app_usage_cli package correctly.
"""
from app_usage_cli.cli import main

if __name__ == "__main__":
    main()
