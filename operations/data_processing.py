#data_processing.py
# clean version 22/may/2025
# ######################################################################
#validated
########################################################################
##Import libraries and locally defined functions
from utility_funcs import print_green, print_cyan, print_orange, print_red, print_orange, standardize_project_no, sanitize_filename, extract_project_no
from config import TABLE_STYLE, TABLE_CELL_STYLE, TABLE_CELL_CONDITIONAL, RIGHT_TABLE_RED_STYLE
########################################################################
import os
import re
import base64
import numpy as np
import pandas as pd
import warnings
from datetime import datetime
import glob
#######################################################################
#file paths
project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
PICKLE_OUTPUT_DIR = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"

#######################################################################
#testing
# ==============================
# DATA LOADING FUNCTIONS
# ==============================

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

def import_forecast_invoicing():
    """
    Import forecast invoicing data from the '6_Summary Invoice' sheet of the project log.
    Returns a DataFrame with forecast values for each month of 2025.
    """
    print_green("Loading forecast invoicing data...")
    
    try:
        # Read the '6_Summary Invoice' sheet
        df_forecast = pd.read_excel(
            project_log_path, 
            sheet_name='6_Summary Invoice',
            header=None,  # No header so we can explicitly find it
            engine='openpyxl'
        )
        
        print_green(f"Successfully loaded '6_Summary Invoice' sheet with shape {df_forecast.shape}")
        
        # Find the header row (row containing 'FORECAST INVOICING')
        header_row = None
        for i in range(5):  # Check first few rows
            if 'FORECAST INVOICING' in str(df_forecast.iloc[i].values):
                header_row = i
                break
        
        if header_row is None:
            print_red("Could not find 'FORECAST INVOICING' header in the sheet")
            # Try to find any row that might contain the header
            for i in range(10):
                row_text = ' '.join([str(x) for x in df_forecast.iloc[i].values])
                if 'FORECAST' in row_text.upper() or 'BUDGET' in row_text.upper():
                    header_row = i
                    print_orange(f"Found possible header in row {i}: {row_text}")
                    break
                    
        if header_row is None:
            print_red("Could not identify the header row, using row 2 as default")
            header_row = 2
        
        # Extract the column headers
        headers = df_forecast.iloc[header_row].values
        forecast_col_idx = None
        month_col_idx = None
        
        # Find the column indices for month and forecast
        for i, header in enumerate(headers):
            header_str = str(header).upper()
            if 'FORECAST' in header_str or 'BUDGET' in header_str:
                forecast_col_idx = i
            if 'MONTH' in header_str:
                month_col_idx = i
                
        if forecast_col_idx is None:
            print_red("Could not find forecast column")
            # Look in column C (index 2) by default
            forecast_col_idx = 2
            print_orange(f"Using default column C (index {forecast_col_idx}) for forecast")
            
        if month_col_idx is None:
            print_red("Could not find month column")
            # Look in column B (index 1) by default
            month_col_idx = 1
            print_orange(f"Using default column B (index {month_col_idx}) for month")
        
        # Extract the data (12 rows starting from header row + 1)
        data_start_row = header_row + 1
        data_end_row = data_start_row + 12  # 12 months
        
        # Create the DataFrame with forecast values for each month
        forecast_data = []
        for i in range(data_start_row, min(data_end_row, len(df_forecast))):
            row = df_forecast.iloc[i]
            
            # Extract month (could be number or name)
            month_value = row.iloc[month_col_idx]
            if pd.isna(month_value):
                # Try to infer month from row number (1-12)
                month = i - data_start_row + 1
            else:
                # Try to convert to int if it's a number
                try:
                    month = int(month_value)
                except (ValueError, TypeError):
                    # If it's a month name, try to convert to number
                    month_str = str(month_value).strip().lower()
                    month_dict = {
                        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                    }
                    for key, val in month_dict.items():
                        if key in month_str:
                            month = val
                            break
                    else:
                        month = i - data_start_row + 1  # Default to position
            
            # Extract forecast value
            forecast_value = row.iloc[forecast_col_idx]
            
            # Try to convert to float if it's a string with $ or ,
            if isinstance(forecast_value, str):
                forecast_value = forecast_value.replace('$', '').replace(',', '')
                try:
                    forecast_value = float(forecast_value)
                except ValueError:
                    forecast_value = None
                    
            forecast_data.append({
                'Month': month,
                'MonthName': pd.Timestamp(2025, month, 1).strftime('%B'),
                'Year': 2025,
                'ForecastValue': forecast_value
            })
        
        # Create DataFrame
        df_result = pd.DataFrame(forecast_data)
        
        # Sort by month to ensure correct order
        df_result = df_result.sort_values('Month')
        
        print_green(f"Successfully created forecast invoicing DataFrame with {len(df_result)} rows")
        print_cyan("Forecast data sample:")
        print(df_result.head())
        
        return df_result
    
    except Exception as e:
        import traceback
        print_red(f"Error loading forecast invoicing data: {str(e)}")
        print_red(traceback.format_exc())
        # Return empty DataFrame with the expected structure
        return pd.DataFrame(columns=['Month', 'MonthName', 'Year', 'ForecastValue'])


