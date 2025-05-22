import sqlite3
import pandas as pd

def get_service_item_summary_from_db(selected_project=None, selected_years=None, db_path="operations/smart_decon.db"):
    """
    Load precomputed service_item_summary from SQLite for fast Dash rendering.
    Optionally filter by project and years.
    """
    query = "SELECT * FROM service_item_summary"
    params = []
    filters = []
    if selected_project:
        filters.append("[Project No] = ?")
        params.append(selected_project)
    if selected_years:
        if not isinstance(selected_years, list):
            selected_years = [selected_years]
        years_placeholder = ','.join(['?'] * len(selected_years))
        filters.append(f"strftime('%Y', last_updated) IN ({years_placeholder})")
        params.extend([str(y) for y in selected_years])
    if filters:
        query += " WHERE " + " AND ".join(filters)
    df = pd.read_sql_query(query, sqlite3.connect(db_path), params=params)
    return df

def get_employee_project_summary_from_db(selected_project=None, selected_years=None, db_path="operations/smart_decon.db"):
    """
    Load precomputed employee_project_summary from SQLite for fast Dash rendering.
    Optionally filter by project and years.
    """
    query = "SELECT * FROM employee_project_summary"
    params = []
    filters = []
    if selected_project:
        filters.append("[Project No] = ?")
        params.append(selected_project)
    if selected_years:
        if not isinstance(selected_years, list):
            selected_years = [selected_years]
        years_placeholder = ','.join(['?'] * len(selected_years))
        filters.append(f"strftime('%Y', last_updated) IN ({years_placeholder})")
        params.extend([str(y) for y in selected_years])
    if filters:
        query += " WHERE " + " AND ".join(filters)
    df = pd.read_sql_query(query, sqlite3.connect(db_path), params=params)
    return df

def get_client_subtable_from_db(client, db_path="operations/smart_decon.db"):
    """
    Load precomputed client_project_summary_<client> from SQLite for fast Dash rendering.
    """
    table = f"client_project_summary_{client.replace(' ', '_').replace('.', '').replace('-', '').lower()}"
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

def get_monthly_report_data_from_db(selected_date, db_path="operations/smart_decon.db"):
    """
    Load precomputed monthly report data for the given date from SQLite.
    Returns (report_data_df, bar_chart_json) or (None, None) if not found.
    """
    date_key = pd.to_datetime(selected_date).strftime('%Y-%m-%d')
    conn = sqlite3.connect(db_path)
    try:
        # Load report data
        df = pd.read_sql_query(
            "SELECT * FROM monthly_report_data WHERE report_date = ?",
            conn, params=(date_key,)
        )
        # Load bar chart JSON
        cur = conn.execute("SELECT chart_json FROM monthly_report_charts WHERE report_date = ?", (date_key,))
        row = cur.fetchone()
        chart_json = row[0] if row else None
        return df, chart_json
    except Exception:
        return None, None
    finally:
        conn.close()
