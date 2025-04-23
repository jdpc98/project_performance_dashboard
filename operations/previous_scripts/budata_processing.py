#backup copy as of 3/6/2025 5:17pm



# data_processing.py

import os
import re
import base64
import numpy as np
import pandas as pd
import warnings
from datetime import datetime

warnings.simplefilter("ignore")  # Suppress warnings if desired

# ==============================
# HELPER & UTILITY FUNCTIONS
# ==============================
def print_green(message):
    """Print a debug message in green (for console debugging)."""
    print("\033[92m" + str(message) + "\033[0m")

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

def extract_project_no(jobcode_str):
    """Return the first 7 characters from jobcode_str (Project No)."""
    return str(jobcode_str)[:7].strip()

# ==============================
# RATES SHEET INGESTION FUNCTIONS
# ==============================
def trm_ingestion(rates_df):
    print_green("Inside trm_ingestion")
    df_rates = rates_df.copy()
    trm_values = df_rates.iloc[0, 4:29].values
    bogota_vals = df_rates.iloc[1, 4:29].values
    houston_vals = df_rates.iloc[2, 4:29].values

    df_dates = df_rates.iloc[4:6, 4:29].copy()
    df_dates.ffill(axis=1, inplace=True)
    df_dates.loc['concat'] = df_dates.loc[4].astype(str) + df_dates.loc[5].astype(str)
    dates_vals = df_dates.loc['concat'].values

    df_trm = pd.DataFrame({
        "TRM": trm_values,
        "Bogota_val": bogota_vals,
        "Houston_val": houston_vals,
        "Dates": dates_vals
    })
    print_green("TRM Ingestion (df_trm_vals) head:")
    print_green(str(df_trm.head()))
    return df_trm

def rates_ingestion(rates_df):
    print_green("Inside rates_ingestion")
    df_rates = rates_df.copy()
    # Drop header rows
    df_rates = df_rates.drop(df_rates.index[0:7])
    # Drop columns beyond index 28 (i.e., 29 total)
    df_rates = df_rates.drop(df_rates.columns[29:], axis=1)

    df_dates = rates_df.iloc[4:6, 4:29].copy()
    df_dates.ffill(axis=1, inplace=True)
    df_dates.loc['concat_cont'] = df_dates.loc[4].astype(str) + df_dates.loc[5].astype(str)

    new_header = np.concatenate(
        (["ID#", "Employee", "2022Whole_Year", "2023Whole_Year"], df_dates.loc['concat_cont'].values)
    )
    print_green("New header (length {}):".format(len(new_header)))
    print_green(str(new_header))
    df_rates.columns = new_header
    print_green("Actual Rates Ingestion (df_actual_rates) head:")
    print_green(str(df_rates.head()))
    return df_rates

def load_coef(rates_df):
    coef = rates_df.iloc[0, 32]
    print_green("Loaded coefficient (loaded_c): " + str(coef))
    return coef

def loaded_rates_ingestion(rates_df):
    print_green("Inside loaded_rates_ingestion")
    lr_df = rates_df.copy()
    lr_df = lr_df.drop(lr_df.index[0:4])
    lr_df = lr_df.drop(lr_df.columns[2:29], axis=1)
    lr_df.index = range(len(lr_df))
    lr_df = lr_df.drop(lr_df.index[2])
    lr_df.index = range(len(lr_df))
    lr_df = lr_df.drop(lr_df.index[0])
    lr_df.index = range(len(lr_df))
    lr_df.columns = ["ID#", "Employee", "RAW_USD", "LOADED_USD", "LOADED_COP", "RAW_COP"]
    lr_df = lr_df.drop(lr_df.index[0])
    lr_df.index = range(len(lr_df))
    print_green("Loaded Rates Ingestion (loaded_rates) head:")
    print_green(str(lr_df.head()))
    return lr_df

def load_rates_from_single_sheet(file_path):
    print_green("Inside load_rates_from_single_sheet")
    df_rates = pd.read_excel(file_path, sheet_name='Rates', header=None)
    print_green("Head of full Rates sheet:")
    print_green(str(df_rates.head(10)))

    df_trm_vals = trm_ingestion(df_rates)
    df_actual_rates = rates_ingestion(df_rates)
    loaded_c = load_coef(df_rates)
    loaded_rates = loaded_rates_ingestion(df_rates)

    print_green("TRM Values (df_trm_vals) shape: " + str(df_trm_vals.shape))
    print_green("Actual Rates (df_actual_rates) shape: " + str(df_actual_rates.shape))
    print_green("Loaded Rates (loaded_rates) shape: " + str(loaded_rates.shape))
    return df_trm_vals, df_actual_rates, loaded_c, loaded_rates

