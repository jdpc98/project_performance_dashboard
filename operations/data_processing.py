# data_processing.py

import os
import re
import base64
import numpy as np
import pandas as pd
import warnings
from datetime import datetime
import glob
#from funcs import print_green, print_cyan, print_orange, print_red #, extract_project_no
warnings.simplefilter("ignore")  # Suppress warnings if desired

PICKLE_OUTPUT_DIR = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"

# ==============================
# HELPER & UTILITY FUNCTIONS
# ==============================


def generate_monthly_report_data(selected_date, global_projects_df, global_merged_df, global_raw_invoices, project_log_path):
    """
    Generate monthly report data based on the selected date.
    Returns report data and columns for displaying the monthly project report.
    """
    if not selected_date:
        return [], []

    # Get month and year from selected date
    date_obj = pd.to_datetime(selected_date)
    selected_month = date_obj.month
    selected_year = date_obj.year

    # Check if year is supported (2023, 2024, or 2025)
    if selected_year not in [2023, 2024, 2025]:
        print_red(f"Reports are only available for years 2023-2025. Selected year: {selected_year}")
        return [], []

    print_green(f"==================== GENERATING REPORT ====================")
    print_green(f"Generating report for {date_obj.strftime('%B %Y')}")
    print_green(f"Selected month: {selected_month}, year: {selected_year}")

    # Load data from the correct sheet based on the selected year
    sheet_name = f"5_Invoice-{selected_year}"

    try:
        # Read the selected sheet from the project log
        df_sheet = pd.read_excel(project_log_path, sheet_name=sheet_name)
        print_green(f"Successfully loaded sheet {sheet_name} from project log")
        print_green(f"Sheet columns: {df_sheet.columns.tolist()}")

        # Add a column to preserve the original order
        df_sheet['Original_Order'] = range(len(df_sheet))

        # Check if column A exists and contains month values
        if 'Month' not in df_sheet.columns and df_sheet.columns[0] != 'Month':
            # If column not named 'Month', rename the first column
            first_col_name = df_sheet.columns[0]
            df_sheet.rename(columns={first_col_name: 'Month'}, inplace=True)
            print_green(f"Renamed first column from '{first_col_name}' to 'Month'")

        # Filter rows where Month column matches the selected month
        df_month = df_sheet[pd.to_numeric(df_sheet['Month'], errors='coerce') == selected_month]
        print_green(f"Found {len(df_month)} projects for month {selected_month} in year {selected_year}")

        # Validate the DataFrame before processing
        if df_month.empty:
            print_red(f"Error: No data found for month {selected_month} in sheet {sheet_name}")
            return [], []

        # Extract project numbers from the filtered sheet
        project_column = 'Project No' if 'Project No' in df_month.columns else 'Project No.'
        if project_column not in df_month.columns:
            # Look for any column that might contain project numbers
            for col in df_month.columns:
                if 'project' in col.lower():
                    project_column = col
                    break

        if project_column not in df_month.columns:
            print_red(f"No project number column found in sheet {sheet_name}")
            print_cyan(f"Available columns: {df_month.columns.tolist()}")
            return [], []

        # Get project numbers from the sheet
        projects_in_month = df_month[project_column].dropna().unique().tolist()
        projects_in_month = [standardize_project_no(str(p)) for p in projects_in_month if str(p).strip().upper() != 'TOTAL']

        # Now build the report with these projects
        active_project_details = []

        for project_no in projects_in_month:
            # Skip 'TOTAL' rows
            if str(project_no).strip().upper() == 'TOTAL':
                continue

            # Find this project in the projects dataframe
            project_df = global_projects_df[global_projects_df['Project No'].apply(
                lambda x: standardize_project_no(str(x)) == project_no
            )]

            if project_df.empty:
                print_red(f"Project {project_no} not found in projects database!")
                continue

            project_row = project_df.iloc[0]

            # Get all invoices for this project (for ER calculation)
            project_invoices = global_raw_invoices[global_raw_invoices['Project No'].apply(
                lambda x: standardize_project_no(str(x)) == project_no
            )]

            if project_invoices.empty:
                print_red(f"No invoices found for project {project_no}")
                # Continue with default values for invoice-related fields
                monthly_invoice = 0
                total_invoice = 0
            else:
                # Convert 'Actual' column to numeric before summing
                project_invoices['Actual'] = pd.to_numeric(project_invoices['Actual'], errors='coerce')

                # Get monthly invoice amount from the sheet
                monthly_invoice_col = 'Actual' if 'Actual' in df_month.columns else None
                if monthly_invoice_col:
                    monthly_invoice = df_month.loc[
                        df_month[project_column].apply(lambda x: standardize_project_no(str(x)) == project_no),
                        monthly_invoice_col
                    ].sum()
                else:
                    monthly_invoice = 0

                # Get total invoice amount (cumulative)
                total_invoice = project_invoices['Actual'].sum()

            # Get total cost from timesheet data
            project_costs = global_merged_df[global_merged_df['Project No'] == project_no]
            total_cost = project_costs['day_cost'].sum() if not project_costs.empty else 0

            # Parse contracted amount
            contracted_amount = project_row.get('Contracted Amount', None)
            if isinstance(contracted_amount, str):
                try:
                    contracted_amount = float(contracted_amount.replace('$', '').replace(',', ''))
                except:
                    contracted_amount = None

            # Calculate ER values
            er_contract = contracted_amount / total_cost if total_cost > 0 and contracted_amount else None
            er_invoiced = total_invoice / total_cost if total_cost > 0 and total_invoice else None

            # Get Projected, Actual, and Acummulative from the sheet for this project
            project_month_data = df_month[df_month[project_column].apply(
                lambda x: standardize_project_no(str(x)) == project_no
            )]
            
            # Extract Projected, Actual, and Acummulative values
            projected_value = None
            actual_value = None
            acummulative_value = None
            
            if not project_month_data.empty:
                if 'Projected' in project_month_data.columns:
                    projected_value = project_month_data['Projected'].iloc[0]
                    if isinstance(projected_value, str):
                        projected_value = projected_value.replace('$', '').replace(',', '')
                    try:
                        projected_value = float(projected_value) if pd.notnull(projected_value) else None
                    except:
                        projected_value = None
                
                if 'Actual' in project_month_data.columns:
                    actual_value = project_month_data['Actual'].iloc[0]
                    if isinstance(actual_value, str):
                        actual_value = actual_value.replace('$', '').replace(',', '')
                    try:
                        actual_value = float(actual_value) if pd.notnull(actual_value) else None
                    except:
                        actual_value = None
                
                # Handle different spellings of "Acummulative"/"Accumulative"
                acum_col = None
                for col in project_month_data.columns:
                    if 'acum' in col.lower() or 'accum' in col.lower():
                        acum_col = col
                        break
                
                if acum_col:
                    acummulative_value = project_month_data[acum_col].iloc[0]
                    if isinstance(acummulative_value, str):
                        acummulative_value = acummulative_value.replace('$', '').replace(',', '')
                    try:
                        acummulative_value = float(acummulative_value) if pd.notnull(acummulative_value) else None
                    except:
                        acummulative_value = None
            # Calculate Invoiced Percentage (total_invoice / contracted_amount)
            invoiced_percent = (total_invoice / contracted_amount * 100) if contracted_amount and total_invoice else None
            
            # Build the project record for the table
            project_record = {
                'Project No': project_no,
                'Clients': project_row.get('Clients', 'Unknown'),
                'Status': project_row.get('Status', 'Unknown'),
                'PM': project_row.get('PM', 'Unknown'),
                'TL': project_row.get('TL', 'Unkown'),
                'Service Line': project_row.get('Service Line', 'Unknown'),  
                'Market Segment': project_row.get('Market Segment', 'Unknown'),  
                'Type': project_row.get('Type', 'Unknown'),  
                'Contracted Amount': f"${contracted_amount:,.2f}" if contracted_amount else "N/A",
                'Projected': f"${projected_value:,.2f}" if projected_value else "N/A",
                'Actual': f"${actual_value:,.2f}" if actual_value else "N/A",
                'Acummulative': f"${acummulative_value:,.2f}" if acummulative_value else "N/A",
                'Monthly Invoice': f"${monthly_invoice:,.2f}" if monthly_invoice else "N/A",
                'Total Invoice': f"${total_invoice:,.2f}" if total_invoice else "N/A",
                'Total Cost': f"${total_cost:,.2f}" if total_cost else "N/A",
                'Invoiced %': f"{invoiced_percent:.1f}%" if invoiced_percent is not None else "N/A",
                'ER Contract': f"{er_contract:.2f}" if er_contract else "N/A",
                'ER Invoiced': f"{er_invoiced:.2f}" if er_invoiced else "N/A"
            }

            # Add Original_Order for sorting if available
            original_order_values = df_month.loc[
                df_month[project_column].apply(lambda x: standardize_project_no(str(x)) == project_no), 
                'Original_Order'
            ]
            if not original_order_values.empty:
                project_record['Original_Order'] = original_order_values.values[0]
            else:
                project_record['Original_Order'] = 999  # Default high value for sorting

            active_project_details.append(project_record)

        # If no valid projects found, return empty data
        if not active_project_details:
            print_red(f"No valid projects found in month {selected_month} of year {selected_year}!")
            return [], []

        # Sort the projects by the original order
        active_project_details = sorted(active_project_details, key=lambda x: x.get('Original_Order', 999))

        # Create columns for the table
        columns = [{'name': col, 'id': col} for col in active_project_details[0].keys() if col != 'Original_Order']

        # Remove Original_Order from the final data
        for record in active_project_details:
            if 'Original_Order' in record:
                del record['Original_Order']

        print_green(f"Final report contains {len(active_project_details)} projects")
        print_green(f"==================== END OF REPORT GENERATION ====================")

        return active_project_details, columns

    except Exception as e:
        import traceback
        print_red(f"Error loading project data: {str(e)}")
        print_red(traceback.format_exc())
        return [], []



