# app.py

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme, Symbol
import plotly.express as px
import pandas as pd
import os 
# Import our separate modules
import data_processing
import config
from data_processing import extract_project_no, standardize_project_no, print_green, print_cyan, print_orange, print_red, last_update #, data_update_date
from config import TABLE_STYLE, TABLE_CELL_STYLE, TABLE_CELL_CONDITIONAL, RIGHT_TABLE_RED_STYLE


#########################

PICKLE_OUTPUT_DIR = r"C:\\Users\\jose.pineda\\Desktop\\operations\\pickles"

#################
# 1) Run the data pipeline to get our DataFrames
#global_merged_df, global_projects_df, global_invoices, global_raw_invoices, last_update = data_processing.main()
#now instead of running the data parsing function, i pre run that, now i just run the pickle loading steps
#global_merged_df = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "\global_merged_df.pkl"))


#global_merged_df = pd.read_pickle(r"C:\Users\jose.pineda\Desktop\operations\pickles\global_merged_df.pkl")
#global_projects_df = pd.read_pickle(r"C:\Users\jose.pineda\Desktop\operations\pickles\global_projects_df.pkl")
#global_invoices = pd.read_pickle(r"C:\Users\jose.pineda\Desktop\operations\pickles\\global_invoices.pkl")
#global_raw_invoices = pd.read_pickle(r"C:\Users\jose.pineda\Desktop\operations\pickles\global_raw_invoices.pkl")

global_merged_df = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_merged_df.pkl"))
global_projects_df = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_projects_df.pkl"))
global_invoices = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_invoices.pkl"))
global_raw_invoices = pd.read_pickle(os.path.join(PICKLE_OUTPUT_DIR, "global_raw_invoices.pkl"))

with open(os.path.join(PICKLE_OUTPUT_DIR, "last_update.txt"), "r") as f:
    last_update = f.read().strip()





# 2) Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# 3) Define the Layout with Tabs in the desired order:
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
                        #options=[
                        #    {'label': '2022', 'value': '2022'},
                        #    {'label': '2023', 'value': '2023'},
                        #    {'label': '2024', 'value': '2024'},
                        #    {'label': '2025', 'value': '2025'}
                        #],
                        #value=['2024', '2025'],
                        
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
                        style_cell=config.TABLE_CELL_STYLE,
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
                        {'name': 'Value_num', 'id': 'Value_num', 'type': 'numeric'},],
                        
                        
                        
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
            # Service Item Details Table
            html.H2("Service Item Details", style={'textAlign': 'center', 'paddingTop': '20px'}),
            html.Div(
                dash_table.DataTable(
                    id='service-item-table',
                    columns=[],
                    data=[],
                    style_table=config.TABLE_STYLE,
                    style_cell=config.TABLE_CELL_STYLE,
                    style_cell_conditional=config.TABLE_CELL_CONDITIONAL
                ),
                style={'width': '60%', 'margin': '0 auto'}
            ),
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
            f"Latest Data Update: {"..."}",
            style={'color': 'gray', 'font-size': '12px', 'text-align': 'center', 'margin-top': '20px'}
            )
                
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
                    dcc.Graph(id='client-total-cost-pie', style={'height': '300px'})
                ], style={'width': '400px', 'display': 'inline-block', 'padding': '10px'}),
                html.Div([
                    dcc.Graph(id='client-total-hours-pie', style={'height': '300px'})
                ], style={'width': '400px', 'display': 'inline-block', 'padding': '10px'})
            ], style={'textAlign': 'center'}),
            
            html.H3("Client Summary", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
            
            # New: Date range picker for invoice dates
            html.Div([
                html.Label("Select Invoice Date Range:", style={'fontFamily': 'Calibri, sans-serif'}),
                dcc.DatePickerRange(
                    id='invoice-date-range',
                    start_date_placeholder_text="Start Date",
                    end_date_placeholder_text="End Date",
                    display_format='YYYY-MM-DD'
                )
            ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),
            
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
            
            # Title for Client Summary Table
            html.H3("Client Project Status", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
        
            # Client Summary Table
            dash_table.DataTable(
                id='client-summary-table',
                columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}],
                data=[],
                style_table={'width': '40%', 'margin': 'auto', 'overflowY': 'auto'},
                style_cell=TABLE_CELL_STYLE
            ),
            # Title for Detailed Projects Table
            html.H3("Project Summary", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif', 'margin-top': '20px'}),
        
            # Detailed Projects Table for the selected client
            dash_table.DataTable(
                id='client-projects-table',
                columns=[],  # set via callback
                data=[],     # set via callback
                style_table={'width': '80%', 'margin': 'auto', 'overflowY': 'auto'},
                style_cell={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'},
                style_data_conditional=config.RIGHT_TABLE_RED_STYLE

            ), 
            #show last update date
            html.Div(
            f"Latest Data Update: {""}",
            style={'color': 'gray', 'font-size': '12px', 'text-align': 'center', 'margin-top': '20px'}
            )
        ])
        
    ]),
    
    # ----------------------------------------------------------------
    # TAB 3: ADD NEW PROJECT
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

