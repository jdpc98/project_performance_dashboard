import os
import re
import base64
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import warnings
from datetime import datetime

# Shut up all warnings (adjust as needed)
warnings.simplefilter("ignore")

# Global variables shared across callbacks
global_merged_df = None
global_projects_df = None
global_invoices = None

# ----- Style settings for our tables -----
TABLE_STYLE = {
    'overflowX': 'auto',
    'width': '100%',
    'border': '1px solid #ccc',
    'borderCollapse': 'collapse'
}
TABLE_CELL_STYLE = {
    'textAlign': 'left',
    'padding': '5px',
    'fontFamily': 'Calibri, sans-serif'
}
TABLE_CELL_CONDITIONAL = [
    {'if': {'column_id': 'Field'}, 'width': '40%'},
    {'if': {'column_id': 'Value'}, 'width': '60%'}
]
RIGHT_TABLE_RED_STYLE = [
    {'if': {'filter_query': '{Field} = "Total Invoice (Temporarily Unavailable)"', 'column_id': 'Value'}, 'color': 'red'},
    {'if': {'filter_query': '{Field} = "Remaining to be invoiced (Temporarily Unavailable)"', 'column_id': 'Value'}, 'color': 'red'},
    {'if': {'filter_query': '{Field} = "ER Contract (Temporarily Unavailable)"', 'column_id': 'Value'}, 'color': 'red'},
    {'if': {'filter_query': '{Field} = "ER Invoiced (Temporarily Unavailable)"', 'column_id': 'Value'}, 'color': 'red'}
]

# Helper for printing debug messages in green
def print_green(message):
    print("\033[92m" + str(message) + "\033[0m")

# Load and encode logo image (using updated path)
logo_path = r"R:\DECON LOGOS\logodecon2.jpg"
encoded_logo = base64.b64encode(open(logo_path, 'rb').read()).decode('ascii')

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def standardize_project_no(x):
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x).strip()

def extract_project_no(jobcode_str):
    return str(jobcode_str)[:7].strip()

# ===== INGESTION FUNCTIONS FOR THE "RATES" SHEET =====
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
    df_rates = df_rates.drop(df_rates.index[0:7])
    df_rates = df_rates.drop(df_rates.columns[29:], axis=1)
    df_dates = rates_df.iloc[4:6, 4:29].copy()
    df_dates.ffill(axis=1, inplace=True)
    df_dates.loc['concat_cont'] = df_dates.loc[4].astype(str) + df_dates.loc[5].astype(str)
    new_header = np.concatenate((["ID#", "Employee", "2022Whole_Year", "2023Whole_Year"], df_dates.loc['concat_cont'].values))
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

# ===== CALCULATION FUNCTIONS =====
def calculate_day_cost(merged_df):
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')
    def row_day_cost(row):
        dt = row['local_date']
        if pd.isnull(dt):
            return 0
        year = dt.year
        if dt.month == 7:
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

# ===== DYNAMIC LOADER FOR PROJECTS FILE =====
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

# ===== FUNCTION TO EXPORT BACKUP DATA (DATA SAFETY) =====
def export_data_safety():
    backup_dir = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    backup_filename = f"data_backup_{timestamp}.xlsx"
    backup_file = os.path.join(backup_dir, backup_filename)
    with pd.ExcelWriter(backup_file, engine="xlsxwriter") as writer:
        global_merged_df.to_excel(writer, sheet_name="Merged", index=False)
        global_projects_df.to_excel(writer, sheet_name="Projects", index=False)
        global_invoices.to_excel(writer, sheet_name="Invoices", index=False)
    print_green("Data backup exported to " + backup_file)
    base_file = os.path.join(backup_dir, "base_data.xlsx")
    with pd.ExcelWriter(base_file, engine="xlsxwriter") as writer:
        global_merged_df.to_excel(writer, sheet_name="Merged", index=False)
        global_projects_df.to_excel(writer, sheet_name="Projects", index=False)
        global_invoices.to_excel(writer, sheet_name="Invoices", index=False)
    print_green("Base data file updated at " + base_file)

