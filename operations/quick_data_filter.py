import pandas as pd
import os
import pickle
from datetime import datetime
import sys

# Add parent directory to path to import app_main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Color printing functions
def print_green(text): print(f"\033[92m{text}\033[0m")
def print_red(text): print(f"\033[91m{text}\033[0m")
def print_orange(text): print(f"\033[93m{text}\033[0m")
def print_cyan(text): print(f"\033[96m{text}\033[0m")

# Use the local Excel file instead of network path for better reliability
PROJECT_LOG_PATH = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\2025 Project Log.xlsx"
PICKLE_OUTPUT_DIR = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"

# Define exact client names based on the search results
EXACT_CLIENT_NAMES = {
    'ESTUDIO ARCHITECTS': 'ESTUDIO ARCHITECTS',
    'AUTOARCH': 'AUTOARCH',
    'M H Builder': 'M H Builder',
    'ARCADE DESIGN Corp': 'ARCADE DESIGN Corp'
}

def get_app_main_data():
    """
    Try to import and use the dataframes from app_main.py
    This gives us access to the complete processed data
    """
    try:
        print_green("Attempting to import data directly from app_main...")
        
        # Try to import app_main
        from operations import app_main
        
        # Check for the global dataframe that contains all project data
        if hasattr(app_main, 'df_all') and isinstance(app_main.df_all, pd.DataFrame) and not app_main.df_all.empty:
            print_green(f"Successfully imported df_all from app_main with {len(app_main.df_all)} rows")
            return app_main.df_all
        
        # If df_all is not available, try df_projects
        elif hasattr(app_main, 'df_projects') and isinstance(app_main.df_projects, pd.DataFrame) and not app_main.df_projects.empty:
            print_green(f"Successfully imported df_projects from app_main with {len(app_main.df_projects)} rows")
            return app_main.df_projects
        
        # If neither is available, return None
        else:
            print_orange("No suitable dataframes found in app_main")
            return None
    except Exception as e:
        print_orange(f"Could not import data from app_main: {str(e)}")
        return None

def load_all_data_sources():
    """
    Load data from all possible sources in order of preference:
    1. Direct import from app_main
    2. Excel file
    3. Pickle files
    """
    # First try to get data directly from app_main
    df = get_app_main_data()
    if df is not None and not df.empty:
        return df
    
    # If that fails, try Excel
    df = load_excel_data()
    if not df.empty:
        return df
    
    # If all else fails, look for pickle files
    return load_project_data()

def load_excel_data():
    """Load project data directly from the Excel file"""
    print_green(f"Loading project data from Excel file: {PROJECT_LOG_PATH}")
    
    try:
        # Try to load the sheet "4_Contracted Projects"
        df_projects = pd.read_excel(PROJECT_LOG_PATH, sheet_name="4_Contracted Projects")
        print_green(f"Successfully loaded sheet '4_Contracted Projects' with {len(df_projects)} projects")
        return df_projects
    except Exception as e:
        print_red(f"Error loading Excel file: {str(e)}")
        return pd.DataFrame()

def load_project_data():
    """Load project data from the most recent pickle file (fallback option)"""
    # Find the most recent projects pickle file
    project_pickle_files = []
    for file in os.listdir(PICKLE_OUTPUT_DIR):
        if file.endswith(".pkl") and "projects" in file.lower():
            project_pickle_files.append(os.path.join(PICKLE_OUTPUT_DIR, file))
    
    if not project_pickle_files:
        print_red(f"No project pickle files found in {PICKLE_OUTPUT_DIR}")
        return pd.DataFrame()
    
    # Get most recent file by creation time
    latest_pickle = max(project_pickle_files, key=os.path.getctime)
    print_green(f"Using pickle file: {os.path.basename(latest_pickle)}")
    
    # Load the pickle file
    try:
        with open(latest_pickle, 'rb') as f:
            df_projects = pickle.load(f)
        print_green(f"Loaded {len(df_projects)} projects from pickle file")
        return df_projects
    except Exception as e:
        print_red(f"Error loading pickle file: {str(e)}")
        return pd.DataFrame()