# ==============================
# CALCULATION FUNCTIONS
# ==============================
def calculate_day_cost(merged_df):
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')

    def row_day_cost(row):
        dt = row['local_date']
        if pd.isnull(dt):
            return 0
        year = dt.year
        if dt.month == 7:
            # Special case for July
            ym = f"{year}JUL (1-15)" if dt.day <= 15 else f"{year}JUL (15-31)"
        else:
            ym = dt.strftime('%Y') + dt.strftime('%b').upper()
        rate = row[ym] if ym in merged_df.columns else 0
        return rate * row['hours']

    merged_df['day_cost'] = merged_df.apply(row_day_cost, axis=1)
    print_green("After calculate_day_cost, head of merged_df:")
    print_green(str(merged_df[['local_date', 'day_cost']].head()))
    return merged_df

def assign_total_hours(merged_df):
    merged_df['total_hours_24'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2024)
    merged_df['total_hours_25'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2025)
    print_green("After assign_total_hours, head of merged_df:")
    print_green(str(merged_df[['total_hours_24', 'total_hours_25']].head()))
    return merged_df

# ==============================
# PROJECTS FILE & BACKUP
# ==============================
def load_third_file_dynamic(third_file):
    print_green("Inside load_third_file_dynamic")
    df_raw = pd.read_excel(third_file, sheet_name='4_Contracted Projects', header=None, engine='openpyxl')
    print_green("Shape of raw projects sheet: " + str(df_raw.shape))

    nrows = len(df_raw)
    end_row = None
    for i in range(630, nrows - 1):
        if pd.isna(df_raw.iloc[i, 1]) and pd.isna(df_raw.iloc[i+1, 1]):
            end_row = i
            break
    if end_row is None:
        end_row = nrows

    df_trunc = df_raw.iloc[:end_row].copy()
    print_green("Shape after truncation: " + str(df_trunc.shape))

    header = [str(col).strip() for col in df_trunc.iloc[0].tolist()]
    print_green("Extracted header: " + str(header))

    df_data = df_trunc.iloc[1:].copy()
    # Drop any row that is identical to the header
    df_data = df_data[~df_data.apply(lambda row: list(row.astype(str).str.strip()) == header, axis=1)]
    df_data.columns = header
    df_data.columns = [col.strip() for col in df_data.columns]

    if "Project No" not in df_data.columns:
        first_col = df_data.columns[0]
        df_data.rename(columns={first_col: "Project No"}, inplace=True)

    df_data["Project No"] = df_data["Project No"].astype(str).str.strip().apply(standardize_project_no)
    print_green("Head of loaded projects data:")
    print_green(str(df_data.head()))
    return df_data.reset_index(drop=True)

# ==============================
# MAIN PIPELINE
# ==============================

def print_orange(message):
    # ANSI escape sequence for an orange-like color (256‑color mode – color 208)
    print("\033[38;5;208m" + str(message) + "\033[0m")
