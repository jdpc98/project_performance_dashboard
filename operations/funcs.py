# funcs.py

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
from dash.dash_table.Format import Format, Scheme, Symbol
import plotly.express as px
import pandas as pd
#import dash_bootstrap_components as dbc
import numpy as np
import pickle
import os
import plotly.graph_objects as go
import traceback
import base64

import data_processing
import config
from print_utils import print_green, print_cyan, print_orange, print_red
from data_processing import extract_project_no
from config import TABLE_STYLE, TABLE_CELL_STYLE, TABLE_CELL_CONDITIONAL, RIGHT_TABLE_RED_STYLE

# Load the logo image
with open(r"C:\Users\jose.pineda\Desktop\smart_decon\operations\logodecon2.jpg", "rb") as image_file:
    encoded_logo = base64.b64encode(open(r"C:\Users\jose.pineda\Desktop\smart_decon\operations\logodecon2.jpg", "rb").read()).decode()

# Load the data directly from Excel for the most up-to-date information
print(f"Loading data from direct Excel processing...")
try:
    # Use the new function that loads data directly from Excel
    global_merged_df, global_projects_df, global_invoices, global_raw_invoices, last_update = data_processing.load_and_process_direct_excel()
    print(f"Data loaded directly from Excel. Last update: {last_update}")
    
    # Check for February 2025 data specifically
    feb_2025_data = global_raw_invoices[
        (global_raw_invoices['Month_numeric'] == 2) & 
        (global_raw_invoices['Invoice_Year'] == 2025)
    ]
    print(f"February 2025 data check: Found {len(feb_2025_data)} records, {feb_2025_data['Project No'].nunique()} unique projects")
    
except Exception as e:
    print(f"Error loading data directly from Excel: {str(e)}")
    print("Falling back to pickle files...")
    
    # Define pickle paths
    PICKLE_DIR = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles"
    
    # Load the data from pickles
    with open(os.path.join(PICKLE_DIR, "global_merged_df.pkl"), 'rb') as f:
        global_merged_df = pickle.load(f)
    
    with open(os.path.join(PICKLE_DIR, "global_projects_df.pkl"), 'rb') as f:
        global_projects_df = pickle.load(f)
    
    with open(os.path.join(PICKLE_DIR, "global_invoices.pkl"), 'rb') as f:
        global_invoices = pickle.load(f)
    
    with open(os.path.join(PICKLE_DIR, "global_raw_invoices.pkl"), 'rb') as f:
        global_raw_invoices = pickle.load(f)
    
    with open(os.path.join(PICKLE_DIR, "last_update.txt"), 'r') as f:
        last_update = f.read().strip()
    print(f"Data loaded from pickle files. Last update: {last_update}")

# Standardize Project No format for all dataframes
def standardize_project_no(x):
    """Convert a project number to float with 2 decimals, or strip string."""
    try:
        # Convert to float and format with 2 decimal places
        float_val = float(x)
        # Return as string with exactly 2 decimal places always (keep .00)
        formatted = f"{float_val:.2f}"
        return formatted
    except Exception:
        return str(x).strip()

# Apply standardization to all dataframes
global_projects_df['Project No'] = global_projects_df['Project No'].apply(standardize_project_no)
global_invoices['Project No'] = global_invoices['Project No'].apply(standardize_project_no)
global_raw_invoices['Project No'] = global_raw_invoices['Project No'].apply(standardize_project_no)


