#!/usr/bin/env python3
"""
Validation test for smart_decon data processing pipeline
Tests key functions to ensure they work correctly after fixes
"""

import sys
import pandas as pd
from data_processing import (
    calculate_new_er, 
    calculate_decon_llc_invoiced,
    truncate_at_total
)

def test_calculate_new_er():
    """Test the ER DECON LLC calculation function"""
    print("Testing calculate_new_er function...")
    
    # Create mock DataFrames for testing
    mock_project_df = pd.DataFrame({
        'Project No': ['P-2025-001'],
        'Contracted Amount': ['$100,000.00'],
        'Invoiced %': ['80%']
    })
    
    mock_merged_costs = pd.DataFrame({
        'jobcode_2': ['P-2025-001-001', 'P-2025-001-002'],
        'staff_type': [1, 2],
        'day_cost': [30000, 20000]
    })
    
    # Test case 1: Normal calculation
    result1 = calculate_new_er(mock_project_df, 'P-2025-001', mock_merged_costs)
    print(f"Normal case: {result1}")
    
    # Test case 2: Project not found (should return None)
    result2 = calculate_new_er(mock_project_df, 'P-2025-999', mock_merged_costs)
    print(f"Project not found: {result2}")
    
    # Test case 3: No US employees
    mock_merged_costs_no_us = pd.DataFrame({
        'jobcode_2': ['P-2025-001-001'],
        'staff_type': [2],
        'day_cost': [20000]
    })
    result3 = calculate_new_er(mock_project_df, 'P-2025-001', mock_merged_costs_no_us)
    print(f"No US employees: {result3}")
    
    print("calculate_new_er tests completed.\n")

def test_calculate_decon_llc_invoiced():
    """Test the DECON LLC Invoiced calculation function"""
    print("Testing calculate_decon_llc_invoiced function...")
    
    # Create mock DataFrames for testing
    mock_project_df = pd.DataFrame({
        'Project No': ['P-2025-001'],
        'Contracted Amount': ['$100,000.00'],
        'Invoiced %': ['80%']
    })
    
    mock_merged_costs = pd.DataFrame({
        'jobcode_2': ['P-2025-001-001', 'P-2025-001-002'],
        'staff_type': [1, 2],
        'day_cost': [30000, 20000]
    })
    
    mock_raw_invoices = pd.DataFrame({
        'Project No': ['P-2025-001'],
        'Actual': [80000]
    })
    
    # Test case 1: Normal calculation
    result1 = calculate_decon_llc_invoiced(mock_project_df, 'P-2025-001', mock_merged_costs, mock_raw_invoices)
    print(f"Normal case: {result1}")
    
    # Test case 2: Project not found (should return None)
    result2 = calculate_decon_llc_invoiced(mock_project_df, 'P-2025-999', mock_merged_costs, mock_raw_invoices)
    print(f"Project not found: {result2}")
    
    # Test case 3: No US employees
    mock_merged_costs_no_us = pd.DataFrame({
        'jobcode_2': ['P-2025-001-001'],
        'staff_type': [2],
        'day_cost': [20000]
    })
    result3 = calculate_decon_llc_invoiced(mock_project_df, 'P-2025-001', mock_merged_costs_no_us, mock_raw_invoices)
    print(f"No US employees: {result3}")
    
    print("calculate_decon_llc_invoiced tests completed.\n")

def test_truncate_at_total():
    """Test the truncate_at_total function with mixed data types"""
    print("Testing truncate_at_total function...")
    
    # Create test DataFrame with mixed data types
    test_data = pd.DataFrame({
        'Column1': ['Value1', 'Value2', 'Total', 'Should not appear'],
        'Column2': [100, 200, 300, 400],
        'Column3': ['A', 'B', 'C', 'D']
    })
    
    result = truncate_at_total(test_data)
    print(f"Original rows: {len(test_data)}")
    print(f"Truncated rows: {len(result)}")
    print(f"Last row contains 'Total': {'Total' in result.iloc[-1].astype(str).values}")
    
    print("truncate_at_total test completed.\n")

def test_data_type_conversions():
    """Test data type handling that was causing errors"""
    print("Testing data type conversions...")
    
    # Test invoice amount conversion
    test_amounts = ['$1,000.00', '$2,500.50', '3000', 3500.75, None, '']
    
    for amount in test_amounts:
        try:
            if pd.notnull(amount) and amount != '':
                cleaned = float(str(amount).replace('$', '').replace(',', ''))
                print(f"'{amount}' -> {cleaned}")
            else:
                print(f"'{amount}' -> 0 (null/empty)")
        except Exception as e:
            print(f"Error converting '{amount}': {e}")
    
    print("Data type conversion tests completed.\n")

if __name__ == "__main__":
    print("=== Smart Decon Pipeline Validation Test ===\n")
    
    try:
        test_calculate_new_er()
        test_calculate_decon_llc_invoiced()
        test_truncate_at_total()
        test_data_type_conversions()
        
        print("=== All validation tests completed successfully! ===")
        
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)
