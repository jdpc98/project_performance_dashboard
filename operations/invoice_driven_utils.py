"""
Invoice-Driven Reporting Utilities

This module provides functions for invoice-driven project reporting.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
from data_processing import (
    standardize_project_no, print_green, print_red, print_cyan, print_orange,
    load_rates_from_single_sheet, load_timesheet_folder, calculate_day_cost
)

warnings.simplefilter("ignore")  # Suppress warnings

def load_invoice_sheets(file_path):
    """
    Load invoice data from the project log Excel file.
    """
    print_green("Loading invoice sheets...")
    
    try:
        # Load data from the Excel file
        sheets = pd.ExcelFile(file_path).sheet_names
        print_green(f"Available sheets: {sheets}")
        
        # Try to find the sheet with invoice data for 2025
        target_sheet = '4_Contracted Projects'  # This is likely your main data sheet
        
        if target_sheet in sheets:
            print_green(f"Loading data from '{target_sheet}' sheet")
            df = pd.read_excel(file_path, sheet_name=target_sheet, header=4)
            print_green(f"Loaded data: {df.shape} rows")
            return df
        else:
            print_red(f"Could not find '{target_sheet}' sheet")
            return None
            
    except Exception as e:
        print_red(f"Error loading data: {str(e)}")
        return None

def generate_monthly_report(month=None, year=None):
    """
    Generate a monthly report for the specified month and year.
    """
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    print_green("=" * 20 + f" GENERATING REPORT FOR {month}/{year} " + "=" * 20)
    
    # Path to the Project Log Excel file
    project_log_path = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    
    # Load invoice data
    df = load_invoice_sheets(project_log_path)
    
    if df is None:
        print_red("Failed to load invoice data")
        return pd.DataFrame()
    
    # Print column names to help with debugging
    print_green(f"Columns in the data: {df.columns.tolist()}")
    
    # Check if we have a month column
    month_col = None
    for col in df.columns:
        if 'month' in str(col).lower():
            month_col = col
            break
    
    if month_col:
        print_green(f"Found month column: '{month_col}'")
    else:
        print_red("Could not find a month column")
        return pd.DataFrame()
    
    # Filter for the target month
    df['Month_Numeric'] = pd.to_numeric(df[month_col], errors='coerce')
    monthly_data = df[df['Month_Numeric'] == month].copy()
    
    print_green(f"Projects for month {month}: {len(monthly_data)}")
    
    # Return the filtered data
    return monthly_data

def save_report_to_excel(report_df, output_dir=None):
    """
    Save a report DataFrame to an Excel file
    """
    if output_dir is None:
        output_dir = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"invoice_report_{today}.xlsx")
    
    with pd.ExcelWriter(output_file) as writer:
        report_df.to_excel(writer, sheet_name="Monthly Report", index=False)
    
    print_green(f"Report saved to {output_file}")
    return output_file