def register_callbacks(app):
    # ------------------------------------------------------------
    # Callback: Overall Client Summary Pie Charts (aggregated)
    @app.callback(
        [Output('client-total-cost-pie', 'figure'),
         Output('client-total-hours-pie', 'figure')],
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
        cost_by_client = df_merged.groupby('Clients', as_index=False)['day_cost'].sum()
        hours_by_client = df_merged.groupby('Clients', as_index=False)['hours'].sum()
        fig_cost = px.pie(cost_by_client, names='Clients', values='day_cost', title="Total Cost by Client")
        fig_hours = px.pie(hours_by_client, names='Clients', values='hours', title="Total Hours by Client")
        fig_cost.update_layout(title={'x': 0.5})
        fig_hours.update_layout(title={'x': 0.5})
        return fig_cost, fig_hours

    # ------------------------------------------------------------
    # Callback: Client Summary (detailed projects table with financial metrics)
    @app.callback(
        [Output('client-summary-table', 'data'),
         Output('client-summary-table', 'columns'),
         Output('client-projects-table', 'data'),
         Output('client-projects-table', 'columns')],
        [Input('client-dropdown', 'value')]
    )
    def update_client_summary(selected_client):
        if not selected_client:
            return [], [], [], []
        
        # Filter projects for the selected client (case-insensitive)
        df_client_projects = global_projects_df[
            global_projects_df['Clients'].str.strip().str.lower() == selected_client.strip().lower()
        ].copy()
        print_green("Client selected: " + selected_client)
        print_green("Number of projects for client: " + str(len(df_client_projects)))
        
        # Build a summary table by fixed status
        possible_statuses = [
            "0-Under Production", "1-Completed Production", "2-Invoicing",
            "3-Retainage Pending", "4-", "5-Canceled", "6-Closed", "7-Frozen"
        ]
        summary_data = []
        for status in possible_statuses:
            count = df_client_projects['Status'].str.strip().str.lower().eq(status.lower()).sum()
            summary_data.append({"Metric": f"{status} Projects", "Value": f"{count}"})
        summary_columns = [
            {'name': 'Metric', 'id': 'Metric'},
            {'name': 'Value', 'id': 'Value'}
        ]
        
        # Detailed Projects Table:
        client_project_nos = df_client_projects['Project No'].unique().tolist()
        invoices_grouped = global_invoices.groupby('Project No', as_index=False)['TotalInvoice'].sum()
        df_timesheet = global_merged_df.copy()
        df_timesheet['Project No'] = df_timesheet['jobcode_2'].apply(extract_project_no)
        cost_grouped = df_timesheet.groupby('Project No', as_index=False)['day_cost'].sum()
        df_detail = df_client_projects.copy()
        df_detail = pd.merge(df_detail, invoices_grouped, on='Project No', how='left')
        df_detail = pd.merge(df_detail, cost_grouped, on='Project No', how='left')
        df_detail.rename(columns={'TotalInvoice': 'Total Invoice', 'day_cost': 'Total Cost'}, inplace=True)
        
        def parse_contract(x):
            try:
                return float(str(x).replace('$', '').replace(',', '').strip())
            except:
                return None
        df_detail['Contracted Amount Parsed'] = df_detail['Contracted Amount'].apply(parse_contract)
        
        # Compute ER values as numeric (do not convert to strings)
        df_detail['ER Contract'] = df_detail.apply(
            lambda row: round(row['Contracted Amount Parsed'] / row['Total Cost'], 2)
            if row['Total Cost'] and row['Contracted Amount Parsed'] is not None else None,
            axis=1
        )
        df_detail['ER Invoiced'] = df_detail.apply(
            lambda row: round(row['Contracted Amount Parsed'] / row['Total Invoice'], 2)
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
        
        detail_cols = ['Project No', 'Status', 'Type', 'Market Segment', 'Contracted Amount',
                       'Total Invoice', 'Total Cost', 'ER Contract', 'ER Invoiced']
        detail_cols = [c for c in detail_cols if c in df_detail.columns]
        df_detail_final = df_detail[detail_cols].copy()
        detail_data = df_detail_final.to_dict('records')
        detail_columns = []
        for col in detail_cols:
            if col in ['ER Contract', 'ER Invoiced']:
                detail_columns.append({
                    'name': col,
                    'id': col,
                    'type': 'numeric',
                    'format': Format(precision=2, scheme=Scheme.fixed)
                })
            else:
                detail_columns.append({'name': col, 'id': col})
        
        return summary_data, summary_columns, detail_data, detail_columns

    # ------------------------------------------------------------
    # Callback: Service Item Details Table
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
            {'name': 'Total Budget', 'id': 'day_cost'}
        ]
        data = grouped.to_dict('records')
        return data, columns

    # ------------------------------------------------------------
    # Callback: Service Item Pie Charts
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
        df_filtered = global_merged_df[global_merged_df['Project No'] == selected_jobcode].copy()
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

    # ------------------------------------------------------------
    # Callback: Time Distribution by Employee Pie Chart
    @app.callback(
    Output('pie-chart', 'figure'),
    [Input('jobcode-dropdown', 'value'),
     Input('year-dropdown', 'value')]
)
    def update_pie_chart(selected_jobcode, selected_years):
        import plotly.express as px
        import plotly.graph_objects as go
        
        print(f"Selected jobcode: {selected_jobcode}")
        print(f"Selected years: {selected_years}")
        
        # Try both filtering methods until one works
        df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
        
        if df_filtered.empty:
            # If first filter didn't work, try with Project No (extracted from jobcode)
            project_no = extract_project_no(selected_jobcode)
            df_filtered = global_merged_df[global_merged_df['Project No'] == project_no].copy()
            print(f"Retrying with Project No: {project_no}, found {len(df_filtered)} rows")
        
        print(f"Filtered DataFrame after jobcode filter: {df_filtered.shape}")
        
        # Print columns to help with debugging
        if not df_filtered.empty:
            print("Columns in df_filtered:")
            print(df_filtered.columns.tolist())
            print(df_filtered[['Project No', 'local_date', 'Service Item', 'day_cost', 'hours']].head(30))
        
        # Apply year filter if provided
        if selected_years:
            selected_years_int = [int(y) for y in selected_years]
            df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
            print(f"Filtered DataFrame after year filter: {df_filtered.shape}")
        
        # If the DataFrame is empty after filtering, return empty figure
        if df_filtered.empty:
            return go.Figure(layout=dict(title="No data available"))
        
        # Check if column exists before using
        if 'hours' in df_filtered.columns:
            value_col = 'hours'  # Default to using the hours column
        else:
            print("No hours column found!")
            return go.Figure(layout=dict(title="Missing hours column"))
        
        # Group by employee
        employee_col = 'Employee'
        if employee_col not in df_filtered.columns:
            for col in ['Personel', 'full_name', 'fname']:
                if col in df_filtered.columns:
                    employee_col = col
                    break
        
        if employee_col not in df_filtered.columns:
            return go.Figure(layout=dict(title="No employee column found"))
        
        # Group and create chart
        grouped = df_filtered.groupby(employee_col, as_index=False)[value_col].sum()
        total_hours = grouped[value_col].sum()
        
        fig = px.pie(
            grouped,
            names=employee_col,
            values=value_col,
            title=f"Percentage of Hours by Employee for {selected_jobcode}<br>Total Hours: {total_hours:.2f}"
        )
        
        fig.update_traces(hovertemplate='<b>%{label}</b><br>Hours: %{value:.2f}<extra></extra>')
        fig.update_layout(title={'x': 0.5}, legend=dict(orientation="v", x=1.1, y=0.5, xanchor="left", yanchor="middle"))
        return fig

    # ------------------------------------------------------------
    # Callback: Cost Distribution by Employee Pie Chart
    @app.callback(
        [Output('cost-pie-chart', 'figure')],
        [Input('jobcode-dropdown', 'value'),
         Input('year-dropdown', 'value')]
    )
    def update_cost_pie_chart(selected_jobcode, selected_years):
        print(f"Selected jobcode: {selected_jobcode}")
        print(f"Selected years: {selected_years}")
        df_filtered = global_merged_df[global_merged_df['jobcode_2'] == selected_jobcode].copy()
        print(f"Filtered DataFrame after jobcode filter: {df_filtered.shape}")
        if selected_years:
            selected_years_int = [int(y) for y in selected_years]
            df_filtered = df_filtered[df_filtered['local_date'].dt.year.isin(selected_years_int)]
            print(f"Filtered DataFrame after year filter: {df_filtered.shape}")
        grouped = df_filtered.groupby('Employee', as_index=False)['day_cost'].sum()
        print(f"Grouped data: {grouped}")
        total_cost = grouped['day_cost'].sum()
        print(f"Total cost: {total_cost}")
        fig = px.pie(
            grouped,
            names='Employee',
            values='day_cost',
            title=f"Cost Distribution by Employee for Jobcode: {extract_project_no(selected_jobcode)}<br><b>Total Cost:</b> ${total_cost:,.2f}"
        )
        fig.update_layout(title={'x': 0.5}, legend=dict(orientation="v", x=1.1, y=0.5, xanchor="left", yanchor="middle"))
        fig.update_traces(hovertemplate='<b>%{label}</b><br>Employee Cost: %{value:$,.2f}<extra></extra>')
        return [fig]

    # ------------------------------------------------------------
    # Callback: Award Date
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

    # ------------------------------------------------------------
    # Callback: Project Description
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

    # ------------------------------------------------------------
    # Callbacks for toggling "Other" dropdown inputs in Add New Project Tab
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

    # ------------------------------------------------------------
    # Callback: Add New Project
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
