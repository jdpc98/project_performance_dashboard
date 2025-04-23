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
global_employee_cost_df = None  # in case we need it later

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in file names."""
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
    """Extract the first 7 characters from the jobcode string."""
    return str(jobcode_str)[:7].strip()

def load_primary_data(file_path):
    """
    Load DataFrames from the primary Excel file.
    Expected sheet names:
      - 'df1' -> used for df_trm_conv
      - 'df2' -> used for df_rates_24_25
      - 'df3' -> used for df_rates_22_23
      - 'df4' -> used for df_loaded_rates
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
            ym = f"{year}JUL (1-15)" if dt.day <= 15 else f"{year}JUL (15-31)"
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
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    
    # Mapping from df_rates_24_25: Personel -> ID#
    mapping = df_rates_24_25.set_index('Personel')['ID#'].to_dict()
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    mapped = mapped.astype(df_rates_24_25['ID#'].dtype)
    df_new.loc[mask, 'correct_number'] = mapped
    
    # Merge using df_rates_24_25's 'ID#' and df_new's 'correct_number'
    merged_df = pd.merge(df_rates_24_25, df_new, left_on='ID#', right_on='correct_number', how='inner')
    
    # === Import Data from the Third File (Contracted Projects) ===
    third_file = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    df_projects = pd.read_excel(third_file, sheet_name='4_Contracted Projects', header=0)
    df_projects.columns = df_projects.columns.str.strip()
    if 'Project No' not in df_projects.columns:
        df_projects.rename(columns={df_projects.columns[0]: 'Project No'}, inplace=True)
    df_projects['Project No'] = df_projects['Project No'].apply(standardize_project_no)
    
    # === Ensure Output Directory Exists ===
    output_directory = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Export initial merged DataFrame.
    output_path_initial = os.path.join(output_directory, "merged_output.xlsx")
    merged_df.to_excel(output_path_initial, index=False)
    print(f"Merged DataFrame exported successfully to {output_path_initial}")
    
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)
    output_path_updated = os.path.join(output_directory, "merged_with_day_cost.xlsx")
    merged_df.to_excel(output_path_updated, index=False)
    print(f"Updated DataFrame with day_cost and total hours exported successfully to {output_path_updated}")
    
    run_jobcode_option = "separate"
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
    
    global_merged_df = merged_df.copy()
    global_merged_df['jobcode_2'] = global_merged_df['jobcode_2'].apply(
        lambda x: f"{float(x):.2f}" if pd.notnull(x) and isinstance(x, (int, float, np.number)) else str(x).strip()
    )
    
    global_projects_df = df_projects.copy()
    
    print("----- Merged DataFrame (final) -----")
    print(merged_df.head())
    print("----- Projects DataFrame (Contracted Projects) -----")
    print(df_projects.head())
    
    return merged_df

processed_df = main()

app = dash.Dash(__name__)

jobcode_options = [{'label': jc, 'value': jc} for jc in global_merged_df['jobcode_2'].unique()]
year_options = [{'label': '2024', 'value': '2024'}, {'label': '2025', 'value': '2025'}]
personnel_options = [{'label': p, 'value': p} for p in sorted(global_merged_df['Personel'].unique())]

app.layout = html.Div([
    html.H1("Jobcode Hours and Project Status Visualization", style={'textAlign': 'center'}),
    html.Div([
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
        ], style={'width': '30%', 'display': 'inline-block', 'marginLeft': '2%'})
    ], style={'textAlign': 'center'}),
    html.Div([
        html.Div([
            html.H2("Project Details for Selected Jobcode", style={'textAlign': 'center'}),
            # Left table: transposed details for descriptive fields.
            dash_table.DataTable(
                id='project-table-left',
                columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],
                data=[],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'}
            )
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '0 auto'}),
        html.Div([
            html.H2("Cost & Contract Details", style={'textAlign': 'center'}),
            dash_table.DataTable(
                id='project-table-right',
                columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],
                data=[],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left'}
            )
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '0 auto'})
    ], style={'textAlign': 'center'}),
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
    grouped = df_filtered.groupby('Personel', as_index=False)[value_col].sum()
    fig = px.pie(
        grouped,
        names='Personel',
        values=value_col,
        title=f"Percentage of Hours by Personel for Jobcode: {selected_jobcode}"
    )
    fig.update_layout(
        title={'x': 0.5},
        legend=dict(
            orientation="v",
            x=1.1,
            y=0.5,
            xanchor="left",
            yanchor="middle"
        )
    )
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
    grouped = df_filtered.groupby('Personel', as_index=False)['day_cost'].sum()
    total_cost = grouped['day_cost'].sum()
    fig = px.pie(
        grouped,
        names='Personel',
        values='day_cost',
        title=f"Cost Distribution by Personel for Jobcode: {selected_jobcode}<br>Total Cost: ${total_cost:,.2f}"
    )
    fig.update_layout(
        title={'x': 0.5},
        legend=dict(
            orientation="v",
            x=1.1,
            y=0.5,
            xanchor="left",
            yanchor="middle"
        )
    )
    fig.update_traces(hovertemplate='<b>%{label}</b><br>employee_cost: %{value:$,.2f}<extra></extra>')
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
    print("Selected jobcode (full):", selected_jobcode)
    print("Extracted (first 7 chars):", extracted_code)
    print("Global Projects DF 'Project No' sample:", global_projects_df['Project No'].head())
    
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    print("Filtered projects:\n", filtered)
    if not filtered.empty:
        # We'll assume one record per jobcode.
        project_record = filtered.iloc[0]
        # Left table: desired fields.
        left_fields = ['Clients', 'Type', 'Status', 'Service Line', 'Market Segment', 'Project Manager']
        left_data = {field: project_record.get(field, None) for field in left_fields if field in filtered.columns}
        left_df = pd.DataFrame(list(left_data.items()), columns=['Field', 'Value'])
        
        # Right table: "Contracted Amount" from projects and computed "Total Cost" from merged data.
        df_cost = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode]
        total_cost = df_cost['day_cost'].sum()
        contracted_amount = project_record.get('Contracted Amount', None) if 'Contracted Amount' in filtered.columns else None
        right_data = {'Contracted Amount': contracted_amount, 'Total Cost': total_cost}
        right_df = pd.DataFrame(list(right_data.items()), columns=['Field', 'Value'])
        
        left_columns = [{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}]
        right_columns = [{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}]
        return left_df.to_dict('records'), left_columns, right_df.to_dict('records'), right_columns
    print("No matching project found for extracted jobcode:", extracted_code)
    return [], [], [], []

if __name__ == '__main__':
    app.run_server(debug=True, host='10.1.2.154', port=7050, use_reloader=False)