def extract_project_no(jobcode_str):
    """Return the first 7 characters from jobcode_str (Project No)."""
    return str(jobcode_str)[:7].strip()


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
    df_rates.columns = new_header

    # Optional debug: see how the final columns look
    print_green("After building actual rates header, columns are:")
    print_cyan(str(df_rates.columns.tolist()))

    return df_rates

def load_coef(rates_df):
    coef = rates_df.iloc[0, 32]
    print_green("Loaded coefficient (loaded_c): " + str(coef))
    return coef

def loaded_rates_ingestion(rates_df):
    print_green("Inside loaded_rates_ingestion")
    lr_df = rates_df.copy()
    
    # Debug to understand the structure
    print_cyan(f"Original loaded rates shape: {lr_df.shape}")
    
    # Dropping rows and columns
    lr_df = lr_df.drop(lr_df.index[0:4])
    lr_df = lr_df.drop(lr_df.columns[2:29], axis=1)
    
    # Print shape after dropping columns to verify
    print_cyan(f"After dropping columns, shape: {lr_df.shape}")
    
    lr_df.index = range(len(lr_df))
    lr_df = lr_df.drop(lr_df.index[2])
    lr_df.index = range(len(lr_df))
    lr_df = lr_df.drop(lr_df.index[0])
    lr_df.index = range(len(lr_df))
    
    # Check the number of columns we actually have
    print_cyan(f"Number of columns before renaming: {lr_df.shape[1]}")
    
    # Dynamically assign column names based on the actual number of columns
    if lr_df.shape[1] == 8:
        lr_df.columns = ["ID#", "Employee", "RAW_USD", "LOADED_USD", "LOADED_COP", "RAW_COP", "Column7", "Column8"]
    elif lr_df.shape[1] == 7:
        lr_df.columns = ["ID#", "Employee", "RAW_USD", "LOADED_USD", "LOADED_COP", "RAW_COP", "Column7"]
    else:
        # Fallback - generate column names based on actual count
        column_names = ["ID#", "Employee"]
        remaining_cols = lr_df.shape[1] - 2
        for i in range(remaining_cols):
            if i == 0:
                column_names.append("RAW_USD")
            elif i == 1:
                column_names.append("LOADED_USD")
            elif i == 2:
                column_names.append("LOADED_COP")
            elif i == 3:
                column_names.append("RAW_COP")
            else:
                column_names.append(f"Column{i+3}")
        lr_df.columns = column_names
    
    lr_df = lr_df.drop(lr_df.index[0])
    lr_df.index = range(len(lr_df))
    
    print_green("Loaded Rates Ingestion (loaded_rates) head:")
    print_red(str(lr_df.head()))
    return lr_df

