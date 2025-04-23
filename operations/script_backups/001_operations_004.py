import os
import re
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import numpy as np
# Global variable to be used by the Dash callbacks.
global_merged_df = None

def sanitize_filename(filename):
    """
    Remove or replace characters that are invalid in file names.
    """
    # Remove any character not allowed in Windows filenames.
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def load_primary_data(file_path):
    """
    Load DataFrames from the primary Excel file.
    Expected sheet names in the file:
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
      - Extract the year and month.
      - For July, choose the appropriate column name based on the day:
            * If day <= 15: use "YYYYJUL (1-15)"
            * Else: use "YYYYJUL (15-31)"
      - For other months, use the format "YYYYMON" (e.g. "2024JAN").
      - Multiply the retrieved rate by the 'hours' value.
      - Store the result in a new column called 'day_cost'.
    """
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')
    
    def row_day_cost(row):
        dt = row['local_date']
        if pd.isnull(dt):
            return 0
        year = dt.year
        if dt.month == 7:
            # Use the appropriate July column based on the day.
            if dt.day <= 15:
                ym = f"{year}JUL (1-15)"
            else:
                ym = f"{year}JUL (15-31)"
        else:
            ym = dt.strftime('%Y') + dt.strftime('%b').upper()
        # If the rate column exists, use its value; otherwise default to 0.
        rate = row[ym] if ym in merged_df.columns else 0
        return rate * row['hours']
    
    merged_df['day_cost'] = merged_df.apply(row_day_cost, axis=1)
    return merged_df

def assign_total_hours(merged_df):
    """
    For each row, if the 'local_date' year is 2024, assign the 'hours' value
    to 'total_hours_24', or if 2025, to 'total_hours_25'. The other column will be NaN.
    """
    merged_df['total_hours_24'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2024)
    merged_df['total_hours_25'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2025)
    return merged_df

def main():
    global global_merged_df  # We'll store the processed merged DataFrame globally for Dash usage.
    
    # === Data Loading and Processing ===
    primary_file = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    df_trm_conv, df_rates_24_25, df_rates_22_23, df_loaded_rates = load_primary_data(primary_file)
    
    second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    df_new = pd.read_csv(second_file, header=0, index_col=0)
    
    # --- Fix merging issues between the two files ---
    # Create a full_name column in df_new.
    df_new['full_name'] = df_new['fname'].astype(str).str.strip() + " " + df_new['lname'].astype(str).str.strip()
    
    # Create a mapping from df_rates_24_25: Personel -> ID#
    mapping = df_rates_24_25.set_index('Personel')['ID#'].to_dict()
    
    # In df_new, create a new column "correct_number":
    # If 'number' is not 0, keep it; if it is 0, replace with the mapped value using full_name.
    df_new['correct_number'] = df_new['number'].astype(np.int64)
    
    mask = df_new['correct_number'] == 0
    mapped = df_new.loc[mask, 'full_name'].map(mapping)
    mapped = mapped.astype(df_rates_24_25['ID#'].dtype)
    df_new.loc[mask, 'correct_number'] = mapped
    
    #df_new.loc[df_new['correct_number'] == 0, 'correct_number'] = df_new.loc[df_new['correct_number'] == 0, 'full_name'].map(mapping)
    
    # Now merge using df_rates_24_25's 'ID#' and df_new's 'correct_number'
    merged_df = pd.merge(df_rates_24_25, df_new, left_on='ID#', right_on='correct_number', how='inner')
    
    # Ensure the output directory exists.
    output_directory = r"C:\Users\jose.pineda\Desktop\operations\output_files"
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    # Export initial merged DataFrame for verification.
    output_path_initial = os.path.join(output_directory, "merged_output.xlsx")
    merged_df.to_excel(output_path_initial, index=False)
    print(f"Merged DataFrame exported successfully to {output_path_initial}")
    
    # Calculate day_cost and assign total hours per row.
    merged_df = calculate_day_cost(merged_df)
    merged_df = assign_total_hours(merged_df)
    
    # Export the updated merged DataFrame.
    output_path_updated = os.path.join(output_directory, "merged_with_day_cost.xlsx")
    merged_df.to_excel(output_path_updated, index=False)
    print(f"Updated DataFrame with day_cost and total hours exported successfully to {output_path_updated}")
    
    # === Jobcode Workflow Options ===
    # Set run_jobcode_option to "separate" to export separate Excel files per jobcode_2,
    # or "direct" to simply create a dictionary of DataFrames for direct use.
    run_jobcode_option = "separate"  # Change to "direct" if desired.
    
    if run_jobcode_option == "separate":
        jobcode_dfs = {jc: merged_df[merged_df['jobcode_2'] == jc] 
                       for jc in merged_df['jobcode_2'].unique()}
        for jc, df in jobcode_dfs.items():
            safe_jc = sanitize_filename(jc)
            output_file = os.path.join(output_directory, f"merged_{safe_jc}.xlsx")
            df.to_excel(output_file, index=False)
        print("Exported separate DataFrames for each unique jobcode_2.")
    elif run_jobcode_option == "direct":
        jobcode_dict = {jc: merged_df[merged_df['jobcode_2'] == jc] 
                        for jc in merged_df['jobcode_2'].unique()}
        print("Created dictionary of filtered DataFrames for each unique jobcode_2 for direct use.")
        print("Unique jobcode_2 values:", list(jobcode_dict.keys()))
    
    # Store the processed merged_df globally for use in the Dash app.
    global_merged_df = merged_df.copy()
    
    # === Optional: Print heads for verification ===
    print("----- Merged DataFrame (final) -----")
    print(merged_df.head())
    
    # Return the merged DataFrame in case you want to use it further.
    return merged_df

