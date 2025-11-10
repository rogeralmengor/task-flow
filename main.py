#!/usr/bin/env python3
"""
Agresso Time Tracker - Main Entry Point
A lazygit-style TUI for tracking time and managing Agresso entries
"""

from tui import TimeTrackingApp

def main():
    """Launch the Time Tracking TUI"""
    app = TimeTrackingApp()
    app.run()

if __name__ == "__main__":
    main()
