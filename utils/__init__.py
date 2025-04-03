"""
Utility modules for KHyTool.
This package contains utility functions and classes used throughout the application.
"""

# Run thumbnail cleanup check at startup
try:
    from utils.helpers import check_and_clean_thumbnails
    # Schedule thumbnail cleanup check
    check_and_clean_thumbnails()
except ImportError:
    # This will happen during early imports, so we can ignore it
    pass
