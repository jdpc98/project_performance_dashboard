import pandas as pd
import os
from db_manager import DatabaseManager

def initialize_database():
    """
    Initial load of all data sources - only run once to populate the database
    """
    # Define paths to your pickle files
    pickle_dir = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"
    
    # Delete existing database file if it exists
    db_path = "operations/smart_decon.db"
    if os.path.exists(db_path):
        print(f"Removing existing database file {db_path}")
        os.remove(db_path)
        
        
    print("Loading data from pickle files...")
    try:
        # Load data from pickle files
        global_merged_df = pd.read_pickle(os.path.join(pickle_dir, "global_merged_df.pkl"))
        global_projects_df = pd.read_pickle(os.path.join(pickle_dir, "global_projects_df.pkl"))
        global_invoices = pd.read_pickle(os.path.join(pickle_dir, "global_invoices.pkl"))
        global_raw_invoices = pd.read_pickle(os.path.join(pickle_dir, "global_raw_invoices.pkl"))
        
        print(f"Loaded {len(global_merged_df)} timesheet entries")
        print(f"Loaded {len(global_projects_df)} projects")
        print(f"Loaded {len(global_invoices)} processed invoices")
        print(f"Loaded {len(global_raw_invoices)} raw invoices")
        
        # Initialize database and import data
        print("Initializing database...")
        db = DatabaseManager()
        
        # Add projects first (because timesheet and invoice tables reference projects)
        print("Adding projects...")
        added, updated = db.add_projects(global_projects_df)
        print(f"Added {added} projects, updated {updated} projects")
        
        # Add timesheet entries
        print("Adding timesheet entries...")
        added = db.add_timesheet_entries(global_merged_df, check_new_only=False)
        print(f"Added {added} timesheet entries")
        
        # Add raw invoices
        print("Adding invoices...")
        added = db.add_invoices(global_raw_invoices, check_new_only=False)
        print(f"Added {added} invoices")
        
        # Save last update files
        db.save_last_update_files(pickle_dir)
        print("Database initialization complete!")
        
    except Exception as e:
        print(f"Error during database initialization: {str(e)}")
    
if __name__ == "__main__":
    initialize_database()