# -------------------------------------------------------------------
# 4) Define all Callbacks (callbacks remain as in your working version)
# -------------------------------------------------------------------
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
    cost_by_client = df_merged.groupby('Clients', as_index=False)['day_cost'].sum()
    hours_by_client = df_merged.groupby('Clients', as_index=False)['hours'].sum()
    #print_green("Aggregated cost_by_client:\n" + str(cost_by_client.head(20)))
    #print_green("Aggregated hours_by_client:\n" + str(hours_by_client.head(20)))
    fig_cost = px.pie(cost_by_client, names='Clients', values='day_cost', title="Total Cost by Client")
    fig_hours = px.pie(hours_by_client, names='Clients', values='hours', title="Total Hours by Client")
    fig_cost.update_layout(title={'x': 0.5})
    fig_hours.update_layout(title={'x': 0.5})
    return fig_cost, fig_hours


def parse_contract(x):
    try:
        return float(str(x).replace('$', '').replace(',', '').strip())
    except:
        return None

def safe_divide_contract(row):
    cost = row['CostNum']
    if (isinstance(cost, (int, float)) and cost > 0 and row['Contracted Amount Parsed'] is not None):
        return row['Contracted Amount Parsed'] / cost
    return None



def safe_divide_invoiced(row):
    inv = row['InvoiceNum']
    if (isinstance(inv, (int, float)) and inv > 0 and row['Contracted Amount Parsed'] is not None):
        return row['Contracted Amount Parsed'] / inv
    return None



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
        global_projects_df['Clients'].str.lower() == selected_client.lower()
    ].copy()
    
    
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
    cost_grouped = df_timesheet_filtered.groupby('Project No', as_index=False)['day_cost'].sum()
    cost_grouped.rename(columns={'day_cost': 'CostNum'}, inplace=True)
    
    
    #merge filtered data with selected client projects 
    df_detail = df_client_projects.copy()

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
                   'Total Invoice', 'Total Cost', 'ER Contract', 'ER Invoiced']
    
    detail_cols = [c for c in detail_cols if c in df_detail.columns]
    df_detail_final = df_detail[detail_cols].copy()
    detail_data = df_detail_final.to_dict('records')
    
    #dash table columns with numeric formatting on er columns 
    detail_columns = []
    for col in detail_cols:
        if col in ['ER Contract', 'ER Invoiced']:
            detail_columns.append({'name': col, 'id': col, 'type': 'numeric', 'format': Format(precision=2, scheme=Scheme.fixed)})
        else:
            detail_columns.append({'name': col, 'id': col})
            #return all 
    return summary_data, summary_columns, detail_data, detail_columns
#######################################end of update client function 