def load_rates_from_single_sheet(file_path):
    print_green("Inside load_rates_from_single_sheet")
    df_rates = pd.read_excel(file_path, sheet_name='Rates', header=None)
    print_red("Head of full Rates sheet:")
    print_green(str(df_rates.head(10)))

    df_trm_vals = trm_ingestion(df_rates)
    df_actual_rates = rates_ingestion(df_rates)
    loaded_c = load_coef(df_rates)
    loaded_rates = loaded_rates_ingestion(df_rates)

    print_orange("TRM Values (df_trm_vals) shape: " + str(df_trm_vals.shape))
    print_green("Actual Rates (df_actual_rates) shape: " + str(df_actual_rates.shape))
    print_orange("Loaded Rates (loaded_rates) shape: " + str(loaded_rates.shape))
    return df_trm_vals, df_actual_rates, loaded_c, loaded_rates


# ==============================
# CALCULATION FUNCTIONS
# ==============================
def calculate_day_cost(merged_df):
    """
    Example day_cost logic:
    - If year == 2023, we might have a single "2023WHOLE_Year" column in df_actual_rates
    - If month == 7, we might have partial July columns (like "2024JUL (1-15)" / "2024JUL (15-31)")
    - Otherwise, for e.g. 2022, we might have "2022JAN", "2022FEB", etc.
    """
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')

    def row_day_cost(row):
        dt = row['local_date']
        if pd.isnull(dt):
            return 0

        year = dt.year
        month = dt.month
        day   = dt.day

        # 1) Fallback for any date before 2022
        if year < 2022:
            col_name = "2022Whole_Year"
            return row.get(col_name, 0) * row['hours']

        # 2) If year == 2022, do partial July if you have those columns, otherwise do 2022Whole_Year
        if year == 2022:
            if month == 7:
                # Only if you truly have "2022JUL (1-15)" in your columns
                if day <= 15:
                    col_name = "2022JUL (1-15)"
                else:
                    col_name = "2022JUL (15-31)"
            else:
                col_name = "2022Whole_Year"
            return row.get(col_name, 0) * row['hours']

        # 3) If year == 2023, assume a single “2023Whole_Year” column
        if year == 2023:
            col_name = "2023Whole_Year"
            return row.get(col_name, 0) * row['hours']

        # 4) If year >= 2024, use monthly columns + partial July
        if month == 7:
            # partial July columns: "2024JUL (1-15)", "2024JUL (15-31)", etc.
            if day <= 15:
                col_name = f"{year}JUL (1-15)"
            else:
                col_name = f"{year}JUL (15-31)"
        else:
            # e.g. "2024JAN", "2024FEB", ...
            col_name = f"{year}{dt.strftime('%b').upper()}"

        return row.get(col_name, 0) * row['hours']


    merged_df['day_cost'] = merged_df.apply(row_day_cost, axis=1)

    print_green("After calculate_day_cost, check a few rows with hours > 0:")
    has_hours = merged_df[merged_df['hours'] > 0].head(15)
    print_cyan(str(has_hours[['local_date','hours','day_cost']]))
    
    debug_zero_cost = merged_df[(merged_df['hours']>0) & (merged_df['day_cost']==0)]
    if not debug_zero_cost.empty:
        print_red("DEBUG: Rows with hours but zero cost:")
        print(debug_zero_cost[['Employee','full_name','jobcode_2','local_date','hours','day_cost']].head(50))

    
    
    return merged_df


