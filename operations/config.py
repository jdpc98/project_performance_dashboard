# config.py

import base64

# ----- Table Style Settings -----
TABLE_STYLE = {
    'overflowX': 'auto',
    'width': '100%',
    'border': '1px solid #ccc',
    'borderCollapse': 'collapse'
}
TABLE_CELL_STYLE = {
    'textAlign': 'left',
    'padding': '5px',
    'fontFamily': 'Calibri, sans-serif'
}
TABLE_CELL_CONDITIONAL = [
    {'if': {'column_id': 'Field'}, 'width': '40%'},
    {'if': {'column_id': 'Value'}, 'width': '60%'}
]

DATA_CONDITIONAL_ER = [

    # ER Contract < 1
    {
        'if': {
            'filter_query': '{Field} = "ER Contract" && {Value_num}  < 1'
            ,'column_id': 'Value'
        },
        'color': 'red',
        'fontWeight': 'bold'
    },
    # ER Contract between 1 and 2
    {
        'if': {
            'filter_query': '{Field} = "ER Contract" && {Value_num}  >= 1 && {Value_num}  <= 2'
            ,'column_id': 'Value'
        },
        'color': 'orange',
        'fontWeight': 'bold'
    },
    # ER Contract > 2
    {
        'if': {
            'filter_query': '{Field} = "ER Contract" && {Value_num}  > 2'
            ,'column_id': 'Value'
        },
        'color': 'green',
        'fontWeight': 'bold'
    },
    # ER Invoiced < 1
    {
        'if': {
            'filter_query': '{Field} = "ER Invoiced" && {Value_num}  < 1'
            ,'column_id': 'Value'
        },
        'color': 'red',
        'fontWeight': 'bold'
    },
    # ER Invoiced between 1 and 2
    {
        'if': {
            'filter_query': '{Field} = "ER Invoiced" && {Value_num}  >= 1 && {Value_num} <= 2'
            ,'column_id': 'Value'
        },
        'color': 'orange',
        'fontWeight': 'bold'
    },
    # ER Invoiced > 2
    {
        'if': {
            'filter_query': '{Field} = "ER Invoiced" && {Value_num}  > 2'
            ,'column_id': 'Value'
        },
        'color': 'green',
        'fontWeight': 'bold'
    },
        # Add the same conditional styling for DECON LLC ONLY ER
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC ONLY ER" && {Value_num} >= 2.5'}, 'color': 'green', 'fontWeight': 'bold'},
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC ONLY ER" && {Value_num} < 1 && {Value_num} >= 1.2'}, 'color': 'orange', 'fontWeight': 'bold'},
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC ONLY ER" && {Value_num} < 1'}, 'color': 'red', 'fontWeight': 'bold'},
    
    # Add conditional styling for DECON LLC Invoiced
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC Invoiced" && {Value_num} < 1'}, 'color': 'red', 'fontWeight': 'bold'},
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC Invoiced" && {Value_num} >= 1 && {Value_num} <= 2.5'}, 'color': 'orange', 'fontWeight': 'bold'},
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC Invoiced" && {Value_num} > 2.5'}, 'color': 'green', 'fontWeight': 'bold'},
    
    # For the client projects table, add similar conditions for the column directly
    {'if': {'column_id': 'DECON LLC ER', 'filter_query': '{DECON LLC ER} >= 2.5'}, 'color': 'green', 'fontWeight': 'bold'},
    {'if': {'column_id': 'DECON LLC ER', 'filter_query': '{DECON LLC ER} < 2.5 && {DECON LLC ER} >= 1.2'}, 'color': 'orange', 'fontWeight': 'bold'},
    {'if': {'column_id': 'DECON LLC ER', 'filter_query': '{DECON LLC ER} < 1'}, 'color': 'red', 'fontWeight': 'bold'},
    
    # Add direct column conditions for DECON LLC Invoiced
    {'if': {'column_id': 'DECON LLC Invoiced', 'filter_query': '{DECON LLC Invoiced} < 1'}, 'color': 'red', 'fontWeight': 'bold'},
    {'if': {'column_id': 'DECON LLC Invoiced', 'filter_query': '{DECON LLC Invoiced} >= 1 && {DECON LLC Invoiced} <= 2.5'}, 'color': 'orange', 'fontWeight': 'bold'},
    {'if': {'column_id': 'DECON LLC Invoiced', 'filter_query': '{DECON LLC Invoiced} > 2.5'}, 'color': 'green', 'fontWeight': 'bold'},
    
    # Total row styling (keep this at the end)
    {'if': {'filter_query': '{Project No} = "TOTAL"'}, 'fontWeight': 'bold'}
]



RIGHT_TABLE_RED_STYLE = [
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
            'filter_query': '{ER Invoiced} >= 1 && {ER Invoiced} <= 2.5',
            'column_id': 'ER Invoiced'
        },
        'color': 'orange',
        'fontWeight': 'bold'
    },
    {
        'if': {
            'filter_query': '{ER Invoiced} > 2.5',
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
            'filter_query': '{ER Contract} >= 1 && {ER Contract} <= 2.5',
            'column_id': 'ER Contract'
        },
        'color': 'orange',
        'fontWeight': 'bold'
    },
    {
        'if': {
            'filter_query': '{ER Contract} > 2.5',
            'column_id': 'ER Contract'
        },
        'color': 'green',
        'fontWeight': 'bold'
    },
    # Add conditional styling for DECON LLC Invoiced
    {
        'if': {
            'filter_query': '{DECON LLC Invoiced} < 1',
            'column_id': 'DECON LLC Invoiced'
        },
        'color': 'red',
        'fontWeight': 'bold'
    },
    {
        'if': {
            'filter_query': '{DECON LLC Invoiced} >= 1 && {DECON LLC Invoiced} <= 2.5',
            'column_id': 'DECON LLC Invoiced'
        },
        'color': 'orange',
        'fontWeight': 'bold'
    },
    {
        'if': {
            'filter_query': '{DECON LLC Invoiced} > 2.5',
            'column_id': 'DECON LLC Invoiced'
        },
        'color': 'green',
        'fontWeight': 'bold'
    },
    # Add the same conditional styling for DECON LLC ONLY ER
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC ONLY ER" && {Value_num} >= 2.5'}, 'color': 'green', 'fontWeight': 'bold'},
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC ONLY ER" && {Value_num} < 2.5 && {Value_num} >= 1.2'}, 'color': 'orange', 'fontWeight': 'bold'},
    {'if': {'column_id': 'Value', 'filter_query': '{Field} = "DECON LLC ONLY ER" && {Value_num} < 1'}, 'color': 'red', 'fontWeight': 'bold'},
    
    # For the client projects table, add similar conditions for the column directly
    {'if': {'column_id': 'DECON LLC ER', 'filter_query': '{DECON LLC ER} >= 2.5'}, 'color': 'green', 'fontWeight': 'bold'},
    {'if': {'column_id': 'DECON LLC ER', 'filter_query': '{DECON LLC ER} < 2.5 && {DECON LLC ER} >= 1.2'}, 'color': 'orange', 'fontWeight': 'bold'},
    {'if': {'column_id': 'DECON LLC ER', 'filter_query': '{DECON LLC ER} < 1'}, 'color': 'red', 'fontWeight': 'bold'},
    
    # Total row styling (keep this at the end)
    {'if': {'filter_query': '{Project No} = "TOTAL"'}, 'fontWeight': 'bold'}
]


# ----- Logo Setup -----
LOGO_PATH = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\logodecon2.jpg"


with open(LOGO_PATH, 'rb') as f:
    encoded_logo = base64.b64encode(f.read()).decode('ascii')