#########################################################################

#warnings.simplefilter("ignore")  # Suppress warnings if desired


# ==============================
# DATA PROCESSING FUNCTIONS     
# ==============================
def calculate_new_er(df_project, project_no, df_merged_costs):
    # First check if there are any staff_type=1 entries (US employees) for this project
    # If there are no US employees, return None (which will display as N/A)
    project_costs = df_merged_costs[df_merged_costs['jobcode_2'].notna() & 
                                  df_merged_costs['jobcode_2'].str.startswith(project_no)]
    
    # Check if we have any US employees (staff_type=1) with hours
    type_1_entries = project_costs[project_costs['staff_type'] == 1]
    if type_1_entries.empty or type_1_entries['day_cost'].sum() == 0:
        return None  # No US employees, so return None which will show as N/A
    
    # Check if the project has 0% invoiced
    project_row = df_project[df_project['Project No'] == project_no]
    if not project_row.empty:
        # Try to extract invoiced percentage
        if 'Invoiced %' in project_row.columns:
            try:
                invoiced_pct = project_row['Invoiced %'].iloc[0]
                # Handle string percentage values (with % symbol)
                if isinstance(invoiced_pct, str) and '%' in invoiced_pct:
                    invoiced_pct = float(invoiced_pct.replace('%', '').strip())
                # If invoice percentage is 0%, return 0 for ER DECON LLC
                if invoiced_pct == 0:
                    return 0
            except:
                pass  # Continue with normal calculation if there's an error
    
    # Check if staff_type exists first
    if 'staff_type' not in df_merged_costs.columns:
        print_orange("DEBUG: 'staff_type' column not found in data")
        print(f"Available columns: {df_merged_costs.columns.tolist()}")
        return None
    
    if project_row.empty or 'Contracted Amount' not in project_row.columns:
        print("DEBUG: No project found or missing Contracted Amount column")
        return None
    
    contracted_amount = project_row['Contracted Amount'].iloc[0]
    # Parse contracted amount if it's a string
    if isinstance(contracted_amount, str):
        try:
            contracted_amount = float(contracted_amount.replace('$', '').replace(',', ''))
        except:
            print(f"DEBUG: Could not parse contracted amount: {contracted_amount}")
            return None
    
    if pd.isna(contracted_amount):
        print("DEBUG: Contracted Amount is NaN")
        return None
    
    # Sum costs by staff type (1 and 2)
    type_1_cost = project_costs[project_costs['staff_type'] == 1]['day_cost'].sum()
    type_2_cost = project_costs[project_costs['staff_type'] == 2]['day_cost'].sum()
    
    if type_1_cost == 0:
        return None  # Can't calculate ratio with zero type_1_cost
    
    new_er = (contracted_amount - type_2_cost) / type_1_cost
    return new_er


