"""
BioPareto Analyzer - Configuration
Global configuration settings
"""

import os

# Application settings
APP_TITLE = "BioPareto Analyzer"
APP_VERSION = "2.0"
DEVELOPER = "Hugo Marciel - USACH 2025"

# Server settings
DEFAULT_PORT = int(os.environ.get("PORT", 80))
HOST = "0.0.0.0"
DEBUG = True

# API endpoints
GPROFILER_BASE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
GPROFILER_ORGANISMS_URL = "https://biit.cs.ut.ee/gprofiler/api/util/organisms_list"

# Color palette for plots
COLORS_PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
]

# Consolidated front color
CONSOLIDATED_FRONT_COLOR = '#000080'  # Navy blue

# Logging configuration
LOG_LEVEL = "INFO"