# Run data processing first.
processed_df = main()

# === Dash App for Visualization ===
app = dash.Dash(__name__)

# Prepare dropdown options.
jobcode_options = [{'label': jc, 'value': jc} for jc in global_merged_df['jobcode_2'].unique()]

year_options = [
    {'label': '2024', 'value': '2024'},
    {'label': '2025', 'value': '2025'}
]

# Get unique personnel names (sorted) from the global DataFrame.
personnel_options = [{'label': p, 'value': p} for p in sorted(global_merged_df['Personel'].unique())]

app.layout = html.Div([
    html.H1("Jobcode Hours Visualization"),
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
            value=[p['value'] for p in personnel_options],  # default all selected
            multi=True,
            clearable=True
        )
    ], style={'width': '30%', 'display': 'inline-block', 'marginLeft': '2%'}),
    dcc.Graph(id='pie-chart')
])

@app.callback(
    Output('pie-chart', 'figure'),
    [
        Input('jobcode-dropdown', 'value'),
        Input('year-dropdown', 'value'),
        Input('personnel-dropdown', 'value')
    ]
)
def update_pie_chart(selected_jobcode, selected_years, selected_personnel):
    # Filter by selected jobcode.
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    
    # Filter by selected years using the local_date year.
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    
    # Filter by selected personnel if provided.
    if selected_personnel and len(selected_personnel) > 0:
        df_filtered = df_filtered[df_filtered['Personel'].isin(selected_personnel)]
    
    # Determine which hours column to sum based on the selected years.
    if set(selected_years) == {"2024"}:
        value_col = 'total_hours_24'
    elif set(selected_years) == {"2025"}:
        value_col = 'total_hours_25'
    else:
        # If both years are selected, create a combined column.
        df_filtered['combined_total_hours'] = df_filtered['total_hours_24'].fillna(0) + df_filtered['total_hours_25'].fillna(0)
        value_col = 'combined_total_hours'
    
    # Group by Personel and sum the appropriate total hours.
    grouped = df_filtered.groupby('Personel', as_index=False)[value_col].sum()
    
    # Create a pie chart showing the percentage of hours per person.
    fig = px.pie(
        grouped,
        names='Personel',
        values=value_col,
        title=f"Percentage of Hours by Personel for Jobcode: {selected_jobcode}"
    )
    return fig

# Run the Dash server.
if __name__ == '__main__':
    app.run_server(debug=True, host='10.1.2.154', port=7050, use_reloader=False)