def assign_total_hours(merged_df):
    for year in range(2017, 2026):
        col_name = f"total_hours_{year}"
        merged_df[col_name] = merged_df['hours'].where(merged_df['local_date'].dt.year == year)

    print_green("After assign_total_hours, sample rows for total_hours columns:")
    print_cyan(str(merged_df[[f"total_hours_{y}" for y in range(2017,2026)]].head(10)))
    return merged_df


# ==============================
# PROJECTS FILE & BACKUP
# ==============================
def load_third_file_dynamic(third_file):
    print_green("Inside load_third_file_dynamic")
    df_raw = pd.read_excel(third_file, sheet_name='4_Contracted Projects', header=None, engine='openpyxl')
    print_cyan("Shape of raw projects sheet: " + str(df_raw.shape))

    nrows = len(df_raw)
    end_row = None
    for i in range(688, nrows - 1):
        if pd.isna(df_raw.iloc[i, 1]) and pd.isna(df_raw.iloc[i+1, 1]):
            end_row = i
            break
    if end_row is None:
        end_row = nrows

    df_trunc = df_raw.iloc[:end_row].copy()
    print_orange("Shape after truncation: " + str(df_trunc.shape))

    header = [str(col).strip() for col in df_trunc.iloc[0].tolist()]
    df_data = df_trunc.iloc[1:].copy()
    df_data = df_data[~df_data.apply(lambda row: list(row.astype(str).str.strip()) == header, axis=1)]
    df_data.columns = header
    df_data.columns = [col.strip() for col in df_data.columns]

    if "Project No" not in df_data.columns:
        first_col = df_data.columns[0]
        df_data.rename(columns={first_col: "Project No"}, inplace=True)

    df_data["Project No"] = df_data["Project No"].astype(str).str.strip().apply(standardize_project_no)

    # Ensure the 'Month' column exists or derive it if possible
    if 'Month' not in df_data.columns:
        if 'Invoice Date' in df_data.columns:
            # Derive 'Month' from 'Invoice Date' if available
            df_data['Month'] = pd.to_datetime(df_data['Invoice Date'], errors='coerce').dt.month
            print_green("Derived 'Month' column from 'Invoice Date'.")
        else:
            # Add a placeholder 'Month' column if it cannot be derived
            df_data['Month'] = None
            print_red("'Month' column not found or derivable. Added as None.")

    # Debug: show a few rows for 1928
    print_green("Projects after truncation & standardization, checking '1928':")
    debug_1928 = df_data[df_data["Project No"].astype(str).str.contains("1928", na=False)]
    print_cyan(str(debug_1928.head(10)))

    return df_data.reset_index(drop=True)


