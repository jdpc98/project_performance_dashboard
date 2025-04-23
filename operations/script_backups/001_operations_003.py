import os
import re
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px

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
    
    # Merge the df_rates_24_25 sheet with the CSV data using 'ID#' and 'number'
    merged_df = pd.merge(df_rates_24_25, df_new, left_on='ID#', right_on='number', how='inner')
    
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
    # Set run_jobcode_option to "separate" to exportasdparate Excel files per jobcode_2,
    # or "direct" to simply create a dictionary of DataFrames for direct use.
    run_jobcode_option = "direct"  # Change to "direct" if desired.
    
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
# This Dash app will work regardless of the jobcode workflow option.
app = dash.Dash(__name__)

# Create a dropdown with unique jobcode_2 values from the global merged DataFrame.
jobcode_options = [{'label': jc, 'value': jc} for jc in global_merged_df['jobcode_2'].unique()]

app.layout = html.Div([
    html.H1("Jobcode Hours Visualization"),
    dcc.Dropdown(
        id='jobcode-dropdown',
        options=jobcode_options,
        value=jobcode_options[0]['value'] if jobcode_options else None,
        clearable=False
    ),
    dcc.Graph(id='pie-chart')
])

@app.callback(
    Output('pie-chart', 'figure'),
    Input('jobcode-dropdown', 'value')
)
def update_pie_chart(selected_jobcode):
    # Filter the global merged DataFrame by the selected jobcode_2.
    filtered_df = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode]
    # Group by 'Personel' and sum the 'hours'
    grouped = filtered_df.groupby('Personel', as_index=False)['hours'].sum()
    
    # Create a pie chart showing percentage of hours by each person
    fig = px.pie(
        grouped,
        names='Personel',
        values='hours',
        title=f"Percentage of Hours by Personel for Jobcode: {selected_jobcode}"
    )
    return fig



# Run the Dash server on port 8050.
if __name__ == '__main__':
    app.run_server(host='10.1.2.154', debug=True, port=7050)

    #app.run_server(debug=True, host='10.1.2.154', port=7050, use_reloader=False)