def main():
    """
    Loads the data from the various sources, merges and calculates the final
    DataFrame, and returns it. Also exports the consolidated Excel file and the updated project log.
    """
    # 1) Load Rates data
    rates_file_path = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    df_trm_vals, df_actual_rates, loaded_c, loaded_rates = load_rates_from_single_sheet(rates_file_path)
    
    # 2) Load timesheet CSV
    #second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    #ill load a csv project report only from 2025 to check all data first. this, because tsheets doesnt allow me to download the reports
    #i might have to download separate months or quarters of each year and craete a local db that gets updated
    
    second_file=r"C:\Users\jose.pineda\Downloads\timesheet_report_2025-01-01_thru_2025-03-06.csv"
    
    df_new = pd.read_csv(second_file, header=0, index_col=0)

    print_green("Head of timesheet CSV (df_new):")
    print_green(str(df_new.head()))
    #org names
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    #replace ñ for n
    df_new['fname']     = df_new['fname'].astype(str).str.replace('Ã±', 'n', regex=False)
    df_new['lname']     = df_new['lname'].astype(str).str.replace('Ã±', 'n', regex=False)
    df_new['full_name'] = df_new['full_name'].astype(str).str.replace('Ã±', 'n', regex=False)

    #consider next line in case theres more ñ's in the file 

    # 3) Merge timesheet with rates (map Employee -> ID#)
    mapping = df_actual_rates.set_index('Employee')['ID#'].to_dict()
    print_green("Mapping from rates (Employee -> ID#):")
    print_green(str(mapping))
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    
    #  Assign mapped to correct_number
    df_new.loc[mask, 'correct_number'] = mapped
    mapped_filled = mapped.fillna(0)
    df_new.loc[mask, 'correct_number'] = mapped_filled.astype(np.int64)
    
    # Fill any NaN with 0
    
    df_new['correct_number'] = df_new['correct_number'].fillna(0).astype(np.int64)
    #df_new['correct_number'] = df_new['correct_number'].astype(np.int64)
      
    #df_new.loc[mask, 'correct_number'] = mapped.astype(np.int64)
    print_green("Head of df_new after mapping:")
    print_green(str(df_new.head()))
    
    merged_df = pd.merge(df_actual_rates, df_new, left_on='ID#', right_on='correct_number', how='inner')
    print_green("Head of merged_df after merging rates and timesheet:")
    print_green(str(merged_df.head()))
    print_green("Columns in merged_df (after merge):")
    print_green(str(merged_df.columns.tolist()))
    
    #Upload real file 
    project_log_path=r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
    
    # 4) Load Projects data
    #third_file = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    #df_projects = load_third_file_dynamic(third_file)
    df_projects=load_third_file_dynamic(project_log_path)
    # 5) Load Invoices data
    #invoice_file = r"C:\Users\jose.pineda\Desktop\operations\invoice_dummy_file.xlsx"
    
    #invoice_file=r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
    
    df_invoices=pd.read_excel(project_log_path, sheet_name='5_Invoice-2025', header=0)
    print_green("Head of df_invoices_test:")
    print_green(str(df_invoices.head()))
    #i check the Payment Date column data type 
    # 1. Convert the Payment Date column to datetime
    df_invoices['Payment Date'] = pd.to_datetime(df_invoices['Payment Date'], errors='coerce')
    # 2. Filter out any rows with an Payment Date that is greater than today's date
    today = pd.to_datetime('today').normalize()
    df_invoices = df_invoices[df_invoices['Payment Date'] <= today]
    
    print_green("Data type of Payment Date column: " + str(df_invoices['Payment Date'].dtype))
    
    
    
    
    #df_invoices = pd.read_excel(invoice_file, sheet_name='Sheet1')
    #df_invoices['Project no'] = df_invoices['Project no'].astype(str).str.strip().apply(standardize_project_no)
    #df_invoices.rename(columns={'date': 'Payment Date'}, inplace=True)
    
    #i get the invoice payment from col. 'Actual'
    df_invoices_sum = df_invoices.groupby('Project No', as_index=False)['Actual'].sum()
    
    print_orange('Head of df_invoices_sum:')
    print(df_invoices_sum.head())    
    
    df_invoices_sum.rename(columns={'project no': 'Project No', 'Actual': 'TotalProjectInvoice'}, inplace=True)
    #convert project nos to string to match in merge function with other dfs
    df_invoices_sum['Project No'] = (
    df_invoices_sum['Project No']
    .astype(str)
    .str.strip()
    .apply(standardize_project_no)
)

    
    
    df_invoices_sum['TotalProjectInvoice'] = pd.to_numeric(df_invoices_sum['TotalProjectInvoice'], errors='coerce')
    global_invoices = df_invoices_sum.copy()
    print_green("Head of df_invoices_sum:")
    print_green(str(global_invoices.head()))

    # 6) Calculate day cost and assign total hours
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)
    
    # Define output directory (ensure it exists)
    output_directory = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # 7) Export consolidated output file with all key DataFrames as sheets
    consolidated_file = os.path.join(output_directory, "consolidated_output_data.xlsx")
    with pd.ExcelWriter(consolidated_file, engine="xlsxwriter") as writer:
        merged_df.to_excel(writer, sheet_name="Merged", index=False)
        df_projects.to_excel(writer, sheet_name="Projects", index=False)
        global_invoices.to_excel(writer, sheet_name="Invoices", index=False)
        # Optionally, add jobcode-specific sheets if needed:
        for jc in merged_df['jobcode_2'].unique():
            safe_jc = sanitize_filename(jc)[:31]
            merged_df[merged_df['jobcode_2'] == jc].to_excel(writer, sheet_name=safe_jc, index=False)
    print_green("Consolidated output exported to " + consolidated_file)
    
    # 8) Export updated project log file separately (without altering the original imported file)
    updated_project_log_file = os.path.join(output_directory, "2025_updated_project_log.xlsx")
    df_projects.to_excel(updated_project_log_file, index=False)
    print_green("Updated project log exported to " + updated_project_log_file)
    last_update = pd.to_datetime('today').strftime('%Y-%m-%d')
    # Return the main DataFrames so the Dash app can use them
    return merged_df, df_projects, global_invoices, last_update

last_update = pd.to_datetime('today').strftime('%Y-%m-%d')

if __name__ == "__main__":
    main()