# ==============================
# TIMESHEET FILE LOADING
# ==============================
def load_timesheet_folder(folder_path):
    """
    Loads CSV files matching 'timesheet_report_*.csv' and merges them.
    Also renames 'service item' -> 'Service Item' if present.
    Returns the merged dataframe and the most recent date from filenames.
    """
    pattern = os.path.join(folder_path, "timesheet_report_*.csv")
    csv_files = glob.glob(pattern)
    if not csv_files:
        print_red(f"No timesheet files found in {folder_path}")
        return pd.DataFrame(), None

    df_list = []
    last_end_date = None
    most_recent_date=None
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        match = re.search(r'thru_(\d{4}-\d{2}-\d{2})\.csv$', filename)
        if match:
            end_date_str = match.group(1)
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                # Update most_recent_date if this date is more recent
                if most_recent_date is None or end_date > most_recent_date:
                    most_recent_date = end_date
            except ValueError:
                end_date = None
        else:
            end_date = None

        df_temp = pd.read_csv(file_path, header=0, index_col=0)

        # rename if you see "service item"
        if 'service item' in df_temp.columns:
            df_temp.rename(columns={'service item': 'Service Item'}, inplace=True)

        df_temp["report_end_date"] = end_date
        df_list.append(df_temp)
        #last_end_date = end_date

    df_merged = pd.concat(df_list, ignore_index=True)
    
    #convert recent date to string format for display
    last_data_update = most_recent_date.strftime('%Y-%m-%d') if most_recent_date else "Unknown"
    print_green(f"Most recent timesheet data date: {last_data_update}")
    
    # Save the most recent data update date to a file
    if most_recent_date:
        try:
            with open(os.path.join(PICKLE_OUTPUT_DIR, "last_data_update.txt"), "w") as f:
                f.write(last_data_update)
            print_green(f"Saved last data update date ({last_data_update}) to file")
        except Exception as e:
            print_red(f"Error saving last data update date: {str(e)}")
    
    return df_merged, most_recent_date


def truncate_at_total(df):
    df_copy = df.copy()
    df_copy.fillna("", inplace=True)
    for i in range(len(df_copy)):
        row_str = " ".join(str(x) for x in df_copy.iloc[i].values)
        if "TOTAL" in row_str.upper():
            return df_copy.iloc[:i].copy()
    return df_copy


