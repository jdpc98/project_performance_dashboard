import os
import re
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# Global variables for use in Dash callbacks.
global_merged_df = None
global_projects_df = None

def sanitize_filename(filename):
    """
    Remove or replace characters that are invalid in file names.
    """
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def standardize_project_no(x):
    """
    Attempt to convert x to a float and return a string formatted to two decimals.
    If conversion fails (e.g. for nonnumeric values like 'TOTAL'), return the stripped string.
    """
    try:
        return f"{float(x):.2f}"
    except Exception:
        return str(x).strip()

def extract_project_no(jobcode_str):
    """
    Extract the first 7 characters from the jobcode string.
    """
    return str(jobcode_str)[:7].strip()

def load_primary_data(file_path):
    """
    Load DataFrames from the primary Excel file.
    Expected sheet names:
      - 'df1'          -> used for df_trm_conv
      - 'df2'          -> used for df_rates_24_25
      - 'df3'          -> used for df_rates_22_23
      - 'df4'          -> used for df_loaded_rates
    """
    df_trm_conv = pd.read_excel(file_path, sheet_name='df1', header=0)
    df_rates_24_25 = pd.read_excel(file_path, sheet_name='df2', header=0)
    df_rates_22_23 = pd.read_excel(file_path, sheet_name='df3', header=0)
    df_loaded_rates = pd.read_excel(file_path, sheet_name='df4', header=0)
    return df_trm_conv, df_rates_24_25, df_rates_22_23, df_loaded_rates

def calculate_day_cost(merged_df):
    """
    For each row in the merged DataFrame:
      - Convert 'local_date' to datetime.
      - For July, if day <= 15 use "YYYYJUL (1-15)", else use "YYYYJUL (15-31)".
      - For other months, use format "YYYYMON" (e.g. "2024JAN").
      - Multiply the corresponding rate by 'hours' and store in 'day_cost'.
    """
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')
    
    def row_day_cost(row):
        dt = row['local_date']
        if pd.isnull(dt):
            return 0
        year = dt.year
        if dt.month == 7:
            if dt.day <= 15:
                ym = f"{year}JUL (1-15)"
            else:
                ym = f"{year}JUL (15-31)"
        else:
            ym = dt.strftime('%Y') + dt.strftime('%b').upper()
        rate = row[ym] if ym in merged_df.columns else 0
        return rate * row['hours']
    
    merged_df['day_cost'] = merged_df.apply(row_day_cost, axis=1)
    return merged_df

def assign_total_hours(merged_df):
    """
    For each row, if the 'local_date' year is 2024, assign the 'hours' value to 'total_hours_24';
    if 2025, assign to 'total_hours_25'.
    """
    merged_df['total_hours_24'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2024)
    merged_df['total_hours_25'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2025)
    return merged_df

def main():
    global global_merged_df, global_projects_df
    
    # === Import Data from the First File (Rates.xlsx) ===
    primary_file = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    df_trm_conv, df_rates_24_25, df_rates_22_23, df_loaded_rates = load_primary_data(primary_file)
    
    # === Import Data from the Second File (Timesheet CSV) ===
    second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    df_new = pd.read_csv(second_file, header=0, index_col=0)
    
    # Create a 'full_name' column in df_new.
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    
    # Create a mapping from df_rates_24_25: Personel -> ID#
    mapping = df_rates_24_25.set_index('Personel')['ID#'].to_dict()
    
    # Create a new column "correct_number" in df_new.
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    mapped = mapped.astype(df_rates_24_25['ID#'].dtype)
    df_new.loc[mask, 'correct_number'] = mapped
    
    # Merge using df_rates_24_25's 'ID#' and df_new's 'correct_number'
    merged_df = pd.merge(df_rates_24_25, df_new, left_on='ID#', right_on='correct_number', how='inner')
    
    # === Import Data from the Third File (Contracted Projects) ===
    third_file = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    # Read with header=0 (the first row is the header)
    df_projects = pd.read_excel(third_file, sheet_name='4_Contracted Projects', header=0)
    df_projects.columns = df_projects.columns.str.strip()  # Clean header names.
    # If "Project No" is not present, rename the first column to "Project No"
    if 'Project No' not in df_projects.columns:
        df_projects.rename(columns={df_projects.columns[0]: 'Project No'}, inplace=True)
    # Standardize the 'Project No' column.
    df_projects['Project No'] = df_projects['Project No'].apply(standardize_project_no)
    
    # (Optionally, you can add more fields to your table here if they exist in df_projects.)
    # For now we assume the header row already contains 'Status', 'Service Line', etc.
    
    # === Ensure Output Directory Exists ===
    output_directory = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Export the initial merged DataFrame.
    output_path_initial = os.path.join(output_directory, "merged_output.xlsx")
    merged_df.to_excel(output_path_initial, index=False)
    print(f"Merged DataFrame exported successfully to {output_path_initial}")
    
    # Calculate day_cost and assign total hours.
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)
    
    # Export the updated merged DataFrame.
    output_path_updated = os.path.join(output_directory, "merged_with_day_cost.xlsx")
    merged_df.to_excel(output_path_updated, index=False)
    print(f"Updated DataFrame with day_cost and total hours exported successfully to {output_path_updated}")
    
    # === Jobcode Workflow Options ===
    run_jobcode_option = "separate"  # "separate" to export files, "direct" for a dictionary.
    if run_jobcode_option == "separate":
        jobcode_dfs = {jc: merged_df[merged_df['jobcode_2'] == jc] for jc in merged_df['jobcode_2'].unique()}
        for jc, df in jobcode_dfs.items():
            safe_jc = sanitize_filename(jc)
            output_file = os.path.join(output_directory, f"merged_{safe_jc}.xlsx")
            df.to_excel(output_file, index=False)
        print("Exported separate DataFrames for each unique jobcode_2.")
    elif run_jobcode_option == "direct":
        jobcode_dict = {jc: merged_df[merged_df['jobcode_2'] == jc] for jc in merged_df['jobcode_2'].unique()}
        print("Created dictionary of filtered DataFrames for each unique jobcode_2 for direct use.")
        print("Unique jobcode_2 values:", list(jobcode_dict.keys()))
    
    # Standardize jobcode_2 in merged_df for matching.
    global_merged_df = merged_df.copy()
    global_merged_df['jobcode_2'] = global_merged_df['jobcode_2'].apply(
        lambda x: f"{float(x):.2f}" if pd.notnull(x) and isinstance(x, (int, float, np.number)) else str(x).strip()
    )
    
    # Store the projects DataFrame globally.
    global_projects_df = df_projects.copy()
    
    print("----- Merged DataFrame (final) -----")
    print(merged_df.head())
    print("----- Projects DataFrame (Contracted Projects) -----")
    print(df_projects.head())
    
    return merged_df

