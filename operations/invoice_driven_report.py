"""
Invoice-Driven Report Generator

This script takes a different approach to generating reports by prioritizing the invoice sheets.
It loads all projects from the three invoice sheets and then maps other data to these projects.
"""

import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
from data_processing import (
    standardize_project_no, print_green, print_red, print_cyan, print_orange,
    load_rates_from_single_sheet, load_timesheet_folder, calculate_day_cost
)
import config

warnings.simplefilter("ignore")  # Suppress warnings

def load_invoice_sheets(file_path):
    """
    Loads the three invoice sheets from the project log Excel file.
    Focuses on preserving all projects from these sheets.
    """
    print_green("Loading invoice sheets directly...")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        print_red(f"File not found: {file_path}")
        return None, None, None
    
    # Load the three invoice sheets
    try:
        # First, get the available sheet names
        available_sheets = pd.ExcelFile(file_path).sheet_names
        print_green(f"Available sheets in the Excel file: {available_sheets}")
        
        # Try to find the correct sheet names
        df_2023 = None
        df_2024 = None
        df_2025 = None
        
        # Try to load 2023 data
        if '5_Invoice-2023' in available_sheets:
            df_2023 = pd.read_excel(file_path, sheet_name='5_Invoice-2023', header=4)
        
        # Try to load 2024 data
        if '5_Invoice-2024' in available_sheets:
            df_2024 = pd.read_excel(file_path, sheet_name='5_Invoice-2024', header=4)
        
        # Try to load 2025 data - check for various possible sheet names
        if '5_Invoice-2025' in available_sheets:
            df_2025 = pd.read_excel(file_path, sheet_name='5_Invoice-2025', header=4)
        elif '4_Contracted Projects' in available_sheets:
            # This appears to be the sheet containing the 2025 data
            df_2025 = pd.read_excel(file_path, sheet_name='4_Contracted Projects', header=4)
            print_green("Using '4_Contracted Projects' sheet for 2025 data")
        
        # Add year columns to identify source
        if df_2023 is not None:
            df_2023['Invoice_Year'] = 2023
        if df_2024 is not None:
            df_2024['Invoice_Year'] = 2024
        if df_2025 is not None:
            df_2025['Invoice_Year'] = 2025
        
        # Log the results
        shape_2023 = df_2023.shape if df_2023 is not None else (0, 0)
        shape_2024 = df_2024.shape if df_2024 is not None else (0, 0)
        shape_2025 = df_2025.shape if df_2025 is not None else (0, 0)
        
        print_green(f"Loaded invoice sheets: 2023 ({shape_2023}), 2024 ({shape_2024}), 2025 ({shape_2025})")
        
        return df_2023, df_2024, df_2025
    
    except Exception as e:
        print_red(f"Error loading invoice sheets: {str(e)}")
        return None, None, None