# ==============================
# MAIN PIPELINE
# ==============================
def main():
    """
    Main pipeline to load rates, timesheet, and project logs; then merges & calculates.
    """
    # 1) Load rates
    rates_file_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\RATES.xlsx"
    df_trm_vals, df_actual_rates, loaded_c, loaded_rates = load_rates_from_single_sheet(rates_file_path)

    
    # 2) Replace '*' with unique int IDs
    mask_star = (df_actual_rates['ID#'] == '*')
    df_star = df_actual_rates.loc[mask_star].copy().reset_index(drop=True)
    start_id = 1001
    df_star['ID#'] = range(start_id, start_id + len(df_star))
    df_actual_rates.loc[mask_star, 'ID#'] = df_star['ID#']
    df_actual_rates['ID#'] = pd.to_numeric(df_actual_rates['ID#'], errors='coerce').fillna(0).astype(int)
    print_orange(f"DEBUG: # of '*' before assignment: {(df_actual_rates['ID#'] == '*').sum()}")
    print_green(f"DEBUG: Unique IDs in df_actual_rates now: {df_actual_rates['ID#'].unique()}")

    # 3) Build a mapping from Employee -> ID#
    mapping = df_actual_rates.set_index('Employee')['ID#'].to_dict()
    print_orange(f"DEBUG: # of '*' after assignment: {(df_actual_rates['ID#'] == '*').sum()}")
    print_green(f"DEBUG: Final IDs in df_actual_rates now: {df_actual_rates['ID#'].unique()}")

    ###sub
    ###load decon llc or decon colombia
        
    df_sub_col = pd.read_excel(rates_file_path, sheet_name='STAFF', header=0, nrows=100)



    # 4) Load timesheet CSV
    timesheet_folder = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\tsheets"
    df_new, most_recent_date = load_timesheet_folder(timesheet_folder)


    #last_data_update=most_recent_date.strftime("%Y-%m-%d") if most_recent_date else 'Unidentified, please verify.'


    print_green("DEBUG: columns in df_new -> " + str(df_new.columns.tolist()))
    # Check if DataFrame is empty or missing required columns
    if df_new.empty:
        print_red("ERROR: No timesheet data found. Please check the folder path:")
        print_red(timesheet_folder)
        return None, None, None, None, pd.to_datetime('today').strftime('%Y-%m-%d')
    
    # Check if required columns exist
    required_columns = ['number', 'fname', 'lname']
    missing_columns = [col for col in required_columns if col not in df_new.columns]
    if missing_columns:
        print_red(f"ERROR: Required columns {missing_columns} not found in timesheet data")
        print_cyan(f"Available columns: {df_new.columns.tolist()}")
        return None, None, None, None, pd.to_datetime('today').strftime('%Y-%m-%d')
        
    # Convert 'number' to numeric
    df_new['number'] = pd.to_numeric(df_new['number'], errors='coerce').fillna(0).astype(int)

    # Make a full_name column BEFORE we fix the 0 IDs
    df_new['fname'] = df_new['fname'].astype(str).str.replace('Ã±', 'n', regex=False)
    df_new['lname'] = df_new['lname'].astype(str).str.replace('Ã±', 'n', regex=False)
    df_new['full_name'] = df_new['fname'].str.strip() + " " + df_new['lname'].str.strip()

    # For rows where number=0, map from full_name -> ID#
    mask_zero = (df_new['number'] == 0)
    df_new.loc[mask_zero, 'number'] = (
        df_new.loc[mask_zero, 'full_name']
        .map(mapping)
        .fillna(0)
        .astype(int)
    )

    # Build 'correct_number' from 'number'
    df_new['correct_number'] = df_new['number']
    # If still 0, try again (some older names might not be in mapping):
    mask_still_zero = (df_new['correct_number'] == 0)
    df_new.loc[mask_still_zero, 'correct_number'] = (
        df_new.loc[mask_still_zero, 'full_name']
        .map(mapping)
        .fillna(0)
        .astype(int)
    )

    print_green("DEBUG: Head of df_new after filling zero IDs:\n" + str(df_new.head(10)))

    # 5) Merge timesheet + rates => merged_df
    merged_df = pd.merge(
        df_actual_rates, df_new,
        left_on='ID#', right_on='correct_number',
        how='inner'
    )
    
    #include df_sub_col in merged df, merging on 'full_name' and in the df_sub_col 'Personel'
    merged_df = pd.merge(
        merged_df, df_sub_col,
        left_on='full_name', right_on='Personel',
        how='left'
    )
    
    print_green("DEBUG: Merged df shape -> " + str(merged_df.shape))
    print_green("DEBUG: Sample rows from merged_df:\n" + str(merged_df.head(10)))
    print_green("DEBUG: merged_df columns -> " + str(merged_df.columns.tolist()))

    # 6) Load Project data
    project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
    df_projects = load_third_file_dynamic(project_log_path)

    # 7) Load Invoices data
    df_invoices_2023 = pd.read_excel(project_log_path, sheet_name='5_Invoice-2023', header=0, dtype={'Actual': str})
    df_invoices_2023['Actual'] = (
        df_invoices_2023['Actual'].astype(str)
        .str.replace('$','', regex=False)
        .str.replace(',','', regex=False)
    )
    df_invoices_2023['Actual'] = pd.to_numeric(df_invoices_2023['Actual'], errors='coerce')
    df_invoices_2023['Invoice_Year'] = 2023  # Add explicit year column based on sheet name

    df_invoices_2024 = pd.read_excel(project_log_path, sheet_name='5_Invoice-2024', header=0)
    df_invoices_2024['Invoice_Year'] = 2024  # Add explicit year column based on sheet name

    df_invoices_2025 = pd.read_excel(project_log_path, sheet_name='5_Invoice-2025', header=0)
    df_invoices_2025['Invoice_Year'] = 2025  # Add explicit year column based on sheet name

    # Possibly truncate each at 'TOTAL'
    df_invoices_2023 = truncate_at_total(df_invoices_2023)
    df_invoices_2024 = truncate_at_total(df_invoices_2024)
    df_invoices_2025 = truncate_at_total(df_invoices_2025)  # Now truncate 2025 data also

    # Clean invoice numbers
    def keep_second_number(val):
        parts = str(val).split()
        if len(parts) >= 2:
            return parts[-1]
        return parts[0] if parts else ""

    df_invoices_2023['Invoice No'] = df_invoices_2023['Invoice No'].apply(keep_second_number)
    df_invoices_2024['Invoice No'] = df_invoices_2024['Invoice No'].apply(keep_second_number)
    df_invoices_2025['Invoice No'] = df_invoices_2025['Invoice No'].apply(keep_second_number)

    # Convert 'Month' column to numeric in all dataframes
    df_invoices_2023['Month_numeric'] = pd.to_numeric(df_invoices_2023['Month'], errors='coerce')
    df_invoices_2024['Month_numeric'] = pd.to_numeric(df_invoices_2024['Month'], errors='coerce')
    df_invoices_2025['Month_numeric'] = pd.to_numeric(df_invoices_2025['Month'], errors='coerce')

    # Ensure consistent column names before concatenation
    required_columns = ['Project No', 'Month', 'Month_numeric', 'Invoice No', 'Invoice Date', 'Actual', 'Invoice_Year']
    for df in [df_invoices_2023, df_invoices_2024, df_invoices_2025]:
        for col in required_columns:
            if col not in df.columns:
                if col == 'Invoice_Year':  # Should already be added above, but just in case
                    continue
                df[col] = None

    # Concatenate all invoice dataframes
    df_invoices = pd.concat([df_invoices_2023, df_invoices_2024, df_invoices_2025], ignore_index=True)
    print_green("DEBUG: Combined df_invoices shape -> " + str(df_invoices.shape))
    print_green("DEBUG: Combined df_invoices columns -> " + str(df_invoices.columns.tolist()))

    # Filter out future-dated invoices
    df_invoices['Invoice Date'] = pd.to_datetime(df_invoices['Invoice Date'], errors='coerce')
    today = pd.to_datetime('today').normalize()
    df_invoices = df_invoices[df_invoices['Invoice Date'] <= today]

    raw_invoices = df_invoices.copy()

    # Summaries
    df_invoices['Actual'] = pd.to_numeric(df_invoices['Actual'], errors='coerce')
    # Filter out NaN values or replace them with 0
    df_invoices['Actual'] = df_invoices['Actual'].fillna(0)
    # Now perform the groupby sum
    df_invoices_sum = df_invoices.groupby('Project No', as_index=False)['Actual'].sum()
    df_invoices_sum.rename(columns={'project no': 'Project No', 'Actual': 'TotalProjectInvoice'}, inplace=True)
    df_invoices_sum['TotalProjectInvoice'] = pd.to_numeric(df_invoices_sum['TotalProjectInvoice'], errors='coerce')
    global_invoices = df_invoices_sum.copy()

    # 8) Now do cost calculations
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)

    # ============ DEBUG BLOCK: find rows with hours > 0 but day_cost=0 ============
    debug_missing_cost = merged_df[(merged_df['hours'] > 0) & (merged_df['day_cost'] == 0)]
    if not debug_missing_cost.empty:
        print_red("DEBUG: The following rows have >0 hours but day_cost=0 (possible missing rates):")
        print_red(str(debug_missing_cost[[
            'Employee','full_name','jobcode_2','jobcode_3','hours','local_date',
            # If your partial July columns exist, also show them
            'day_cost'
        ]].head(50)))
    # ==============================================================================

    # If you need a final "Project No" column that merges 1928 logic:
    # (You might have already done it above or in the dash code.)
    # Example:
    # def conditional_extract_project_no(row):
    #     jc2 = str(row.get('jobcode_2','')).strip()
    #     jc3 = str(row.get('jobcode_3','')).strip()
    #     if jc2.startswith('1928'):
    #         return jc3[:7].strip()
    #     return jc2[:7].strip()
    # merged_df['Project No'] = merged_df.apply(conditional_extract_project_no, axis=1)

    # Print final shape
    print_green("Final merged_df shape -> " + str(merged_df.shape))

    # Possibly check a sample for older projects
    # e.g. 1871 or 1872
    # debug_1871 = merged_df[merged_df['jobcode_2'].str.contains('1871', na=False)]
    # print_cyan("DEBUG: 1871 sample ->\n"+str(debug_1871[['Employee','hours','day_cost','local_date']].head(20)))

    # Return for pickling
    # Return for pickling - add the most_recent_date 
    last_update = pd.to_datetime('today').strftime('%Y-%m-%d')
    last_data_update = most_recent_date.strftime('%Y-%m-%d') if most_recent_date else "Unknown"
    print_orange(">>> Finished main() and returning data now.")
    return merged_df, df_projects, global_invoices, raw_invoices, last_update, last_data_update


