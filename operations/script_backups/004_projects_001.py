import os
import re
import base64
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
import warnings

# Suppress all warnings (you can later limit this if desired)
warnings.simplefilter("ignore")

# Global variables for use in Dash callbacks.
global_merged_df = None
global_projects_df = None
global_employee_cost_df = None  # In case we need it later

# --- Style Snippet for Tables ---
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

# Helper function for green terminal prints.
def print_green(message):
    print("\033[92m" + message + "\033[0m")

# Load and encode the logo image.
logo_path = r"C:\Users\jose.pineda\Desktop\operations\visual_content\logo_1.png"
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

# --- Ingestion Functions for the "Rates" Sheet ---

def trm_ingestion(rates_df):
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
    df_rates = rates_df.copy()
    df_rates = df_rates.drop(df_rates.index[0:7])
    df_rates = df_rates.drop(df_rates.columns[29:], axis=1)
    
    df_dates = rates_df.iloc[4:6, 4:29].copy()
    df_dates.ffill(axis=1, inplace=True)
    df_dates.loc['concat_cont'] = df_dates.loc[4].astype(str) + df_dates.loc[5].astype(str)
    # Prepend constant columns to match the final number of columns
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

# --- Calculation Functions ---
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
    return merged_df

def assign_total_hours(merged_df):
    merged_df['total_hours_24'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2024)
    merged_df['total_hours_25'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2025)
    return merged_df

# --- Dynamic Loader for the Projects File ---
def load_third_file_dynamic(third_file):
    df_raw = pd.read_excel(third_file, sheet_name='4_Contracted Projects', header=None, engine='openpyxl')
    nrows = len(df_raw)
    end_row = None
    for i in range(630, nrows - 1):
        if pd.isna(df_raw.iloc[i, 1]) and pd.isna(df_raw.iloc[i+1, 1]):
            end_row = i
            break
    if end_row is None:
        end_row = nrows
    df_trunc = df_raw.iloc[:end_row].copy()
    header = [str(col).strip() for col in df_trunc.iloc[0].tolist()]
    df_data = df_trunc.iloc[1:].copy()
    df_data = df_data[~df_data.apply(lambda row: list(row.astype(str).str.strip()) == header, axis=1)]
    df_data.columns = header
    df_data.columns = [col.strip() for col in df_data.columns]
    if "Project No" not in df_data.columns:
        first_col = df_data.columns[0]
        df_data.rename(columns={first_col: "Project No"}, inplace=True)
    df_data["Project No"] = df_data["Project No"].astype(str).str.strip().apply(standardize_project_no)
    return df_data.reset_index(drop=True)

# --- Dashboard Main Pipeline ---
def main():
    global global_merged_df, global_projects_df
    rates_file_path = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    df_trm_vals, df_actual_rates, loaded_c, loaded_rates = load_rates_from_single_sheet(rates_file_path)
    
    second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    df_new = pd.read_csv(second_file, header=0, index_col=0)
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    
    mapping = df_actual_rates.set_index('Employee')['ID#'].to_dict()
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    df_new.loc[mask, 'correct_number'] = mapped.astype(np.int64)
    
    merged_df = pd.merge(df_actual_rates, df_new, left_on='ID#', right_on='correct_number', how='inner')
    
    third_file = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    df_projects = load_third_file_dynamic(third_file)
    
    output_directory = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    output_path_initial = os.path.join(output_directory, "merged_output.xlsx")
    merged_df.to_excel(output_path_initial, index=False)
    print_green(f"Merged DataFrame exported successfully to {output_path_initial}")
    
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)
    output_path_updated = os.path.join(output_directory, "merged_with_day_cost.xlsx")
    merged_df.to_excel(output_path_updated, index=False)
    print_green(f"Updated DataFrame with day_cost and total hours exported successfully to {output_path_updated}")
    
    run_jobcode_option = "separate"
    if run_jobcode_option == "separate":
        jobcode_dfs = {jc: merged_df[merged_df['jobcode_2'] == jc] for jc in merged_df['jobcode_2'].unique()}
        for jc, df_ in jobcode_dfs.items():
            safe_jc = sanitize_filename(jc)
            output_file = os.path.join(output_directory, f"merged_{safe_jc}.xlsx")
            df_.to_excel(output_file, index=False)
        print_green("Exported separate DataFrames for each unique jobcode_2.")
    elif run_jobcode_option == "direct":
        jobcode_dict = {jc: merged_df[merged_df['jobcode_2'] == jc] for jc in merged_df['jobcode_2'].unique()}
        print_green("Created dictionary of filtered DataFrames for each unique jobcode_2 for direct use.")
        print_green("Unique jobcode_2 values: " + str(list(jobcode_dict.keys())))
    
    global_merged_df = merged_df.copy()
    global_merged_df['jobcode_2'] = global_merged_df['jobcode_2'].apply(
        lambda x: f"{float(x):.2f}" if pd.notnull(x) and isinstance(x, (int, float, np.number)) else str(x).strip()
    )
    
    global_projects_df = df_projects.copy()
    
    print_green("----- Merged DataFrame (final) -----")
    print_green(str(merged_df.head()))
    print_green("----- Projects DataFrame (Contracted Projects) -----")
    print_green(str(df_projects.head()))
    
    return merged_df