# ===== MAIN PIPELINE =====
def main():
    global global_merged_df, global_projects_df, global_invoices
    # 1) Load Rates data
    rates_file_path = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    df_trm_vals, df_actual_rates, loaded_c, loaded_rates = load_rates_from_single_sheet(rates_file_path)
    
    # 2) Load timesheet CSV
    second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    df_new = pd.read_csv(second_file, header=0, index_col=0)
    print_green("Head of timesheet CSV (df_new):")
    print_green(str(df_new.head()))
    print_green("Columns in df_new (before merge):")
    print_green(str(df_new.columns.tolist()))
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    
    # 3) Merge timesheet with rates (map Employee -> ID#)
    mapping = df_actual_rates.set_index('Employee')['ID#'].to_dict()
    print_green("Mapping from rates (Employee -> ID#):")
    print_green(str(mapping))
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    df_new.loc[mask, 'correct_number'] = mapped.astype(np.int64)
    print_green("Head of df_new after mapping:")
    print_green(str(df_new.head()))
    
    merged_df = pd.merge(df_actual_rates, df_new, left_on='ID#', right_on='correct_number', how='inner')
    print_green("Head of merged_df after merging rates and timesheet:")
    print_green(str(merged_df.head()))
    print_green("Columns in merged_df (after merge):")
    print_green(str(merged_df.columns.tolist()))
    
    # 4) Load Projects data
    third_file = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    df_projects = load_third_file_dynamic(third_file)
    
    # 5) Load Invoices data
    invoice_file = r"C:\Users\jose.pineda\Desktop\operations\invoice_dummy_file.xlsx"
    df_invoices = pd.read_excel(invoice_file, sheet_name='Sheet1')
    df_invoices['project no'] = df_invoices['project no'].astype(str).str.strip().apply(standardize_project_no)
    df_invoices_sum = df_invoices.groupby('project no', as_index=False)['amount'].sum()
    df_invoices_sum.rename(columns={'project no': 'Project No', 'amount': 'TotalInvoice'}, inplace=True)
    df_invoices_sum['TotalInvoice'] = pd.to_numeric(df_invoices_sum['TotalInvoice'], errors='coerce')
    global_invoices = df_invoices_sum.copy()
    print("Invoice dtypes:\n", global_invoices.dtypes)
    print_green("Head of df_invoices_sum:")
    print_green(str(global_invoices.head()))
    
    # 6) Export debug Excel file
    output_directory = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    output_path_initial = os.path.join(output_directory, "merged_output.xlsx")
    merged_df.to_excel(output_path_initial, index=False)
    print_green(f"Merged DataFrame exported successfully to {output_path_initial}")
    
    # 7) Calculate day cost and assign total hours
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)
    output_path_updated = os.path.join(output_directory, "merged_with_day_cost.xlsx")
    merged_df.to_excel(output_path_updated, index=False)
    print_green(f"Updated DataFrame with day_cost and total hours exported successfully to {output_path_updated}")
    
    # 8) Export one Excel file with multiple sheets for each jobcode.
    run_jobcode_option = "separate"
    if run_jobcode_option == "separate":
        single_output_file = os.path.join(output_directory, "merged_with_jobcodes.xlsx")
        with pd.ExcelWriter(single_output_file, engine="xlsxwriter") as writer:
            jobcode_dfs = {jc: merged_df[merged_df['jobcode_2'] == jc] for jc in merged_df['jobcode_2'].unique()}
            for jc, df_ in jobcode_dfs.items():
                safe_jc = sanitize_filename(jc)[:31]
                df_.to_excel(writer, sheet_name=safe_jc, index=False)
        print_green("Exported single Excel file with multiple sheets for each jobcode_2 -> " + single_output_file)
    elif run_jobcode_option == "direct":
        jobcode_dict = {jc: merged_df[merged_df['jobcode_2'] == jc] for jc in merged_df['jobcode_2'].unique()}
        print_green("Created dictionary of filtered DataFrames for each unique jobcode_2 for direct use.")
        print_green("Unique jobcode_2 values: " + str(list(jobcode_dict.keys())))
    
    # 9) Save final data globally for callbacks
    global_merged_df = merged_df.copy()
    global_merged_df['jobcode_2'] = global_merged_df['jobcode_2'].apply(
        lambda x: f"{float(x):.2f}" if pd.notnull(x) and isinstance(x, (int, float, np.number)) else str(x).strip()
    )
    global_projects_df = df_projects.copy()
    
    print_green("----- Merged DataFrame (final) -----")
    print_green(str(merged_df.head()))
    print_green("----- Projects DataFrame (Contracted Projects) -----")
    print_green(str(df_projects.head()))
    
    # 10) Export a backup file with all key dataframes.
    export_data_safety()
    
    return merged_df

