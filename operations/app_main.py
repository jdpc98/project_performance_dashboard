import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme, Symbol
import plotly.express as px
import pandas as pd
import os 
import weasyprint
import io
from dash import dcc
# Import our separate modules
import data_processing
import config
from data_processing import calculate_new_er,extract_project_no, standardize_project_no, print_green, print_cyan, print_orange, print_red, last_update, generate_monthly_report_data
from config import TABLE_STYLE, TABLE_CELL_STYLE, TABLE_CELL_CONDITIONAL, RIGHT_TABLE_RED_STYLE
import base64
import plotly.io as pio
from data_processing import get_project_log_data


#########################################################################################################################
PICKLE_OUTPUT_DIR = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"
#################################################################################################################
# Upload data to dataframes from pickle files 
global_merged_df = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_merged_df.pkl"))
global_projects_df = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_projects_df.pkl"))
global_invoices = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_invoices.pkl"))
global_raw_invoices = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_raw_invoices.pkl"))
#################################################################################################################
#func for 1928 extra filter [jobcode 3 inclusion on project no]

# Import last update date for display on dash
with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "r") as f:
    last_update = f.read().strip()

# Import last data update date for display on dash
try:
    with open(os.path.join(PICKLE_OUTPUT_DIR, "last_data_update.txt"), "r") as f:
        last_data_update = f.read().strip()
except FileNotFoundError:
    last_data_update = "Unknown"

"""
def get_week_in_month(date_obj):

Return a consistent week number within a month.
All dates in the same week will have the same week number,
even if they span across two months.

# Get the Monday of the current week
monday_of_week = date_obj - pd.Timedelta(days=date_obj.weekday())

# Use the Monday's month to determine which month this week belongs to
week_month = monday_of_week.month
week_year = monday_of_week.year

# If the date is in a different month than the Monday,
# we'll still use the Monday's month for consistency
if date_obj.month != week_month:
    # The date is in the next month, but belongs to the previous month's week
    # We'll get the week number from the Monday
    first_day = monday_of_week.replace(day=1)
    days_since_month_start = (monday_of_week - first_day).days
    return days_since_month_start // 7 + 1
else:
    # Normal case: date is in the same month as the Monday of its week
    first_day = date_obj.replace(day=1)
    first_monday = first_day
    while first_monday.weekday() != 0:  # Monday is 0
        first_monday += pd.Timedelta(days=1)
    
    # Calculate the week number (1-based)
    days_since_first_monday = (date_obj - first_monday).days
    return days_since_first_monday // 7 + 1
"""



def conditional_extract_project_no(row):
    """
    If jobcode_2 starts with '1928', use the first 7 characters of jobcode_3;
    otherwise, use the first 7 characters of jobcode_2.
    """
    jc2 = str(row.get('jobcode_2', '')).strip()
    jc3 = str(row.get('jobcode_3', '')).strip()
    
    if jc2.startswith("1928"):
        # For all 1928* jobcodes in jobcode_2, use jobcode_3's first 7 characters
        return jc3[:7].strip()
    else:
        # Otherwise, just use jobcode_2's first 7
        return jc2[:7].strip()

#################################################################################################################
#create new id for all project storage
#if 'Project No' not in global_merged_df.columns:
#    global_merged_df['Project No'] = global_merged_df.apply(conditional_extract_project_no, axis=1)
    
global_merged_df['Project No'] = global_merged_df.apply(conditional_extract_project_no, axis=1)

#import last update date for display on dash
with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "r") as f:
    last_update = f.read().strip()