def extract_client_projects(target_clients=None, start_year=2017, partial_match=False):
    """
    Extract projects for specific clients from all available data sources
    
    Args:
        target_clients: List of client names to search for
        start_year: Start year for filtering projects
        partial_match: Whether to use partial matching for client names
    """
    if target_clients is None:
        # Use the exact client names we identified
        target_clients = list(EXACT_CLIENT_NAMES.keys())
    
    print_green(f"Looking for projects with {'partial' if partial_match else 'exact'} matches for clients: {', '.join(target_clients)}")
    
    # Load ALL available project data - prioritizing app_main data
    df_projects = load_all_data_sources()
    
    if df_projects.empty:
        print_red("No project data available from any source")
        return pd.DataFrame(), None
    
    print_cyan(f"Working with dataset containing {len(df_projects)} projects and {len(df_projects.columns)} columns")
    
    # Find client column
    client_column = None
    for col in df_projects.columns:
        if col.lower() in ['client', 'clients', 'client name']:
            client_column = col
            break
    
    if client_column is None:
        print_red("Client column not found")
        return pd.DataFrame(), None
    
    print_cyan(f"Using '{client_column}' column for client filtering")
    
    # Convert client column to string
    df_projects[client_column] = df_projects[client_column].fillna('').astype(str)
    
    # Client matching strategy
    if partial_match:
        # Partial matching for better recall
        client_mask = df_projects[client_column].str.lower().apply(
            lambda x: any(client.lower() in x.lower() for client in target_clients)
        )
    else:
        # Exact matching for precision
        client_mask = df_projects[client_column].apply(lambda x: x in target_clients)
    
    filtered_df = df_projects[client_mask].copy()
    print_cyan(f"Found {len(filtered_df)} projects for the specified clients")
    
    # Find date column
    date_column = None
    date_column_candidates = ['award date', 'date', 'start date', 'project date']
    
    for candidate in date_column_candidates:
        for col in df_projects.columns:
            if isinstance(col, str) and candidate in col.lower():
                date_column = col
                print_cyan(f"Using '{date_column}' as date column")
                break
        if date_column:
            break
    
    if date_column and start_year:
        try:
            filtered_df['Year'] = pd.to_datetime(filtered_df[date_column], errors='coerce').dt.year
            year_mask = filtered_df['Year'] >= start_year
            filtered_df = filtered_df[year_mask]
            filtered_df = filtered_df.drop('Year', axis=1)
            print_cyan(f"Found {len(filtered_df)} projects since {start_year}")
        except Exception as e:
            print_orange(f"Could not filter by year: {str(e)}")
    
    # Save the filtered data with better formatting
    if not filtered_df.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a descriptive filename
        match_type = "partial" if partial_match else "exact"
        output_path = os.path.join(output_dir, f"client_projects_{match_type}_matches_since_{start_year}_{timestamp}.xlsx")
        
        # Fill NaN values before writing to Excel
        filtered_df_clean = filtered_df.fillna('')
        
        try:
            # Use ExcelWriter with nan_inf_to_errors option
            with pd.ExcelWriter(output_path, engine='xlsxwriter', engine_kwargs={'options': {'nan_inf_to_errors': True}}) as writer:
                filtered_df_clean.to_excel(writer, index=False, sheet_name='Client Projects')
                
                # Access the workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Client Projects']
                
                # Define formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#D9E1F2',
                    'border': 1
                })
                
                # Add a title with client names
                client_list = ', '.join(target_clients)
                title_str = f"Projects for {client_list} (Since {start_year})"
                title_format = workbook.add_format({
                    'bold': True,
                    'font_size': 14,
                    'align': 'center',
                    'valign': 'vcenter'
                })
                worksheet.merge_range(0, 0, 0, len(filtered_df.columns) - 1, title_str, title_format)
                
                # Add a filter for the column headers
                worksheet.autofilter(1, 0, 1 + len(filtered_df), len(filtered_df.columns) - 1)
                
                # Write the column headers with the header format (starting from row 1, not 0)
                for col_num, value in enumerate(filtered_df.columns.values):
                    worksheet.write(1, col_num, str(value), header_format)
                
                # Auto-adjust column widths
                for col_num, column in enumerate(filtered_df.columns):
                    column_width = max(
                        filtered_df_clean[column].astype(str).map(len).max(),  # Max data width
                        len(str(column))  # Column header width
                    ) + 2  # Add a little padding
                    worksheet.set_column(col_num, col_num, min(column_width, 30))  # Limit width to 30
            
            print_green(f"Saved enhanced Excel report to {output_path}")
            print_green(f"Excel file saved with {len(filtered_df)} projects for clients: {', '.join(target_clients)}")
            return filtered_df, output_path
        except Exception as e:
            print_red(f"Error saving to Excel with formatting: {str(e)}")
            # Fall back to simple export if the enhanced version fails
            try:
                filtered_df.to_excel(output_path, index=False)
                print_green(f"Saved filtered projects to {output_path} (simple format)")
                return filtered_df, output_path
            except Exception as e2:
                print_red(f"Error saving to Excel (simple format): {str(e2)}")
    
    return filtered_df, None

if __name__ == "__main__":
    # Use the exact client names we identified
    target_clients = list(EXACT_CLIENT_NAMES.keys())
    
    # Try both exact and partial matches to be thorough
    print_green("First trying exact client matches...")
    exact_df, exact_path = extract_client_projects(target_clients, start_year=2017, partial_match=False)
    
    if exact_df.empty or len(exact_df) < 5:  # If few or no results with exact matching
        print_orange("Few or no exact matches found. Trying partial matching...")
        partial_df, partial_path = extract_client_projects(target_clients, start_year=2017, partial_match=True)
        
        if not partial_df.empty:
            print_cyan("\nSample of projects found with partial matching:")
            print(partial_df.head())
            print_cyan(f"Total projects found: {len(partial_df)}")
            if partial_path:
                print_green(f"Results saved to: {partial_path}")
        else:
            print_red("No matching projects found with either method")
            print_orange("Check if client names need to be updated or if there are no projects since 2017")
    else:
        print_cyan("\nSample of projects found with exact matching:")
        print(exact_df.head())
        print_cyan(f"Total projects found: {len(exact_df)}")
        if exact_path:
            print_green(f"Results saved to: {exact_path}")