# Callback for Service Item Details Table
@app.callback(
    [Output('service-item-table', 'data'),
     Output('service-item-table', 'columns')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_service_item_table(selected_jobcode, selected_years):
    if selected_jobcode is None:
        return [], []
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    service_item_col = None
    for col in df_filtered.columns:
        if col.lower().replace("_", " ").strip() == "service item":
            service_item_col = col
            break
    if service_item_col is None:
        return [], []
    grouped = df_filtered.groupby(service_item_col, as_index=False).agg({'hours': 'sum', 'day_cost': 'sum'})
    grouped['day_cost'] = grouped['day_cost'].apply(lambda x: f"${x:,.2f}")
    grouped['hours'] = grouped['hours'].apply(lambda x: f"{x:.2f}")
    columns = [
        {'name': 'Service Item', 'id': service_item_col},
        {'name': 'Total Hours', 'id': 'hours'},
        {'name': 'Total Cost', 'id': 'day_cost'}
    ]
    data = grouped.to_dict('records')
    return data, columns

# Callback for Service Item Pie Charts
@app.callback(
    [Output('service-hours-pie-chart', 'figure'),
     Output('service-cost-pie-chart', 'figure')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_service_item_pie_charts(selected_jobcode, selected_years):
    import plotly.express as px
    if not selected_jobcode:
        default_fig = px.pie(title="No data available")
        return default_fig, default_fig
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        try:
            selected_years_int = [int(y) for y in selected_years]
            df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
        except Exception:
            pass
    if df_filtered.empty:
        default_fig = px.pie(title="No data available after filtering")
        return default_fig, default_fig
    service_item_col = None
    for col in df_filtered.columns:
        if col.lower().replace("_", " ").strip() == "service item":
            service_item_col = col
            break
    if service_item_col is None:
        for col in df_filtered.columns:
            if "service" in col.lower():
                service_item_col = col
                break
    if service_item_col is None:
        default_fig = px.pie(title="No 'service item' column found")
        return default_fig, default_fig
    grouped = df_filtered.groupby(service_item_col, as_index=False).agg({'hours': 'sum', 'day_cost': 'sum'})
    if grouped.empty:
        default_fig = px.pie(title="No data after grouping")
        return default_fig, default_fig
    fig_hours = px.pie(grouped, names=service_item_col, values='hours', title="Total Hours per Service Item")
    fig_hours.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
    fig_hours.update_layout(title={'text': "Total Hours per Service Item", 'x': 0.5})
    
    fig_cost = px.pie(grouped, names=service_item_col, values='day_cost', title="Total Cost per Service Item")
    fig_cost.update_traces(hovertemplate='<b>%{label}</b><br>Cost: $%{value:,.2f}<extra></extra>')
    fig_cost.update_layout(title={'text': "Total Cost per Service Item", 'x': 0.5})
    
    return fig_hours, fig_cost

# Callback for updating jobcode-dropdown options based on filters
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
        if 'Award Date' in filtered_projects.columns:
            # Convert to datetime (if not already)
            filtered_projects['Award Date'] = pd.to_datetime(filtered_projects['Award Date'], errors='coerce')
            filtered_projects = filtered_projects[
                filtered_projects['Award Date'].dt.year.isin([2017, 2025])
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
    valid_projects = filtered_projects['Project No'].unique()
    valid_jobcodes = global_merged_df[global_merged_df['jobcode_2'].apply(lambda x: extract_project_no(x) in valid_projects)]
    jobcode_values = valid_jobcodes['jobcode_2'].unique()
    options = [{'label': jc, 'value': jc} for jc in sorted(jobcode_values)]
    return options

@app.callback(
    Output('award-date', 'children'),
    [Input('jobcode-dropdown', 'value')]
)
def update_award_date(selected_jobcode):
    if selected_jobcode is None:
        return ""
    extracted_code = extract_project_no(selected_jobcode)
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
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

@app.callback(
    Output('project-description', 'children'),
    [Input('jobcode-dropdown', 'value')]
)
def update_project_description(selected_jobcode):
    if selected_jobcode is None:
        return ""
    extracted_code = extract_project_no(selected_jobcode)
    filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    if not filtered.empty:
        project_record = filtered.iloc[0]
        description = project_record.get('Project Description', "No Description Available")
        return html.Div([html.B("Project Description:"), " " + str(description)])
    return "No Project Description Found."
"""def update_pie_chart(selected_jobcode, selected_years):
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    if set(selected_years) == {"2024"}:
        value_col = 'total_hours_2024'
    elif set(selected_years) == {"2025"}:
        value_col = 'total_hours_2025'
    else:
        df_filtered['combined_total_hours'] = df_filtered['total_hours_2024'].fillna(0) + df_filtered['total_hours_2025'].fillna(0)
        value_col = 'combined_total_hours'
    grouped = df_filtered.groupby('Employee', as_index=False)[value_col].sum()
    total_hours = grouped[value_col].sum()
    fig = px.pie(
        grouped,
        names='Employee',
        values=value_col,
        title=f"Percentage of Hours by Employee for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Hours:</b> {total_hours:.2f}"
    )
    fig.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
    fig.update_layout(title={'x': 0.5}, legend=dict(orientation="v", x=1.1, y=0.5, xanchor="left", yanchor="middle"))
    return fig"""
@app.callback(
    Output('pie-chart', 'figure'),
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)



def update_pie_chart(selected_jobcode, selected_years):
    import plotly.express as px

    # 1) Filter for the selected jobcode
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if not selected_jobcode:
        return px.pie(title="No Jobcode Selected")

    # 2) Filter by year range
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]

    # 3) If your assign_total_hours function created total_hours_YYYY for each year:
    #    We can sum up whichever columns the user wants.
    if not selected_years:
        # No year selected? Just default to all hours?
        df_filtered['combined_total_hours'] = df_filtered['hours'].fillna(0)
        value_col = 'combined_total_hours'
    elif len(selected_years) == 1:
        # If exactly one year is selected, use that year’s column
        year = selected_years_int[0]
        value_col = f"total_hours_{year}"
    else:
        # If multiple years are selected, sum over all those columns
        df_filtered['combined_total_hours'] = 0
        for y in selected_years_int:
            col_name = f"total_hours_{y}"
            # If col_name doesn’t exist, skip it or fill with 0
            if col_name in df_filtered.columns:
                df_filtered['combined_total_hours'] += df_filtered[col_name].fillna(0)
        value_col = 'combined_total_hours'

    # 4) Group and create the pie chart
    if value_col not in df_filtered.columns:
        return px.pie(title=f"No column '{value_col}' found")

    grouped = df_filtered.groupby('Employee', as_index=False)[value_col].sum()
    total_hours = grouped[value_col].sum()
    fig = px.pie(
        grouped,
        names='Employee',
        values=value_col,
        title=f"Percentage of Hours by Employee for {selected_jobcode}<br><b>Total Hours:</b> {total_hours:.2f}"
    )
    fig.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
    fig.update_layout(title={'x': 0.5})
    return fig
@app.callback(
    [Output('cost-pie-chart', 'figure')],
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
def update_cost_pie_chart(selected_jobcode, selected_years):
    df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
    if selected_years:
        selected_years_int = [int(y) for y in selected_years]
        df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
    grouped = df_filtered.groupby('Employee', as_index=False)['day_cost'].sum()
    total_cost = grouped['day_cost'].sum()
    fig = px.pie(
        grouped,
        names='Employee',
        values='day_cost',
        title=f"Cost Distribution by Employee for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Cost:</b> ${total_cost:,.2f}"
    )
    fig.update_layout(title={'x': 0.5}, legend=dict(orientation="v", x=1.1, y=0.5, xanchor="left", yanchor="middle"))
    fig.update_traces(hovertemplate='<b>%{label}</b><br>Employee Cost: %{value:$,.2f}<extra></extra>')
    return [fig]

@app.callback(
    [Output('project-table-left', 'data'),
     Output('project-table-left', 'columns'),
     Output('project-table-right', 'data'),
     Output('project-table-right', 'columns')],
    [Input('jobcode-dropdown', 'value')]
)
def update_project_tables(selected_jobcode):
    if not selected_jobcode:
        return [], [], [], []

    extracted_code = extract_project_no(selected_jobcode)
    # 1) Find the relevant project row(s) in global_projects_df
    df_filtered = global_projects_df[global_projects_df['Project No'].str[:7] == extracted_code]
    
    if df_filtered.empty:
        print_green(f"No matching project found for jobcode: {selected_jobcode}")
        return [], [], [], []

    # We'll just take the first matching row
    project_record = df_filtered.iloc[0]

    # 2) Build the left table from selected fields
    left_fields = ['Clients', 'Type', 'Status', 'Service Line', 'Market Segment', 'PM']
    left_available = [col for col in left_fields if col in project_record.index]
    left_df = pd.DataFrame([(fld, project_record[fld]) for fld in left_available],
                           columns=['Field', 'Value'])

  # 3) Filter raw invoices for the same Project No & sum
    project_no = project_record['Project No']
    project_no_std = standardize_project_no(project_no)  # Standardize the project no from the project log

    # Make a copy of raw invoices and standardize its "Project No" column
    df_invoices_filtered = global_raw_invoices.copy()
    df_invoices_filtered['Project No'] = df_invoices_filtered['Project No']\
        .astype(str).str.strip().apply(standardize_project_no)

    # Filter on the standardized value
    df_invoices_filtered = df_invoices_filtered[df_invoices_filtered['Project No'] == project_no_std]
    total_invoice_val = df_invoices_filtered['Actual'].sum()  # sum of 'Actual' amounts

    # 4) Filter timesheet for the same jobcode & sum cost
    df_timesheet_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode]
    total_cost = df_timesheet_filtered['day_cost'].sum()

    # 5) Parse contracted amount from the project record
    contracted_amount = project_record.get('Contracted Amount', None)
    # If "Contracted Amount" is a string like "$52,000.00", parse to float
    def parse_contract(x):
        try:
            return float(str(x).replace('$', '').replace(',', '').strip())
        except:
            return None
    contracted_float = parse_contract(contracted_amount)

    # 6) Compute any derived fields
    remaining_to_invoice = None
    if contracted_float is not None:
        remaining_to_invoice = contracted_float - total_invoice_val
    er_contract = None
    if contracted_float and total_cost:
        er_contract = contracted_float / total_cost
    er_invoiced = None
    if contracted_float and total_invoice_val:
        er_invoiced = total_invoice_val / total_cost


    
    # 7) Build the right table
    right_data = {
        'Contracted Amount': contracted_amount,
        'Total Invoice': total_invoice_val,
        'Remaining to be invoiced': remaining_to_invoice,
        'Total Cost': total_cost,
        'ER Contract': er_contract,
        'ER Invoiced': er_invoiced
    }
    # Format numeric fields
    formatted_right_data = {}
    for key, val in right_data.items():
        if val is None:
            formatted_right_data[key] = "N/A"
        elif isinstance(val, (int, float)):
            # If it's one of the ER fields, show 2 decimals
            if "ER" in key:
                formatted_right_data[key] = f"{val:.2f}"
            else:
                # It's a money value
                formatted_right_data[key] = f"${val:,.2f}"
        else:
            # It's likely a string like "$52,000.00" for 'Contracted Amount'
            formatted_right_data[key] = val
    right_df = pd.DataFrame(list(formatted_right_data.items()), columns=['Field', 'Value'])

    # 8) Return data/columns for left & right tables
    left_columns = [{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}]
    right_columns = [{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}]

    return (
        left_df.to_dict('records'), left_columns,
        right_df.to_dict('records'), right_columns
    )


# Callbacks for toggling "Other" dropdown inputs in Add New Project tab
@app.callback(Output('status-other-div', 'style'), [Input('input-status-dropdown', 'value')])
def toggle_status_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('type-other-div', 'style'), [Input('input-type-dropdown', 'value')])
def toggle_type_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('service-line-other-div', 'style'), [Input('input-service-line-dropdown', 'value')])
def toggle_service_line_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('market-other-div', 'style'), [Input('input-market-dropdown', 'value')])
def toggle_market_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('pm-other-div', 'style'), [Input('input-pm-dropdown', 'value')])
def toggle_pm_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

