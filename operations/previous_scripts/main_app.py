# main_app.py

import dash
from dash import dcc, html, dash_table
import funcs   # import callbacks and data from funcs.py
import config

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = dcc.Tabs(id='tabs-example', value='tab-dashboard', children=[
    # -------------------------
    # TAB 1: DASHBOARD
    # -------------------------
    dcc.Tab(label='Dashboard', value='tab-dashboard', children=[
        html.Div([
            # Logo
            html.Div(
                [html.Img(src='data:image/png;base64,{}'.format(config.encoded_logo), style={'height': '75px'})],
                style={'textAlign': 'center', 'padding': '10px'}
            ),
            html.H1("Project Performance", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
            
            # Filter dropdowns
            html.Div([
                html.H3("Filter Jobcodes by Project Details", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
                dcc.Dropdown(
                    id='filter-clients',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(funcs.global_projects_df['Clients'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Clients"
                ),
                dcc.Dropdown(
                    id='filter-type',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(funcs.global_projects_df['Type'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Type"
                ),
                dcc.Dropdown(
                    id='filter-status',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(funcs.global_projects_df['Status'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Status"
                ),
                dcc.Dropdown(
                    id='filter-service',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(funcs.global_projects_df['Service Line'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Service Line"
                ),
                dcc.Dropdown(
                    id='filter-market',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(funcs.global_projects_df['Market Segment'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select Market Segment"
                ),
                dcc.Dropdown(
                    id='filter-pm',
                    options=[{'label': str(val), 'value': str(val)} 
                             for val in sorted(funcs.global_projects_df['PM'].dropna().unique(), key=lambda x: str(x))],
                    multi=True,
                    placeholder="Select PM"
                )
            ], style={'width': '80%', 'margin': 'auto', 'padding': '20px', 'textAlign': 'center'}),
            
            # Jobcode and Year dropdowns
            html.Div([
                html.Div([
                    html.Label("Select Jobcode:"),
                    dcc.Dropdown(
                        id='jobcode-dropdown',
                        options=[],  # Updated via callback
                        clearable=False
                    )
                ], style={'width': '30%', 'margin': 'auto'}),
                html.Div([
                    html.Label("Select Year(s):"),
                    dcc.Dropdown(
                        id='year-dropdown',
                        options=[
                            {'label': '2022', 'value': '2022'},
                            {'label': '2023', 'value': '2023'},
                            {'label': '2024', 'value': '2024'},
                            {'label': '2025', 'value': '2025'}
                        ],
                        value=['2024', '2025'],
                        multi=True,
                        clearable=False
                    )
                ], style={'width': '30%', 'margin': 'auto', 'paddingTop': '10px'})
            ], style={'textAlign': 'center'}),
            
            # Project description and award date placeholders
            html.Div(id='project-description', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
            html.Div(id='award-date', style={'textAlign': 'center', 'padding': '20px', 'margin': '20px', 'fontSize': '18px'}),
            
            # Two tables: Project Details and Cost & Contract Details
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
                        columns=[{'name': 'Field', 'id': 'Field'}, {'name': 'Value', 'id': 'Value'}],
                        data=[],
                        style_table=config.TABLE_STYLE,
                        style_cell=config.TABLE_CELL_STYLE,
                        style_cell_conditional=config.TABLE_CELL_CONDITIONAL,
                        style_data_conditional=config.RIGHT_TABLE_RED_STYLE
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
            
            # Two small pie charts for service item totals
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
            
            # Pie charts for employee distributions
            html.H2("Time Distribution by Employee", style={'textAlign': 'center', 'paddingTop': '20px'}),
            html.Div(dcc.Graph(id='pie-chart'), style={'width': '60%', 'margin': '0 auto'}),
            html.Div([
                html.H2("Cost Distribution by Employee", style={'textAlign': 'center'}),
                html.Div(dcc.Graph(id='cost-pie-chart'), style={'width': '60%', 'margin': '0 auto'})
            ], style={'textAlign': 'center', 'paddingTop': '20px'})
        ])
    ]),
    
    # -------------------------
    # TAB 2: CLIENT SUMMARY
    # -------------------------
    dcc.Tab(label='Client Summary', value='tab-clients', children=[
        html.Div([
            # Overall client pie charts
            html.Div([
                html.Div([
                    dcc.Graph(id='client-total-cost-pie', style={'height': '300px'})
                ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'}),
                html.Div([
                    dcc.Graph(id='client-total-hours-pie', style={'height': '300px'})
                ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'})
            ], style={'textAlign': 'center'}),
            
            html.H3("Client Summary", style={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'}),
            
            # Client Dropdown
            html.Div([
                html.Label("Select Client:", style={'fontFamily': 'Calibri, sans-serif'}),
                dcc.Dropdown(
                    id='client-dropdown',
                    options=[{'label': c, 'value': c}
                             for c in sorted(funcs.global_projects_df['Clients'].dropna().unique())],
                    placeholder="Type or select a client...",
                    clearable=True
                )
            ], style={'width': '30%', 'margin': 'auto', 'padding': '10px'}),
            html.Hr(),
            
            # Client Summary Table
            dash_table.DataTable(
                id='client-summary-table',
                columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}],
                data=[],
                style_table={'width': '40%', 'margin': 'auto', 'overflowY': 'auto'},
                style_cell= config.TABLE_CELL_STYLE
            ),
            
            # Detailed Projects Table for the selected client (with conditional styling)
            dash_table.DataTable(
                id='client-projects-table',
                columns=[],  # set via callback
                data=[],     # set via callback
                style_table={'width': '80%', 'margin': 'auto', 'overflowY': 'auto'},
                style_cell={'textAlign': 'center', 'fontFamily': 'Calibri, sans-serif'},
                style_data_conditional=[
                    {
                        'if': {
                            'filter_query': '{ER Invoiced} < 1',
                            'column_id': 'ER Invoiced'
                        },
                        'color': 'red',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{ER Invoiced} >= 1 && {ER Invoiced} <= 2',
                            'column_id': 'ER Invoiced'
                        },
                        'color': 'orange',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{ER Invoiced} > 2',
                            'column_id': 'ER Invoiced'
                        },
                        'color': 'green',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{ER Contract} < 1',
                            'column_id': 'ER Contract'
                        },
                        'color': 'red',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{ER Contract} >= 1 && {ER Contract} <= 2',
                            'column_id': 'ER Contract'
                        },
                        'color': 'orange',
                        'fontWeight': 'bold'
                    },
                    {
                        'if': {
                            'filter_query': '{ER Contract} > 2',
                            'column_id': 'ER Contract'
                        },
                        'color': 'green',
                        'fontWeight': 'bold'
                    }
                ]
            )
        ])
    ]),
    
    # -------------------------
    # TAB 3: ADD NEW PROJECT
    # -------------------------
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
                             for val in sorted(funcs.global_projects_df['Status'].dropna().unique())] 
                             + [{'label': 'Other', 'value': 'Other'}],
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
                             for val in sorted(funcs.global_projects_df['Type'].dropna().unique())] 
                             + [{'label': 'Other', 'value': 'Other'}],
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
                             for val in sorted(funcs.global_projects_df['Service Line'].dropna().unique())] 
                             + [{'label': 'Other', 'value': 'Other'}],
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
                             for val in sorted(funcs.global_projects_df['Market Segment'].dropna().unique())] 
                             + [{'label': 'Other', 'value': 'Other'}],
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
                             for val in sorted(funcs.global_projects_df['PM'].dropna().unique())] 
                             + [{'label': 'Other', 'value': 'Other'}],
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
                             for val in sorted(funcs.global_projects_df['Clients'].dropna().unique())] 
                             + [{'label': 'Other', 'value': 'Other'}],
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

# Register callbacks from funcs.py
funcs.register_callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=True, host='10.1.2.111', port=7050, use_reloader=False)
