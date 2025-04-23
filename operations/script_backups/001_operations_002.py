import pandas as pd

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
      - If the month is July, check the day:
            - If day <= 15: use the column "YYYYJUL (1-15)"
            - If day > 15:  use the column "YYYYJUL (15-31)"
      - For other months, use the column in the format "YYYYMON" (e.g. "2024JAN", "2024FEB", etc.).
      - Multiply the retrieved rate by the 'hours' value.
      - Store the result in a new column called 'day_cost'.
    """
    # Convert 'local_date' to datetime
    merged_df['local_date'] = pd.to_datetime(merged_df['local_date'], errors='coerce')
    
    def row_day_cost(row):
        dt = row['local_date']
        if pd.isnull(dt):
            return 0
        year = dt.year
        # For July, choose the appropriate column name based on the day of month
        if dt.month == 7:
            if dt.day <= 15:
                ym = f"{year}JUL (1-15)"
            else:
                ym = f"{year}JUL (15-31)"
        else:
            ym = dt.strftime('%Y') + dt.strftime('%b').upper()
        # If the rate column exists, use its value; otherwise default to 0.
        if ym in merged_df.columns:
            rate = row[ym]
        else:
            rate = 0
        return rate * row['hours']
    
    merged_df['day_cost'] = merged_df.apply(row_day_cost, axis=1)
    return merged_df

def assign_total_hours(merged_df):
    """
    For each row, assign the 'hours' value to a new column corresponding
    to the year of the 'local_date'. For example, if the date is in 2024,
    'total_hours_24' will contain the 'hours' value and 'total_hours_25' will be blank.
    """
    # Assuming 'local_date' is already converted to datetime in calculate_day_cost.
    merged_df['total_hours_24'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2024)
    merged_df['total_hours_25'] = merged_df['hours'].where(merged_df['local_date'].dt.year == 2025)
    return merged_df

def main():
    # Path to the primary Excel file with multiple sheets
    primary_file = r"C:\Users\jose.pineda\Desktop\operations\RATES.xlsx"
    
    # Load DataFrames from the primary Excel file.
    df_trm_conv, df_rates_24_25, df_rates_22_23, df_loaded_rates = load_primary_data(primary_file)
    
    # Path to the secondary CSV file
    second_file = r"C:\Users\jose.pineda\Desktop\operations\BEXAR\timesheet_report_2023-01-01_thru_2025-02-13.csv"
    
    # Load the CSV file using pd.read_csv.
    # Ensure that the CSV file contains columns 'local_date', 'hours', and 'number'
    df_new = pd.read_csv(second_file, header=0, index_col=0)
    
    # Merge df_rates_24_25 with the new DataFrame.
    # 'ID#' in df_rates_24_25 matches with 'number' in df_new.
    merged_df = pd.merge(df_rates_24_25, df_new, left_on='ID#', right_on='number', how='inner')
    
    # Export the initial merged DataFrame for verification.
    output_path_initial = r"C:\Users\jose.pineda\Desktop\operations\output_files\merged_output.xlsx"
    merged_df.to_excel(output_path_initial, index=False)
    print(f"Merged DataFrame exported successfully to {output_path_initial}")
    
    # Calculate the day_cost column based on local_date, rate columns, and hours.
    merged_df = calculate_day_cost(merged_df)
    
    # Assign total hours for each row based on the year in local_date.
    merged_df = assign_total_hours(merged_df)
    
    # Export the updated merged DataFrame (with day_cost and total hours) to Excel.
    output_path_updated = r"C:\Users\jose.pineda\Desktop\operations\output_files\merged_with_day_cost.xlsx"
    merged_df.to_excel(output_path_updated, index=False)
    print(f"Updated DataFrame with day_cost and total hours exported successfully to {output_path_updated}")
    
    # Print heads for verification
    print("----- df_trm_conv -----")
    print(df_trm_conv.head())
    
    print("\n----- df_rates_24_25 -----")
    print(df_rates_24_25.head())
    
    print("\n----- df_rates_22_23 -----")
    print(df_rates_22_23.head())
    
    print("\n----- df_loaded_rates (sheet 'df4') -----")
    print(df_loaded_rates.head())
    
    print("\n----- New DataFrame (from CSV file) -----")
    print(df_new.head())
    
    print("\n----- Merged DataFrame (after calculating day_cost and assigning total hours) -----")
    print(merged_df.head())

if __name__ == "__main__":
    main()