# Run data processing.
processed_df = main()

# === Dash App for Visualization ===
app = dash.Dash(__name__)

# Prepare dropdown options.
jobcode_options = [{'label': jc, 'value': jc} for jc in global_merged_df['jobcode_2'].unique()]
year_options = [{'label': '2024', 'value': '2024'}, {'label': '2025', 'value': '2025'}]
personnel_options = [{'label': p, 'value': p} for p in sorted(global_merged_df['Personel'].unique())]

app.layout = html.Div([
    html.H1("Jobcode Hours and Project Status Visualization"),
    html.Div([
        html.Label("Select Jobcode:"),
        dcc.Dropdown(
            id='jobcode-dropdown',
            options=jobcode_options,
            value=jobcode_options[0]['value'] if jobcode_options else None,
            clearable=False
        )
    ], style={'width': '30%', 'display': 'inline-block'}),
    html.Div([
        html.Label("Select Year(s):"),
        dcc.Dropdown(
            id='year-dropdown',
            options=year_options,
            value=['2024', '2025'],
            multi=True,
            clearable=False
        )
    ], style={'width': '30%', 'display': 'inline-block', 'marginLeft': '2%'}),
    html.Div([
        html.Label("Select Personnel (optional):"),
        dcc.Dropdown(
            id='personnel-dropdown',
            options=personnel_options,
            value=[p['value'] for p in personnel_options],
            multi=True,
            clearable=True
        )
    ], style={'width': '30%', 'display': 'inline-block', 'marginLeft': '2%'}),
    dcc.Graph(id='pie-chart'),
    html.H2("Project Details for Selected Jobcode"),
    dash_table.DataTable(
        id='project-table',
        # Now include additional fields in the table.
        columns=[{'name': 'Status', 'id': 'Status'},
                 {'name': 'Type', 'id': 'Type'},
                 {'name': 'Service Line', 'id': 'Service Line'},
                 {'name': 'Market Segment', 'id': 'Market Segment'},
                 {'name': 'Project Manager', 'id': 'Project Manager'},
                 {'name': 'Contracted Amount', 'id': 'Contracted Amount'},
                 {'name': 'Description', 'id': 'Description'},
                 {'name': 'Clients', 'id': 'Clients'}],
        data=[],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left'}
    )
])

@app.callback(
    Output('pie-chart', 'figure'),
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value'),
     Input('personnel-dropdown', 'value')]
)
def update_pie_chart(selected_jobcode, selected_years, selected_personnel):
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    if selected_personnel and len(selected_personnel) > 0:
        df_filtered = df_filtered[df_filtered['Personel'].isin(selected_personnel)]
    if set(selected_years) == {"2024"}:
        value_col = 'total_hours_24'
    elif set(selected_years) == {"2025"}:
        value_col = 'total_hours_25'
    else:
        df_filtered['combined_total_hours'] = df_filtered['total_hours_24'].fillna(0) + df_filtered['total_hours_25'].fillna(0)
        value_col = 'combined_total_hours'
    grouped = df_filtered.groupby('Personel', as_index=False)[value_col].sum()
    fig = px.pie(
        grouped,
        names='Personel',
        values=value_col,
        title=f"Percentage of Hours by Personel for Jobcode: {selected_jobcode}"
    )
    return fig

@app.callback(
    [Output('project-table', 'data'),
     Output('project-table', 'columns')],
    [Input('jobcode-dropdown', 'value')]
)
def update_project_table(selected_jobcode):
    if selected_jobcode is None:
        return [], []
    # Compare only the first 7 characters of the selected jobcode.
    extracted_code = extract_project_no(selected_jobcode)
    print("Selected jobcode (full):", selected_jobcode)
    print("Extracted (first 7 chars):", extracted_code)
    print("Global Projects DF 'Project No' sample:", global_projects_df['Project No'].head())
    
    # Filter projects DataFrame by comparing the first 7 characters.
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    print("Filtered projects:\n", filtered)
    
    # Define desired columns to display.
    desired_columns = ['Status', 'Type', 'Service Line', 'Market Segment', 
                       'Project Manager', 'Contracted Amount', 'Description', 'Clients']
    # Only include columns that exist in the DataFrame.
    available_columns = [col for col in desired_columns if col in filtered.columns]
    
    if not filtered.empty and available_columns:
        filtered = filtered[available_columns]
        columns = [{'name': col, 'id': col} for col in available_columns]
        data = filtered.to_dict('records')
        return data, columns
    else:
        print("No matching project found for extracted jobcode:", extracted_code)
        return [], []

if __name__ == '__main__':
    app.run_server(debug=True, host='10.1.2.154', port=7050, use_reloader=False)