def calculate_decon_llc_invoiced(df_project, project_no, df_merged_costs, df_raw_invoices):
    """
    Calculate the DECON LLC Invoiced ratio: (Invoiced Amount - Type 2 Cost) / Type 1 Cost
    
    Args:
        df_project: DataFrame containing project information
        project_no: Project number to calculate for
        df_merged_costs: DataFrame containing timesheet and rate information
        df_raw_invoices: DataFrame containing invoice information
        
    Returns:
        float: DECON LLC Invoiced value or None if can't be calculated
    """
    # Debug for specific projects with issues
    debug_project = (project_no == "2051.00")
    
    if debug_project:
        print_orange(f"DEBUG {project_no}: Starting calculation for DECON LLC Invoiced")
    
    # First check if there are any staff_type=1 entries (US employees) for this project
    # If there are no US employees, return None (which will display as N/A)
    project_costs = df_merged_costs[df_merged_costs['jobcode_2'].notna() & 
                                  df_merged_costs['jobcode_2'].str.startswith(project_no)]
    
    # Check if we have any US employees (staff_type=1) with hours
    type_1_entries = project_costs[project_costs['staff_type'] == 1]
    if type_1_entries.empty or type_1_entries['day_cost'].sum() == 0:
        if debug_project:
            print_orange(f"DEBUG {project_no}: No US employees (staff_type=1) found or zero cost, returning None")
        return None
    
    # Check if staff_type exists
    if 'staff_type' not in df_merged_costs.columns:
        print_orange(f"DEBUG {project_no}: 'staff_type' column not found in data")
        return None
    
    # First, check if the project has 0% invoiced
    project_row = df_project[df_project['Project No'] == project_no]
    if not project_row.empty:
        # Try to extract invoiced percentage
        if 'Invoiced %' in project_row.columns:
            try:
                invoiced_pct = project_row['Invoiced %'].iloc[0]
                # Handle string percentage values (with % symbol)
                if isinstance(invoiced_pct, str) and '%' in invoiced_pct:
                    invoiced_pct = float(invoiced_pct.replace('%', '').strip())
                # If invoice percentage is 0%, return 0
                if invoiced_pct == 0:
                    if debug_project:
                        print_orange(f"DEBUG {project_no}: 0% invoiced project, returning 0")
                    return 0
                # Debug for 100% invoiced projects
                if invoiced_pct == 100 and debug_project:
                    print_orange(f"DEBUG {project_no}: Found 100% invoiced project")
            except Exception as e:
                if debug_project:
                    print_orange(f"DEBUG {project_no}: Error extracting invoiced %: {str(e)}")
    
    # Get the total invoiced amount for this project
    invoiced_amount = None
    project_invoices = df_raw_invoices[df_raw_invoices['Project No'].apply(
        lambda x: standardize_project_no(str(x)) == project_no
    )]
    
    if not project_invoices.empty:
        # Convert 'Actual' column to numeric before summing
        project_invoices['Actual'] = pd.to_numeric(project_invoices['Actual'], errors='coerce')
        invoiced_amount = project_invoices['Actual'].sum()
        
        if debug_project:
            print_orange(f"DEBUG {project_no}: Found {len(project_invoices)} invoices with total amount: {invoiced_amount}")
    else:
        if debug_project:
            print_orange(f"DEBUG {project_no}: No invoices found in df_raw_invoices")
    
    if pd.isna(invoiced_amount) or invoiced_amount == 0:
        if debug_project:
            print_orange(f"DEBUG {project_no}: No invoices found or zero amount")
        return None
    
    # Sum costs by staff type (1 and 2)
    type_1_cost = project_costs[project_costs['staff_type'] == 1]['day_cost'].sum()
    type_2_cost = project_costs[project_costs['staff_type'] == 2]['day_cost'].sum()
    
    if debug_project:
        print_orange(f"DEBUG {project_no}: type_1_cost = {type_1_cost}, type_2_cost = {type_2_cost}")
    
    if type_1_cost == 0:
        if debug_project:
            print_orange(f"DEBUG {project_no}: type_1_cost is zero, calculation not possible")
        return None
    
    # Calculate DECON LLC Invoiced
    decon_llc_invoiced = (invoiced_amount - type_2_cost) / type_1_cost
    
    if debug_project:
        print_orange(f"DEBUG {project_no}: Final calculation: ({invoiced_amount} - {type_2_cost}) / {type_1_cost} = {decon_llc_invoiced}")
    
    return decon_llc_invoiced

