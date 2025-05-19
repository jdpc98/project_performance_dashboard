import sqlite3
import pandas as pd
import os
from datetime import datetime
import numpy as np

class DatabaseManager:
    def __init__(self, db_path="operations/smart_decon.db"):
        """Initialize the database connection and create tables if needed"""
        self.db_path = db_path
        self.conn = None
        self.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.initialize_db()
        
    def initialize_db(self):
        """Connect to database and initialize schema"""
        #ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = OFF")
        
        # Create projects table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_no TEXT UNIQUE NOT NULL,
            clients TEXT,
            type TEXT,
            status TEXT,
            service_line TEXT,
            market_segment TEXT,
            pm TEXT,
            tl TEXT,
            project_description TEXT,
            award_date TEXT,
            contracted_amount REAL,
            last_updated TEXT
        )
        ''')
        
        # Create timesheet entries table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS timesheet_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_no TEXT,
            employee TEXT,
            personel TEXT,
            local_date TEXT,
            hours REAL,
            day_cost REAL,
            service_item TEXT,
            staff_type INTEGER,
            jobcode_2 TEXT,
            jobcode_3 TEXT,
            last_updated TEXT
           
        )
        ''')
        
        # FOREIGN KEY (project_no) REFERENCES projects(project_no) #left out for now to avoid circular dependency
        
        # Create invoices table
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_no TEXT,
            invoice_no TEXT,
            invoice_date TEXT,
            amount REAL,
            payment_status TEXT,
            payment_date TEXT,
            last_updated TEXT
            
        )
        ''')
        #FOREIGN KEY (project_no) REFERENCES projects(project_no) #left out for now to avoid circular dependency
        
        
        # Create metadata table for tracking last updates
        self.conn.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Create indexes for faster queries
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_project_no ON projects(project_no)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_timesheet_project ON timesheet_entries(project_no)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_timesheet_date ON timesheet_entries(local_date)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_invoice_project ON invoices(project_no)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoices(invoice_date)')
        
        self.conn.commit()
        
    def get_last_update(self, key="last_update"):
        """Get the last update timestamp for a specific data source"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
        result = cursor.fetchone()
        return result[0] if result else None
        
    def set_last_update(self, key="last_update", value=None):
        """Set the last update timestamp for a specific data source"""
        if value is None:
            value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()
        return value
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def add_projects(self, df, update_existing=True):
        """
        Add or update projects from a DataFrame
        
        Args:
            df: DataFrame with project data
            update_existing: If True, update existing records; if False, only insert new ones
        
        Returns:
            Tuple of (num_added, num_updated)
        """
        if df.empty:
            return 0, 0
        
        # Create a copy and ensure all string columns are properly handled
        df = df.copy()
        
        # Handle date columns
        if 'Award Date' in df.columns:
            df['Award Date'] = pd.to_datetime(df['Award Date'], errors='coerce')
            df['Award Date'] = df['Award Date'].dt.strftime('%Y-%m-%d')
        
        # Handle NaN values
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna('')
            elif pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
        
        # Add last_updated column
        df['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        added = 0
        updated = 0
        
        # Map DataFrame column names to database column names
        column_map = {
            'Project No': 'project_no',
            'Clients': 'clients',
            'Type': 'type',
            'Status': 'status',
            'Service Line': 'service_line',
            'Market Segment': 'market_segment',
            'PM': 'pm',
            'TL': 'tl',
            'Project Description': 'project_description',
            'Award Date': 'award_date',
            'Contracted Amount': 'contracted_amount',
            'last_updated': 'last_updated'
        }
        
        # Process each row individually for better error handling
        for _, row in df.iterrows():
            try:
                # Check if project exists
                cursor = self.conn.cursor()
                cursor.execute("SELECT 1 FROM projects WHERE project_no = ?", (row['Project No'],))
                exists = cursor.fetchone() is not None
                
                if exists and update_existing:
                    # Update existing project
                    params = []
                    update_cols = []
                    
                    for df_col, db_col in column_map.items():
                        if df_col == 'Project No':
                            continue  # Skip the key field for updates
                            
                        if df_col in row:
                            value = row[df_col]
                            
                            # Special handling for contracted amount
                            if df_col == 'Contracted Amount':
                                try:
                                    if isinstance(value, str):
                                        value = float(value.replace('$', '').replace(',', ''))
                                    else:
                                        value = float(value) if pd.notnull(value) else 0.0
                                except (ValueError, TypeError):
                                    value = 0.0
                            
                            update_cols.append(f"{db_col} = ?")
                            params.append(value)
                    
                    params.append(str(row['Project No']))  # Add where clause parameter
                    
                    # Execute update
                    query = f"UPDATE projects SET {', '.join(update_cols)} WHERE project_no = ?"
                    cursor.execute(query, params)
                    updated += 1
                    
                elif not exists:
                    # Insert new project
                    fields = []
                    placeholders = []
                    params = []
                    
                    for df_col, db_col in column_map.items():
                        if df_col in row:
                            value = row[df_col]
                            
                            # Special handling for contracted amount
                            if df_col == 'Contracted Amount':
                                try:
                                    if isinstance(value, str):
                                        value = float(value.replace('$', '').replace(',', ''))
                                    else:
                                        value = float(value) if pd.notnull(value) else 0.0
                                except (ValueError, TypeError):
                                    value = 0.0
                            
                            fields.append(db_col)
                            placeholders.append('?')
                            params.append(value)
                    
                    # Execute insert
                    query = f"INSERT INTO projects ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                    cursor.execute(query, params)
                    added += 1
                    
                    
            except Exception as e:
                print(f"Error processing project {row.get('Project No')}: {str(e)}")
                continue
        
        self.conn.commit()
        self.set_last_update('projects_last_update')
        return added, updated
        
    def add_timesheet_entries(self, df, check_new_only=True):
        """
        Add timesheet entries, filtering for only new data if requested
        
        Args:
            df: DataFrame with timesheet entries
            check_new_only: If True, only add entries newer than the latest in database
            
        Returns:
            Number of entries added
        """
        if df.empty:
            return 0
            
        # Create a copy and standardize column names
        df = df.copy()
        
        # Handle date column - ensure it's in a consistent format
        if 'local_date' in df.columns:
            df['local_date'] = pd.to_datetime(df['local_date'], errors='coerce')
            
            # If check_new_only, get the latest date in the database
            if check_new_only:
                cursor = self.conn.cursor()
                cursor.execute("SELECT MAX(local_date) FROM timesheet_entries")
                latest_date = cursor.fetchone()[0]
                
                if latest_date:
                    # Convert database string to datetime for comparison
                    latest_dt = pd.to_datetime(latest_date)
                    # Filter the dataframe for dates newer than latest
                    df = df[df['local_date'] > latest_dt]
            
            # Format dates as strings for database
            df['local_date'] = df['local_date'].dt.strftime('%Y-%m-%d')
            
        # Handle missing Project No column
        if 'Project No' not in df.columns and 'jobcode_2' in df.columns:
            # Extract Project No from jobcode_2 using the conditional_extract_project_no logic
            df['Project No'] = df.apply(lambda row: 
                str(row.get('jobcode_3', ''))[:7].strip() 
                if str(row.get('jobcode_2', '')).strip().startswith('1928') 
                else str(row.get('jobcode_2', ''))[:7].strip(), 
                axis=1)
        
        if df.empty:  # If after filtering there's no new data
            return 0
            
        # Add last_updated timestamp
        df['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Map DataFrame columns to database columns
        column_map = {
            'Project No': 'project_no',
            'Employee': 'employee',
            'Personel': 'personel',
            'local_date': 'local_date',
            'hours': 'hours',
            'day_cost': 'day_cost',
            'Service Item': 'service_item',
            'staff_type': 'staff_type',
            'jobcode_2': 'jobcode_2',
            'jobcode_3': 'jobcode_3',
            'last_updated': 'last_updated'
        }
        
        # Fill nulls
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna('')
            elif pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
        
        # Insert in batches for better performance
        rows_added = 0
        for i in range(0, len(df), 1000):  # Process 1000 rows at a time
            batch = df.iloc[i:i+1000]
            
            # Prepare data for insertion
            values = []
            for _, row in batch.iterrows():
                row_values = []
                for df_col, db_col in column_map.items():
                    if df_col in row:
                        row_values.append(row[df_col])
                    else:
                        # Use an appropriate default value
                        if db_col in ['hours', 'day_cost']:
                            row_values.append(0.0)
                        elif db_col == 'staff_type':
                            row_values.append(0)
                        else:
                            row_values.append('')
                
                values.append(tuple(row_values))
            
            # Generate query
            columns = ', '.join(column_map.values())
            placeholders = ', '.join(['?'] * len(column_map))
            

            # Use executemany for batch insertion
            try:
                cursor = self.conn.cursor()
                cursor.executemany(
                    f"INSERT INTO timesheet_entries ({columns}) VALUES ({placeholders})",
                    values
                )
                rows_added += len(batch)
            except Exception as e:
                print(f"Error inserting timesheet batch: {str(e)}")
                # Continue with the next batch rather than stopping on error
                continue
        
        self.conn.commit()
        self.set_last_update('timesheet_last_update')
        return rows_added
    
    def add_invoices(self, df, check_new_only=True):
        """
        Add invoice entries, filtering for only new data if requested
        
        Args:
            df: DataFrame with invoice data
            check_new_only: If True, only add entries newer than the latest in database
            
        Returns:
            Number of entries added
        """
        if df.empty:
            return 0
            
        # Create a copy
        df = df.copy()
        
        # Handle date columns
        if 'Invoice Date' in df.columns:
            df['Invoice Date'] = pd.to_datetime(df['Invoice Date'], errors='coerce')
            
            # If check_new_only, get the latest date in the database
            if check_new_only:
                cursor = self.conn.cursor()
                cursor.execute("SELECT MAX(invoice_date) FROM invoices")
                latest_date = cursor.fetchone()[0]
                
                if latest_date:
                    # Convert to datetime for comparison
                    latest_dt = pd.to_datetime(latest_date)
                    # Filter for newer records
                    df = df[df['Invoice Date'] > latest_dt]
            
            # Format dates as strings for storage
            df['Invoice Date'] = df['Invoice Date'].dt.strftime('%Y-%m-%d')
        
        # Handle Payment Date
        if 'Payment Date' in df.columns:
            df['Payment Date'] = pd.to_datetime(df['Payment Date'], errors='coerce')
            df['Payment Date'] = df['Payment Date'].dt.strftime('%Y-%m-%d')
        
        # Standardize Project No if needed
        if 'Project No' in df.columns:
            df['Project No'] = df['Project No'].astype(str).str.strip()
            
        if df.empty:  # If after filtering there's no new data
            return 0
        
        # Add last_updated
        df['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert amounts to numeric if they're strings
        if 'Actual' in df.columns:
            df['Amount'] = df['Actual'].apply(lambda x: 
                float(str(x).replace('$', '').replace(',', '')) 
                if isinstance(x, str) else float(x) if pd.notnull(x) else 0.0)
        
        # Map DataFrame columns to database columns
        column_map = {
            'Project No': 'project_no',
            'Invoice No': 'invoice_no',
            'Invoice Date': 'invoice_date',
            'Amount': 'amount',
            'Payment': 'payment_status',
            'Payment Date': 'payment_date',
            'last_updated': 'last_updated'
        }
        
        # Fill nulls
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna('')
            elif pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0)
        
        # Insert in batches
        rows_added = 0
        for i in range(0, len(df), 1000):
            batch = df.iloc[i:i+1000]
            
            # Prepare data
            values = []
            for _, row in batch.iterrows():
                row_values = []
                for df_col, db_col in column_map.items():
                    if df_col in row:
                        row_values.append(row[df_col])
                    else:
                        # Default values
                        if db_col == 'amount':
                            row_values.append(0.0)
                        else:
                            row_values.append('')
                            
                values.append(tuple(row_values))
            
            # Generate query
            columns = ', '.join(column_map.values())
            placeholders = ', '.join(['?'] * len(column_map))
            
            # Insert batch
            cursor = self.conn.cursor()
            cursor.executemany(
                f"INSERT INTO invoices ({columns}) VALUES ({placeholders})",
                values
            )
            
            rows_added += len(batch)
        
        self.conn.commit()
        self.set_last_update('invoices_last_update')
        return rows_added
    
    def get_projects_df(self, conditions=None):
        """
        Get projects as a DataFrame with optional filtering
        
        Args:
            conditions: Dictionary of column=value pairs for filtering
            
        Returns:
            DataFrame with projects data
        """
        query = "SELECT * FROM projects"
        params = []
        
        if conditions:
            # Build WHERE clause from conditions
            where_clauses = []
            for column, value in conditions.items():
                if isinstance(value, (list, tuple)):
                    # For IN clauses
                    placeholders = ','.join(['?'] * len(value))
                    where_clauses.append(f"{column} IN ({placeholders})")
                    params.extend(value)
                else:
                    where_clauses.append(f"{column} = ?")
                    params.append(value)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        # Execute query and get DataFrame
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Rename columns to match the original format
        column_map = {
            'project_no': 'Project No',
            'clients': 'Clients',
            'type': 'Type',
            'status': 'Status',
            'service_line': 'Service Line',
            'market_segment': 'Market Segment',
            'pm': 'PM',
            'tl': 'TL',
            'project_description': 'Project Description',
            'award_date': 'Award Date',
            'contracted_amount': 'Contracted Amount'
        }
        
        # Rename only the columns that exist in the result
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)
        
        # Format the Contracted Amount as currency if present
        if 'Contracted Amount' in df.columns:
            df['Contracted Amount'] = df['Contracted Amount'].apply(
                lambda x: f"${x:,.2f}" if pd.notnull(x) and x > 0 else ""
            )
        
        return df
    
    def get_merged_df(self, conditions=None, start_date=None, end_date=None):
        """
        Get timesheet entries as a DataFrame with optional filtering
        
        Args:
            conditions: Dictionary of column=value pairs
            start_date: Optional start date for filtering (YYYY-MM-DD)
            end_date: Optional end date for filtering (YYYY-MM-DD)
            
        Returns:
            DataFrame with timesheet data, joined with project info
        """
        # Start with base query joining timesheet with projects
        query = """
        SELECT t.*, p.clients, p.type, p.status, p.service_line, p.market_segment, p.pm, p.tl,
               p.project_description, p.award_date, p.contracted_amount
        FROM timesheet_entries t
        LEFT JOIN projects p ON t.project_no = p.project_no
        """
        params = []
        where_clauses = []
        
        # Add date range filter
        if start_date:
            where_clauses.append("t.local_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("t.local_date <= ?")
            params.append(end_date)
        
        # Add other condition filters
        if conditions:
            for column, value in conditions.items():
                table_prefix = 't.' if column in ('project_no', 'employee', 'personel', 'local_date', 
                                                  'hours', 'day_cost', 'service_item', 'staff_type',
                                                  'jobcode_2', 'jobcode_3') else 'p.'
                                                  
                if isinstance(value, (list, tuple)):
                    # For IN clauses
                    placeholders = ','.join(['?'] * len(value))
                    where_clauses.append(f"{table_prefix}{column} IN ({placeholders})")
                    params.extend(value)
                else:
                    where_clauses.append(f"{table_prefix}{column} = ?")
                    params.append(value)
        
        # Add WHERE clause if there are conditions
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Execute query and get DataFrame
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Rename columns to match the original format
        column_map = {
            'project_no': 'Project No',
            'employee': 'Employee',
            'personel': 'Personel',
            'local_date': 'local_date',
            'service_item': 'Service Item',
            'clients': 'Clients',
            'type': 'Type',
            'status': 'Status',
            'service_line': 'Service Line',
            'market_segment': 'Market Segment',
            'pm': 'PM',
            'tl': 'TL',
            'project_description': 'Project Description',
            'award_date': 'Award Date',
            'contracted_amount': 'Contracted Amount'
        }
        
        # Rename only the columns that exist
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)
        
        # Convert local_date back to datetime
        if 'local_date' in df.columns:
            df['local_date'] = pd.to_datetime(df['local_date'])
        
        return df
    
    def get_invoices_df(self, conditions=None, start_date=None, end_date=None):
        """
        Get invoices as a DataFrame with optional filtering
        
        Args:
            conditions: Dictionary of column=value pairs
            start_date: Optional start date for filtering (YYYY-MM-DD)
            end_date: Optional end date for filtering (YYYY-MM-DD)
            
        Returns:
            DataFrame with invoice data
        """
        query = """
        SELECT i.*, p.clients, p.type, p.status, p.service_line, p.market_segment, p.pm, p.tl, 
               p.project_description
        FROM invoices i
        LEFT JOIN projects p ON i.project_no = p.project_no
        """
        params = []
        where_clauses = []
        
        # Add date range filter
        if start_date:
            where_clauses.append("i.invoice_date >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("i.invoice_date <= ?")
            params.append(end_date)
        
        # Add other condition filters
        if conditions:
            for column, value in conditions.items():
                table_prefix = 'i.' if column in ('project_no', 'invoice_no', 'invoice_date', 
                                                 'amount', 'payment_status', 'payment_date') else 'p.'
                                                 
                if isinstance(value, (list, tuple)):
                    # For IN clauses
                    placeholders = ','.join(['?'] * len(value))
                    where_clauses.append(f"{table_prefix}{column} IN ({placeholders})")
                    params.extend(value)
                else:
                    where_clauses.append(f"{table_prefix}{column} = ?")
                    params.append(value)
        
        # Add WHERE clause if needed
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Execute query
        df = pd.read_sql_query(query, self.conn, params=params)
        
        # Rename columns to match original format
        column_map = {
            'project_no': 'Project No',
            'invoice_no': 'Invoice No',
            'invoice_date': 'Invoice Date',
            'amount': 'Actual',
            'payment_status': 'Payment',
            'payment_date': 'Payment Date',
            'clients': 'Clients',
            'type': 'Type',
            'status': 'Status',
            'service_line': 'Service Line',
            'market_segment': 'Market Segment',
            'pm': 'PM',
            'tl': 'TL',
            'project_description': 'Project Description'
        }
        
        # Rename only existing columns
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)
        
        # Format amounts and convert dates
        if 'Actual' in df.columns:
            df['Actual'] = df['Actual'].apply(
                lambda x: f"${x:,.2f}" if pd.notnull(x) and x > 0 else ""
            )
        if 'Invoice Date' in df.columns:
            df['Invoice Date'] = pd.to_datetime(df['Invoice Date'])
        if 'Payment Date' in df.columns:
            df['Payment Date'] = pd.to_datetime(df['Payment Date'])
        
        return df
        
    def save_last_update_files(self, pickle_dir="operations/pickles"):
        """Save the last update information to text files for display in the Dash app"""
        os.makedirs(pickle_dir, exist_ok=True)
        
        # Save overall last update
        with open(os.path.join(pickle_dir, "last_update.txt"), "w") as f:
            f.write(self.last_update)
        
        # Save last data update
        data_last_update = self.get_last_update('timesheet_last_update')
        if not data_last_update:
            data_last_update = self.last_update
            
        with open(os.path.join(pickle_dir, "last_data_update.txt"), "w") as f:
            f.write(data_last_update)