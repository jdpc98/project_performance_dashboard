import os
import re
import base64
import numpy as np
import pandas as pd
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px

# Global variables for use in Dash callbacks.
global_merged_df = None
global_projects_df = None
global_employee_cost_df = None  # In case we need it later

# --- Style Snippet for Tables ---
TABLE_STYLE = {
    'overflowX': 'auto',
    'width': '100%'
}
TABLE_CELL_STYLE = {
    'textAlign': 'left',
    'padding': '5px'
}
TABLE_CELL_CONDITIONAL = [
    {'if': {'column_id': 'Field'}, 'width': '40%'},
    {'if': {'column_id': 'Value'}, 'width': '60%'}
]
# Conditional styling based on data (using filter_query) for the right table.
RIGHT_TABLE_RED_STYLE = [
    {
        'if': {
            'filter_query': '{Field} = "Total Invoice"',
            'column_id': 'Value'
        },
        'color': 'red'
    },
    {
        'if': {
            'filter_query': '{Field} = "Remaining to be invoiced"',
            'column_id': 'Value'
        },
        'color': 'red'
    },
    {
        'if': {
            'filter_query': '{Field} = "ER Contract (Temporarily Unavailable)"',
            'column_id': 'Value'
        },
        'color': 'red'
    },
    {
        'if': {
            'filter_query': '{Field} = "ER Invoiced (Temporarily Unavailable)"',
            'column_id': 'Value'
        },
        'color': 'red'
    }
]

# Helper function for green terminal prints.
def print_green(message):
    print("\033[92m" + message + "\033[0m")

# Load and encode the logo image.
logo_path = r"C:\Users\jose.pineda\Desktop\operations\visual_content\logo_1.png"
encoded_logo = base64.b64encode(open(logo_path, 'rb').read()).decode('ascii')

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in file names."""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def standardize_project_no(x):
    """
    Attempt to convert x to a float and return a string formatted to two decimals.
    If conversion fails, return the stripped string.
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
    primary_file = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    df_trm_conv, df_rates_24_25, df_rates_22_23, df_loaded_rates = load_primary_data(primary_file)
    
    second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    df_new = pd.read_csv(second_file, header=0, index_col=0)
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    
    mapping = df_rates_24_25.set_index('Personel')['ID#'].to_dict()
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    df_new.loc[mask, 'correct_number'] = mapped.astype(np.int64)  # Explicit casting
    
    merged_df = pd.merge(df_rates_24_25, df_new, left_on='ID#', right_on='correct_number', how='inner')
    
    third_file = r"C:\Users\jose.pineda\Desktop\operations\2025 Project Log.xlsx"
    df_projects = pd.read_excel(third_file, sheet_name='4_Contracted Projects', header=0)
    df_projects.columns = df_projects.columns.str.strip()
    if 'Project No' not in df_projects.columns:
        df_projects.rename(columns={df_projects.columns[0]: 'Project No'}, inplace=True)
    df_projects['Project No'] = df_projects['Project No'].apply(standardize_project_no)
    
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
        for jc, df in jobcode_dfs.items():
            safe_jc = sanitize_filename(jc)
            output_file = os.path.join(output_directory, f"merged_{safe_jc}.xlsx")
            df.to_excel(output_file, index=False)
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

jobcode_options = [{'label': jc, 'value': jc} for jc in global_merged_df['jobcode_2'].unique()]
year_options = [{'label': '2024', 'value': '2024'}, {'label': '2025', 'value': '2025'}]
personnel_options = [{'label': p, 'value': p} for p in sorted(global_merged_df['Personel'].unique())]

app.layout = html.Div([
    # Logo at the top.
    html.Div([
        html.Img(src='data:image/png;base64,{}'.format(encoded_logo), style={'height': '75px'})
    ], style={'textAlign': 'center', 'padding': '10px'}),
    
    html.H1("Project Performance", style={'textAlign': 'center'}),
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
    
    # Project Description block with extra margin and bold label.
    html.Div(id='project-description', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
    
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
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '0 auto'}),
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
        ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '0 auto'})
    ], style={'textAlign': 'center'}),
    
    # Additional title for the first pie chart.
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
    grouped = df_filtered.groupby('Personel', as_index=False)[value_col].sum()
    total_hours = grouped[value_col].sum()
    fig = px.pie(
        grouped,
        names='Personel',
        values=value_col,
        title=f"Percentage of Hours by Personel for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Hours:</b> {total_hours:.2f}"
    )
    fig.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
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
        title=f"Cost Distribution by Personel for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Cost:</b> ${total_cost:,.2f}"
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
            'Total Invoice': total_invoice,
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
    app.run_server(debug=True, host='10.1.2.154', port=7050, use_reloader=False)
