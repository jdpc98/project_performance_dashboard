import pandas as pd
import os
import pickle
import sys
import numpy as np
from datetime import datetime

# Define colored print functions for better debugging visibility
def print_green(message):
    """Print a debug message in green."""
    print("\033[92m" + str(message) + "\033[0m")

def print_orange(message):
    """Print a debug message in orange."""
    print("\033[38;5;208m" + str(message) + "\033[0m")

def print_red(message):
    """Print a debug message in red."""
    print("\033[91m" + str(message) + "\033[0m")

def print_cyan(message):
    """Print a debug message in cyan."""
    print("\033[96m" + str(message) + "\033[0m")

def standardize_project_no(x):
    """Convert a project number to float with 2 decimals, or strip string."""
    try:
        # Convert to float and format with 2 decimal places
        float_val = float(x)
        # Return as string with exactly 2 decimal places always (keep .00)
        formatted = f"{float_val:.2f}"
        return formatted
    except Exception:
        return str(x).strip()

def load_and_check_pickle_data():
    """Load pickle data and perform detailed checks on the Month column."""
    PICKLE_DIR = r"C:\Users\jose.pineda\Desktop\operations\pickles"
    
    # Load the raw invoices data
    try:
        raw_invoices_path = os.path.join(PICKLE_DIR, "global_raw_invoices.pkl")
        if os.path.exists(raw_invoices_path):
            with open(raw_invoices_path, 'rb') as f:
                invoices_df = pickle.load(f)
            print_green(f"Successfully loaded invoices data from {raw_invoices_path}")
            print_green(f"Invoices DataFrame shape: {invoices_df.shape}")
        else:
            print_red(f"Pickle file not found at {raw_invoices_path}")
            return
    except Exception as e:
        print_red(f"Error loading invoice data: {str(e)}")
        return
    
    # First, check the columns in the DataFrame
    print_green("\n===== COLUMNS IN INVOICES DATAFRAME =====")
    print_green(invoices_df.columns.tolist())
    
    # Check for any missing columns that we expect
    expected_cols = ['Month', 'Project No', 'Invoice Date', 'Actual']
    missing = [col for col in expected_cols if col not in invoices_df.columns]
    if missing:
        print_red(f"Missing expected columns: {missing}")
    
    # Check if Month_numeric column exists
    if 'Month_numeric' not in invoices_df.columns:
        print_red("No Month_numeric column found! Adding it now...")
        invoices_df['Month_numeric'] = pd.to_numeric(invoices_df['Month'], errors='coerce')
    
    if 'Invoice_Year' not in invoices_df.columns:
        print_red("No Invoice_Year column found! Adding it now...")
        invoices_df['Invoice_Year'] = invoices_df['Invoice Date'].dt.year
    
    # Basic stats on the Month column
    print_green("\n===== BASIC STATS FOR MONTH COLUMN =====")
    print_green(f"Month column dtype: {invoices_df['Month'].dtype}")
    print_green(f"Month column unique values: {sorted(invoices_df['Month'].unique())}")
    print_green(f"Month_numeric column unique values: {sorted(invoices_df['Month_numeric'].dropna().unique())}")
    print_green(f"Invoice_Year column unique values: {sorted(invoices_df['Invoice_Year'].dropna().unique())}")
    
    # Convert Month and Year to numeric for filtering
    invoices_df['Month_numeric'] = pd.to_numeric(invoices_df['Month'], errors='coerce')
    
    # Examine February 2025 data specifically
    print_orange("\n===== FEBRUARY 2025 DATA ANALYSIS =====")
    
    # Check how many records we have for each month in 2025
    month_counts_2025 = invoices_df[invoices_df['Invoice_Year'] == 2025]['Month_numeric'].value_counts().sort_index()
    print_orange(f"Month counts for 2025: {month_counts_2025.to_dict()}")
    
    # Look specifically at February 2025 data
    feb_2025 = invoices_df[
        (invoices_df['Month_numeric'] == 2) & 
        (invoices_df['Invoice_Year'] == 2025)
    ]
    
    print_orange(f"Found {len(feb_2025)} records for February 2025")
    
    # Show a sample of these records
    print_orange("Sample of February 2025 records:")
    if len(feb_2025) > 0:
        sample_cols = ['Month', 'Month_numeric', 'Project No', 'Type', 'Invoice Date', 'Invoice_Year', 'Actual']
        available_cols = [col for col in sample_cols if col in feb_2025.columns]
        print_cyan(feb_2025[available_cols].head(10).to_string())
    else:
        print_red("No records found for February 2025!")
    
    # Now let's check our expected project list against what we find
    print_orange("\n===== CHECKING FOR EXPECTED FEBRUARY 2025 PROJECTS =====")
    expected_projects = [
        '1705.00', '1751.09', '1751.10', '1765.04', '1765.05', '1785.00', '1787.00', '1787.01', '1787.02', 
        '1872.35', '1872.36', '1872.37', '1888.00', '1897.04', '1921.02', '1928.01', '1938.00',
        '1958.23', '1958.24', '1958.25', '1958.26', '1958.27', '1958.28', '1958.29', '1978.03',
        '1987.00', '1988.03', '1994.01', '1995.00', '7010.03', '2004.00', '2006.01', '2017.02',
        '2020.00', '2023.00', '2029.00', '2031.00', '2033.00', '2035.00', '2039.00', '2041.00',
        '2042.00', '2043.00', '2043.01', '2044.00', '7019.00', '7020.00', '1701.00'
    ]
    
    # Standardize all project numbers for comparison
    expected_projects_std = [standardize_project_no(p) for p in expected_projects]
    
    # Check each expected project
    all_project_nos = invoices_df['Project No'].astype(str).apply(standardize_project_no).unique()
    
    print_orange(f"Total unique Project Nos in the entire dataset: {len(all_project_nos)}")
    
    for proj in expected_projects_std:
        # First check if the project exists at all in the dataset
        if proj in all_project_nos:
            # Check if it exists specifically for February 2025
            proj_feb_2025 = invoices_df[
                (invoices_df['Project No'].astype(str).apply(standardize_project_no) == proj) & 
                (invoices_df['Month_numeric'] == 2) & 
                (invoices_df['Invoice_Year'] == 2025)
            ]
            if len(proj_feb_2025) > 0:
                print_green(f"✓ Project {proj} found in February 2025 data")
            else:
                print_red(f"✗ Project {proj} exists in the dataset but NOT found in February 2025 data")
                
                # Find where this project actually appears
                proj_data = invoices_df[invoices_df['Project No'].astype(str).apply(standardize_project_no) == proj]
                if not proj_data.empty:
                    print_red(f"  Instead found in: Month={proj_data['Month_numeric'].tolist()}, Year={proj_data['Invoice_Year'].tolist()}")
        else:
            print_red(f"✗ Project {proj} NOT found anywhere in the dataset!")
    
    # Now let's also check the raw Excel file
    print_orange("\n===== CHECKING RAW EXCEL FILE FOR FEBRUARY 2025 DATA =====")
    try:
        excel_path = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
        raw_df = pd.read_excel(excel_path, sheet_name='5_Invoice-2025', header=None)
        print_green(f"Successfully loaded raw Excel data from {excel_path}")
        print_green(f"Raw Excel shape: {raw_df.shape}")
        
        # We need to skip headers, usually first 4-5 rows
        data_df = raw_df.iloc[4:].copy()
        
        # Set column names based on common structure
        columns = ["Month", "Project No", "Type", "Invoice No", "Rev", "Contracted Amount", 
                  "Client", "Payment Date", "Payment", "Invoice Date", "Actual", "Percentage", 
                  "Status", "Notes", "Date Payment Received"]
        
        # Adjust columns based on actual column count
        data_df.columns = columns[:len(data_df.columns)]
        
        # Filter for February entries
        feb_entries = data_df[data_df['Month'] == 2]
        print_orange(f"Found {len(feb_entries)} February entries in the raw Excel 2025 sheet")
        print_cyan(feb_entries[['Month', 'Project No', 'Type']].head(20).to_string())
        
        # Compare against our expected list
        excel_projects = feb_entries['Project No'].astype(str).apply(standardize_project_no).unique()
        print_green(f"Found {len(excel_projects)} unique projects for February in Excel:")
        print_green(str(sorted(excel_projects)))
        
        # Check missing projects
        missing_from_excel = [p for p in expected_projects_std if p not in excel_projects]
        if missing_from_excel:
            print_red(f"Projects in expected list but missing from Excel: {missing_from_excel}")
        
        # Check extra projects 
        extra_in_excel = [p for p in excel_projects if p not in expected_projects_std]
        if extra_in_excel:
            print_orange(f"Projects in Excel but not in expected list: {extra_in_excel}")
        
    except Exception as e:
        print_red(f"Error checking raw Excel file: {str(e)}")
    
    print_green("\n===== ANALYSIS COMPLETE =====")
    return invoices_df

if __name__ == "__main__":
    data = load_and_check_pickle_data()
    
    # Let's do one final test with data
    if data is not None:
        # Filter for February 2025
        feb_2025_data = data[
            (data['Month_numeric'] == 2) & 
            (data['Invoice_Year'] == 2025)
        ]
        
        print_cyan("\n===== FINAL FEBRUARY 2025 PROJECT COUNT =====")
        print_cyan(f"Found {len(feb_2025_data)} total records")
        print_cyan(f"Found {feb_2025_data['Project No'].nunique()} unique projects")
        print_cyan(f"Project numbers: {sorted(feb_2025_data['Project No'].unique())}")