last_update = pd.to_datetime('today').strftime('%Y-%m-%d')

"""
def precompute_and_save():
    
    #Runs the main data processing pipeline and saves the resulting DataFrames
    #as pickle files for faster future loading.
    
    global_merged_df, global_projects_df, global_invoices, global_raw_invoices, last_update = main()

    if global_merged_df is None:
        print_red("ERROR: Merged DF is None; cannot save pickles.")
        return

    if not os.path.exists(PICKLE_OUTPUT_DIR):
        os.makedirs(PICKLE_OUTPUT_DIR)

    global_merged_df.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_merged_df.pkl"))
    print_green("Saved global_merged_df.pkl")

    global_projects_df.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_projects_df.pkl"))
    global_invoices.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_invoices.pkl"))
    global_raw_invoices.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_raw_invoices.pkl"))

    with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "w") as f:
        f.write(last_update)

    print_green("Precomputed pickle files saved successfully.")"""


def precompute_and_save():
    """
    Runs the main data processing pipeline and saves the resulting DataFrames
    as pickle files for faster future loading and also exports to Excel for debugging.
    """
    global_merged_df, global_projects_df, global_invoices, global_raw_invoices, last_update, last_data_update = main()

    if global_merged_df is None:
        print_red("ERROR: Merged DF is None; cannot save pickles.")
        return

    if not os.path.exists(PICKLE_OUTPUT_DIR):
        os.makedirs(PICKLE_OUTPUT_DIR)

    # Save pickle files (original functionality)
    global_merged_df.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_merged_df.pkl"))
    global_projects_df.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_projects_df.pkl"))
    global_invoices.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_invoices.pkl"))
    global_raw_invoices.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_raw_invoices.pkl"))

    with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "w") as f:
        f.write(last_update)
    # Save the last data update date to a separate file
    with open(os.path.join(PICKLE_OUTPUT_DIR, "last_data_update.txt"), "w") as f:
        f.write(last_data_update)
    print_green("Precomputed pickle files saved successfully.")
    
    # Export to Excel for debugging