######################################################









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
        df_month = df_sheet[pd.to_numeric(df_sheet['Month'], errors='coerce') == selected_month].copy()
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

            # Calculate ER DECON LLC (excluding Colombian staff)
            new_er = calculate_new_er(global_projects_df, project_no, global_merged_df)
            
            # Calculate DECON LLC Invoiced (excluding Colombian staff for invoiced amount)
            decon_llc_invoiced = calculate_decon_llc_invoiced(global_projects_df, project_no, global_merged_df, global_raw_invoices)


            def extract_number_part(value):
                """Extract just the number prefix from strings like '1-Something', '2-Other', etc."""
                if not isinstance(value, str):
                    return value
                
                # Look for patterns like "1-", "2.", "3:", etc.
                import re
                match = re.match(r'^(\d+)[-\.\s:]', value)
                if match:
                    return match.group(1)
                return value
            
            
            # Get Projected, Actual, and Acummulative from the sheet for this project
            project_month_data = df_month[df_month[project_column].apply(
                lambda x: standardize_project_no(str(x)) == project_no
            )].copy()
            
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
            # Store both numeric and formatted versions of invoiced_percent
            if contracted_amount and actual_value:
                invoiced_percent_num = (actual_value / contracted_amount * 100)
                invoiced_percent = f"{invoiced_percent_num:.1f}%"  # Formatted for display
            else:
                invoiced_percent_num = None
                invoiced_percent = None


            
            # Build the project record for the table
            project_record = {
                'Project No': project_no,
                'Clients': project_row.get('Clients', 'Unknown'),
                'Status': extract_number_part(project_row.get('Status', 'Unknown')),
                'PM': project_row.get('PM', 'Unknown'),
                'Project Description': project_row.get('Project Description', 'No Description'),
                'TL': project_row.get('TL', 'Unknown'),
                'Service Line': extract_number_part(project_row.get('Service Line', 'Unknown')),  
                'Market Segment': extract_number_part(project_row.get('Market Segment', 'Unknown')),  
                'Type': extract_number_part(project_row.get('Type', 'Unknown')),  
                
                
   
                'Contracted Amount': contracted_amount if contracted_amount is not None else None,
                'Projected': projected_value if projected_value is not None else 0,
                'Actual': actual_value if actual_value is not None else 0,
                'Acummulative': acummulative_value if acummulative_value is not None else None,
                'Monthly Invoice': monthly_invoice if monthly_invoice is not None else 0,
                'Total Invoice': total_invoice if total_invoice is not None else 0,
                'Total Cost': total_cost if total_cost is not None else 0,
                'Invoiced %': invoiced_percent if invoiced_percent is not None else 0,
                'Invoiced %_num': invoiced_percent_num if invoiced_percent_num is not None else 0,
                
               
                
                # Add hidden numeric column for Invoiced %
                'Invoiced %_num': invoiced_percent_num,
                'ER Contract': er_contract if er_contract is not None else None,
                'ER Invoiced': er_invoiced if er_invoiced is not None else None,
                'ER DECON LLC': new_er if new_er is not None else None,
                'DECON LLC Invoiced': decon_llc_invoiced if decon_llc_invoiced is not None else None,
            }

            # Check if there are worked hours for this project for ER DECON LLC display
            has_worked_hours = not project_costs.empty and project_costs['hours'].sum() > 0
            
            # For ER DECON LLC:
            # - Display "N/A" for projects with no worked hours
            # - Display actual value if calculated
            # - Only display "0.00" for projects with worked hours but zero calculated value
            if not has_worked_hours:
                project_record['ER DECON LLC'] = "N/A"
            else:
                # If we have a valid value, use it
                if new_er is not None:
                    project_record['ER DECON LLC'] = f"{new_er:.2f}"
                # Special handling for 100% invoiced projects - should never show 0.00
                elif invoiced_percent_num is not None and invoiced_percent_num >= 99.9:  # Use 99.9% to handle floating point issues
                    # For 100% invoiced projects, show N/A if we can't calculate a proper value
                    project_record['ER DECON LLC'] = "N/A"
                else:
                    # For all other cases with worked hours but no calculated value
                    project_record['ER DECON LLC'] = "0.00"

            # For DECON LLC Invoiced - similar logic as above:
            # - Display "N/A" for projects with no worked hours
            # - Display actual value if calculated
            # - Only display "0.00" for projects with worked hours but zero calculated value
            if not has_worked_hours:
                project_record['DECON LLC Invoiced'] = "N/A"
            else:
                # If we have a valid value, use it
                if decon_llc_invoiced is not None:
                    project_record['DECON LLC Invoiced'] = f"{decon_llc_invoiced:.2f}"
                # Special handling for 100% invoiced projects - should never show 0.00
                elif invoiced_percent_num is not None and invoiced_percent_num >= 99.9:  # Use 99.9% to handle floating point issues
                    # For 100% invoiced projects, show N/A if we can't calculate a proper value
                    project_record['DECON LLC Invoiced'] = "N/A"
                else:
                    # For all other cases with worked hours but no calculated value
                    project_record['DECON LLC Invoiced'] = "0.00"

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

        # Create columns for the table - include the new hidden numeric column
        columns = [{'name': col, 'id': col, 'type': 'text' if not col.endswith('_num') else 'numeric'} 
                   for col in active_project_details[0].keys() 
                   if col != 'Original_Order']

        # Hide the numeric helper column
        for col in columns:
            if col['id'] == 'Invoiced %_num':
                col['hidden'] = True

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