#################################################################################################################
# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
# Define the Layout with Tabs in the desired order:
# Dashboard, then Client Summary, then Add New Project
app.layout = dcc.Tabs(id='tabs-example', value='tab-dashboard', children=[
    # Dashboard Tab
    dcc.Tab(label='Dashboard', value='tab-dashboard', children=[
        html.Div([
            # Logo at the top
            html.Div(
                [html.Img(src='data:image/png;base64,{}'.format(config.encoded_logo), style={'height': '75px'})],
                style={'textAlign': 'center', 'padding': '10px'}
            ),
            html.H1("Project Performance", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
            # Filter section for project details
            html.Div([
                html.H3("Filter Jobcodes by Project Details", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
                dcc.Dropdown(
                    id='filter-clients',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Clients'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Clients"
                ),
                dcc.Dropdown(
                    id='filter-type',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Type'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Type"
                ),
                dcc.Dropdown(
                    id='filter-status',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Status'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Status"
                ),
                dcc.Dropdown(
                    id='filter-service',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Service Line'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Service Line"
                ),
                dcc.Dropdown(
                    id='filter-market',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Market Segment'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Market Segment"
                ),
                dcc.Dropdown(
                    id='filter-pm',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['PM'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select PM"
                )
            ], style={'width': '80%', 'margin': 'auto', 'padding': '20px', 'textAlign': 'center'}),
            # Jobcode selection dropdown
            html.Div([
                html.Label("Select Jobcode:"),
                dcc.Dropdown(
                    id='jobcode-dropdown',
                    options=[],  # Updated via callback
                    clearable=False
                )
            ], style={'width': '30%', 'margin': 'auto'}),
            # Year selection dropdown
            html.Div([
                html.Div([
                    html.Label("Select Year(s):"),
                    dcc.Dropdown(
                        id='year-dropdown',
                        
                        
                        options=[{'label': str(y), 'value': str(y)} for y in range(2017, 2026)],
                        value=[str(y) for y in range(2017, 2026)],  # Default selected years
                        
                        multi=True,
                        clearable=False
                    )
                ], style={'width': '30%', 'margin': 'auto'})
            ], style={'textAlign': 'center', 'paddingBottom': '20px'}),
            # Project description and award date placeholders
            html.Div(id='project-description', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
            html.Div(id='award-date', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
            # Two tables for project details and cost/contract details
            html.Div([
                html.Div([
                    html.H2("Project Details", style={'textAlign': 'center'}),
                    dash_table.DataTable(
                        id='project-table-left',
                        columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],
                        data=[],
                        style_table=config.TABLE_STYLE,
                        #style_cell=config.TABLE_CELL_STYLE,
                        style_cell={'textAlign': 'left', 'padding': '5px', 'fontFamily': 'Calibri, sans-serif'},
                        style_cell_conditional=config.TABLE_CELL_CONDITIONAL
                    )
                ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '10px'}),
                html.Div([
                    html.H2("Cost & Contract Details", style={'textAlign': 'center'}),
                    

                        dash_table.DataTable(
                        id='project-table-right',
                        #columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],



                        #add hidden numeric values for color coding 
                        columns=[{'name': 'Field', 'id': 'Field', 'type': 'text'},
                        {'name': 'Value', 'id': 'Value', 'type': 'text'},
                        # The hidden numeric column
                        {'name': 'Value_num', 'id': 'Value_num', 'type': 'numeric'}],
                        
                        
                        
                        data=[],
                        # Hide header cells for Value_num
                        style_header_conditional=[{'if': {'column_id': 'Value_num'},'display': 'none'}],
                        #style_data_conditional=config.RIGHT_TABLE_RED_STYLE,
                        style_data_conditional=config.DATA_CONDITIONAL_ER,
                        style_table=config.TABLE_STYLE,
                        style_cell=config.TABLE_CELL_STYLE,
                        #style_cell_conditional=config.TABLE_CELL_CONDITIONAL,
                        style_cell_conditional=[{'if': {'column_id': 'Field'}, 'width': '40%'},{'if': {'column_id': 'Value'}, 'width': '60%'},{'if': {'column_id': 'Value_num'},'display': 'none'}],
                        
                    )
                ], style={'width': '40%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '10px', 'margin': '10px'})
            ], style={'textAlign': 'center'}),
            
            html.Div([
                html.Div([
                    html.H2("Service Item Details", style={'textAlign': 'left'}),
                    dash_table.DataTable(
                        id='service-item-table',
                        columns=[],  # set via callback
                        data=[],     # set via callback
                        #style_table={'width': '100%'},
                        style_table=config.TABLE_STYLE,
                        style_cell=config.TABLE_CELL_STYLE,
                    )
                ], style={
                    'width': '30%',
                    'marginRight': '10%',
                    'display': 'inline-block',
                    'verticalAlign': 'top'
                }),

                html.Div([
                    html.H2("Project Invoices", style={'textAlign': 'left'}),
                    dash_table.DataTable(
                        id='invoice-table',
                        columns=[],
                        data=[],
                        #style_table={'width': '50%'},
                        style_table=config.TABLE_STYLE,
                        style_cell=config.TABLE_CELL_STYLE,
                    )
                ], style={
                    'width': '30%',
                    'display': 'inline-block',
                    'verticalAlign': 'top'
                }),
            ], style={
                'display': 'flex',
                'alignItems': 'flex-start',  # top-align the child Divs
                'justifyContent': 'center'
            }),

            
            
            # Two small pie charts: total hours and total cost per service item
            html.Div([
                html.Div([
                    html.H2("Total Hours per Service Item", style={'textAlign': 'center'}),
                    dcc.Graph(id='service-hours-pie-chart', style={'height': '300px'})
                ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'}),
                html.Div([
                    html.H2("Total Cost per Service Item", style={'textAlign': 'center'}),
                    dcc.Graph(id='service-cost-pie-chart', style={'height': '300px'})
                ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'})
            ], style={'textAlign': 'center', 'paddingTop': '20px'}),
            # Pie charts for time and cost distributions by employee
            html.H2("Time Distribution by Employee", style={'textAlign': 'center', 'paddingTop': '20px'}),
            html.Div(dcc.Graph(id='pie-chart'), style={'width': '60%', 'margin': '0 auto'}),
            html.Div([
                html.H2("Cost Distribution by Employee", style={'textAlign': 'center'}),
                html.Div(dcc.Graph(id='cost-pie-chart'), style={'width': '60%', 'margin': '0 auto'})
            ], style={'textAlign': 'center', 'paddingTop': '20px'}),
            #show last run date
            html.Div(
            f"Latest Dashboard Update(Latest Run Date): {last_update}",
            style={'color': 'gray', 'font-size': '12px', 'text-align': 'center', 'margin-top': '20px'}
            ),
            #show last run date
            html.Div(
            f"Latest Data Update: {last_data_update}",
            style={'color': 'gray', 'font-size': '12px', 'text-align': 'center', 'margin-top': '20px'}
            ),
            html.Div([
                html.Button("Export Dashboard to Excel", id="export-excel-dashboard", n_clicks=0),
                dcc.Download(id="download-excel-dashboard")
            ], style={'textAlign': 'center', 'marginTop': '20px'}),

            html.Div([
                html.Button("Export Dashboard to PDF", id="export-pdf-dashboard", n_clicks=0),
                dcc.Download(id="download-pdf-dashboard")
            ], style={'textAlign': 'center', 'marginTop': '10px'})
        ])
        
        
    ]),
    

    # ----------------------------------------------------------------
    # TAB 2: CLIENT SUMMARY
    # ----------------------------------------------------------------
    dcc.Tab(label='Client Summary', value='tab-clients', children=[
        html.Div([
            # Two overall pie charts (aggregated over all clients)
            html.Div([
                html.Div([
                    dcc.Graph(id='client-total-cost-pie', style={'height': '450px'})
                ], style={'width': '600px', 'display': 'inline-block', 'padding': '10px'}),
                html.Div([
                    dcc.Graph(id='client-total-hours-pie', style={'height': '450px'})
                ], style={'width': '600px', 'display': 'inline-block', 'padding': '10px'})
            ], style={'textAlign': 'center'}),
            
            
            
            # Dropdown to choose the client
            html.Div([
                html.Label("Select Client:", style={'fontFamily': 'Calibri, sans-serif'}),
                dcc.Dropdown(
                    id='client-dropdown',
                    options=[{'label': c, 'value': c} 
                             for c in sorted(global_projects_df['Clients'].dropna().unique())],
                    placeholder="Type or select a client...",
                    clearable=True
                )
            ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),
            html.Hr(),
                      
                      
            html.H3("Client Summary", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),          
            
            # Title for Client Summary Table
            html.H3("Client Project Status", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
        
            # Client Summary Table
            dash_table.DataTable(
                id='client-summary-table',
                columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}],
                data=[],
                style_table={'width': '40%', 'margin': 'auto', 'overflowY': 'auto'},
                #style_cell=TABLE_CELL_STYLE
                style_cell={'textAlign': 'left', 'fontFamily': 'Calibri, sans-serif'}
            ),
            # Title for Detailed Projects Table
            html.H3("Project Summary", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif', 'margin-top': '20px'}),
        
            # Detailed Projects Table for the selected client
            dash_table.DataTable(
                id='client-projects-table',
                columns=[],  # set via callback
                data=[],     # set via callback
                style_table={'width': '80%', 'margin': 'auto', 'overflowY': 'auto'},
                style_cell={'textAlign': 'left', 'fontFamily': 'Calibri, sans-serif'},
                style_data_conditional=config.RIGHT_TABLE_RED_STYLE

            ), # New: Date range picker for invoice dates
            html.Div([
                html.Label("Select Invoice Date Range:", style={'fontFamily': 'Calibri, sans-serif'}),
                dcc.DatePickerRange(
                    id='invoice-date-range',
                    start_date_placeholder_text="Start Date",
                    end_date_placeholder_text="End Date",
                    display_format='YYYY-MM-DD'
                )
            ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),
            
   
            #show last update date
            html.Div(
            f"Latest Data Update: {last_data_update}",
            style={'color': 'gray', 'font-size': '12px', 'text-align': 'center', 'margin-top': '20px'}
            ),
            html.Div([
                html.Button("Export Client Summary to Excel", id="export-excel-client", n_clicks=0),
            dcc.Download(id="download-excel-client")
            ], style={'textAlign': 'center', 'marginTop': '20px'}),
            html.Div([
                html.Button("Export Client Summary to PDF", id="export-pdf-client", n_clicks=0),
                dcc.Download(id="download-pdf-client")
            ], style={'textAlign': 'center', 'marginTop': '10px'})
        ])
        
    ]),
    
    #     # ----------------------------------------------------------------
    # TAB 4*: ADD NEW PROJECT
    # ----------------------------------------------------------------
    dcc.Tab(label='Reports', value='tab-reports', children=[
        html.Div([
            html.H1("Weekly Project Reports", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
            
            # Date selection controls
            html.Div([
                html.Label("Select Month and Year:", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                dcc.DatePickerSingle(
                    id='report-week-picker',  # keeping the name for compatibility
                    date=pd.Timestamp.now().date(),
                    display_format='MMMM YYYY'  # Format to show only month and year
                ),
                html.Div(id='selected-week-display', style={'marginTop': '10px'})
            ], style={'width': '30%', 'margin': 'auto', 'textAlign': 'center', 'padding': '20px'}),
            
            # All projects table
            html.Div([
                html.H2(id='report-table-title', style={'textAlign': 'center'}),
                html.H3("Monthly Invoice Report", style={'textAlign': 'center'}),
                dash_table.DataTable(
                    id='weekly-report-table',
                    columns=[],
                    data=[],
                    style_table={'width': '95%', 'margin': 'auto', 'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'fontFamily': 'Calibri, sans-serif'},
                    style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'column_id': 'ER Invoiced', 'filter_query': '{ER Invoiced} < 1'},
                            'color': 'red', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'ER Invoiced', 'filter_query': '{ER Invoiced} >= 1 && {ER Invoiced} <= 2.5'},
                            'color': 'orange', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'ER Invoiced', 'filter_query': '{ER Invoiced} > 2.5'},
                            'color': 'green', 'fontWeight': 'bold'
                        },
                        
                        
                        {
                            'if': {'column_id': 'ER DECON LLC', 'filter_query': '{ER DECON LLC} < 1'},
                            'color': 'red', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'ER DECON LLC', 'filter_query': '{ER DECON LLC} >= 1 && {ER DECON LLC} <= 2.5'},
                            'color': 'orange', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'ER DECON LLC', 'filter_query': '{ER DECON LLC} > 2.5'},
                            'color': 'green', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'DECON LLC Invoiced', 'filter_query': '{DECON LLC Invoiced} < 1'},
                            'color': 'red', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'DECON LLC Invoiced', 'filter_query': '{DECON LLC Invoiced} >= 1 && {DECON LLC Invoiced} <= 2.5'},
                            'color': 'orange', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'DECON LLC Invoiced', 'filter_query': '{DECON LLC Invoiced} > 2.5'},
                            'color': 'green', 'fontWeight': 'bold'
                        },
                        # Updated conditional formatting for Invoiced % using the numeric column
                        {
                            'if': {'column_id': 'Invoiced %', 'filter_query': '{Invoiced %_num} < 0'},
                            'color': 'red', 'fontWeight': 'bold'  # For N/A values (-1)
                        },
                        {
                            'if': {'column_id': 'Invoiced %', 'filter_query': '{Invoiced %_num} = 0'},
                            'color': 'red', 'fontWeight': 'bold'  # For 0%
                        },
                        {
                            'if': {'column_id': 'Invoiced %', 'filter_query': '{Invoiced %_num} > 0 && {Invoiced %_num} < 60'},
                            'color': 'darkorange', 'fontWeight': 'bold'  # 0-60%
                        },
                        {
                            'if': {'column_id': 'Invoiced %', 'filter_query': '{Invoiced %_num} >= 60 && {Invoiced %_num} < 80'},
                            'color': 'gold', 'fontWeight': 'bold'  # 60-80%
                        },
                        {
                            'if': {'column_id': 'Invoiced %', 'filter_query': '{Invoiced %_num} >= 80 && {Invoiced %_num} < 90'},
                            'color': 'yellowgreen', 'fontWeight': 'bold'  # 80-90%
                        },
                        {
                            'if': {'column_id': 'Invoiced %', 'filter_query': '{Invoiced %_num} >= 90 && {Invoiced %_num} <= 100'},
                            'color': 'forestgreen', 'fontWeight': 'bold'  # 90-100%
                        }
                    ]
                ),
            ], style={'padding': '20px'}),
            
            # Forecast summary table
            html.Div([
                html.H3("Forecast Summary", style={'textAlign': 'center'}),
                dash_table.DataTable(
                    id='forecast-summary-table',
                    columns=[],
                    data=[],
                    style_table={'width': '70%', 'margin': 'auto', 'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'fontFamily': 'Calibri, sans-serif'},
                    style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'column_id': '%Forecast vs Actual', 'filter_query': '{%Forecast vs Actual} < "30%"'},
                            'color': 'red', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': '%Forecast vs Actual', 'filter_query': '{%Forecast vs Actual} >= "30%" && {%Forecast vs Actual} < "75%"'},
                            'color': 'orange', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': '%Forecast vs Actual', 'filter_query': '{%Forecast vs Actual} >= "75%"'},
                            'color': 'green', 'fontWeight': 'bold'
                        }
                    ]
                )
            ], style={'padding': '20px'}),
            
            # Forecast by type table
            html.Div([
                html.H3("Forecast by Type", style={'textAlign': 'center'}),
                dash_table.DataTable(
                    id='forecast-type-table',
                    columns=[],
                    data=[],
                    style_table={'width': '80%', 'margin': 'auto', 'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'fontFamily': 'Calibri, sans-serif'},
                    style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'column_id': 'Percentage Projected vs Actual', 'filter_query': '{Percentage Projected vs Actual} < "30%"'},
                            'color': 'red', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'Percentage Projected vs Actual', 'filter_query': '{Percentage Projected vs Actual} >= "30%" && {Percentage Projected vs Actual} < "75%"'},
                            'color': 'orange', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'column_id': 'Percentage Projected vs Actual', 'filter_query': '{Percentage Projected vs Actual} >= "75%"'},
                            'color': 'green', 'fontWeight': 'bold'
                        },
                        {
                            'if': {'row_index': -1},  # Last row (TOTAL)
                            'fontWeight': 'bold'
                        }
                    ]
                )
            ], style={'padding': '20px'}),
            html.Div([
                html.H2("Projected vs Actual by Project Type", style={'textAlign':'center'}),
                dcc.Graph(id='report-bar-chart')      # <-- placeholder
            ], style={'padding':'20px'}),
            # Export button
            html.Div([
                html.Button("Export to PDF", id="export-weekly-report", n_clicks=0),
                dcc.Download(id="download-weekly-report-pdf")
            ], style={'textAlign': 'center', 'marginTop': '20px', 'marginBottom': '40px'}),
            html.Div(
            f"Latest Data Update: {last_data_update}",
            style={'color': 'gray', 'font-size': '12px', 'text-align': 'center', 'margin-top': '10px', 'marginBottom': '40px'}
        )
        ])
    ]),
    # ----------------------------------------------------------------
    # TAB 4*: ADD NEW PROJECT
    # ----------------------------------------------------------------
    dcc.Tab(label='Add New Project', value='tab-add', children=[
        html.Div([
            html.H3("Add a New Project", style={'textAlign': 'center'}),
            html.Div([
                html.Label("Project No:"),
                dcc.Input(id='input-project-no', type='text', placeholder='Project No')
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Status:"),
                dcc.Dropdown(
                    id='input-status-dropdown',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Status'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Status",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-status-other', type='text', placeholder='Enter new Status'),
                    id='status-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Type:"),
                dcc.Dropdown(
                    id='input-type-dropdown',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Type'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Type",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-type-other', type='text', placeholder='Enter new Type'),
                    id='type-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Service Line:"),
                dcc.Dropdown(
                    id='input-service-line-dropdown',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Service Line'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Service Line",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-service-line-other', type='text', placeholder='Enter new Service Line'),
                    id='service-line-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            
            
            
            html.Div([
                html.Label("Market Segment:"),
                dcc.Dropdown(
                    id='input-market-dropdown',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Market Segment'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Market Segment",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-market-other', type='text', placeholder='Enter new Market Segment'),
                    id='market-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Project Manager (PM):"),
                dcc.Dropdown(
                    id='input-pm-dropdown',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['PM'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select PM",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-pm-other', type='text', placeholder='Enter new PM'),
                    id='pm-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Project Description:"),
                dcc.Input(id='input-project-description', type='text', placeholder='Project Description', style={'width': '100%'})
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("No.:"),
                dcc.Input(id='input-no', type='text', placeholder='No.')
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Clients:"),
                dcc.Dropdown(
                    id='input-clients-dropdown',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(global_projects_df['Clients'].dropna().unique())] + [{'label': 'Other', 'value': 'Other'}],
                    placeholder="Select Clients",
                    clearable=True
                ),
                html.Div(
                    dcc.Input(id='input-clients-other', type='text', placeholder='Enter new Clients'),
                    id='clients-other-div',
                    style={'display': 'none', 'margin-top': '5px'}
                )
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Award Date (YYYY-MM-DD):"),
                dcc.Input(id='input-award-date', type='text', placeholder='Award Date')
            ], style={'margin-bottom': '10px'}),
            html.Div([
                html.Label("Contracted Amount:"),
                dcc.Input(id='input-contracted-amount', type='number', placeholder='Contracted Amount')
            ], style={'margin-bottom': '10px'}),
            html.Button("Add Project", id='submit-new-project'),
            html.Div(id='new-project-message', style={'margin-top': '10px', 'color': 'blue'})
        ], style={'padding': '20px', 'textAlign': 'center'})
    ])
])
#################################################################################################################
# -------------------------------------------------------------------
#  Define all Callbacks (callbacks remain as in your working version)
# -------------------------------------------------------------------
#################################################################################################################
#test for report export to pdf files 

# Callback to update the date display




@app.callback(
    Output('report-bar-chart','figure'),
    Input('report-week-picker','date')
)
def update_report_bar_chart(selected_date):
    import plotly.graph_objects as go
    import pandas as pd

    # 1) regenerate your report_data from your data_processing function
    report_data, all_cols = data_processing.generate_monthly_report_data(
        selected_date,
        global_projects_df,
        global_merged_df,
        global_raw_invoices,
        project_log_path
    )
    df = pd.DataFrame(report_data)
    # drop the TOTAL row if you included it in report_data
    df = df[df['Type'] != 'TOTAL']

    # 2) parse currency strings into floats
    def to_num(x):
        return float(str(x).replace('$','').replace(',','')) if isinstance(x, str) else float(x)

    types   = df['Type'].tolist()
    projected = df['Projected'].map(to_num).tolist()
    actual    = df['Actual'].map(to_num).tolist()

    # 3) build the grouped bar chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=types, y=projected, name='Projected'))
    fig.add_trace(go.Bar(x=types, y=actual,    name='Actual'))
    fig.update_layout(
        barmode='group',
        title='Projected vs Actual by Project Type',
        title_x=0.5,
        xaxis_title='Project Type',
        yaxis_title='Amount (USD)',
        yaxis_tickprefix='$'
    )
    return fig




@app.callback(
    Output('selected-week-display', 'children'),
    Input('report-week-picker', 'date')
)
def update_date_display(selected_date):
    if selected_date:
        date_obj = pd.to_datetime(selected_date)
        month_name = date_obj.strftime('%B')
        year = date_obj.year
        
        # Calculate the week of the month using the same logic as in export function
        # Get the first day of the month
        first_day = date_obj.replace(day=1)
        
        # Find the week number using isocalendar
        first_day_week = first_day.isocalendar()[1]
        current_week = date_obj.isocalendar()[1]
        
        # Calculate week of month (1-based)
        week_of_month = current_week - first_day_week + 1
        
        # Handle edge case where week spans across months/years
        if week_of_month <= 0:
            # We're in the same week as the end of the previous month
            week_of_month = 1
            
        return f"Selected: {month_name} {year} - Week {week_of_month}"
    return ""


############################################

@app.callback(
    Output("download-excel-dashboard", "data"),
    Input("export-excel-dashboard", "n_clicks"),
    [
        State("project-table-left", "data"),
        State("project-table-right", "data"),
        State("service-item-table", "data"),
        State("invoice-table", "data"),
        State("jobcode-dropdown", "value"),
        State("yeare-dropdown", "value"),
    ],
    prevent_initial_call=True
)
def export_dashboard_excel(n_clicks, left_data, right_data, service_data, invoice_data, selected_project, selected_years):
    # Convert table data to DataFrames
    df_left = pd.DataFrame(left_data) if left_data and len(left_data) > 0 else pd.DataFrame()
    df_right = pd.DataFrame(right_data) if right_data and len(right_data) > 0 else pd.DataFrame()
    df_service = pd.DataFrame(service_data) if service_data and len(service_data) > 0 else pd.DataFrame()
    df_invoice = pd.DataFrame(invoice_data) if invoice_data and len(invoice_data) > 0 else pd.DataFrame()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheet_name = "Dashboard Report"
        workbook  = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet

        current_row = 0

        # Write a header for the selected project.
        worksheet.write(current_row, 0, "Selected Project:")
        worksheet.write(current_row, 1, selected_project if selected_project else "All")
        current_row += 2

        # Write the table data to the worksheet:
        if not df_left.empty:
            df_left.to_excel(writer, sheet_name=sheet_name, startrow=current_row, index=False)
            current_row += len(df_left) + 2
        if not df_right.empty:
            df_right.to_excel(writer, sheet_name=sheet_name, startrow=current_row, index=False)
            current_row += len(df_right) + 2
        if not df_service.empty:
            df_service.to_excel(writer, sheet_name=sheet_name, startrow=current_row, index=False)
            current_row += len(df_service) + 2
        if not df_invoice.empty:
            df_invoice.to_excel(writer, sheet_name=sheet_name, startrow=current_row, index=False)
            current_row += len(df_invoice) + 2

        # Generate pie charts using your function.
        from data_processing import update_service_item_pie_charts
        fig_hours, fig_cost = update_service_item_pie_charts(selected_project, selected_years)
        
        # Generate PNG image bytes for each chart:
        img_bytes_hours = fig_hours.to_image(format="png")
        img_bytes_cost = fig_cost.to_image(format="png")
        
        # Insert images into the Excel file:
        # (You might need to adjust the cell positions and scaling)
        worksheet.insert_image(current_row, 0, "hours_chart.png", {'image_data': io.BytesIO(img_bytes_hours)})
        current_row += 20  # adjust as needed
        worksheet.insert_image(current_row, 0, "cost_chart.png", {'image_data': io.BytesIO(img_bytes_cost)})

    output.seek(0)
    filename = f"dashboard_report_{selected_project}.xlsx" if selected_project else "dashboard_report.xlsx"
    return dcc.send_bytes(output.read(), filename)
################################################################################################################
@app.callback(
    Output("download-pdf-dashboard", "data"),
    Input("export-pdf-dashboard", "n_clicks"),
    [
        State("project-table-left", "data"),
        
        State("project-table-right", "data"),
        State("service-item-table", "data"),
        State("invoice-table", "data"),
        State("jobcode-dropdown", "value"),  
        State("years-dropdown", "value")
    ],
    prevent_initial_call=True
)
def export_dashboard_pdf(n_clicks, left_data, right_data, service_data, invoice_data, selected_project, selected_years):
    def data_to_html(data, title):
        if not data or len(data)==0:
            return f"<h2>{title}</h2><p>No data available.</p>"
        df = pd.DataFrame(data)
        return f"<h2>{title}</h2>" + df.to_html(index=False, border=1)
    
    # Generate the two pie chart figures from your function
    # (Assuming update_service_item_pie_charts returns (fig_hours, fig_cost))
    from data_processing import update_service_item_pie_charts
    fig_hours, fig_cost = update_service_item_pie_charts(selected_project, selected_years)
    
    # Convert figures to PNG bytes (using kaleido)
    img_bytes_hours = fig_hours.to_image(format="png")
    img_bytes_cost = fig_cost.to_image(format="png")
    
    # Convert to base64 strings for embedding into HTML:
    img_base64_hours = base64.b64encode(img_bytes_hours).decode('utf-8')
    img_base64_cost = base64.b64encode(img_bytes_cost).decode('utf-8')
    
    # Build the HTML string including the images
    html_string = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          @page {{
            size: letter landscape; /* US Letter in landscape orientation */
            margin-left: 2cm;     /* INCREASED from 0.75cm to 2cm */
            margin-right: 2cm;    /* INCREASED from 0.75cm to 2cm */
            margin-top: 1.5cm;    /* INCREASED from 1cm */
            margin-bottom: 1.5cm; /* INCREASED from 1cm */
          }}
          body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            font-size: 9px;
          }}
          table {{
            width: 90%;          /* REDUCED from 98% to 90% */
            border-collapse: collapse;
            table-layout: fixed;
            margin: 0 auto;      /* Centers the table */
            max-width: 90%;      /* Added max-width constraint */
          }}
          th, td {{ border: 1px solid black; border-collapse: collapse; padding: 5px; }}
          h1, h2 {{ text-align: center; }}
          img {{ display: block; margin-left: auto; margin-right: auto; max-width: 90%; }}
        </style>
      </head>
      <body>
        <h1>Dashboard Report</h1>
        {data_to_html(left_data, "Project Details")}
        {data_to_html(right_data, "Cost & Contract Details")}
        {data_to_html(service_data, "Service Item Details")}
        {data_to_html(invoice_data, "Invoices")}
        <h2>Total Hours per Service Item</h2>
        <img src="data:image/png;base64,{img_base64_hours}">
        <h2>Total Cost per Service Item</h2>
        <img src="data:image/png;base64,{img_base64_cost}">
      </body>
    </html>
    """
    pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
    return dcc.send_bytes(pdf_bytes, "dashboard_report.pdf")
#################################################################################################################
@app.callback(
    Output("download-pdf-client", "data"),
    Input("export-pdf-client", "n_clicks"),
    [State("client-dropdown", "value"),
     State("invoice-date-range", "start_date"),
     State("invoice-date-range", "end_date")],
    prevent_initial_call=True
)
def export_client_pdf(n_clicks, selected_client, start_date, end_date):
    if not selected_client:
        return dcc.send_string("No data", "empty.pdf")
    
        # 1. Filter projects for the selected client.
    df_client_projects = global_projects_df[
        global_projects_df['Clients'].str.strip().str.lower() == selected_client.lower()
    ].copy()
    
    # 2. Filter invoices by the date range.
    df_invoices_filtered = global_raw_invoices.copy()
    if start_date and end_date:
        df_invoices_filtered['Invoice Date'] = pd.to_datetime(
            df_invoices_filtered['Invoice Date'], errors='coerce')
        df_invoices_filtered = df_invoices_filtered[
            (df_invoices_filtered['Invoice Date'] >= start_date) &
            (df_invoices_filtered['Invoice Date'] <= end_date)
        ]
    invoices_grouped = df_invoices_filtered.groupby('Project No', as_index=False)['Actual'].sum()
    invoices_grouped.rename(columns={'Actual': 'InvoiceNum'}, inplace=True)
    
    # 3. Filter timesheet data by the same date range.
    df_timesheet_filtered = global_merged_df.copy()
    if start_date and end_date:
        df_timesheet_filtered['local_date'] = pd.to_datetime(
            df_timesheet_filtered['local_date'], errors='coerce')
        df_timesheet_filtered = df_timesheet_filtered[
            (df_timesheet_filtered['local_date'] >= start_date) &
            (df_timesheet_filtered['local_date'] <= end_date)
        ]
    # Extract "Project No" from jobcode_2
    df_timesheet_filtered['Project No'] = df_timesheet_filtered['jobcode_2'].apply(extract_project_no)
    cost_grouped = df_timesheet_filtered.groupby('Project No', as_index=False)['day_cost'].sum()
    cost_grouped.rename(columns={'day_cost': 'CostNum'}, inplace=True)
    
    # 4. Standardize the 'Project No' strings.
    invoices_grouped['Project No'] = (
        invoices_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no))
    cost_grouped['Project No'] = (
        cost_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no))
    df_client_projects['Project No'] = (
        df_client_projects['Project No'].astype(str).str.strip().apply(standardize_project_no))
    
    # 5. Merge the invoices and timesheet cost into the client projects.
    df_detail = pd.merge(df_client_projects, invoices_grouped, on='Project No', how='left')
    df_detail = pd.merge(df_detail, cost_grouped, on='Project No', how='left')
    
    # 6. Parse numeric values and format the cost columns.
    df_detail['Contracted Amount Parsed'] = df_detail['Contracted Amount'].apply(parse_contract)
    df_detail['TotalCostNum'] = df_detail['CostNum'].fillna(0)
    
    df_detail['Total Cost'] = df_detail['TotalCostNum'].apply(
        lambda x: f"${x:,.2f}" if x > 0 else "N/A")
    df_detail['Total Invoice'] = df_detail['InvoiceNum'].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) and x > 0 else "N/A")
    df_detail['Contracted Amount'] = df_detail['Contracted Amount Parsed'].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
    
    df_detail['ER Contract'] = df_detail.apply(safe_divide_contract, axis=1)
    df_detail['ER Invoiced'] = df_detail.apply(safe_divide_invoiced, axis=1)
    df_detail['ER Contract'] = df_detail['ER Contract'].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
    df_detail['ER Invoiced'] = df_detail['ER Invoiced'].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
    
    # You can build an HTML table from it:
    html_string = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          table, th, td {{ border: 1px solid black; border-collapse: collapse; padding: 5px; }}
        </style>
      </head>
      <body>
        <h1>Client Summary Report for {selected_client}</h1>
        {df_detail.to_html(index=False)}
      </body>
    </html>
    """
    pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
    return dcc.send_bytes(pdf_bytes, "client_summary_report.pdf")