@app.callback(Output('clients-other-div', 'style'), [Input('input-clients-dropdown', 'value')])
def toggle_clients_other(selected_value):
    return {'display': 'block', 'margin-top': '5px'} if selected_value == 'Other' else {'display': 'none'}

# Callback for submitting a new project
@app.callback(
    Output('new-project-message', 'children'),
    [Input('submit-new-project', 'n_clicks')],
    [
        State('input-project-no', 'value'),
        State('input-status-dropdown', 'value'),
        State('input-status-other', 'value'),
        State('input-type-dropdown', 'value'),
        State('input-type-other', 'value'),
        State('input-service-line-dropdown', 'value'),
        State('input-service-line-other', 'value'),
        State('input-market-dropdown', 'value'),
        State('input-market-other', 'value'),
        State('input-project-description', 'value'),
        State('input-no', 'value'),
        State('input-clients-dropdown', 'value'),
        State('input-clients-other', 'value'),
        State('input-award-date', 'value'),
        State('input-contracted-amount', 'value'),
        State('input-pm-dropdown', 'value'),
        State('input-pm-other', 'value')
    ]
)
def add_new_project(n_clicks, proj_no, status_dd, status_other, type_dd, type_other,
                    service_line_dd, service_line_other, market_dd, market_other,
                    proj_desc, no_val, clients_dd, clients_other, award_date,
                    contracted_amt, pm_dd, pm_other):
    if not n_clicks:
        return ""
    status_val = status_other if status_dd == 'Other' else status_dd
    type_val = type_other if type_dd == 'Other' else type_dd
    service_line_val = service_line_other if service_line_dd == 'Other' else service_line_dd
    market_val = market_other if market_dd == 'Other' else market_dd
    clients_val = clients_other if clients_dd == 'Other' else clients_dd
    pm_val = pm_other if pm_dd == 'Other' else pm_dd
    new_project = {
        "Project No": standardize_project_no(proj_no) if proj_no else "",
        "Status": status_val if status_val else "",
        "Type": type_val if type_val else "",
        "Service Line": service_line_val if service_line_val else "",
        "Market Segment": market_val if market_val else "",
        "Project Description": proj_desc if proj_desc else "",
        "No.": no_val if no_val else "",
        "Clients": clients_val if clients_val else "",
        "Award Date": award_date if award_date else "",
        "Contracted Amount": f"${float(contracted_amt):,.2f}" if contracted_amt else "",
        "PM": pm_val if pm_val else ""
    }
    global global_projects_df
    global_projects_df = pd.concat([global_projects_df, pd.DataFrame([new_project])], ignore_index=True)
    print_green("New project added:")
    print_green(str(new_project))
    
    return "New project added successfully and backup updated!"

# -------------------------------------------------------------------
# 5) Run the Server
# -------------------------------------------------------------------
if __name__ == '__main__':
    print(">>> main() returned. Now starting server.")

    app.run_server(debug=True, host='10.1.2.149', port=7050, use_reloader=False)
