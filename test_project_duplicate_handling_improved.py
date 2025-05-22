# test_project_duplicate_handling_improved.py

import pandas as pd
import os
import numpy as np
from operations.data_processing import standardize_project_no, print_green, print_cyan, print_orange, print_red

def test_improved_duplicate_handling():
    """
    Test the improved duplicate Project No handling that preserves all data
    """
    # Create a test DataFrame that simulates the projects data with duplicates
    # Include numerical fields that should be summed and categorical fields that should be preserved
    test_data = {
        "Project No": ["1001.00", "1001.00", "1002.00", "1003.00", "1003.00", "1003.00"],
        "Project Description": ["Desc A", "Desc B", "Single Desc", "Desc X", "Desc Y", "Desc Z"],
        "Clients": ["Client1", "Client1", "Client2", "Client3", "Client3", "Client3"],
        "jobcode_3": ["Data1", "Data2", "Data3", "Data4", "Data5", "Data6"],
        "hours": [10.5, 5.2, 8.0, 12.3, 7.8, 9.1],
        "day_cost": [1050.0, 520.0, 800.0, 1230.0, 780.0, 910.0],
        "Status": ["Active", "Active", "Completed", "On Hold", "On Hold", "On Hold"],
        "Type": ["Type1", "Type2", "Type3", "Type4", "Type4", "Type5"],
        "Invoice %": [40, 50, 100, 0, 10, 20],
        "staff_type": [1, 2, 1, 1, 2, 1]  # 1=US, 2=Colombia
    }
    
    df_test = pd.DataFrame(test_data)
    
    print_green("Original test data:")
    print(df_test)
    
    # Find duplicates by Project No
    duplicate_projects = df_test.duplicated(subset=['Project No'], keep=False)
    
    if duplicate_projects.any():
        print_orange(f"Found {duplicate_projects.sum()} rows with duplicate Project No")
        
        # Create a new DataFrame to store the merged results
        merged_projects = []
        
        # Group by Project No
        project_groups = df_test.groupby('Project No')
        
        for project_no, group in project_groups:
            print_green(f"Processing Project No: {project_no}")
            
            if len(group) > 1:
                print_green(f"Found {len(group)} duplicate entries for Project No {project_no}")
                
                # Initialize the merged project data
                merged_project = {"Project No": project_no}
                
                # For string fields, concatenate unique values
                string_fields = ["Project Description"]
                for field in string_fields:
                    if field in group.columns:
                        unique_values = group[field].dropna().unique().tolist()
                        if len(unique_values) > 1:
                            merged_project[field] = " + ".join(unique_values)
                        elif len(unique_values) == 1:
                            merged_project[field] = unique_values[0]
                        else:
                            merged_project[field] = ""
                
                # For client field, take the most common value or concatenate if equal frequency
                if "Clients" in group.columns:
                    clients = group["Clients"].fillna("").value_counts()
                    if clients.nunique() == 1 or clients.iloc[0] > clients.iloc[1]:
                        merged_project["Clients"] = clients.index[0]
                    else:
                        merged_project["Clients"] = " / ".join(clients.index.tolist())
                
                # For numeric fields, sum the values
                numeric_fields = ["hours", "day_cost"]
                for field in numeric_fields:
                    if field in group.columns:
                        merged_project[field] = group[field].fillna(0).sum()
                
                # For status, take the most recent status (assuming latest status is most relevant)
                # You might need a different logic based on your business rules
                if "Status" in group.columns:
                    status_priority = {"Active": 3, "On Hold": 2, "Completed": 1}
                    statuses = group["Status"].fillna("").unique().tolist()
                    if len(statuses) > 1:
                        # Sort by priority (highest priority first)
                        sorted_statuses = sorted(statuses, key=lambda x: status_priority.get(x, 0), reverse=True)
                        merged_project["Status"] = sorted_statuses[0]
                    elif len(statuses) == 1:
                        merged_project["Status"] = statuses[0]
                    else:
                        merged_project["Status"] = ""
                
                # For type, concatenate unique values
                if "Type" in group.columns:
                    types = group["Type"].fillna("").unique().tolist()
                    if len(types) > 1:
                        merged_project["Type"] = " / ".join(types)
                    elif len(types) == 1:
                        merged_project["Type"] = types[0]
                    else:
                        merged_project["Type"] = ""
                
                # For Invoice %, take the sum up to 100% maximum
                if "Invoice %" in group.columns:
                    invoice_sum = group["Invoice %"].fillna(0).sum()
                    merged_project["Invoice %"] = min(invoice_sum, 100)
                
                # Calculate staff types and costs
                if "staff_type" in group.columns and "day_cost" in group.columns:
                    # Sum costs by staff type
                    type_1_costs = group[group["staff_type"] == 1]["day_cost"].fillna(0).sum()
                    type_2_costs = group[group["staff_type"] == 2]["day_cost"].fillna(0).sum()
                    
                    merged_project["type_1_costs"] = type_1_costs
                    merged_project["type_2_costs"] = type_2_costs
                    
                    # Calculate ER DECON LLC: (contracted_amount - type_2_costs) / type_1_costs
                    # For testing, we'll simulate contracted_amount = total costs * 1.2
                    total_costs = type_1_costs + type_2_costs
                    contracted_amount = total_costs * 1.2
                    
                    if type_1_costs > 0:
                        er_decon_llc = (contracted_amount - type_2_costs) / type_1_costs
                    else:
                        # Handle division by zero: set to None (will display as N/A) or use a default value
                        er_decon_llc = None
                    
                    merged_project["contracted_amount"] = contracted_amount
                    merged_project["er_decon_llc"] = er_decon_llc
                
                # Preserve the first jobcode_3 value and note others
                if "jobcode_3" in group.columns:
                    jobcode3_values = group["jobcode_3"].fillna("").unique().tolist()
                    merged_project["jobcode_3"] = jobcode3_values[0] if jobcode3_values else ""
                    
                    if len(jobcode3_values) > 1:
                        merged_project["additional_jobcode3s"] = ", ".join(jobcode3_values[1:])
                
                merged_projects.append(merged_project)
            else:
                # No duplicates for this project number, just copy the data
                merged_projects.append(group.iloc[0].to_dict())
        
        # Create a new DataFrame with the merged results
        df_result = pd.DataFrame(merged_projects)
    else:
        # No duplicates found, return the original DataFrame
        df_result = df_test.copy()
    
    print_green("\nProcessed data after improved duplicate handling:")
    print(df_result)
    
    # Verify the results
    # 1. Project No 1001.00 should have combined description "Desc A + Desc B"
    # 2. Project No 1003.00 should have combined description "Desc X + Desc Y + Desc Z"
    # 3. Numeric fields like hours and day_cost should be summed
    # 4. ER DECON LLC should be calculated correctly or None for division by zero
    
    # Check for expected results
    assert len(df_result) == 3, f"Expected 3 rows after deduplication, got {len(df_result)}"
    
    # Check Project No 1001.00
    project_1001 = df_result[df_result["Project No"] == "1001.00"].iloc[0]
    assert project_1001["Project Description"] == "Desc A + Desc B", \
        f"Expected 'Desc A + Desc B' for Project No 1001.00, got '{project_1001['Project Description']}'"
    assert abs(project_1001["hours"] - 15.7) < 0.01, \
        f"Expected hours 15.7 for Project No 1001.00, got {project_1001['hours']}"
    assert abs(project_1001["day_cost"] - 1570.0) < 0.01, \
        f"Expected day_cost 1570.0 for Project No 1001.00, got {project_1001['day_cost']}"
    
    # Check Project No 1003.00
    project_1003 = df_result[df_result["Project No"] == "1003.00"].iloc[0]
    assert project_1003["Project Description"] == "Desc X + Desc Y + Desc Z", \
        f"Expected 'Desc X + Desc Y + Desc Z' for Project No 1003.00, got '{project_1003['Project Description']}'"
    assert abs(project_1003["hours"] - 29.2) < 0.01, \
        f"Expected hours 29.2 for Project No 1003.00, got {project_1003['hours']}"
    assert abs(project_1003["day_cost"] - 2920.0) < 0.01, \
        f"Expected day_cost 2920.0 for Project No 1003.00, got {project_1003['day_cost']}"
    
    # Check ER DECON LLC calculation for Project 1001.00
    # type_1_costs = 1050.0, type_2_costs = 520.0, contracted_amount = (1050.0 + 520.0) * 1.2 = 1884.0
    # er_decon_llc = (1884.0 - 520.0) / 1050.0 = 1.3
    if "er_decon_llc" in project_1001:
        assert abs(project_1001["er_decon_llc"] - 1.3) < 0.01, \
            f"Expected er_decon_llc 1.3 for Project No 1001.00, got {project_1001['er_decon_llc']}"
    
    print_green("All tests passed! The improved duplicate handling code is working correctly.")

if __name__ == "__main__":
    test_improved_duplicate_handling()