################################################################################################################
@app.callback(
    Output("download-excel-client", "data"),
    Input("export-excel-client", "n_clicks"),
    [State("client-dropdown", "value"),
     State("invoice-date-range", "start_date"),
     State("invoice-date-range", "end_date")],
    prevent_initial_call=True
)
def export_client_excel(n_clicks, selected_client, start_date, end_date):
    if not selected_client:
        return dcc.send_data_frame(pd.DataFrame().to_excel, "empty.xlsx", index=False)
    
    # Replicate the filtering logic from update_client_summary
    df_client_projects = global_projects_df[
        global_projects_df['Clients'].str.strip().str.lower() == selected_client.lower()
    ].copy()
    
    # Filter invoices by date
    df_invoices_filtered = global_raw_invoices.copy()
    if start_date and end_date:
        df_invoices_filtered['Invoice Date'] = pd.to_datetime(df_invoices_filtered['Invoice Date'], errors='coerce')
        df_invoices_filtered = df_invoices_filtered[
            (df_invoices_filtered['Invoice Date'] >= start_date) & (df_invoices_filtered['Invoice Date'] <= end_date)
        ]
    invoices_grouped = df_invoices_filtered.groupby('Project No', as_index=False)['Actual'].sum()
    invoices_grouped.rename(columns={'Actual': 'InvoiceNum'}, inplace=True)
    
    # Filter timesheet data by date
    df_timesheet_filtered = global_merged_df.copy()
    if start_date and end_date:
        df_timesheet_filtered['local_date'] = pd.to_datetime(df_timesheet_filtered['local_date'], errors='coerce')
        df_timesheet_filtered = df_timesheet_filtered[
            (df_timesheet_filtered['local_date'] >= start_date) & (df_timesheet_filtered['local_date'] <= end_date)
        ]
    df_timesheet_filtered['Project No'] = df_timesheet_filtered['jobcode_2'].apply(extract_project_no)
    cost_grouped = df_timesheet_filtered.groupby('Project No', as_index=False)['day_cost'].sum()
    cost_grouped.rename(columns={'day_cost': 'CostNum'}, inplace=True)
    
    # Merge invoices and cost into the client projects
    df_detail = df_client_projects.copy()
    df_detail['Project No'] = df_detail['Project No'].astype(str).str.strip().apply(standardize_project_no)
    invoices_grouped['Project No'] = invoices_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no)
    cost_grouped['Project No'] = cost_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no)
    df_detail = pd.merge(df_detail, invoices_grouped, on='Project No', how='left')
    df_detail = pd.merge(df_detail, cost_grouped, on='Project No', how='left')
    
    # Here goes any additional formatting 
    #
    
    # Now write to an Excel file in-memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_detail.to_excel(writer, sheet_name="Client Summary", index=False)
    output.seek(0)
    return dcc.send_bytes(output.read(), "client_summary_report.xlsx")
#################################################################################################################

def parse_money(val):
    """
    Safely convert a string like '$2,300' to float 2300.0.
    Returns None if it fails or if val is NaN/None.
    """
    if pd.isnull(val):
        return None
    try:
        # Remove '$', commas, and whitespace, then convert to float.
        cleaned = str(val).replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except:
        return None

def keep_second_number(val):
    """
    Splits the value on whitespace; if two or more parts exist,
    returns the last part; otherwise, returns the first.
    """
    parts = str(val).split()
    if len(parts) >= 2:
        return parts[-1]
    return parts[0] if parts else ""

def revert_money(s):
    """
    Converts a formatted money string like "$4,500.00" to a float.
    Returns 0.0 if conversion fails.
    """
    try:
        return float(s.replace('$', '').replace(',', ''))
    except Exception:
        return 0.0

