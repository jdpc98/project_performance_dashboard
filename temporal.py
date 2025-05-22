import sqlite3
conn = sqlite3.connect("operations/smart_decon.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS monthly_report_charts (
    report_date TEXT PRIMARY KEY,
    chart_json TEXT,
    last_updated TEXT
)
""")
conn.commit()
conn.close()