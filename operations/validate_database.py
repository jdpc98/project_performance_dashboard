import os
import sqlite3
import pandas as pd
from db_manager import DatabaseManager

def validate_database():
    """
    Validate that the SQLite database was created correctly by:
    1. Checking if file exists
    2. Verifying tables exist with expected row counts
    3. Running sample queries and comparing to pickle data
    """
    db_path = "operations/smart_decon.db"
    pickle_dir = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"
    
    # 1. Check if database file exists
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False
    
    # Get file size
    db_size = os.path.getsize(db_path) / (1024 * 1024)  # Size in MB
    print(f"✅ Database file exists ({db_size:.2f} MB)")
    
    # 2. Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("✅ Successfully connected to database")
        
        # 3. Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['projects', 'timesheet_entries', 'invoices', 'metadata']
        
        for table in expected_tables:
            if table in tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' is missing!")
                return False
        
        # 4. Check row counts
        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]
        print(f"✅ Projects table has {project_count} rows")
        
        cursor.execute("SELECT COUNT(*) FROM timesheet_entries")
        timesheet_count = cursor.fetchone()[0]
        print(f"✅ Timesheet entries table has {timesheet_count} rows")
        
        cursor.execute("SELECT COUNT(*) FROM invoices")
        invoice_count = cursor.fetchone()[0]
        print(f"✅ Invoices table has {invoice_count} rows")
        
        # 5. Compare with original data
        orig_projects = pd.read_pickle(os.path.join(pickle_dir, "global_projects_df.pkl"))
        orig_timesheets = pd.read_pickle(os.path.join(pickle_dir, "global_merged_df.pkl"))
        orig_invoices = pd.read_pickle(os.path.join(pickle_dir, "global_raw_invoices.pkl"))
        
        print("\nComparing with original data:")
        print(f"Projects: {len(orig_projects)} original, {project_count} in database")
        print(f"Timesheets: {len(orig_timesheets)} original, {timesheet_count} in database")
        print(f"Invoices: {len(orig_invoices)} original, {invoice_count} in database")
        
        # 6. Run sample queries
        print("\nRunning sample queries:")
        
        # Sample project data
        cursor.execute("SELECT project_no, clients, status FROM projects LIMIT 5")
        print("\nSample projects:")
        for row in cursor.fetchall():
            print(f"  Project {row[0]}: {row[1]} (Status: {row[2]})")
        
        # Sample timesheet data
        cursor.execute("""
            SELECT t.project_no, t.employee, t.hours, t.local_date 
            FROM timesheet_entries t
            LIMIT 5
        """)
        print("\nSample timesheet entries:")
        for row in cursor.fetchall():
            print(f"  {row[1]} worked {row[2]} hours on {row[0]} on {row[3]}")
        
        # Sample invoice data
        cursor.execute("SELECT project_no, amount FROM invoices LIMIT 5")
        print("\nSample invoices:")
        for row in cursor.fetchall():
            print(f"  Project {row[0]}: ${row[1]:.2f}")
        
        # 7. Check join operations
        print("\nTesting joins between tables:")
        cursor.execute("""
            SELECT p.project_no, p.clients, COUNT(t.id) as timesheet_entries,
                   COALESCE(SUM(t.hours), 0) as total_hours
            FROM projects p
            LEFT JOIN timesheet_entries t ON p.project_no = t.project_no
            GROUP BY p.project_no
            LIMIT 5
        """)
        print("\nProject summary with timesheet data:")
        for row in cursor.fetchall():
            print(f"  Project {row[0]} ({row[1] or 'No client'}): {row[2]} entries, {row[3]:.1f} hours")
            
        # 8. Verify using DatabaseManager
        print("\nVerifying with DatabaseManager:")
        db = DatabaseManager()
        df1 = db.get_projects_df()
        print(f"✅ get_projects_df() returns {len(df1)} rows")
        
        df2 = db.get_merged_df()
        print(f"✅ get_merged_df() returns {len(df2)} rows")
        
        df3 = db.get_invoices_df()
        print(f"✅ get_invoices_df() returns {len(df3)} rows")
        
        # Close connection
        conn.close()
        print("\n✅ Database validation complete!")
        return True
    
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    validate_database()