# funcs.py
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme, Symbol
import plotly.express as px
import pandas as pd
import numpy as np
import pickle
import os
import plotly.graph_objects as go
import traceback
import base64
###################################################


import config

from config import TABLE_STYLE, TABLE_CELL_STYLE, TABLE_CELL_CONDITIONAL, RIGHT_TABLE_RED_STYLE

# ==============================
#  UTILITY FUNCTIONS
# ==============================

def print_orange(message):
    """Print a debug message in orange."""
    print("\033[38;5;208m" + str(message) + "\033[0m")


def print_red(message):
    """Print a debug message in red."""
    print("\033[91m" + str(message) + "\033[0m")

def print_cyan(message):
    """Print a debug message in cyan."""
    print("\033[96m" + str(message) + "\033[0m")
    
def print_green(message):
    """Print a debug message in green."""
    print("\033[92m" + str(message) + "\033[0m")

def extract_project_no(jobcode_str):
    """Return the first 7 characters from jobcode_str (Project No)."""
    return str(jobcode_str)[:7].strip()


def sanitize_filename(filename):
    """Remove invalid characters for file names."""
    filename_str = str(filename)
    return re.sub(r'[<>:"/\\|?*]', '', filename_str)

def standardize_project_no(x):
    """Convert a project number to float with 2 decimals, or strip string."""
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x).strip()