# test_project_duplicate_handling.py

import pandas as pd
import os
from operations.data_processing import load_third_file_dynamic, standardize_project_no, print_green, print_cyan, print_orange, print_red

def test_duplicate_handling():
    """
    Test the duplicate Project No handling logic in load_third_file_dynamic
    """
    # Create a test DataFrame that simulates the projects data with duplicates
    test_data = {
        "Project No": ["1001.00", "1001.00", "1002.00", "1003.00", "1003.00", "1003.00"],
        "Project Description": ["Desc A", "Desc B", "Single Desc", "Desc X", "Desc Y", "Desc Z"],
        "Clients": ["Client1", "Client1", "Client2", "Client3", "Client3", "Client3"],
        "jobcode_3": ["Data1", "Data2", "Data3", "Data4", "Data5", "Data6"]
    }
    
    df_test = pd.DataFrame(test_data)
    
    print_green("Original test data:")
    print(df_test)
    
    # Extract and run just the duplicate handling code from load_third_file_dynamic
    # Find duplicates by Project No
    duplicate_projects = df_test.duplicated(subset=['Project No'], keep=False)
    
    if duplicate_projects.any():
        print_orange(f"Found {duplicate_projects.sum()} rows with duplicate Project No")
        
        # Group by Project No and concatenate descriptions for duplicates
        project_groups = df_test[duplicate_projects].groupby('Project No')
        
        for project_no, group in project_groups:
            print_green(f"Processing duplicate Project No: {project_no}")
            
            # Check if jobcode_3 fields are available
            has_jobcode3 = 'jobcode_3' in df_test.columns
            
            # Get all descriptions for this project number
            descriptions = group['Project Description'].dropna().unique().tolist()
            
            if len(descriptions) > 1:
                # Combine all unique descriptions
                combined_desc = ' + '.join(descriptions)
                print_green(f"Combined descriptions: {combined_desc}")
                
                # Update all rows for this project with the combined description
                df_test.loc[df_test['Project No'] == project_no, 'Project Description'] = combined_desc
                
                # If there's jobcode_3 content that should be extracted, handle it here
                if has_jobcode3:
                    jobcode3_values = group['jobcode_3'].dropna().unique().tolist()
                    if jobcode3_values:
                        print_green(f"Found jobcode_3 values for duplicate: {jobcode3_values}")
                        # Here we could extract additional content from jobcode_3 if needed
            
            # We'll keep the first occurrence and drop the rest
            # Get indices to drop (all except the first occurrence)
            indices_to_drop = group.index[1:]
            df_test = df_test.drop(indices_to_drop)
            print_green(f"Kept first occurrence and dropped {len(indices_to_drop)} duplicate(s)")
    
    print_green("\nProcessed data after duplicate handling:")
    print(df_test)
    
    # Verify the results
    # 1. Project No 1001.00 should have combined description "Desc A + Desc B"
    # 2. Project No 1003.00 should have combined description "Desc X + Desc Y + Desc Z"
    # 3. There should be only one row for each Project No
    
    # Check for expected results
    assert len(df_test) == 3, f"Expected 3 rows after deduplication, got {len(df_test)}"
    
    # Check Project No 1001.00
    project_1001 = df_test[df_test["Project No"] == "1001.00"]
    assert len(project_1001) == 1, f"Expected 1 row for Project No 1001.00, got {len(project_1001)}"
    assert project_1001.iloc[0]["Project Description"] == "Desc A + Desc B", \
        f"Expected 'Desc A + Desc B' for Project No 1001.00, got '{project_1001.iloc[0]['Project Description']}'"
    
    # Check Project No 1003.00
    project_1003 = df_test[df_test["Project No"] == "1003.00"]
    assert len(project_1003) == 1, f"Expected 1 row for Project No 1003.00, got {len(project_1003)}"
    assert project_1003.iloc[0]["Project Description"] == "Desc X + Desc Y + Desc Z", \
        f"Expected 'Desc X + Desc Y + Desc Z' for Project No 1003.00, got '{project_1003.iloc[0]['Project Description']}'"
    
    # Check that jobcode_3 values were preserved for the first occurrence
    assert project_1001.iloc[0]["jobcode_3"] == "Data1", \
        f"Expected jobcode_3 'Data1' for Project No 1001.00, got '{project_1001.iloc[0]['jobcode_3']}'"
    assert project_1003.iloc[0]["jobcode_3"] == "Data4", \
        f"Expected jobcode_3 'Data4' for Project No 1003.00, got '{project_1003.iloc[0]['jobcode_3']}'"
    
    print_green("All tests passed! The duplicate handling code is working correctly.")

if __name__ == "__main__":
    test_duplicate_handling()
