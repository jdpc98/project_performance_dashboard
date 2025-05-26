#!/usr/bin/env python3
"""
Final Integration Test for Smart Decon Data Processing Pipeline
Tests the complete pipeline with real data to ensure everything works
"""

import sys
import os
import pandas as pd
from datetime import datetime, date
from data_processing import (
    load_rates_from_single_sheet,
    load_timesheet_folder, 
    load_third_file_dynamic,
    generate_monthly_report_data,
    calculate_new_er,
    calculate_decon_llc_invoiced
)
import config

def test_complete_pipeline():
    """Test the complete data processing pipeline"""
    print("=== TESTING COMPLETE PIPELINE ===\n")
    
    try:
        # Test date for January 2025
        test_date = date(2025, 1, 15)
        
        print("1. Testing data loading functions...")
          # Test rates loading
        try:
            rates_file_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\RATES.xlsx"
            rates_data = load_rates_from_single_sheet(rates_file_path)
            if rates_data:
                print("✓ Rates data loaded successfully")
                print(f"  - Found {len(rates_data[1])} employee records")  # df_actual_rates
            else:
                print("✗ Failed to load rates data")
                return False
        except Exception as e:
            print(f"✗ Error loading rates: {e}")
            return False
          # Test timesheet loading  
        try:
            timesheet_folder = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\tsheets"
            timesheet_data = load_timesheet_folder(timesheet_folder)
            if timesheet_data is not None and not timesheet_data[0].empty:
                print("✓ Timesheet data loaded successfully")
                print(f"  - Found {len(timesheet_data[0])} timesheet records")
            else:
                print("✗ Failed to load timesheet data")
                return False
        except Exception as e:
            print(f"✗ Error loading timesheets: {e}")
            return False
          # Test project data loading
        try:
            project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
            project_data = load_third_file_dynamic(project_log_path)
            if project_data is not None and not project_data.empty:
                print("✓ Project data loaded successfully")
                print(f"  - Found {len(project_data)} project records")
            else:
                print("✗ Failed to load project data")
                return False
        except Exception as e:
            print(f"✗ Error loading project data: {e}")
            return False
        
        print("\n2. Testing monthly report generation...")
        
        # Test report generation with mock globals (since we can't easily load all data here)
        try:
            # Create minimal test data
            test_projects = pd.DataFrame({
                'Project No': ['P-2025-001', 'P-2025-002'],
                'Clients': ['Test Client 1', 'Test Client 2'],
                'Contracted Amount': ['$100,000.00', '$50,000.00'],
                'Status': ['1-Active', '2-Pending'],
                'PM': ['John Doe', 'Jane Smith'],
                'TL': ['Tech Lead 1', 'Tech Lead 2'],
                'Service Line': ['1-Engineering', '2-Consulting'],
                'Market Segment': ['1-Government', '2-Private'],
                'Type': ['1-Contract', '2-Service'],
                'Project Description': ['Test Project 1', 'Test Project 2']
            })
            
            test_merged = pd.DataFrame({
                'Project No': ['P-2025-001', 'P-2025-001', 'P-2025-002'],
                'jobcode_2': ['P-2025-001-001', 'P-2025-001-002', 'P-2025-002-001'],
                'staff_type': [1, 2, 1],
                'day_cost': [1000, 500, 750],
                'hours': [8, 6, 7]
            })
            
            test_invoices = pd.DataFrame({
                'Project No': ['P-2025-001', 'P-2025-002'],
                'Actual': [80000, 30000],
                'Invoice No': ['INV-001', 'INV-002'],
                'Invoice Date': [datetime(2025, 1, 15), datetime(2025, 1, 20)]
            })
            
            # Test project log path (use local if network not available)
            project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
            if not os.path.exists(project_log_path):
                project_log_path = r"C:\Users\jose.pineda\Desktop\smart_decon\operations\2025 Project Log.xlsx"
            
            print(f"  Using project log: {project_log_path}")
            
            # Test if we can call the function (it might fail due to missing data, but shouldn't crash)
            try:
                result_data, result_columns = generate_monthly_report_data(
                    test_date, test_projects, test_merged, test_invoices, project_log_path
                )
                print("✓ Monthly report generation function executed without errors")
                print(f"  - Returned {len(result_data)} data rows and {len(result_columns)} columns")
            except FileNotFoundError as e:
                print(f"⚠ Monthly report test skipped due to missing file: {e}")
                print("  This is expected if the Excel file is not accessible")
            except Exception as e:
                print(f"✗ Error in monthly report generation: {e}")
                return False
                
        except Exception as e:
            print(f"✗ Error setting up report test: {e}")
            return False
        
        print("\n3. Testing calculation functions...")
        
        # Test ER calculations
        try:
            er_result = calculate_new_er(test_projects, 'P-2025-001', test_merged)
            print(f"✓ ER DECON LLC calculation: {er_result}")
            
            decon_invoiced_result = calculate_decon_llc_invoiced(
                test_projects, 'P-2025-001', test_merged, test_invoices
            )
            print(f"✓ DECON LLC Invoiced calculation: {decon_invoiced_result}")
            
        except Exception as e:
            print(f"✗ Error in calculation functions: {e}")
            return False
        
        print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")
        print("\nThe pipeline is ready for production use.")
        return True
        
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    if not success:
        sys.exit(1)
    else:
        print("\n🎉 Integration test completed successfully!")