def clean_invoice_data(df, year):
    """
    Clean and standardize an invoice dataframe
    """
    if df is None:
        return pd.DataFrame()
    
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Rename columns to ensure consistent naming across years
    if 'Month' not in df.columns and 'month' in df.columns:
        df.rename(columns={'month': 'Month'}, inplace=True)
        
    if 'Project No' not in df.columns and 'project no' in df.columns:
        df.rename(columns={'project no': 'Project No'}, inplace=True)
    
    if 'Actual' not in df.columns:
        # Try to find the actual column based on common naming patterns
        actual_columns = [col for col in df.columns if 'actual' in str(col).lower()]
        if actual_columns:
            df.rename(columns={actual_columns[0]: 'Actual'}, inplace=True)
    
    # Remove rows where Project No or Month is missing
    df = df[df['Project No'].notna() & df['Month'].notna()]
    
    # Remove TOTAL rows
    df = df[~df['Project No'].astype(str).str.upper().str.contains('TOTAL')]
    
    # Convert Month to numeric
    df['Month_numeric'] = pd.to_numeric(df['Month'], errors='coerce')
    
    # Fix Invoice Date
    if 'Invoice Date' in df.columns:
        df['Invoice Date'] = pd.to_datetime(df['Invoice Date'], errors='coerce')
    
    # Standardize Project No
    df['Project No'] = df['Project No'].astype(str).str.strip().apply(standardize_project_no)
    
    # Clean Actual column (remove $ and commas)
    if 'Actual' in df.columns:
        df['Actual'] = (
            df['Actual'].astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        df['Actual'] = pd.to_numeric(df['Actual'], errors='coerce')
    
    print_green(f"Cleaned {year} invoice data: {df.shape} rows, {df['Project No'].nunique()} unique projects")
    return df

def build_complete_project_list(df_2023, df_2024, df_2025):
    """
    Build a complete list of all projects from all three invoice sheets
    """
    # Combine all projects from all invoice sheets
    all_projects = set()
    
    for df, year in [(df_2023, 2023), (df_2024, 2024), (df_2025, 2025)]:
        if df is not None and not df.empty:
            projects = set(df['Project No'].dropna().unique())
            print_green(f"Found {len(projects)} unique projects in {year} invoice sheet")
            all_projects.update(projects)
    
    print_green(f"Total unique projects across all invoice sheets: {len(all_projects)}")
    return sorted(list(all_projects))

def get_monthly_data_by_project(df_invoices, month, year):
    """
    Get all invoice data for a specific month and year
    """
    # Filter for the specified month and year
    filtered = df_invoices[
        (df_invoices['Month_numeric'] == month) & 
        (df_invoices['Invoice_Year'] == year)
    ]
    
    # Group by Project No and sum the Actual column
    if 'Actual' in filtered.columns:
        result = filtered.groupby('Project No', as_index=False)['Actual'].sum()
        print_green(f"Found {len(result)} projects with invoices for month {month}, year {year}")
        return result
    else:
        print_red(f"'Actual' column not found in filtered data for month {month}, year {year}")
        return pd.DataFrame(columns=['Project No', 'Actual'])

def load_cost_data(timesheet_folder, rates_file_path):
    """
    Load timesheet and rates data for cost calculations
    """
    # Load rates data
    df_trm_vals, df_actual_rates, loaded_c, loaded_rates = load_rates_from_single_sheet(rates_file_path)
    
    # Replace * with unique IDs in rates
    mask_star = (df_actual_rates['ID#'] == '*')
    df_star = df_actual_rates.loc[mask_star].copy().reset_index(drop=True)
    start_id = 1001
    df_star['ID#'] = range(start_id, start_id + len(df_star))
    df_actual_rates.loc[mask_star, 'ID#'] = df_star['ID#']
    df_actual_rates['ID#'] = pd.to_numeric(df_actual_rates['ID#'], errors='coerce').fillna(0).astype(int)
    
    # Build mapping from Employee -> ID#
    mapping = df_actual_rates.set_index('Employee')['ID#'].to_dict()
    
    # Load timesheet data
    df_timesheet, update_date = load_timesheet_folder(timesheet_folder)
    
    # Process timesheet data
    df_timesheet['number'] = pd.to_numeric(df_timesheet['number'], errors='coerce').fillna(0).astype(int)
    
    # Make a full_name column
    df_timesheet['fname'] = df_timesheet['fname'].astype(str).str.replace('Ã±', 'n', regex=False)
    df_timesheet['lname'] = df_timesheet['lname'].astype(str).str.replace('Ã±', 'n', regex=False)
    df_timesheet['full_name'] = df_timesheet['fname'].str.strip() + " " + df_timesheet['lname'].str.strip()
    
    # For rows where number=0, map from full_name -> ID#
    mask_zero = (df_timesheet['number'] == 0)
    df_timesheet.loc[mask_zero, 'number'] = df_timesheet.loc[mask_zero, 'full_name'].map(mapping).fillna(0).astype(int)
    
    # Build 'correct_number' from 'number'
    df_timesheet['correct_number'] = df_timesheet['number']
    
    # Merge timesheet + rates
    merged_df = pd.merge(
        df_actual_rates, df_timesheet,
        left_on='ID#', right_on='correct_number',
        how='inner'
    )
    
    # Calculate day cost
    merged_df = calculate_day_cost(merged_df)
    
    print_green(f"Loaded and processed cost data: {merged_df.shape} rows")
    return merged_df

def extract_project_costs(merged_df, target_month, target_year):
    """
    Extract project costs for a specific month and year
    """
    # Convert local_date to datetime if it's not already
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')
    
    # Filter for the target month and year
    filtered = merged_df[
        (merged_df['local_date'].dt.month == target_month) &
        (merged_df['local_date'].dt.year == target_year)
    ]
    
    # Extract the standard project number (first 7 chars)
    filtered['Project_No_Standard'] = filtered['jobcode_2'].astype(str).str[:7].str.strip()
    
    # Apply standardize_project_no to ensure consistent formatting
    filtered['Project_No_Standard'] = filtered['Project_No_Standard'].apply(standardize_project_no)
    
    # Group by the standardized project number and sum day_cost
    project_costs = filtered.groupby('Project_No_Standard', as_index=False)['day_cost'].sum()
    project_costs.rename(columns={'Project_No_Standard': 'Project No', 'day_cost': 'Cost'}, inplace=True)
    
    print_green(f"Found costs for {len(project_costs)} projects in month {target_month}, year {target_year}")
    return project_costs

def calculate_er_values(invoices_df, costs_df):
    """
    Calculate ER values (Efficiency Ratio) for each project
    """
    if invoices_df.empty or costs_df.empty:
        print_red("Cannot calculate ER values - missing invoice or cost data")
        return pd.DataFrame(columns=['Project No', 'Actual', 'Cost', 'ER'])
    
    # Merge invoice and cost data
    merged = pd.merge(invoices_df, costs_df, on='Project No', how='outer')
    
    # Fill NaN values with 0
    merged['Actual'] = merged['Actual'].fillna(0)
    merged['Cost'] = merged['Cost'].fillna(0)
    
    # Calculate ER (Efficiency Ratio)
    merged['ER'] = merged.apply(
        lambda row: row['Actual'] / row['Cost'] if row['Cost'] > 0 else None, 
        axis=1
    )
    
    print_green(f"Calculated ER values for {len(merged)} projects")
    return merged

def generate_monthly_report(month=None, year=None):
    """
    Generate a monthly report for the specified month and year.
    If month/year are not provided, use the current month and year.
    """
    # Set default month and year if not provided
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year
    
    print_green("=" * 20 + " GENERATING REPORT " + "=" * 20)
    print_green(f"Generating report for {datetime(year, month, 1).strftime('%B %Y')}")
    print_green(f"Selected month: {month}, year: {year}")
    
    # Path to the Project Log Excel file
    project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
    
    # If the network path isn't accessible, try the local copy
    if not os.path.exists(project_log_path):
        print_orange("Network path not accessible, trying local copy...")
        project_log_path = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    
    # 1. Load all three invoice sheets
    df_2023_raw, df_2024_raw, df_2025_raw = load_invoice_sheets(project_log_path)
    
    # 2. Clean each invoice sheet
    df_2023 = clean_invoice_data(df_2023_raw, 2023)
    df_2024 = clean_invoice_data(df_2024_raw, 2024)
    df_2025 = clean_invoice_data(df_2025_raw, 2025)
    
    # 3. Combine all invoice data
    all_invoices = pd.concat([df_2023, df_2024, df_2025], ignore_index=True)
    print_green(f"Raw invoices shape: {all_invoices.shape}")
    print_green(f"Raw invoices columns: {all_invoices.columns.tolist()}")
    
    # Display distribution statistics
    month_counts = all_invoices['Month_numeric'].value_counts().sort_index().to_dict()
    year_counts = all_invoices['Invoice_Year'].value_counts().sort_index().to_dict()
    print_green(f"Month distribution: {month_counts}")
    print_green(f"Year distribution: {year_counts}")
    
    # 4. Filter invoices for the target month and year
    monthly_invoices = all_invoices[
        (all_invoices['Month_numeric'] == month) & 
        (all_invoices['Invoice_Year'] == year)
    ]
    
    print_green(f"Found {len(monthly_invoices)} invoices for month {month} and year {year}")
    
    # Show a sample of the filtered invoices
    if not monthly_invoices.empty:
        print_green("Sample of filtered invoices:")
        print_green(monthly_invoices[['Project No', 'Month_numeric', 'Invoice_Year', 'Actual']].head())
    
    # 5. Group by Project No and sum Actual values
    project_invoices = monthly_invoices.groupby('Project No', as_index=False)['Actual'].sum()
    
    print_green(f"Number of unique projects with invoices this month: {len(project_invoices)}")
    print_green(f"Project numbers: {project_invoices['Project No'].tolist()[:10]}...")
    
    # 6. Load cost data
    rates_file_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\RATES.xlsx"
    if not os.path.exists(rates_file_path):
        rates_file_path = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    
    timesheet_folder = r"C:\Users\jose.pineda\Desktop\operations\tsheets"
    merged_df = load_cost_data(timesheet_folder, rates_file_path)
    
    # 7. Extract project costs for the target month and year
    project_costs = extract_project_costs(merged_df, month, year)
    
    # 8. Calculate ER values
    report_df = calculate_er_values(project_invoices, project_costs)
    
    # 9. Prepare the final report
    final_report = report_df.sort_values(by='Project No')
    
    # Count projects with valid ER values
    valid_er_count = final_report['ER'].notna().sum()
    print_green(f"Final report contains {len(final_report)} projects, with {valid_er_count} having valid ER values")
    
    print_green("=" * 20 + " END OF REPORT GENERATION " + "=" * 20)
    
    return final_report

if __name__ == "__main__":
    # Generate a report for the current month and year
    # You can specify a different month and year if needed:
    # report = generate_monthly_report(month=2, year=2025)
    report = generate_monthly_report(month=2, year=2025)
    
    # Save the report to Excel
    output_dir = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"invoice_driven_report_{today}.xlsx")
    
    with pd.ExcelWriter(output_file) as writer:
        report.to_excel(writer, sheet_name="Monthly Report", index=False)
    
    print_green(f"Report saved to {output_file}")