@app.callback(
    [Output('invoice-table', 'data'),
     Output('invoice-table', 'columns')],
    [Input('jobcode-dropdown', 'value')]
)
def update_invoice_table(selected_jobcode):
    if not selected_jobcode:
        return ([], [])
    
    # Standardize the selected project number.
    project_no_std = standardize_project_no(selected_jobcode)
    
    # Copy raw invoices and filter by project.
    df_invoices = global_raw_invoices.copy()
    df_invoices['Project No'] = df_invoices['Project No'].astype(str).str.strip().apply(standardize_project_no)
    df_invoices = df_invoices[df_invoices['Project No'] == project_no_std]
    if df_invoices.empty:
        return ([], [])
    
    # Rename columns: 'Actual' -> 'Amount'
    rename_map = {}
    if 'Actual' in df_invoices.columns:
        rename_map['Actual'] = 'Amount'
    if 'Payment' in df_invoices.columns:
        rename_map['Payment'] = 'Payment'
    if 'Payment Date' in df_invoices.columns:
        rename_map['Payment Date'] = 'Payment Date'
    df_invoices.rename(columns=rename_map, inplace=True)
    
    # Convert 'Invoice Date' to datetime and format as string.
    df_invoices['Invoice Date'] = pd.to_datetime(df_invoices['Invoice Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    # Convert 'payment Date' to datetime and format as string.
    df_invoices['Payment Date'] = pd.to_datetime(df_invoices['Payment Date'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # Clean "Invoice No": keep only the second (or last) number if there are multiples.
    df_invoices['Invoice No'] = df_invoices['Invoice No'].apply(keep_second_number)
    
    # Process "Amount": Create a helper numeric column and then format it.
    df_invoices['Amount_num'] = df_invoices['Amount'].apply(
        lambda x: revert_money(x) if isinstance(x, str) and x.strip() != "" else (x if pd.notnull(x) else 0)
    )
    df_invoices['Amount'] = df_invoices['Amount_num'].apply(lambda x: f"${x:,.2f}" if x > 0 else "")
    
    # Process Payment: leave it as text.
    if 'Payment' in df_invoices.columns:
        df_invoices['Payment'] = df_invoices['Payment'].fillna('').astype(str).str.strip()
    
    # Create "Recieved_invoices_num": if Payment equals "payment recieved" (case-insensitive), copy Amount_num.
    df_invoices['Recieved_invoices_num'] = df_invoices.apply(
        lambda row: row['Amount_num']
        if row.get('Payment', '').strip().lower() == "payment received"
        else 0,
        axis=1
    )

    df_invoices['Recieved invoices'] = df_invoices['Recieved_invoices_num'].apply(
        lambda x: f"${x:,.2f}" if x > 0 else ""
    )
    
    # Build the columns for the Dash table.
    columns = [
        {'name': 'Invoice Date', 'id': 'Invoice Date'},
        {'name': 'Invoice No',   'id': 'Invoice No'},
        {'name': 'Amount',       'id': 'Amount'},
        {'name': 'Payment',      'id': 'Payment'},
        {'name': 'Payment Date', 'id': 'Payment Date'},
        {'name': 'Received Payments', 'id': 'Recieved invoices'}
    ]
    
    # Append a TOTAL row.
    total_amount = df_invoices['Amount_num'].sum()
    total_recieved = df_invoices['Recieved_invoices_num'].sum()
    total_row = {
        'Invoice Date': 'TOTAL',
        'Invoice No': '',
        'Amount': f"${total_amount:,.2f}" if total_amount > 0 else "",
        'Payment': '',
        'Payment Date': '',
        'Recieved invoices': f"${total_recieved:,.2f}" if total_recieved > 0 else ""
    }
    df_invoices = pd.concat([df_invoices, pd.DataFrame([total_row])], ignore_index=True)
    
    final_col_ids = [col['id'] for col in columns]
    data = df_invoices[final_col_ids].to_dict('records')
    return data, columns



# Helper function to revert a money string to a float.
#################################################################################################################
@app.callback(
    [
        Output('client-total-cost-pie', 'figure'),
        Output('client-total-hours-pie', 'figure')
    ],
    [Input('tabs-example', 'value')]
)
def update_client_summary_pies(selected_tab):
    import plotly.express as px
    df = global_merged_df.copy()
    df['Project No'] = df['jobcode_2'].apply(extract_project_no)
    df_merged = pd.merge(
        df,
        global_projects_df[['Project No', 'Clients']],
        on='Project No',
        how='left'
    )
    print_green("Shape of df_merged for client pies: " + str(df_merged.shape))
    #print_green(str(df_merged[['Project No', 'Clients', 'day_cost', 'hours']].head(20)))
    
    # Filter out DECON LLC from the data because this is the tab for DECON LLC + DECON SAS, well include decon sas as a contractor on the llc only tab
    
    df_merged_filtered = df_merged[~df_merged['Clients'].str.contains('DECON LLC', case=False, na=False)]
    
    cost_by_client = df_merged_filtered.groupby('Clients', as_index=False)['day_cost'].sum()
    hours_by_client = df_merged_filtered.groupby('Clients', as_index=False)['hours'].sum()
    #print_green("Aggregated cost_by_client:\n" + str(cost_by_client.head(20)))
    #print_green("Aggregated hours_by_client:\n" + str(hours_by_client.head(20)))
    fig_cost = px.pie(cost_by_client, names='Clients', values='day_cost', title="Total Cost by Client")
    fig_hours = px.pie(hours_by_client, names='Clients', values='hours', title="Total Hours by Client")
    fig_cost.update_layout(title={'x': 0.5})
    fig_hours.update_layout(title={'x': 0.5})
    
    fig_cost.update_traces(
        textinfo='none',  # hide the default labels
        hovertemplate='<b>%{label}</b><br>Cost: $%{value:,.2f}<br>Percent: %{percent:.1%}<extra></extra>'
    )
    fig_hours.update_traces(
        textinfo='none',
        hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<br>Percent: %{percent:.1%}<extra></extra>'
    )

    return fig_cost, fig_hours
#################################################################################################################
def parse_contract(x):
    try:
        return float(str(x).replace('$', '').replace(',', '').strip())
    except:
        return None
#################################################################################################################
def safe_divide_contract(row):
    cost = row['CostNum']
    if (isinstance(cost, (int, float)) and cost > 0 and row['Contracted Amount Parsed'] is not None):
        return row['Contracted Amount Parsed'] / cost
    return None
def safe_divide_invoiced(row):
    inv = row['InvoiceNum']
    cost = row['CostNum']
    if isinstance(inv, (int, float)) and inv > 0 and isinstance(cost, (int, float)) and cost > 0 :
        return  inv/cost
    return None
#################################################################################################################
# Callback for Client Summary Tab (with additional metrics and time filter)
@app.callback(
    [
        Output('client-summary-table', 'data'),
        Output('client-summary-table', 'columns'),
        Output('client-projects-table', 'data'),
        Output('client-projects-table', 'columns')
    ],
    [Input('client-dropdown', 'value'),
     Input('invoice-date-range', 'start_date'),
     Input('invoice-date-range', 'end_date')]
)
def update_client_summary(selected_client, start_date, end_date):

    
    
    #return empty if no client is selected in the dropdown
    if not selected_client:
        return [], [], [], []
    
    #filter projects for selected client
    df_client_projects = global_projects_df[
        #global_projects_df['Clients'].str.lower() == selected_client.lower()
        global_projects_df['Clients'].str.strip().str.lower() == selected_client.lower()
    ].copy()
    
    df_detail= df_client_projects.copy()
    
    print_green("Client selected: " + selected_client)
    print_green("Number of projects for client: " + str(len(df_client_projects)))
    
    #build summary data
    possible_statuses = [
        "0-Under Production", "1-Completed Production", "2-Invoicing",
        "3-Retainage Pending", "4-", "5-Canceled", "6-Closed", "7-Frozen"
    ]
    
    
    summary_data = []
    for status in possible_statuses:
        count = df_client_projects['Status'].str.strip().str.lower().eq(status.lower()).sum()
        summary_data.append({"Metric": f"{status} Projects", "Value": f"{count}"})
    summary_columns = [{'name': 'Metric', 'id': 'Metric'},
                       {'name': 'Value', 'id': 'Value'}]
    
    #client_project_nos = df_client_projects['Project No'].unique().tolist()
    # --- Filter Invoices by Date Range ---
    #df_invoices_filtered = global_invoices.copy()
    
    
    #filter invoices by date range using raw invoices df
    df_invoices_filtered = global_raw_invoices.copy()

    # Assume invoices have a column named "Invoice Date"
    if start_date and end_date:
        df_invoices_filtered['Invoice Date'] = pd.to_datetime(df_invoices_filtered['Invoice Date'], errors='coerce')
        df_invoices_filtered = df_invoices_filtered[
            (df_invoices_filtered['Invoice Date'] >= start_date) &
            (df_invoices_filtered['Invoice Date'] <= end_date)
        ]
    #invoices_grouped = df_invoices_filtered.groupby('Project No', as_index=False)['TotalProjectInvoice'].sum()
    #i changed this because im accesing a raw data df
    
    invoices_grouped = df_invoices_filtered.groupby('Project No', as_index=False)['Actual'].sum()
    #invoices_grouped.rename(columns={'Actual': 'TotalProjectInvoice'}, inplace=True)
    invoices_grouped.rename(columns={'Actual': 'InvoiceNum'}, inplace=True)

    #4 filter timesheet data by date range:

    # Also filter timesheet data using the same date range (assuming 'local_date' is the date in the timesheet)
    df_timesheet_filtered = global_merged_df.copy()
    
    if start_date and end_date:
        df_timesheet_filtered['local_date'] = pd.to_datetime(df_timesheet_filtered['local_date'], errors='coerce')
        df_timesheet_filtered = df_timesheet_filtered[
            (df_timesheet_filtered['local_date'] >= start_date) &
            (df_timesheet_filtered['local_date'] <= end_date)
        ]
        
    # Extract "Project No" from "jobcode_2"
    df_timesheet_filtered['Project No'] = df_timesheet_filtered['jobcode_2'].apply(extract_project_no)
    #cost_grouped = df_timesheet_filtered.groupby('Project No', as_index=False)['day_cost'].sum()
    cost_grouped = df_timesheet_filtered.groupby('Project No', as_index=False).agg({
        'day_cost': 'sum',
        'hours': 'sum'  # Add this line to also sum hours
    })
    
    cost_grouped.rename(columns={'day_cost': 'CostNum', 'hours': 'HoursNum'}, inplace=True)
    
    type1_cost_grouped = df_timesheet_filtered[df_timesheet_filtered['staff_type'] == 1].groupby('Project No', as_index=False)['day_cost'].sum()
    type2_cost_grouped = df_timesheet_filtered[df_timesheet_filtered['staff_type'] == 2].groupby('Project No', as_index=False)['day_cost'].sum()
    
    type1_cost_grouped.rename(columns={'day_cost': 'Type1CostNum'}, inplace=True)
    type2_cost_grouped.rename(columns={'day_cost': 'Type2CostNum'}, inplace=True)
    type1_hours_grouped = df_timesheet_filtered[df_timesheet_filtered['staff_type'] == 1].groupby('Project No', as_index=False)['hours'].sum()
    type2_hours_grouped = df_timesheet_filtered[df_timesheet_filtered['staff_type'] == 2].groupby('Project No', as_index=False)['hours'].sum()

    type1_hours_grouped.rename(columns={'hours': 'Type1HoursNum'}, inplace=True)
    type2_hours_grouped.rename(columns={'hours': 'Type2HoursNum'}, inplace=True)

    # Standardize project numbers
    type1_cost_grouped['Project No'] = type1_cost_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no)
    type2_cost_grouped['Project No'] = type2_cost_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no)
    type1_hours_grouped['Project No'] = type1_hours_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no)
    type2_hours_grouped['Project No'] = type2_hours_grouped['Project No'].astype(str).str.strip().apply(standardize_project_no)

    # Merge them into df_detail along with the other data
    df_detail = pd.merge(df_detail, type1_cost_grouped, on='Project No', how='left')
    df_detail = pd.merge(df_detail, type2_cost_grouped, on='Project No', how='left')
    df_detail = pd.merge(df_detail, type1_hours_grouped, on='Project No', how='left')
    df_detail = pd.merge(df_detail, type2_hours_grouped, on='Project No', how='left')

    # Fill NaN values with 0
    df_detail['Type1CostNum'] = df_detail['Type1CostNum'].fillna(0)
    df_detail['Type2CostNum'] = df_detail['Type2CostNum'].fillna(0)
    df_detail['Type1HoursNum'] = df_detail['Type1HoursNum'].fillna(0)
    df_detail['Type2HoursNum'] = df_detail['Type2HoursNum'].fillna(0)

    # Format for display
    df_detail['DECON LLC Cost'] = df_detail['Type1CostNum'].apply(
        lambda x: f"${x:,.2f}" if x > 0 else "N/A"
    )
    df_detail['DECON Col Cost'] = df_detail['Type2CostNum'].apply(
        lambda x: f"${x:,.2f}" if x > 0 else "N/A"
    )
    
        
        # Format for display
    df_detail['DECON LLC Hours'] = df_detail['Type1HoursNum'].apply(
        lambda x: f"{x:.2f}" if x > 0 else "N/A"
    )
    df_detail['DECON Col Hours'] = df_detail['Type2HoursNum'].apply(
        lambda x: f"{x:.2f}" if x > 0 else "N/A"
    )




    #merge filtered data with selected client projects 
    #df_detail = df_client_projects.copy()

    #standardize 'Project No' strings 
    invoices_grouped['Project No'] = (
        invoices_grouped['Project No']
        .astype(str)
        .str.strip()
        .apply(standardize_project_no))

    
    cost_grouped['Project No'] = (
        cost_grouped['Project No']
        .astype(str)
        .str.strip()
        .apply(standardize_project_no))
    df_detail['Project No'] = (
        df_detail['Project No']
        .astype(str)
        .str.strip()
        .apply(standardize_project_no)
    )
    
    
    ##############
    

    #  Merge invoice totals and cost into df_detail
    df_detail = pd.merge(df_detail, invoices_grouped, on='Project No', how='left')
    #
    df_detail = pd.merge(df_detail, cost_grouped, on='Project No', how='left')
    
    
    #  Rename columns so day_cost becomes 'Total Cost'
    #df_detail.rename(columns={'TotalProjectInvoice': 'Total Invoice', 'day_cost': 'Total Cost'}, inplace=True)
    
    print_cyan(type(df_detail['Contracted Amount']))
    print("Contracted Amount column dtype:", df_detail['Contracted Amount'].dtype)
    if not df_detail['Contracted Amount'].empty:
        print("Type of first element:", type(df_detail['Contracted Amount'].iloc[0]))

    
    # Parse the contracted amount into a numeric column
    df_detail['Contracted Amount Parsed'] = df_detail['Contracted Amount'].apply(parse_contract)
    
    
    #  Keep a purely numeric column for cost
    
    
    #compute er fields on numeric coluns
    
    #(Contract = Contracted Amount / total cost, Invoiced = Contracted Amount / invoice total)
    
    
    
    #  Keep numeric cost in df_detail['TotalCostNum']
    df_detail['TotalCostNum'] = df_detail['CostNum'].fillna(0)

    df_detail['ER Contract'] = df_detail.apply(safe_divide_contract, axis=1)
    df_detail['ER Invoiced'] = df_detail.apply(safe_divide_invoiced, axis=1)
    
    #format numeric columns for display
    
    #    - We'll create "Total Cost" and "Total Invoice" display columns from numeric
    df_detail['Total Cost'] = df_detail['CostNum'].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) and x > 0 else "N/A"
    )
    df_detail['Total Cost'] = df_detail['TotalCostNum'].apply(
    lambda x: f"${x:,.2f}" if x > 0 else "N/A")

    df_detail['Total Invoice'] = df_detail['InvoiceNum'].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) and x > 0 else "N/A"
    )
    df_detail['Contracted Amount'] = df_detail['Contracted Amount Parsed'].apply(
        lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A"
    )
    # Convert ER columns to string with 2 decimals, or N/A
    df_detail['ER Contract'] = df_detail['ER Contract'].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"
    )
    df_detail['ER Invoiced'] = df_detail['ER Invoiced'].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"
    )
    df_detail['Total Hours'] = df_detail['HoursNum'].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) and x > 0 else "N/A"
    )

    df_detail['New_ER'] = None
    for idx, row in df_detail.iterrows():
        project_no = row['Project No']
        new_er = calculate_new_er(global_projects_df, project_no, global_merged_df)
        df_detail.at[idx, 'New_ER'] = new_er
    
    # Format the new ER column like the other ER columns
    df_detail['DECON LLC ER'] = df_detail['New_ER'].apply(
        lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"
    )
    """
    # 3) Create a separate display column for total cost
    df_detail['Total Cost'] = df_detail['TotalCostNum'].apply(
        lambda x: f"${x:,.2f}" if x > 0 else "N/A"
    )    
    
    df_detail['ER Invoiced'] = df_detail.apply(
        lambda row: row['Contracted Amount Parsed'] / row['Total Invoice']
            if row['Total Invoice'] and row['Contracted Amount Parsed'] is not None else None,
        axis=1
    )
    def format_currency(x):
        try:
            return f"${float(x):,.2f}"
        except:
            return str(x)
    df_detail['Contracted Amount'] = df_detail['Contracted Amount Parsed'].apply(lambda x: format_currency(x) if x is not None else "N/A")
    df_detail['Total Invoice'] = df_detail['Total Invoice'].apply(lambda x: format_currency(x) if pd.notnull(x) else "N/A")
    df_detail['Total Cost'] = df_detail['Total Cost'].apply(lambda x: format_currency(x) if pd.notnull(x) else "N/A")
    """
    
    
    
    #prepare final cols for project summary table 
    
    detail_cols = ['Project No', 'Status', 'Type', 'Market Segment', 'Contracted Amount',
                   'Total Invoice', 'Total Cost', 'Total Hours','DECON LLC Hours','DECON Col Hours','DECON LLC Cost','DECON Col Cost','ER Contract', 'ER Invoiced', 'DECON LLC ER']
    
    detail_cols = [c for c in detail_cols if c in df_detail.columns]
    df_detail_final = df_detail[detail_cols].copy()
    ###############
    
    totals_row = {col: '' for col in df_detail_final.columns}  # Initialize with empty strings
    totals_row['Project No'] = 'TOTAL'
    
    # Calculate totals from the numeric columns we stored earlier
    total_contracted = df_detail['Contracted Amount Parsed'].sum()
    total_invoice = df_detail['InvoiceNum'].sum()
    total_cost = df_detail['TotalCostNum'].sum()
    total_hours = df_detail['HoursNum'].sum()
    total_type1_cost = df_detail['Type1CostNum'].sum()
    total_type2_cost = df_detail['Type2CostNum'].sum()
    total_type1_hours = df_detail['Type1HoursNum'].sum()
    total_type2_hours = df_detail['Type2HoursNum'].sum()

    totals_row['DECON LLC Cost'] = f"${total_type1_cost:,.2f}" if not pd.isna(total_type1_cost) else "N/A"
    totals_row['DECON Col Cost'] = f"${total_type2_cost:,.2f}" if not pd.isna(total_type2_cost) else "N/A"
   
    totals_row['DECON LLC Hours'] = f"{total_type1_hours:.2f}" if not pd.isna(total_type1_hours) else "N/A"
    totals_row['DECON Col Hours'] = f"{total_type2_hours:.2f}" if not pd.isna(total_type2_hours) else "N/A" 
    # Format the totals for display
    totals_row['Contracted Amount'] = f"${total_contracted:,.2f}" if not pd.isna(total_contracted) else "N/A"
    totals_row['Total Invoice'] = f"${total_invoice:,.2f}" if not pd.isna(total_invoice) else "N/A"
    totals_row['Total Cost'] = f"${total_cost:,.2f}" if not pd.isna(total_cost) else "N/A"
    totals_row['Total Hours'] = f"{total_hours:.2f}" if not pd.isna(total_hours) else "N/A"
    
    
    # Calculate the weighted average ERs (optional)
    """if total_cost > 0 and not pd.isna(total_contracted):
        totals_row['ER Contract'] = f"{total_contracted / total_cost:.2f}"
    else:
        totals_row['ER Contract'] = "N/A"
        
    if total_cost > 0 and not pd.isna(total_invoice):
        totals_row['ER Invoiced'] = f"{total_invoice / total_cost:.2f}"
    else:
        totals_row['ER Invoiced'] = "N/A"
    """    
    # Append the totals row to the DataFrame
    df_detail_final = pd.concat([df_detail_final, pd.DataFrame([totals_row])], ignore_index=True)
     
  
    
    ##########################
    detail_data = df_detail_final.to_dict('records')
    
    #dash table columns with numeric formatting on er columns 
    detail_columns = []
    for col in detail_cols:
        if col in ['ER Contract', 'ER Invoiced', 'DECON LLC ER']:
            detail_columns.append({'name': col, 'id': col, 'type': 'numeric', 'format': Format(precision=2, scheme=Scheme.fixed)})
        else:
            detail_columns.append({'name': col, 'id': col})
            #return all 
    return summary_data, summary_columns, detail_data, detail_columns