# ==============================
# CALCULATION FUNCTIONS
# ==============================



def calculate_invoiced_percentage(actual_value, contracted_amount):
    """
    Calculate invoiced percentage properly, handling edge cases.
    
    Args:
        actual_value: The actual invoice amount
        contracted_amount: The contracted amount
        
    Returns:
        tuple: (formatted_percentage_string, numeric_percentage_for_filtering)
    """
    # Convert values to float if they're strings
    if isinstance(actual_value, str):
        actual_value = float(actual_value.replace('$', '').replace(',', ''))
    if isinstance(contracted_amount, str):
        contracted_amount = float(contracted_amount.replace('$', '').replace(',', ''))
        
    # Calculate percentage if we have valid inputs
    if contracted_amount is not None and contracted_amount > 0 and actual_value is not None and actual_value > 0:
        percentage = (actual_value / contracted_amount) * 100
        return f"{percentage:.1f}%", percentage
    elif actual_value is not None and actual_value > 0:
        # We have invoices but no valid contract amount
        return "N/A", -1  # Use -1 as a sentinel value for N/A
    else:
        # No invoice amount
        return "0.0%", 0


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



# ==============================
# TIMESHEET FILE LOADING
# ==============================


def truncate_at_total(df):
    df_copy = df.copy()
    
    # Fill NA values appropriately by dtype
    for col in df_copy.columns:
        if df_copy[col].dtype == 'object':  # String columns
            df_copy[col] = df_copy[col].fillna("")
        else:  # Numeric or other columns
            df_copy[col] = df_copy[col].fillna(0)
    
    for i in range(len(df_copy)):
        row_str = " ".join([str(x) for x in df_copy.iloc[i].values])
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

    df_invoices_2024 = pd.read_excel(project_log_path, sheet_name='5_Invoice-2024', header=0).copy()
    df_invoices_2024['Invoice_Year'] = 2024  # Add explicit year column based on sheet name

    df_invoices_2025 = pd.read_excel(project_log_path, sheet_name='5_Invoice-2025', header=0).copy()
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
    df_invoices_2023=df_invoices_2023.copy()
    #df_invoices_2024=df_invoices_2024.copy()
    #df_invoices_2025=df_invoices_2025.copy()
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
########################################
# ==============================
# DATA CACHING FUNCTIONS 
# ==============================
def precompute_and_save():
    """
    Runs the main data processing pipeline and saves the resulting DataFrames
    as pickle files for faster future loading.
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
    
    # Add forecast invoicing data
    forecast_df = import_forecast_invoicing()
    forecast_df.to_pickle(os.path.join(PICKLE_OUTPUT_DIR, "forecast_invoicing.pkl"))
    print_green("Added forecast invoicing data to pickles")

    with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "w") as f:
        f.write(last_update)
    # Save the last data update date to a separate file
    with open(os.path.join(PICKLE_OUTPUT_DIR, "last_data_update.txt"), "w") as f:
        f.write(last_data_update)
    print_green("Precomputed pickle files saved successfully.")



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