processed_df = main()
print_green("global_merged_df shape: " + str(global_merged_df.shape))
print_green("global_projects_df shape: " + str(global_projects_df.shape))
print_green("global_invoices shape: " + str(global_invoices.shape))
# ===== SET UP THE DASH APP WITH TABS =====
app = dash.Dash(__name__)

# ===== CALLBACK FOR SERVICE ITEM DETAILS TABLE =====
@app.callback(
    [Output('service-item-table', 'data'),
     Output('service-item-table', 'columns')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_service_item_table(selected_jobcode, selected_years):
    print_green("Inside update_service_item_table callback...")
    print_green(f"Selected jobcode: {selected_jobcode}")
    print_green(f"Selected years: {selected_years}")
    if selected_jobcode is None:
        print_green("No jobcode selected, returning empty.")
        return [], []
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    print_green("Filtered shape: " + str(df_filtered.shape))
    print_green("Columns in filtered df: " + str(df_filtered.columns.tolist()))
    service_item_col = None
    for col in df_filtered.columns:
        # Use a flexible check (remove underscores and spaces)
        if col.lower().replace("_", " ").strip() == "service item":
            service_item_col = col
            break
    if service_item_col is None:
        print_green("Service item column not found in filtered data. Available columns:")
        print_green(str(df_filtered.columns.tolist()))
        return [], []
    grouped = df_filtered.groupby(service_item_col, as_index=False).agg({'hours': 'sum', 'day_cost': 'sum'})
    grouped['day_cost'] = grouped['day_cost'].apply(lambda x: f"${x:,.2f}")
    grouped['hours'] = grouped['hours'].apply(lambda x: f"{x:.2f}")
    columns = [
        {'name': 'Service Item', 'id': service_item_col},
        {'name': 'Total Hours', 'id': 'hours'},
        {'name': 'Total Cost', 'id': 'day_cost'}
    ]
    data = grouped.to_dict('records')
    return data, columns






# ===== DASHBOARD LAYOUT WITH TABS =====
app.layout = dcc.Tabs(id='tabs-example', value='tab-dashboard', children=[
    dcc.Tab(label='Dashboard', value='tab-dashboard', children=[
        html.Div([
            # Logo at the top.
            html.Div([html.Img(src='data:image/png;base64,{}'.format(encoded_logo), style={'height': '75px'})],
                     style={'textAlign': 'center', 'padding': '10px'}),
            html.H1("Project Performance", style={'textAlign': 'center'}),
            # Filter section for project details.
            html.Div([
                html.H3("Filter Jobcodes by Project Details", style={'textAlign': 'center'}),
                dcc.Dropdown(
                    id='filter-clients',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Clients'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Clients"
                ),
                dcc.Dropdown(
                    id='filter-type',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Type'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Type"
                ),
                dcc.Dropdown(
                    id='filter-status',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Status'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Status"
                ),
                dcc.Dropdown(
                    id='filter-service',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Service Line'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Service Line"
                ),
                dcc.Dropdown(
                    id='filter-market',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Market Segment'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Market Segment"
                ),
                dcc.Dropdown(
                    id='filter-pm',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['PM'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select PM"
                )
            ], style={'width': '80%', 'margin': 'auto', 'padding': '20px', 'textAlign': 'center'}),
            # Jobcode selection dropdown.
            html.Div([
                html.Label("Select Jobcode:"),
                dcc.Dropdown(
                    id='jobcode-dropdown',
                    options=[],  # Updated via callback.
                    clearable=False
                )
            ], style={'width': '30%', 'margin': 'auto'}),
            # Year selection dropdown.
            html.Div([
                html.Div([
                    html.Label("Select Year(s):"),
                    dcc.Dropdown(
                        id='year-dropdown',
                        options=[
                            {'label': '2022', 'value': '2022'},
                            {'label': '2023', 'value': '2023'},
                            {'label': '2024', 'value': '2024'},
                            {'label': '2025', 'value': '2025'}
                        ],
                        value=['2024', '2025'],
                        multi=True,
                        clearable=False
                    )
                ], style={'width': '30%', 'margin': 'auto'})
            ], style={'textAlign': 'center', 'paddingBottom': '20px'}),
            # Project description and award date placeholders.
            html.Div(id='project-description', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
            html.Div(id='award-date', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
            # Two tables for project details and cost/contract details.
            html.Div([
                html.Div([
                    html.H2("Project Details", style={'textAlign': 'center'}),
                    dash_table.DataTable(
                        id='project-table-left',
                        columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],
                        data=[],
                        style_table=TABLE_STYLE,
                        style_cell=TABLE_CELL_STYLE,
                        style_cell_conditional=TABLE_CELL_CONDITIONAL
                    )
                ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '10px 10px 10px 20px'}),
                html.Div([
                    html.H2("Cost & Contract Details", style={'textAlign': 'center'}),
                    dash_table.DataTable(
                        id='project-table-right',
                        columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],
                        data=[],
                        style_table=TABLE_STYLE,
                        style_cell=TABLE_CELL_STYLE,
                        style_cell_conditional=TABLE_CELL_CONDITIONAL,
                        style_data_conditional=RIGHT_TABLE_RED_STYLE
                    )
                ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '10px 10px 10px 20px'})
            ], style={'textAlign': 'center'}),
            # New Service Item Details Table.
            html.H2("Service Item Details", style={'textAlign': 'center', 'paddingTop': '20px'}),
            html.Div(
                dash_table.DataTable(
                    id='service-item-table',
                    columns=[],  # Updated via callback.
                    data=[],
                    style_table=TABLE_STYLE,
                    style_cell=TABLE_CELL_STYLE,
                    style_cell_conditional=TABLE_CELL_CONDITIONAL
                ),
                style={'width': '60%', 'margin': '0 auto'}
            ),
            #ppie chart for service items
            
            
            html.Div([
                html.H2("Total Hours per Service Item", style={'textAlign': 'center'}),
                dcc.Graph(id='service-hours-pie-chart', style={'height': '300px'})
            ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'}),
            html.Div([
                html.H2("Total Cost per Service Item", style={'textAlign': 'center'}),
                dcc.Graph(id='service-cost-pie-chart', style={'height': '300px'})
            ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'}),

            
            
            
            
            
            # Pie charts for time and cost distributions.
            html.H2("Time Distribution by Employee", style={'textAlign': 'center', 'paddingTop': '20px'}),
            html.Div(dcc.Graph(id='pie-chart'), style={'width': '60%', 'margin': '0 auto'}),
            html.Div([
                html.H2("Cost Distribution by Employee", style={'textAlign': 'center'}),
                html.Div(dcc.Graph(id='cost-pie-chart'), style={'width': '60%', 'margin': '0 auto'})
            ], style={'textAlign': 'center', 'paddingTop': '20px'})
        ])
    ]),
    dcc.Tab(label='Add New Project', value='tab-add', children=[
        html.Div([
            html.H3("Add a New Project", style={'textAlign': 'center'}),
            html.Div([
                html.Label("Project No:"),
                dcc.Input(id='input-project-no', type='text', placeholder='Project No')
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Status:"),
                dcc.Dropdown(
                    id='input-status-dropdown',
                    options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Status'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Status",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-status-other', type='text', placeholder='Enter new Status'),
                    id='status-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Type:"),
                dcc.Dropdown(
                    id='input-type-dropdown',
                    options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Type'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Type",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-type-other', type='text', placeholder='Enter new Type'),
                    id='type-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Service Line:"),
                dcc.Dropdown(
                    id='input-service-line-dropdown',
                    options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Service Line'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Service Line",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-service-line-other', type='text', placeholder='Enter new Service Line'),
                    id='service-line-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Market Segment:"),
                dcc.Dropdown(
                    id='input-market-dropdown',
                    options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Market Segment'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Market Segment",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-market-other', type='text', placeholder='Enter new Market Segment'),
                    id='market-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Project Manager (PM):"),
                dcc.Dropdown(
                    id='input-pm-dropdown',
                    options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['PM'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select PM",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-pm-other', type='text', placeholder='Enter new PM'),
                    id='pm-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Project Description:"),
                dcc.Input(id='input-project-description', type='text', placeholder='Project Description', style={'width': '100%'})
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("No.:"),
                dcc.Input(id='input-no', type='text', placeholder='No.')
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Clients:"),
                dcc.Dropdown(
                    id='input-clients-dropdown',
                    options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Clients'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Clients",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-clients-other', type='text', placeholder='Enter new Clients'),
                    id='clients-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Award Date (YYYY-MM-DD):"),
                dcc.Input(id='input-award-date', type='text', placeholder='Award Date')
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Contracted Amount:"),
                dcc.Input(id='input-contracted-amount', type='number', placeholder='Contracted Amount')
            ], style={'margin-bottom': '10px'}),
            html.Button("Add Project", id='submit-new-project'),
            html.Div(id='new-project-message', style={'margin-top': '10px', 'color': 'blue'})
        ], style={'padding': '20px', 'textAlign': 'center'})
    ])
])

# ===== CALLBACKS FOR "OTHER" DROPDOWN TOGGLE =====
@app.callback(Output('status-other-div', 'style'), [Input('input-status-dropdown', 'value')])
def toggle_status_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('type-other-div', 'style'), [Input('input-type-dropdown', 'value')])
def toggle_type_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('service-line-other-div', 'style'), [Input('input-service-line-dropdown', 'value')])
def toggle_service_line_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('market-other-div', 'style'), [Input('input-market-dropdown', 'value')])
def toggle_market_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('pm-other-div', 'style'), [Input('input-pm-dropdown', 'value')])
def toggle_pm_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('clients-other-div', 'style'), [Input('input-clients-dropdown', 'value')])
def toggle_clients_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}


# callback for updating service item details pie charts (by hours and by cost)
def update_service_item_pie_charts(selected_jobcode, selected_years):
    if selected_jobcode is None:
        return {}, {}
    
    # Filter data by selected jobcode and years
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    
    # Find the "service item" column (flexible check as before)
    service_item_col = None
    for col in df_filtered.columns:
        if col.lower().replace("_", " ").strip() == "service item":
            service_item_col = col
            break
    if service_item_col is None:
        return {}, {}
    
    # Group data by service item to aggregate hours and day_cost
    grouped = df_filtered.groupby(service_item_col, as_index=False).agg({'hours': 'sum', 'day_cost': 'sum'})
    
    # Create pie chart for total hours per service item
    fig_hours = px.pie(
        grouped,
        names=service_item_col,
        values='hours',
        title="Total Hours per Service Item"
    )
    fig_hours.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
    
    # Create pie chart for total cost per service item
    fig_cost = px.pie(
        grouped,
        names=service_item_col,
        values='day_cost',
        title="Total Cost per Service Item"
    )
    fig_cost.update_traces(hovertemplate='<b>%{label}</b><br>Cost: $%{value:,.2f}<extra></extra>')
    
    return fig_hours, fig_cost

@app.callback(
    [Output('service-hours-pie-chart', 'figure'),
     Output('service-cost-pie-chart', 'figure')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)


# ===== CALLBACK FOR SUBMITTING A NEW PROJECT =====
@app.callback(
    Output('new-project-message', 'children'),
    [Input('submit-new-project', 'n_clicks')],
    [
        State('input-project-no', 'value'),
        State('input-status-dropdown', 'value'),
        State('input-status-other', 'value'),
        State('input-type-dropdown', 'value'),
        State('input-type-other', 'value'),
        State('input-service-line-dropdown', 'value'),
        State('input-service-line-other', 'value'),
        State('input-market-dropdown', 'value'),
        State('input-market-other', 'value'),
        State('input-project-description', 'value'),
        State('input-no', 'value'),
        State('input-clients-dropdown', 'value'),
        State('input-clients-other', 'value'),
        State('input-award-date', 'value'),
        State('input-contracted-amount', 'value'),
        State('input-pm-dropdown', 'value'),
        State('input-pm-other', 'value')
    ]
)
def add_new_project(n_clicks, proj_no, status_dd, status_other, type_dd, type_other,
                    service_line_dd, service_line_other, market_dd, market_other,
                    proj_desc, no_val, clients_dd, clients_other, award_date,
                    contracted_amt, pm_dd, pm_other):
    if not n_clicks:
        return ""
    status_val = status_other if status_dd == 'Other' else status_dd
    type_val = type_other if type_dd == 'Other' else type_dd
    service_line_val = service_line_other if service_line_dd == 'Other' else service_line_dd
    market_val = market_other if market_dd == 'Other' else market_dd
    clients_val = clients_other if clients_dd == 'Other' else clients_dd
    pm_val = pm_other if pm_dd == 'Other' else pm_dd
    new_project = {
        "Project No": standardize_project_no(proj_no) if proj_no else "",
        "Status": status_val if status_val else "",
        "Type": type_val if type_val else "",
        "Service Line": service_line_val if service_line_val else "",
        "Market Segment": market_val if market_val else "",
        "Project Description": proj_desc if proj_desc else "",
        "No.": no_val if no_val else "",
        "Clients": clients_val if clients_val else "",
        "Award Date": award_date if award_date else "",
        "Contracted Amount": f"${float(contracted_amt):,.2f}" if contracted_amt else "",
        "PM": pm_val if pm_val else ""
    }
    global global_projects_df
    global_projects_df = pd.concat([global_projects_df, pd.DataFrame([new_project])], ignore_index=True)
    print_green("New project added:")
    print_green(str(new_project))
    export_data_safety()
    return "New project added successfully and backup updated!"

# ===== CALLBACK FOR SERVICE ITEM DETAILS TABLE =====


# ===== EXISTING DASHBOARD CALLBACKS =====
@app.callback(
    Output('jobcode-dropdown', 'options'),
    [Input('filter-clients', 'value'),
     Input('filter-type', 'value'),
     Input('filter-status', 'value'),
     Input('filter-service', 'value'),
     Input('filter-market', 'value'),
     Input('filter-pm', 'value')]
)
def update_jobcode_options(filter_clients, filter_type, filter_status, filter_service, filter_market, filter_pm):
    filtered_projects = global_projects_df.copy()
    if filter_clients:
        filtered_projects = filtered_projects[filtered_projects['Clients'].isin(filter_clients)]
    if filter_type:
        filtered_projects = filtered_projects[filtered_projects['Type'].isin(filter_type)]
    if filter_status:
        filtered_projects = filtered_projects[filtered_projects['Status'].isin(filter_status)]
    if filter_service:
        filtered_projects = filtered_projects[filtered_projects['Service Line'].isin(filter_service)]
    if filter_market:
        filtered_projects = filtered_projects[filtered_projects['Market Segment'].isin(filter_market)]
    if filter_pm:
        filtered_projects = filtered_projects[filtered_projects['PM'].isin(filter_pm)]
    valid_projects = filtered_projects['Project No'].unique()
    valid_jobcodes = global_merged_df[global_merged_df['jobcode_2'].apply(lambda x: extract_project_no(x) in valid_projects)]
    jobcode_values = valid_jobcodes['jobcode_2'].unique()
    options = [{'label': jc, 'value': jc} for jc in sorted(jobcode_values)]
    return options

@app.callback(
    Output('award-date', 'children'),
    [Input('jobcode-dropdown', 'value')]
)
def update_award_date(selected_jobcode):
    if selected_jobcode is None:
        return ""
    extracted_code = extract_project_no(selected_jobcode)
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    if not filtered.empty:
        project_record = filtered.iloc[0]
        award_date_raw = project_record.get('Award Date', "No Award Date Available")
        try:
            award_date = pd.to_datetime(award_date_raw)
            formatted_date = award_date.strftime("%d %B %Y")
        except Exception:
            formatted_date = str(award_date_raw)
        return html.Div([html.B("Award Date:"), " " + formatted_date])
    return "No Award Date Found."

@app.callback(
    Output('project-description', 'children'),
    [Input('jobcode-dropdown', 'value')]
)
def update_project_description(selected_jobcode):
    if selected_jobcode is None:
        return ""
    extracted_code = extract_project_no(selected_jobcode)
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    if not filtered.empty:
        project_record = filtered.iloc[0]
        description = project_record.get('Project Description', "No Description Available")
        return html.Div([html.B("Project Description:"), " " + str(description)])
    return "No Project Description Found."

@app.callback(
    Output('pie-chart', 'figure'),
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_pie_chart(selected_jobcode, selected_years):
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    if set(selected_years) == {"2024"}:
        value_col = 'total_hours_24'
    elif set(selected_years) == {"2025"}:
        value_col = 'total_hours_25'
    else:
        df_filtered['combined_total_hours'] = df_filtered['total_hours_24'].fillna(0) + df_filtered['total_hours_25'].fillna(0)
        value_col = 'combined_total_hours'
    grouped = df_filtered.groupby('Employee', as_index=False)[value_col].sum()
    total_hours = grouped[value_col].sum()
    fig = px.pie(
        grouped,
        names='Employee',
        values=value_col,
        title=f"Percentage of Hours by Employee for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Hours:</b> {total_hours:.2f}"
    )
    fig.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
    fig.update_layout(title={'x': 0.5}, legend=dict(orientation="v", x=1.1, y=0.5, xanchor="left", yanchor="middle"))
    return fig

@app.callback(
    [Output('cost-pie-chart', 'figure')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_cost_pie_chart(selected_jobcode, selected_years):
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    grouped = df_filtered.groupby('Employee', as_index=False)['day_cost'].sum()
    total_cost = grouped['day_cost'].sum()
    fig = px.pie(
        grouped,
        names='Employee',
        values='day_cost',
        title=f"Cost Distribution by Employee for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Cost:</b> ${total_cost:,.2f}"
    )
    fig.update_layout(title={'x': 0.5}, legend=dict(orientation="v", x=1.1, y=0.5, xanchor="left", yanchor="middle"))
    fig.update_traces(hovertemplate='<b>%{label}</b><br>Employee Cost: %{value:$,.2f}<extra></extra>')
    return [fig]

@app.callback(
    [Output('project-table-left', 'data'),
     Output('project-table-left', 'columns'),
     Output('project-table-right', 'data'),
     Output('project-table-right', 'columns')],
    [Input('jobcode-dropdown', 'value')]
)
def update_project_tables(selected_jobcode):
    if selected_jobcode is None:
        return [], [], [], []
    extracted_code = extract_project_no(selected_jobcode)
    print_green("Selected jobcode (full): " + selected_jobcode)
    print_green("Extracted (first 7 chars): " + extracted_code)
    print_green("Global Projects DF 'Project No' sample: " + str(global_projects_df['Project No'].head()))
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    print_green("Filtered projects:\n" + str(filtered))
    if not filtered.empty:
        project_record = filtered.iloc[0]
        left_fields = ['Clients', 'Type', 'Status', 'Service Line', 'Market Segment', 'PM']
        left_available = [col for col in left_fields if col in filtered.columns]
        left_df = pd.DataFrame(list(project_record[left_available].items()), columns=['Field', 'Value'])
        project_no = project_record['Project No']
        invoice_row = global_invoices[global_invoices['Project No'] == project_no]
        if not invoice_row.empty:
            total_invoice_val = invoice_row['TotalInvoice'].iloc[0]
        else:
            total_invoice_val = 0
        df_cost = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode]
        total_cost = df_cost['day_cost'].sum()
        contracted_amount = project_record['Contracted Amount'] if 'Contracted Amount' in filtered.columns else None
        remaining_to_invoice = (contracted_amount - total_invoice_val) if (contracted_amount is not None) else None
        er_contract = contracted_amount / total_cost if total_cost != 0 and contracted_amount is not None else None
        er_invoiced = total_invoice_val / total_cost if total_cost != 0 else None
        right_data = {
            'Contracted Amount': contracted_amount,
            'Total Invoice': total_invoice_val,
            'Remaining to be invoiced': remaining_to_invoice,
            'Total Cost': total_cost,
            'ER Contract (Temporarily Unavailable)': er_contract,
            'ER Invoiced (Temporarily Unavailable)': er_invoiced
        }
        formatted_right_data = {}
        for key, value in right_data.items():
            if value is not None and isinstance(value, (int, float)):
                if 'ER Contract' in key or 'ER Invoiced' in key:
                    formatted_right_data[key] = f"{value:.2f}"
                else:
                    formatted_right_data[key] = f"${value:,.2f}"
            else:
                formatted_right_data[key] = value
        right_df = pd.DataFrame(list(formatted_right_data.items()), columns=['Field', 'Value'])
        left_columns = [{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}]
        right_columns = [{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}]
        return left_df.to_dict('records'), left_columns, right_df.to_dict('records'), right_columns
    print_green("No matching project found for extracted jobcode: " + extracted_code)
    return [], [], [], []

if __name__ == '__main__':
    app.run_server(debug=True, host='10.1.2.111', port=7050, use_reloader=False)