processed_df = main()

app = dash.Dash(__name__)

# Layout with filter dropdowns for project details and jobcode.
app.layout = html.Div([
    html.Div([
        html.Img(src='data:image/png;base64,{}'.format(encoded_logo), style={'height': '75px'})
    ], style={'textAlign': 'center', 'padding': '10px'}),
    html.H1("Project Performance", style={'textAlign': 'center'}),
    html.Div([
        html.H3("Filter Jobcodes by Project Details", style={'textAlign': 'center'}),
        dcc.Dropdown(
            id='filter-clients',
            options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Clients'].dropna().unique(), key=lambda x: str(x))],
            multi=True,
            placeholder="Select Clients"
        ),
        dcc.Dropdown(
            id='filter-type',
            options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Type'].dropna().unique(), key=lambda x: str(x))],
            multi=True,
            placeholder="Select Type"
        ),
        dcc.Dropdown(
            id='filter-status',
            options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Status'].dropna().unique(), key=lambda x: str(x))],
            multi=True,
            placeholder="Select Status"
        ),
        dcc.Dropdown(
            id='filter-service',
            options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Service Line'].dropna().unique(), key=lambda x: str(x))],
            multi=True,
            placeholder="Select Service Line"
        ),
        dcc.Dropdown(
            id='filter-market',
            options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['Market Segment'].dropna().unique(), key=lambda x: str(x))],
            multi=True,
            placeholder="Select Market Segment"
        ),
        dcc.Dropdown(
            id='filter-pm',
            options=[{'label': str(val), 'value': str(val)} for val in sorted(global_projects_df['PM'].dropna().unique(), key=lambda x: str(x))],
            multi=True,
            placeholder="Select PM"
        )
    ], style={'width': '80%', 'margin': 'auto', 'padding': '20px', 'textAlign': 'center'}),
    html.Div([
        html.Label("Select Jobcode:"),
        dcc.Dropdown(
            id='jobcode-dropdown',
            options=[],  # Updated via callback
            clearable=False
        )
    ], style={'width': '30%', 'margin': 'auto'}),
    html.Div([
        html.Div([
            html.Label("Select Year(s):"),
            dcc.Dropdown(
                id='year-dropdown',
                options=[{'label': '2024', 'value': '2024'}, {'label': '2025', 'value': '2025'}],
                value=['2024', '2025'],
                multi=True,
                clearable=False
            )
        ], style={'width': '30%', 'margin': 'auto'})
    ], style={'textAlign': 'center', 'paddingBottom': '20px'}),
    html.Div(id='project-description', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
    html.Div(id='award-date', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
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
    html.H2("Time Distribution by Personel", style={'textAlign': 'center', 'paddingTop': '20px'}),
    html.Div(
        dcc.Graph(id='pie-chart'),
        style={'width': '60%', 'margin': '0 auto'}
    ),
    html.Div([
        html.H2("Cost Distribution by Personel", style={'textAlign': 'center'}),
        html.Div(
            dcc.Graph(id='cost-pie-chart'),
            style={'width': '60%', 'margin': '0 auto'}
        )
    ], style={'textAlign': 'center', 'paddingTop': '20px'})
])

@app.callback(
    Output('jobcode-dropdown', 'options'),
    [
        Input('filter-clients', 'value'),
        Input('filter-type', 'value'),
        Input('filter-status', 'value'),
        Input('filter-service', 'value'),
        Input('filter-market', 'value'),
        Input('filter-pm', 'value')
    ]
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
    # NOTE: Using 'Employee' here because our rates ingestion now uses "Employee" as the identifier.
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
    # Group by "Employee" since our merged data uses that column.
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
        
        df_cost = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode]
        total_cost = df_cost['day_cost'].sum()
        contracted_amount = project_record['Contracted Amount'] if 'Contracted Amount' in filtered.columns else None
        total_invoice = 1000000  # constant value
        remaining_to_invoice = contracted_amount - total_invoice if contracted_amount is not None else None
        er_contract = contracted_amount / total_cost if total_cost != 0 and contracted_amount is not None else None
        er_invoiced = total_invoice / total_cost if total_cost != 0 else None
        right_data = {
            'Contracted Amount': contracted_amount,
            'Total Invoice (Temporarily Unavailable)': total_invoice,
            'Remaining to be invoiced (Temporarily Unavailable)': remaining_to_invoice,
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
    app.run_server(debug=True, host='10.1.2.154', port=7050, use_reloader=False)
