"""
Excel Data Diagnostic Script

This script analyzes the structure of the Project Log Excel file
and helps identify why only 25 projects are showing for February 2025.
"""

import pandas as pd
import os
from data_processing import print_green, print_red, print_cyan, print_orange, standardize_project_no

def diagnose_excel_file(file_path):
    """Analyze the structure and content of an Excel file"""
    print_green(f"Analyzing Excel file: {file_path}")
    
    # Check if the file exists
    if not os.path.exists(file_path):
        print_red(f"File not found: {file_path}")
        return
    
    # Get sheet names
    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        print_green(f"Found {len(sheet_names)} sheets in the Excel file: {sheet_names}")
        
        # Analyze each sheet
        for sheet_name in sheet_names:
            print_cyan(f"\nAnalyzing sheet: {sheet_name}")
            
            # Try different header rows to find the correct structure
            for header_row in range(0, 10):
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
                    print_green(f"With header={header_row}: Found {df.shape[0]} rows and {df.shape[1]} columns")
                    print_green(f"Column names: {df.columns.tolist()}")
                    
                    # Check for month-related columns
                    month_cols = [col for col in df.columns if 'month' in str(col).lower()]
                    if month_cols:
                        print_green(f"Found month-related columns: {month_cols}")
                        
                        for month_col in month_cols:
                            # Count values in the month column
                            value_counts = df[month_col].value_counts().sort_index()
                            print_green(f"Distribution of values in '{month_col}': {value_counts.to_dict()}")
                            
                            # Check specific month values
                            month_2_count = len(df[df[month_col] == 2])
                            print_green(f"Number of rows where {month_col} = 2: {month_2_count}")
                            
                            if month_2_count > 0:
                                # Print some sample projects for month 2
                                sample = df[df[month_col] == 2].head(5)
                                print_green("Sample projects for month 2:")
                                for _, row in sample.iterrows():
                                    if 'Project No' in df.columns:
                                        print_green(f"Project No: {row['Project No']}")
                                    elif 'project no' in df.columns:
                                        print_green(f"Project No: {row['project no']}")
                                    else:
                                        print_red("Could not find 'Project No' column")
                                        
                                # Count unique projects for month 2
                                if 'Project No' in df.columns:
                                    unique_projects = df[df[month_col] == 2]['Project No'].nunique()
                                    print_green(f"Number of unique projects for month 2: {unique_projects}")
                                elif 'project no' in df.columns:
                                    unique_projects = df[df[month_col] == 2]['project no'].nunique()
                                    print_green(f"Number of unique projects for month 2: {unique_projects}")
                    
                    # Break after finding the likely header structure
                    if len(df.columns) > 5 and any('project' in str(col).lower() for col in df.columns):
                        print_cyan(f"Most likely header row for {sheet_name}: {header_row}")
                        break
                        
                except Exception as e:
                    print_red(f"Error reading sheet {sheet_name} with header={header_row}: {str(e)}")
    
    except Exception as e:
        print_red(f"Error analyzing Excel file: {str(e)}")

if __name__ == "__main__":
    # Path to your Project Log Excel file
    excel_file_path = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    
    # Run the diagnostic
    diagnose_excel_file(excel_file_path)
    
    print_green("\nDiagnosis complete! Check the output above to understand your Excel structure.")
    print_green("Look for the section that shows 'Number of rows where month = 2' to see why you're getting 25 projects.")