#######################################end of update client function 
# Callback for Service Item Details Table#################################################################################################################
@app.callback(
    [Output('service-item-table', 'data'),
     Output('service-item-table', 'columns')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_service_item_table(selected_project_no, selected_years):
    # Now the dropdown value is a project number from the project log.
    if selected_project_no is None:
        return [], []
    
    # Create a new column "Project No" in merged timesheet data if not already present.
    if 'Project No' not in global_merged_df.columns:
        #global_merged_df['Project No'] = global_merged_df['jobcode_2'].apply(extract_project_no)
        df_filtered = global_projects_df[global_projects_df['Project No'] == selected_project_no]

    
    # Filter the merged timesheet data using the selected project number.
    #df_filtered = global_merged_df[global_merged_df['Project No'] == selected_project_no]
    df_filtered = global_merged_df[global_merged_df['Project No'] == selected_project_no].copy()

    # Then, filter further by year if provided.
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    
    
    
    # Debug: print the available columns in df_filtered
    print("Columns in df_filtered:")
    print(df_filtered.columns.tolist())
    
    # Now try printing the subset you need
    print(df_filtered[['Project No','local_date','Service Item','day_cost','hours']].tail(50))
    
    
    
    
    
    # Group by the service item column. For example, assume the column is named "Service Item".
    service_item_col = None
    for col in df_filtered.columns:
        if col.lower().replace("_", " ").strip() == "service item":
            service_item_col = col
            break
    if service_item_col is None:
        return [], []
    
    grouped = df_filtered.groupby(service_item_col, as_index=False).agg({'hours': 'sum', 'day_cost': 'sum'})
    
    # Format display columns.
    grouped['Total Hours'] = grouped['hours'].apply(lambda x: f"{x:.2f}")
    grouped['Total Cost'] = grouped['day_cost'].apply(lambda x: f"${x:,.2f}")
    
    # Compute totals.
    total_hours = grouped['hours'].sum()
    total_cost = grouped['day_cost'].sum()
    
    # Convert to records and append a final "Total" row.
    data = grouped[[service_item_col, 'Total Hours', 'Total Cost']].to_dict('records')
    data.append({
        service_item_col: "Total",
        'Total Hours': f"{total_hours:.2f}",
        'Total Cost': f"${total_cost:,.2f}"
    })
    
    columns = [
        {'name': 'Service Item', 'id': service_item_col},
        {'name': 'Total Hours', 'id': 'Total Hours'},
        {'name': 'Total Cost', 'id': 'Total Cost'}
    ]
    #print("DEBUG: Rows for project =", selected_project_no, "years =", selected_years)
    #print(df_filtered[['Project No','local_date','Service Item','day_cost','hours']].tail(50))

    return data, columns
# Callback for Service Item Pie Charts#################################################################################################################
@app.callback(
    [Output('service-hours-pie-chart', 'figure'),
     Output('service-cost-pie-chart', 'figure')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_service_item_pie_charts(selected_project_no, selected_years):
    if not selected_project_no:
        default_fig = px.pie(title="No data available")
        return default_fig, default_fig

    # Filter by 'Project No' instead of 'jobcode_2'
    df_filtered = global_merged_df[global_merged_df['Project No'] == selected_project_no].copy()

    if selected_years:
        try:
            selected_years_int = [int(y) for y in selected_years]
            df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
        except Exception:
            pass

    if df_filtered.empty:
        default_fig = px.pie(title="No data available after filtering")
        return default_fig, default_fig

    # Identify the "service item" column
    service_item_col = None
    for col in df_filtered.columns:
        if col.lower().replace("_", " ").strip() == "service item":
            service_item_col = col
            break
    if service_item_col is None:
        # Alternatively, try scanning for any column name containing "service"
        for col in df_filtered.columns:
            if "service" in col.lower():
                service_item_col = col
                break

    if not service_item_col:
        default_fig = px.pie(title="No 'service item' column found")
        return default_fig, default_fig

    grouped = df_filtered.groupby(service_item_col, as_index=False).agg({'hours': 'sum', 'day_cost': 'sum'})
    if grouped.empty:
        default_fig = px.pie(title="No data after grouping")
        return default_fig, default_fig                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               

    # Build the two pie charts
    fig_hours = px.pie(grouped, names=service_item_col, values='hours', title="Total Hours per Service Item")
    fig_hours.update_traces(textinfo='none', hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
    fig_hours.update_layout(title={'text': "Total Hours per Service Item", 'x': 0.5})

    fig_cost = px.pie(grouped, names=service_item_col, values='day_cost', title="Total Cost per Service Item")
    fig_cost.update_traces(textinfo='none', hovertemplate='<b>%{label}</b><br>Cost: $%{value:,.2f}<extra></extra>')
    fig_cost.update_layout(title={'text': "Total Cost per Service Item", 'x': 0.5})

    return fig_hours, fig_cost
# Callback for updating jobcode-dropdown options based on filters#################################################################################################################
@app.callback(
    Output('jobcode-dropdown', 'options'),
    [Input('filter-clients', 'value'),
     Input('filter-type', 'value'),
     Input('filter-status', 'value'),
     Input('filter-service', 'value'),
     Input('filter-market', 'value'),
     Input('filter-pm', 'value')]
)
def update_jobcode_options(filter_clients, filter_type, filter_status, filter_service, filter_market, filter_pm):
    filtered_projects = global_projects_df.copy()
    
    if not any([filter_clients, filter_type, filter_status, filter_service, filter_market, filter_pm]):
        pass
        if 'Award Date' in filtered_projects.columns:
            # Convert to datetime (if not already)
            filtered_projects['Award Date'] = pd.to_datetime(filtered_projects['Award Date'], errors='coerce')
            filtered_projects = filtered_projects[
                filtered_projects['Award Date'].dt.year.isin(range(2016, 2030))
            ]
    else:
    
    
        if filter_clients:
            print("Filter Clients:", filter_clients)
            filtered_projects = filtered_projects[filtered_projects['Clients'].isin(filter_clients)]
            print("After client filter:", len(filtered_projects))
        if filter_type:
            print("Filter Type:", filter_type)
            filtered_projects = filtered_projects[filtered_projects['Type'].isin(filter_type)]
            print("After type filter:", len(filtered_projects))
        if filter_status:
            print("Filter Status:", filter_status)
            filtered_projects = filtered_projects[filtered_projects['Status'].isin(filter_status)]
            print("After status filter:", len(filter_status))
        if filter_service:
            print("Filter Service:", filter_service)
            filtered_projects = filtered_projects[filtered_projects['Service Line'].isin(filter_service)]
            print("After Service filter:", len(filter_service))
        if filter_market:
            print("Filter Market:", filter_market)
            filtered_projects = filtered_projects[filtered_projects['Market Segment'].isin(filter_market)]
            print("After Market filter:", len(filter_market))
        if filter_pm:
            print("Filter PM:", filter_pm)
            filtered_projects = filtered_projects[filtered_projects['PM'].isin(filter_pm)]
            print("After PM filter:", len(filter_pm))
            
    #valid_projects = filtered_projects['Project No'].unique()
    #valid_jobcodes = global_merged_df[global_merged_df['jobcode_2'].apply(lambda x: extract_project_no(x) in valid_projects)]
    #jobcode_values = valid_jobcodes['jobcode_2'].unique()
    #options = [{'label': jc, 'value': jc} for jc in sorted(jobcode_values)]
    
    
    project_nos = sorted(filtered_projects['Project No'].unique())
    options = [{'label': pn, 'value': pn} for pn in project_nos]
    print_green("All project options:")
    print_green(options)
    
    return options
#################################################################################################################
@app.callback(
    Output('award-date', 'children'),
    [Input('jobcode-dropdown', 'value')]
)
def update_award_date(selected_jobcode):
    if selected_jobcode is None:
        return ""
    
    #extracted_code = extract_project_no(selected_jobcode)
    #filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    filtered = global_projects_df[global_projects_df['Project No'] == selected_jobcode]

    
    if not filtered.empty:
        project_record = filtered.iloc[0]
        award_date_raw = project_record.get('Award Date', "No Award Date Available")
        try:
            award_date = pd.to_datetime(award_date_raw)
            formatted_date = award_date.strftime("%d %B %Y")
        except Exception:
            formatted_date = str(award_date_raw)
        return html.Div([html.B("Award Date:"), " " + formatted_date])
    return "No Award Date Found."
#################################################################################################################





@app.callback(
    [Output('project-table-left', 'data'),
     Output('project-table-left', 'columns'),
     Output('project-table-right', 'data'),
     Output('project-table-right', 'columns')],
    [Input('jobcode-dropdown', 'value')]
)
def update_project_tables(selected_jobcode):
    if not selected_jobcode:
        return [], [{"name": "Field", "id": "Field"}, {"name": "Value", "id": "Value"}], [], [
            {"name": "Field", "id": "Field"}, 
            {"name": "Value", "id": "Value"},
            {"name": "Value_num", "id": "Value_num", "type": "numeric"}#, "hidden": True}
        ]

    print(f"Selected jobcode: {selected_jobcode}")
    
    # Create a direct copy to avoid modifying the original
    projects_df_copy = global_projects_df.copy()
    
    # Print project columns to debug
    print(f"Projects DataFrame columns: {projects_df_copy.columns.tolist()}")
    print(f"First few Project No values: {projects_df_copy['Project No'].head(5).tolist()}")
    
    # Use multiple matching methods to find the project
    # Method 1: Direct match
    filtered = projects_df_copy[projects_df_copy['Project No'].astype(str).str.strip() == str(selected_jobcode).strip()]
    print(f"Method 1 (Direct match) found {len(filtered)} rows")
    
    # Method 2: Match with standardized project numbers
    if filtered.empty:
        selected_std = standardize_project_no(str(selected_jobcode))
        projects_std = projects_df_copy['Project No'].astype(str).apply(standardize_project_no)
        filtered = projects_df_copy[projects_std == selected_std]
        print(f"Method 2 (Standardized match) found {len(filtered)} rows")
    
    # Method 3: Check if it's a substring (last resort)
    if filtered.empty:
        filtered = projects_df_copy[projects_df_copy['Project No'].astype(str).str.contains(str(selected_jobcode), regex=False)]
        print(f"Method 3 (Substring match) found {len(filtered)} rows")
    
    # If still no match, create manual data
    if filtered.empty:
        print(f"ERROR: No project found for {selected_jobcode}")
        
        # Create hardcoded data for testing/demonstration
        left_data = [
            {"Field": "Project No", "Value": selected_jobcode},
            {"Field": "Status", "Value": "Data not found"},
            {"Field": "Type", "Value": "Data not found"},
            {"Field": "Service Line", "Value": "Data not found"}
        ]
        
        right_table_data = [
            {"Field": "Contracted Amount", "Value": "Data not found", "Value_num": 0},
            {"Field": "Total Invoice", "Value": "Data not found", "Value_num": 0}, 
            {"Field": "Total Cost", "Value": "Data not found", "Value_num": 0},
            {"Field": "ER Contract", "Value": "Data not found", "Value_num": 0}
        ]
        
        left_columns = [{"name": "Field", "id": "Field"}, {"name": "Value", "id": "Value"}]
        right_columns = [
            {"name": "Field", "id": "Field"},
            {"name": "Value", "id": "Value"},
            {"name": "Value_num", "id": "Value_num", "type": "numeric", "hidden": True}
        ]
        
        return left_data, left_columns, right_table_data, right_columns
    
    # We found a match, proceed with creating the tables
    project_record = filtered.iloc[0]
    print(f"Found project: {project_record['Project No']}")
    
    # Create the left table data (Project Details)
    left_fields = ['Project No', 'Clients', 'Type', 'Status', 'Service Line', 'Market Segment', 'PM', 'TL']
    left_data = []
    
    for field in left_fields:
        if field in project_record and pd.notna(project_record[field]):
            left_data.append({
                'Field': field,
                'Value': str(project_record[field])
            })
    
    # Process cost data
    total_cost = 0
    df_filtered = global_merged_df[global_merged_df['Project No'] == str(selected_jobcode)]
    if df_filtered.empty:
        df_filtered = global_merged_df[global_merged_df['jobcode_2'].astype(str).apply(lambda x: extract_project_no(x)) == str(selected_jobcode)]
    
    if not df_filtered.empty:
        total_cost = df_filtered['day_cost'].sum()
    
    # Get invoice data
    total_invoice = 0
    if 'Project No' in global_raw_invoices.columns:
        df_invoices = global_raw_invoices[global_raw_invoices['Project No'].astype(str).str.strip() == str(selected_jobcode).strip()]
        if not df_invoices.empty and 'Actual' in df_invoices.columns:
            total_invoice = df_invoices['Actual'].sum()
    
    # Get contracted amount
    contracted_amount = None
    if 'Contracted Amount' in project_record and pd.notna(project_record['Contracted Amount']):
        try:
            if isinstance(project_record['Contracted Amount'], str):
                contracted_amount = float(project_record['Contracted Amount'].replace('$', '').replace(',', ''))
            else:
                contracted_amount = float(project_record['Contracted Amount'])
        except:
            contracted_amount = None
    
    # Calculate derived values
    remaining_to_invoice = contracted_amount - total_invoice if contracted_amount is not None and total_invoice > 0 else None
    er_contract = contracted_amount / total_cost if total_cost > 0 and contracted_amount is not None else None
    er_invoiced = total_invoice / total_cost if total_cost > 0 and total_invoice > 0 else None
    
    # Format values
    format_money = lambda x: f"${x:,.2f}" if x is not None else "N/A"
    format_er = lambda x: f"{x:.2f}" if x is not None else "N/A"
    
    # Create right table
    right_table_data = [
        {"Field": "Contracted Amount", "Value": format_money(contracted_amount), "Value_num": contracted_amount or 0},
        {"Field": "Total Invoice", "Value": format_money(total_invoice), "Value_num": total_invoice},
        {"Field": "Total Cost", "Value": format_money(total_cost), "Value_num": total_cost},
        {"Field": "Remaining to Invoice", "Value": format_money(remaining_to_invoice), "Value_num": remaining_to_invoice or 0},
        {"Field": "ER Contract", "Value": format_er(er_contract), "Value_num": er_contract or 0},
        {"Field": "ER Invoiced", "Value": format_er(er_invoiced), "Value_num": er_invoiced or 0}
    ]
    
    # Define columns
    left_columns = [{"name": "Field", "id": "Field"}, {"name": "Value", "id": "Value"}]
    right_columns = [
        {"name": "Field", "id": "Field"},
        {"name": "Value", "id": "Value"},
        {"name": "Value_num", "id": "Value_num", "type": "numeric"}#, "hidden": True}
    ]
    
    return left_data, left_columns, right_table_data, right_columns




@app.callback(
    Output('project-description', 'children'),
    [Input('jobcode-dropdown', 'value')]
)
def update_project_description(selected_jobcode):
    if selected_jobcode is None:
        return ""
    
    ##extracted_code = extract_project_no(selected_jobcode)
    #filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    #filtered = global_projects_df[global_projects_df['Project No'] == selected_project_no]

    filtered = global_projects_df[global_projects_df['Project No'] == selected_jobcode]

    if not filtered.empty:
        project_record = filtered.iloc[0]
        description = project_record.get('Project Description', "No Description Available")
        return html.Div([html.B("Project Description:"), " " + str(description)])
    return "No Project Description Found."
#################################################################################################################
# Correcting the project log path
project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
@app.callback(
    Output("download-weekly-report-pdf", "data"),
    Input("export-weekly-report", "n_clicks"),
    [State('weekly-report-table', 'data'),
     State('weekly-report-table', 'columns'),
     State('forecast-summary-table', 'data'),
     State('forecast-summary-table', 'columns'),
     State('forecast-type-table', 'data'),
     State('forecast-type-table', 'columns'),
     State('report-week-picker', 'date')],
    prevent_initial_call=True
)
def export_weekly_report_pdf(n_clicks, table_data, table_columns, forecast_summary_data, forecast_summary_columns, 
                            forecast_type_data, forecast_type_columns, selected_date):
    if not selected_date or not table_data:
        return dcc.send_string("No data to export", "empty_report.pdf")
    
    date_obj = pd.to_datetime(selected_date)
    month_name = date_obj.strftime('%B')
    year = date_obj.year
    # Better week calculation that handles Mondays correctly
    # Get the first day of the month
    first_day = date_obj.replace(day=1)
    
    # Find the week number using isocalendar
    # This returns a tuple (year, week_number, weekday)
    first_day_week = first_day.isocalendar()[1]
    current_week = date_obj.isocalendar()[1]
    
    # Calculate week of month (1-based)
    # If the first day of the month and the selected date are in different ISO weeks
    week_of_month = current_week - first_day_week + 1
    
    # Handle edge case where week spans across months/years
    if week_of_month <= 0:
        # We're in the same week as the end of the previous month
        week_of_month = 1
    # Get the last data update date
    try:
        with open(os.path.join(PICKLE_OUTPUT_DIR, "last_data_update.txt"), "r") as f:
            last_data_update = f.read().strip()
    except:
        last_data_update = "Unknown"
    
    # Convert table data to DataFrames
    df_all = pd.DataFrame(table_data) if table_data else pd.DataFrame()
    df_forecast_summary = pd.DataFrame(forecast_summary_data) if forecast_summary_data else pd.DataFrame()
    df_forecast_type = pd.DataFrame(forecast_type_data) if forecast_type_data else pd.DataFrame()
    
    # Create HTML string for the report
    html_string = f"""
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          @page {{
            size: letter landscape; /* US Letter in landscape orientation */
            margin-left: 2cm;     /* INCREASED from 0.75cm to 2cm */
            margin-right: 2cm;    /* INCREASED from 0.75cm to 2cm */
            margin-top: 1.5cm;    /* INCREASED from 1cm */
            margin-bottom: 1.5cm; /* INCREASED from 1cm */
          }}
          body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            font-size: 9px;
          }}
          table {{
            width: 90%;          /* REDUCED from 98% to 90% */
            border-collapse: collapse;
            table-layout: fixed;
            margin: 0 auto;      /* Centers the table */
            max-width: 90%;      /* Added max-width constraint */
          }}
          th, td {{
            border: 1px solid black;
            padding: 3px 4px; /* Adjusted padding for better spacing */
            text-align: center; /* Default alignment is center */
            word-wrap: break-word;
            overflow: hidden;
            max-width: 150px;  /* Limit maximum width for any column */
          }}
          th {{
            background-color: #f2f2f2;
            font-weight: bold;
          }}
          .text-left {{
            text-align: left;
          }}
          .text-right {{
            text-align: right;
          }}
          h1 {{ font-size: 16px; text-align: center; margin: 6px 0; }}
          h2 {{ font-size: 14px; text-align: center; margin: 5px 0; }}
          h3 {{ font-size: 12px; text-align: center; margin: 4px 0; }}
          .er-low {{ color: red; font-weight: bold; }}
          .er-mid {{ color: orange; font-weight: bold; }}
          .er-high {{ color: green; font-weight: bold; }}
          .logo-container {{ text-align: center; margin-bottom: 10px; }}
          .forecast-table {{ margin-bottom: 20px; }}
          .forecast-value {{ color: black; }}
          .forecast-percentage {{ font-weight: bold; }}
          .forecast-percentage-low {{ color: red; font-weight: bold; }}
          .forecast-percentage-med {{ color: orange; font-weight: bold; }}
          .forecast-percentage-high {{ color: green; font-weight: bold; }}
        </style>
      </head>
      <body>
        <div class="logo-container">
          <img src="data:image/png;base64,{config.encoded_logo}" style="height: 70px;">
        </div>
        <h1>Monthly Invoice Report</h1>
        <h2>{month_name} {year}- Week {week_of_month}</h2>
    """
    
    # Add the main table
    if not df_all.empty:
        # Calculate column width percentage based on number of columns
        columns = [c for c in table_columns if c['id'] != 'Original_Order' and c['id'] != 'Invoiced %_num']
        col_count = len(columns)
        
        # Simple approach: evenly distribute widths
        col_width_percent = 100 / col_count
        col_widths = {col['id']: col_width_percent for col in columns}
        
        # For key columns that need slight adjustments
        # Just make minor adjustments rather than dramatic differences
        col_widths['Project No'] = col_width_percent * 1.2  # Slightly wider
        col_widths['Project Description'] = col_width_percent * 1.4  # Slightly wider
        col_widths['Clients'] = col_width_percent * 1.2  # Slightly wider
        col_widths['PM'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['TL'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['Type'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['Status'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['Service Line'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['Market Segment'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['SL'] = col_width_percent * 0.6  # Slightly narrower
        col_widths['MS'] = col_width_percent * 0.6  # Slightly narrower
        
        # Custom HTML table with formatting
        html_string += f"<h3>Monthly Invoice Report</h3>"
        html_string += f"<table border='1' cellspacing='0' cellpadding='1' style='width: 90%; margin: 0 auto;'><thead><tr>"
        for col in columns:
            col_id = col['id']
            col_name = col['name'] if 'name' in col else col_id
            width = col_widths.get(col_id, col_width_percent)
            html_string += f"<th style='width: {width}%;'>{col_name}</th>"
        html_string += "</tr></thead><tbody>"
        
        for row in table_data:
            html_string += "<tr>"
            for col in columns:
                col_id = col['id']
                col_name = col['name'] if 'name' in col else col_id
                value = row.get(col_id, '')
                
                # Determine text alignment based on column type
                text_align_class = ''
                # Left align text for descriptive fields
                if col_id in ['Project No', 'Project Description', 'Clients']:
                    text_align_class = 'class="text-left"'
                # Right align text for monetary values
                elif any(money_term in col_id for money_term in ['ER', 'Fee', 'Projected', 'Actual', 'Contract']):
                    text_align_class = 'class="text-right"'
                
                # Apply conditional formatting for ER values
                if col_id == 'ER DECON LLC' or col_id == 'DECON LLC Invoiced' or col_id == 'ER Invoiced':
                    try:
                        # Remove % and convert to float for comparison
                        numeric_value = float(str(value).replace('%', '').replace('$', '').replace(',', ''))
                        if numeric_value < 1:
                            html_string += f"<td class='er-low text-right'>{value}</td>"
                        elif numeric_value <= 2.5:
                            html_string += f"<td class='er-mid text-right'>{value}</td>"
                        else:
                            html_string += f"<td class='er-high text-right'>{value}</td>"
                    except:
                        html_string += f"<td {text_align_class}>{value}</td>"
                # Apply conditional formatting for Invoiced %
                elif col_id == 'Invoiced %':
                    try:
                        # Try to extract percentage value
                        if value == 'N/A':
                            html_string += f"<td class='er-low'>{value}</td>"
                        else:
                            numeric_value = float(str(value).replace('%', ''))
                            if numeric_value == 0:
                                html_string += f"<td class='er-low'>{value}</td>"
                            elif numeric_value < 60:
                                html_string += f"<td style='color:darkorange;font-weight:bold;'>{value}</td>"
                            elif numeric_value < 80:
                                html_string += f"<td style='color:gold;font-weight:bold;'>{value}</td>"
                            elif numeric_value < 90:
                                html_string += f"<td style='color:yellowgreen;font-weight:bold;'>{value}</td>"
                            else:
                                html_string += f"<td class='er-high'>{value}</td>"
                    except:
                        html_string += f"<td>{value}</td>"
                else:
                    html_string += f"<td {text_align_class}>{value}</td>"
            html_string += "</tr>"
        html_string += "</tbody></table>"
    
    # Add forecast summary table
    if not df_forecast_summary.empty:
        html_string += f"<h3>Forecast Summary</h3>"
        html_string += f"<table border='1' cellspacing='0' cellpadding='1' class='forecast-table' style='width: 70%; margin: 20px auto;'><thead><tr>"
        
        for col in forecast_summary_columns:
            col_name = col['name'] if 'name' in col else col['id']
            html_string += f"<th>{col_name}</th>"
        
        html_string += "</tr></thead><tbody>"
        
        for row in forecast_summary_data:
            html_string += "<tr>"
            for col in forecast_summary_columns:
                col_id = col['id']
                value = row.get(col_id, '')
                
                # Determine text alignment based on column type
                text_align_class = ''
                # Right align text for monetary values
                if col_id in ['Projected', 'Actual']:
                    text_align_class = 'class="text-right"'
                
                # Apply conditional formatting for %Forecast vs Actual
                if col_id == '%Forecast vs Actual':
                    try:
                        numeric_value = float(str(value).replace('%', ''))
                        if numeric_value < 30:
                            html_string += f"<td class='forecast-percentage-low'>{value}</td>"
                        elif numeric_value < 75:
                            html_string += f"<td class='forecast-percentage-med'>{value}</td>"
                        else:
                            html_string += f"<td class='forecast-percentage-high'>{value}</td>"
                    except:
                        html_string += f"<td>{value}</td>"
                else:
                    html_string += f"<td {text_align_class}>{value}</td>"
            
            html_string += "</tr>"
        
        html_string += "</tbody></table>"
    
    # Add forecast type table
    if not df_forecast_type.empty:
        html_string += f"<h3>Forecast by Type</h3>"
        html_string += f"<table border='1' cellspacing='0' cellpadding='1' class='forecast-table' style='width: 80%; margin: 20px auto;'><thead><tr>"
        
        for col in forecast_type_columns:
            col_name = col['name'] if 'name' in col else col['id']
            html_string += f"<th>{col_name}</th>"
        
        html_string += "</tr></thead><tbody>"
        
        for row in forecast_type_data:
            is_total_row = row.get('Type') == 'TOTAL'
            html_string += f"<tr {'style=\"font-weight: bold;\"' if is_total_row else ''}>"
            
            for col in forecast_type_columns:
                col_id = col['id']
                value = row.get(col_id, '')
                
                # Determine text alignment based on column type
                text_align_class = ''
                # Left align Type column
                if col_id == 'Type':
                    text_align_class = 'class="text-left"'
                # Right align text for monetary values
                elif col_id in ['Projected', 'Actual']:
                    text_align_class = 'class="text-right"'
                
                # Apply conditional formatting for Percentage column
                if col_id == 'Percentage Projected vs Actual':
                    try:
                        numeric_value = float(str(value).replace('%', ''))
                        style_class = ""
                        
                        # Fix for 100% value - this should be green, not red
                        if numeric_value == 100:
                            html_string += f"<td class='forecast-percentage-high'>{value}</td>"
                        elif numeric_value < 30:
                            html_string += f"<td class='forecast-percentage-low'>{value}</td>"
                        elif numeric_value < 75:
                            html_string += f"<td class='forecast-percentage-med'>{value}</td>"
                        else:
                            html_string += f"<td class='forecast-percentage-high'>{value}</td>"
                    except:
                        html_string += f"<td>{value}</td>"
                else:
                    html_string += f"<td {text_align_class}>{value}</td>"
            
            html_string += "</tr>"
        
        html_string += "</tbody></table>"

    # Generate the bar chart for Projected vs Actual by project type
    if not df_forecast_type.empty:
        try:
            import plotly.graph_objects as go
            
            # Check if we're dealing with a DataFrame or a list of dictionaries
            if isinstance(df_forecast_type, pd.DataFrame):
                # Filter out the 'TOTAL' row for the chart
                df_for_chart = df_forecast_type[df_forecast_type['Type'] != 'TOTAL'].copy()
                
                # Prepare data for the chart
                project_types = df_for_chart['Type'].tolist()
                
                # Extract numeric values from currency strings
                def parse_currency(value):
                    if isinstance(value, str):
                        return float(value.replace('$', '').replace(',', ''))
                    return float(value) if pd.notnull(value) else 0
                
                # Convert currency strings to float values
                projected_values = [parse_currency(val) for val in df_for_chart['Projected']]
                actual_values = [parse_currency(val) for val in df_for_chart['Actual']]
                
            else:
                # We're dealing with a list of dictionaries (records)
                # Filter out the 'TOTAL' row for the chart
                df_for_chart = [row for row in df_forecast_type if row.get('Type') != 'TOTAL']
                
                # Prepare data for the chart
                project_types = [row.get('Type', '') for row in df_for_chart]
                projected_values = []
                actual_values = []
                
                for row in df_for_chart:
                    # Extract numeric values from currency strings
                    projected_str = row.get('Projected', '$0.00')
                    actual_str = row.get('Actual', '$0.00')
                    
                    # Convert the currency strings to float
                    projected_val = float(projected_str.replace('$', '').replace(',', ''))
                    actual_val = float(actual_str.replace('$', '').replace(',', ''))
                    
                    projected_values.append(projected_val)
                    actual_values.append(actual_val)
            
            # Create a grouped bar chart using plotly
            fig = go.Figure()
            
            # Add bars for Projected
            fig.add_trace(go.Bar(
                x=project_types,
                y=projected_values,
                name='Projected',
                marker_color='#4086F4'
            ))
            
            # Add bars for Actual
            fig.add_trace(go.Bar(
                x=project_types,
                y=actual_values,
                name='Actual',
                marker_color='#3EA045'
            ))
            
            # Update layout - Fixed the titlefont issue by using the correct property structure
            fig.update_layout(
                title='Monthly Invoicing',
                title_x=0.5,
                xaxis=dict(
                    title='Project Type',
                    title_font=dict(size=12),  # Updated from titlefont_size to title_font
                ),
                yaxis=dict(
                    title='Monthly Amount',
                    title_font=dict(size=12),  # Updated from titlefont_size to title_font
                    tickformat='$,.0f',
                ),
                barmode='group',
                template='plotly_white',
                height=500,
                margin=dict(l=50, r=50, t=80, b=50),
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="right",
                    x=0.99
                )
            )
            
            # Convert the figure to a PNG image
            img_bytes = fig.to_image(format="png", scale=2.0)
            
            # Convert to base64 for embedding in HTML
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Add the chart to the HTML
            html_string += f"""
            <div style="text-align: center; margin: 30px 0;">
                <h3>Projected vs Actual by Project Type</h3>
                <img src="data:image/png;base64,{img_base64}" style="max-width: 90%; height: auto;">
            </div>
            """
        except Exception as e:
            print_red(f"Error generating chart: {str(e)}")
            html_string += f"""
            <div style="text-align: center; color: red; margin: 20px 0;">
                Error generating chart: {str(e)}
            </div>
            """
    
    from datetime import datetime
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_string += f"""
        <div class="footer">
            Latest Data Update: {last_data_update} | Report Generated: {current_datetime}
        </div>
    </body>
    </html>
    """
    
    # Generate PDF from HTML with specific options
    # Update the PDF file name to include week number for better identification:
    try:
        # Using CSS @page settings for landscape orientation
        pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
        return dcc.send_bytes(pdf_bytes, f"monthly_report_{month_name}_{year}_week_{week_of_month}.pdf")
    except Exception as e:
        print_red(f"Error generating PDF: {str(e)}")
        return dcc.send_string(f"Error generating PDF: {str(e)}", "error.pdf")
# Fixing syntax and logical errors in the script
@app.callback(
    [Output('weekly-report-table', 'data'),
     Output('weekly-report-table', 'columns'),
     Output('forecast-summary-table', 'data'),
     Output('forecast-summary-table', 'columns'),
     Output('forecast-type-table', 'data'),
     Output('forecast-type-table', 'columns')],
    Input('report-week-picker', 'date')
)

def generate_monthly_report(selected_date):
    if not selected_date:
        return [], [], [], [], [], []
    
    # Call the function from data_processing
    project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
    
    report_data, all_columns = data_processing.generate_monthly_report_data(
        selected_date, 
        global_projects_df, 
        global_merged_df, 
        global_raw_invoices,
        project_log_path
    )
    if not report_data:
        return [], [], [], [], [], []
    
    # Define which columns to display (customize this list as needed)
    visible_columns = [
        'Project No', 
        'PM', 
        'TL',
        'Project Description',
        'Clients', 
        'Type', 
        'Status', 
        'Service Line',     
        'Market Segment',  
        'Projected',  
        'Actual',
        'Invoiced %',
        'DECON LLC Invoiced'
    ]
    
    # Filter columns to only show the ones we want, maintaining the specified order
    display_columns = []
    for col_id in visible_columns:
        for col in all_columns:
            if col['id'] == col_id:
                display_columns.append(col)
                break
            
    for col in display_columns:
        if col['id'] == 'Service Line':
            col['name'] = 'SL'
        elif col['id'] == 'Market Segment':
            col['name'] = 'MS'
        elif col['id'] == 'ER DECON LLC':
            col['name'] = 'ER Decon LLC'
        elif col['id'] == 'Clients':
            col['name'] = 'Client'
        elif col['id'] == 'DECON LLC Invoiced':
            col['name'] = 'ER DECON LLC'
    
    # Create a totals row
    totals_row = {col: '' for col in visible_columns}  # Initialize with empty strings for all columns
    totals_row['Project No'] = 'TOTAL:'
    
    # Helper function to extract numeric values from formatted strings
    def extract_numeric(value):
        if isinstance(value, str):
            # Remove $, % and commas, then convert to float
            cleaned = value.replace('$', '').replace(',', '').replace('%', '')
            try:
                return float(cleaned)
            except:
                return 0
        return 0
    
    # Calculate totals for numeric columns
    if report_data:
        # Calculate sum for Projected column
        if 'Projected' in visible_columns:
            projected_sum = sum(extract_numeric(row.get('Projected', 0)) for row in report_data if 'TOTAL:' not in str(row.get('Project No', '')))
            totals_row['Projected'] = f"${projected_sum:,.2f}" if projected_sum > 0 else "N/A"
        
        # Calculate sum for Actual column
        if 'Actual' in visible_columns:
            actual_sum = sum(extract_numeric(row.get('Actual', 0)) for row in report_data if 'TOTAL:' not in str(row.get('Project No', '')))
            totals_row['Actual'] = f"${actual_sum:,.2f}" if actual_sum > 0 else "N/A"
        
    # Append the totals row
    report_data.append(totals_row)
    
    # ------------------- CREATE FORECAST SUMMARY TABLE -------------------
    # Get date information for getting the right forecast data
    date_obj = pd.to_datetime(selected_date)
    selected_month = date_obj.month
    selected_year = date_obj.year
    
    # Load forecast data
    forecast_df = load_forecast_invoicing()
    
    # Create forecast summary table data
    forecast_summary_data = []
    
    if not forecast_df.empty:
        # Filter for selected month
        month_forecast = forecast_df[forecast_df['Month'] == selected_month]
        if not month_forecast.empty:
            forecast_value = month_forecast.iloc[0].get('ForecastValue', 0)
            
            # Get projected and actual totals
            projected_sum = sum(extract_numeric(row.get('Projected', 0)) for row in report_data if 'TOTAL:' not in str(row.get('Project No', '')))
            actual_sum = sum(extract_numeric(row.get('Actual', 0)) for row in report_data if 'TOTAL:' not in str(row.get('Project No', '')))
            
            # Calculate percentage of forecast vs actual
            percent_forecast_actual = (actual_sum / forecast_value * 100) if forecast_value > 0 else 0
            
            # Add data row
            forecast_summary_data.append({
                'ForecastValue': f"${forecast_value:,.2f}" if forecast_value > 0 else "$0.00",
                'Projected': f"${projected_sum:,.2f}" if projected_sum > 0 else "$0.00",
                'Actual': f"${actual_sum:,.2f}" if actual_sum > 0 else "$0.00",
                '%Forecast vs Actual': f"{percent_forecast_actual:.0f}%"
            })
    
    # If no data, add empty row
    if not forecast_summary_data:
        forecast_summary_data.append({
            'ForecastValue': "$0.00",
            'Projected': "$0.00",
            'Actual': "$0.00",
            '%Forecast vs Actual': "0%"
        })
    
    forecast_summary_columns = [
        {'name': 'ForecastValue', 'id': 'ForecastValue'},
        {'name': 'Projected', 'id': 'Projected'},
        {'name': 'Actual', 'id': 'Actual'},
        {'name': '%Forecast vs Actual', 'id': '%Forecast vs Actual'}
    ]
    
    # ------------------- CREATE FORECAST BY TYPE TABLE -------------------
    # Create forecast by type table data
    forecast_type_data = []
    
    if report_data:
        # Group the data by Type
        type_groups = {}
        for row in report_data:
            if 'TOTAL:' in str(row.get('Project No', '')):
                continue
                
            row_type = row.get('Type', 'Unknown')
            projected = extract_numeric(row.get('Projected', 0))
            actual = extract_numeric(row.get('Actual', 0))
            
            if row_type not in type_groups:
                type_groups[row_type] = {'Projected': 0, 'Actual': 0}
            
            type_groups[row_type]['Projected'] += projected
            type_groups[row_type]['Actual'] += actual
        
        # Create rows for each type
        for type_name, values in type_groups.items():
            projected = values['Projected']
            actual = values['Actual']
            percent = (actual / projected * 100) if projected > 0 else 0
            
            forecast_type_data.append({
                'Type': type_name,
                'Projected': f"${projected:,.2f}" if projected > 0 else "$0.00",
                'Actual': f"${actual:,.2f}" if actual > 0 else "$0.00",
                'Percentage Projected vs Actual': f"{percent:.0f}%"
            })
        
        # Sort by type
        forecast_type_data = sorted(forecast_type_data, key=lambda x: x['Type'])
        
        # Add TOTAL row
        total_projected = sum(type_groups[t]['Projected'] for t in type_groups)
        total_actual = sum(type_groups[t]['Actual'] for t in type_groups)
        total_percent = (total_actual / total_projected * 100) if total_projected > 0 else 0
        
        forecast_type_data.append({
            'Type': 'TOTAL',
            'Projected': f"${total_projected:,.2f}" if total_projected > 0 else "$0.00",
            'Actual': f"${total_actual:,.2f}" if total_actual > 0 else "$0.00",
            'Percentage Projected vs Actual': f"{total_percent:.0f}%"
        })
    
    # If no data, add empty row with totals
    if not forecast_type_data:
        forecast_type_data = [
            {'Type': '0-Pay App (LS)', 'Projected': '$0.00', 'Actual': '$0.00', 'Percentage Projected vs Actual': '0%'},
            {'Type': '1-Pay App (TM)', 'Projected': '$0.00', 'Actual': '$0.00', 'Percentage Projected vs Actual': '0%'},
            {'Type': '2-Organic', 'Projected': '$0.00', 'Actual': '$0.00', 'Percentage Projected vs Actual': '0%'},
            {'Type': '3-Large', 'Projected': '$0.00', 'Actual': '$0.00', 'Percentage Projected vs Actual': '0%'},
            {'Type': 'TOTAL', 'Projected': '$0.00', 'Actual': '$0.00', 'Percentage Projected vs Actual': '0%'}
        ]
    
    forecast_type_columns = [
        {'name': 'Type', 'id': 'Type'},
        {'name': 'Projected', 'id': 'Projected'},
        {'name': 'Actual', 'id': 'Actual'},
        {'name': 'Percentage Projected vs Actual', 'id': 'Percentage Projected vs Actual'}
    ]
    
    # The data still has all fields, but we're only showing selected columns
    return report_data, display_columns, forecast_summary_data, forecast_summary_columns, forecast_type_data, forecast_type_columns


def load_forecast_invoicing():
    """Load forecast invoicing data from pickle file or generate it on the fly"""
    try:
        pickle_path = os.path.join(PICKLE_OUTPUT_DIR, "forecast_invoicing.pkl")
        if os.path.exists(pickle_path):
            df_forecast = pd.read_pickle(pickle_path)
            print_green(f"Successfully loaded forecast invoicing data with {len(df_forecast)} rows")
            return df_forecast
        else:
            print_orange("Forecast invoicing pickle file not found.")
            # Try to generate it on the fly
            from data_processing import import_forecast_invoicing
            df_forecast = import_forecast_invoicing()
            return df_forecast
    except Exception as e:
        print_red(f"Error loading forecast invoicing data: {str(e)}")
        return pd.DataFrame(columns=['Month', 'MonthName', 'Year', 'ForecastValue'])


#############################################

@app.callback(
    Output('pie-chart', 'figure'),
    [Input('jobcode-dropdown','value'),
     Input('year-dropdown','value')]
)
def update_time_distribution_pie_chart(selected_project_no, selected_years):
    import plotly.express as px, plotly.graph_objects as go

    # 1) Quick debug
    print("↪ selected_project_no:", selected_project_no)
    print("↪ sample Project Nos:", global_merged_df['Project No'].unique()[:5])

    if not selected_project_no:
        return go.Figure(layout={'title': "No project selected"})

    # 2) Match project (strip spacing & cast to str)
    df_filtered = global_merged_df[
        global_merged_df['Project No'].astype(str).str.strip()
        == str(selected_project_no).strip()
    ].copy()
    print("↪ after Project No filter:", len(df_filtered), "rows")

    if df_filtered.empty:
        return go.Figure(layout={'title': "No data for selected project"})

    # 3) Ensure datetime
    df_filtered['local_date'] = pd.to_datetime(df_filtered['local_date'], errors='coerce')

    # 4) Apply year filter
    if selected_years:
        yrs = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(yrs)]
        print("↪ after year filter:", len(df_filtered), "rows")
    if df_filtered.empty:
        return go.Figure(layout={'title': "No data for selected years"})

    # 5) Detect employee column robustly
    candidates = ['Employee', 'Personnel', 'Employee Name', 'full_name', 'fname']
    employee_col = next((c for c in candidates if c in df_filtered.columns), None)
    if not employee_col:
        print("ERROR: no employee column found; available:", df_filtered.columns.tolist())
        return go.Figure(layout={'title': "No employee data found"})

    # 6) Group and plot
    df_grouped = df_filtered.groupby(employee_col)['hours'].sum().reset_index()
    if df_grouped['hours'].sum() == 0:
        return go.Figure(layout={'title': "No hours recorded"})

    fig = px.pie(df_grouped, names=employee_col, values='hours',
                 title=f"Time Distribution by Employee for {selected_project_no}")
    fig.update_traces(textinfo='none',
                      hovertemplate='<b>%{label}</b><br>Hours: %{value:.1f}<br>Percent: %{percent:.1%}')
    fig.update_layout(title_x=0.5)
    return fig


@app.callback(
    Output('cost-pie-chart', 'figure'),
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_cost_distribution_pie_chart(selected_project_no, selected_years):
    import plotly.express as px
    import plotly.graph_objects as go
    
    # Debug information
    print(f"Cost distribution chart callback - Project: {selected_project_no}, Years: {selected_years}")
    
    if not selected_project_no:
        return go.Figure(layout=dict(
            title="No project selected",
            annotations=[dict(text="Please select a project", x=0.5, y=0.5, showarrow=False)]
        ))
    
    # Filter dataframe for the selected project
    df_filtered = global_merged_df[global_merged_df['Project No'] == selected_project_no].copy()
    print(f"Filtered rows by project: {len(df_filtered)}")
    
    # Filter by selected years
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
        print(f"Filtered rows after year filter: {len(df_filtered)}")
    
    if df_filtered.empty:
        return go.Figure(layout=dict(
            title="No data for selected filters",
            annotations=[dict(text="No timesheet entries found", x=0.5, y=0.5, showarrow=False)]
        ))
    
    # Look for employee column
    employee_col = None
    for col_name in ['Employee', 'Personel', 'full_name', 'fname']:
        if col_name in df_filtered.columns and not df_filtered[col_name].isna().all():
            employee_col = col_name
            break
    
    if employee_col is None:
        print("DEBUG: No valid employee column found")
        return go.Figure(layout=dict(
            title="No employee data found",
            annotations=[dict(text="Could not identify employee column", x=0.5, y=0.5, showarrow=False)]
        ))
    
    # Group by employee, but make sure day_cost is numeric
    df_filtered['day_cost'] = pd.to_numeric(df_filtered['day_cost'], errors='coerce')
    cost_by_user = df_filtered.groupby(employee_col)['day_cost'].sum().reset_index()
    
    # Filter out zero or negative costs
    cost_by_user = cost_by_user[cost_by_user['day_cost'] > 0]
    
    print(f"DEBUG: Grouped cost data: {cost_by_user.head().to_dict('records')}")
    
    if cost_by_user.empty:
        print("DEBUG: No cost data after grouping")
        return go.Figure(layout=dict(
            title="No cost data",
            annotations=[dict(text="No costs recorded for this project", x=0.5, y=0.5, showarrow=False)]
        ))
    
    # Create pie chart
    fig = px.pie(
        cost_by_user,
        names=employee_col,
        values='day_cost',
        title=f"Cost Distribution by Employee for {selected_project_no}"
    )
    
    fig.update_traces(
        textinfo='none',
        hovertemplate='<b>%{label}</b><br>Cost: $%{value:.2f}<br>Percent: %{percent:.1%}<extra></extra>'
    )
    
    fig.update_layout(
        title_x=0.5,
        legend=dict(
            orientation="v", 
            x=1.1,
            y=0.5, 
            xanchor="left",
            yanchor="middle"
        )
    )
    
    return fig########
############################




def main():
    """Main script to load and process project data for 2023, 2024, and 2025."""
    print("Starting main script...")

    # Load project log data for each year
    years = [2023, 2024, 2025]
    all_projects = []

    for year in years:
        print(f"Loading project data for year {year}...")
        df_projects = get_project_log_data(years=[year])

        if df_projects.empty:
            print(f"Warning: No project data loaded for year {year}. Please check the source file.")
        else:
            print(f"Project data for year {year} loaded successfully.")
            print(df_projects.head())
            all_projects.append(df_projects)

    # Combine all project data into a single DataFrame
    if all_projects:
        combined_projects = pd.concat(all_projects, ignore_index=True)
        print("Combined project data from all years:")
        print(combined_projects.head())
    else:
        print("Error: No project data loaded for any year.")
        return

if __name__ == "__main__":
    main()
    #app.run_server(debug=True, host='10.1.2.189', port=8050, use_reloader=False) 
    # Add this somewhere before the server starts
    print("First few rows of merged data:")
    print(global_merged_df[['Project No', 'jobcode_2', 'hours', 'Employee', 'Personel']].head(5))#app.run(debug=True, host='localhost', port=7050, use_reloader=False)  
    app.run(debug=True, host='0.0.0.0', port=7050, use_reloader=False)

# Callback for Time Distribution By Employee Pie Chart
# Callback for Time Distribution By Employee Pie Chart