""" excel_path = os.path.join(PICKLE_OUTPUT_DIR, "data_check.xlsx")
with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        # Export each DataFrame to a separate sheet
        print_cyan("Exporting DataFrames to Excel for debugging...")
        
        global_merged_df.to_excel(writer, sheet_name='merged_df')
        print_green("- Exported global_merged_df")
        
        global_projects_df.to_excel(writer, sheet_name='projects_df')
        print_green("- Exported global_projects_df")
        
        global_invoices.to_excel(writer, sheet_name='invoices')
        print_green("- Exported global_invoices")
        
        global_raw_invoices.to_excel(writer, sheet_name='raw_invoices')
        print_green("- Exported global_raw_invoices")
        
        with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "w") as f:
            f.write(last_update)"""
    #print_green(f"Excel debug file saved to: {excel_path}")


# Exporting the project log and related variables for external use
project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
    

def get_project_log_data(years=[2023, 2024, 2025]):
    """Load and return the project log data from all invoice sheets for the specified years.
    
    Args:
        years (list): List of years for which to load data (default: [2023, 2024, 2025])
    
    Returns:
        pandas.DataFrame: The combined loaded project data with Month column and Year column
    """
    combined_df = pd.DataFrame()
    
    for year in years:
        try:
            # Use the correct sheet name based on year
            sheet_name = f"5_Invoice-{year}"
            
            print_green(f"Attempting to load project log from: {project_log_path}, sheet: {sheet_name}")
            df_projects = pd.read_excel(project_log_path, sheet_name=sheet_name, engine='openpyxl')
            print_green(f"Successfully loaded sheet {sheet_name} with {len(df_projects)} rows")
            
            # Add a Year column to identify the source
            df_projects['Year'] = year
            
            # Check if 'Month' column exists
            if 'Month' in df_projects.columns:
                # Convert Month to numeric values
                df_projects['Month'] = pd.to_numeric(df_projects['Month'], errors='coerce')
            else:
                print_red(f"Month column not found in {sheet_name}")
                # Try to find a column that might contain month information
                date_columns = [col for col in df_projects.columns if 'date' in str(col).lower()]
                if date_columns and 'Invoice Date' in date_columns:
                    print_green(f"Deriving 'Month' column from 'Invoice Date'")
                    df_projects['Month'] = pd.to_datetime(df_projects['Invoice Date'], errors='coerce').dt.month
                elif len(df_projects.columns) > 0:
                    # If no date column, check if first column might contain month info
                    first_col = df_projects.columns[0]
                    if df_projects[first_col].dtype in ['int64', 'float64'] or pd.to_numeric(df_projects[first_col], errors='coerce').notna().any():
                        df_projects['Month'] = pd.to_numeric(df_projects[first_col], errors='coerce')
            
            # Check if Project No column exists, standardize if it does
            if 'Project No' in df_projects.columns:
                df_projects["Project No"] = df_projects["Project No"].astype(str).str.strip().apply(standardize_project_no)
            
            # Add to the combined DataFrame
            combined_df = pd.concat([combined_df, df_projects], ignore_index=True)
            
        except Exception as e:
            print_red(f"Error loading data for year {year}: {str(e)}")
    
    if combined_df.empty:
        print_red("No data could be loaded from any year sheet")
        # Return an empty DataFrame with required columns as fallback
        return pd.DataFrame(columns=['Project No', 'Month', 'Actual', 'Invoice Date', 'Year'])
    
    print_green(f"Final combined dataframe has {len(combined_df)} rows")
    return combined_df


# Exporting the function for external use
__all__ = ['get_project_log_data']


def last_update():
    """Read the last data update date from file"""
    try:
        with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "r") as f:
            return f.read().strip()
    except Exception:
        return pd.to_datetime('today').strftime('%Y-%m-%d')

def last_data_update():
    """Read the last data update date from file"""
    try:
        with open(os.path.join(PICKLE_OUTPUT_DIR, "last_data_update.txt"), "r") as f:
            return f.read().strip()
    except Exception:
        return "Unknown"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "precompute":
        precompute_and_save()
    else:
        main()


