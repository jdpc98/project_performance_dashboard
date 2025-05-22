# Smart Decon Code Restructuring Plan

## Current Issues Identified
1. **Duplicate Functions**: Multiple `generate_monthly_report` functions across different files
2. **Mixed Responsibilities**: Functions handling both data processing and UI logic
3. **Missing Type Column**: Error in project type extraction
4. **Invoiced % Calculation Errors**: Inconsistent percentage calculations
5. **Redundant Imports**: Multiple files importing same libraries

## Clean 4-File Architecture

### 1. `config.py` - Configuration & Constants
**Purpose**: All configuration, constants, file paths, and settings
```python
# File paths
PROJECT_LOG_PATH = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
RATES_FILE_PATH = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\RATES.xlsx"
TIMESHEET_FOLDER = r"C:\Users\jose.pineda\Desktop\operations\tsheets"
PICKLE_OUTPUT_DIR = r"C:\Users\jose.pineda\Desktop\operations\cache"

# Constants
SUPPORTED_YEARS = [2023, 2024, 2025]
INVOICE_SHEET_FORMAT = "5_Invoice-{year}"
DEFAULT_ER_THRESHOLDS = {"low": 1.0, "mid": 2.5}

# UI Configuration
LOGO_PATH = "logo.png"
TABLE_COLUMNS_CONFIG = {...}
```

### 2. `utility_funcs.py` - Pure Utility Functions
**Purpose**: Reusable helper functions with no dependencies on global data
```python
# String processing
def standardize_project_no(project_no)
def extract_project_no(jobcode)
def extract_number_part(value)
def parse_currency(value)
def format_currency(value)

# Date utilities
def calculate_week_of_month(date)
def get_month_year_from_date(date)

# Data validation
def validate_project_data(df)
def clean_numeric_columns(df, columns)

# File operations
def safe_file_read(path, fallback_path=None)
def get_last_update_timestamp()

# Logging/printing utilities
def print_green(msg)
def print_red(msg)
def print_cyan(msg)
```

### 3. `data_processing.py` - Data Loading, Processing & Business Logic
**Purpose**: All data operations, calculations, and business logic
```python
# === DATA LOADING FUNCTIONS ===
def load_timesheet_folder(folder_path)
def load_project_log_data(years=[2023, 2024, 2025])
def load_invoice_data(project_log_path, year)
def load_rates_data(rates_path)

# === CORE PROCESSING FUNCTIONS ===
def generate_monthly_report_data(selected_date, global_projects_df, global_merged_df, global_raw_invoices, project_log_path)
    """
    SINGLE SOURCE OF TRUTH for monthly report data generation
    Consolidates all duplicate generate_monthly_report functions
    """

# === CALCULATION FUNCTIONS ===
def calculate_er_values(project_no, projects_df, merged_df, invoices_df)
def calculate_invoiced_percentage(total_invoice, contracted_amount)
def calculate_decon_llc_metrics(project_no, projects_df, merged_df, invoices_df)

# === DATA AGGREGATION ===
def aggregate_forecast_data(report_data)
def aggregate_by_project_type(report_data)
def create_summary_tables(report_data)

# === CACHING FUNCTIONS ===
def load_cached_data(cache_key)
def save_to_cache(data, cache_key)
def import_forecast_invoicing()
```

### 4. `app_main.py` - UI, Dash Callbacks & Presentation
**Purpose**: User interface, Dash app setup, callbacks, and presentation logic
```python
# === APP SETUP ===
app = dash.Dash(__name__)
layout definition...

# === UI CALLBACKS ===
@app.callback(...)
def generate_monthly_report(selected_date):
    """Calls data_processing.generate_monthly_report_data and formats for UI"""

@app.callback(...)
def export_weekly_report_pdf(n_clicks, table_data, ...):
    """Takes UI data and exports to PDF"""

@app.callback(...)
def update_charts(selected_project, selected_years):
    """Chart generation for UI"""

# === EXPORT CALLBACKS ===
@app.callback(...)
def export_excel_dashboard(...)

@app.callback(...)
def export_client_pdf(...)

# === UI HELPER FUNCTIONS ===
def format_table_for_display(data, columns)
def apply_conditional_formatting(data)
def create_html_for_pdf(data, title)
```

## Functions to Consolidate/Remove

### Duplicate `generate_monthly_report` functions to merge into ONE:
1. `data_processing.py::generate_monthly_report_data()` ✅ **KEEP as main function**
2. `invoice_driven_report.py::generate_monthly_report()` ❌ **REMOVE**
3. `invoice_driven_utils.py::generate_monthly_report()` ❌ **REMOVE**
4. `app_main.py::generate_monthly_report()` ✅ **KEEP as UI callback only**

### Files to Clean Up/Remove:
- `invoice_driven_report.py` - Functions to be merged into `data_processing.py`
- `invoice_driven_utils.py` - Functions to be merged into `data_processing.py`
- `pre_processing.ipynb` - Convert useful functions to Python and integrate

## Specific Issues to Fix

### 1. Type Column Missing/Error
**Location**: `data_processing.py::generate_monthly_report_data()`
**Issue**: Type extraction not working properly
**Fix**: 
```python
# In extract_number_part function
def extract_number_part(value):
    """Extract just the number prefix from strings like '1-Something', '2-Other', etc."""
    if not isinstance(value, str):
        return value
    
    import re
    # Look for patterns like "1-", "2.", "3:", etc.
    match = re.match(r'^(\d+)[-\.\s:]', value)
    if match:
        return match.group(1)
    return value
```

### 2. Invoiced % Calculation Errors
**Location**: `data_processing.py::generate_monthly_report_data()`
**Issue**: Division by zero and null handling
**Fix**:
```python
def calculate_invoiced_percentage(total_invoice, contracted_amount):
    """Safe calculation of invoiced percentage"""
    if not contracted_amount or contracted_amount <= 0:
        return None
    if not total_invoice or total_invoice < 0:
        return 0.0
    return min((total_invoice / contracted_amount * 100), 100.0)  # Cap at 100%
```

### 3. ER DECON LLC Calculation Issues
**Location**: `data_processing.py::calculate_new_er()`
**Issue**: Inconsistent handling of Colombian staff exclusion
**Fix**: Standardize the Colombian staff filtering logic

## Migration Steps

### Phase 1: Consolidation (Week 1)
1. Create new clean `config.py` with all constants
2. Move all utility functions to `utility_funcs.py`
3. Consolidate duplicate functions in `data_processing.py`
4. Remove redundant files (`invoice_driven_report.py`, `invoice_driven_utils.py`)

### Phase 2: Bug Fixes (Week 1)
1. Fix Type column extraction
2. Fix invoiced percentage calculations  
3. Fix ER DECON LLC calculations
4. Add proper error handling

### Phase 3: Testing & Validation (Week 2)
1. Test all existing functionality
2. Validate calculations against known good data
3. Performance testing
4. UI testing

### Phase 4: Documentation (Week 2)
1. Add comprehensive docstrings
2. Create function documentation
3. Add type hints
4. Create usage examples

## Expected Benefits
- **50% reduction in code duplication**
- **Clearer separation of concerns**
- **Easier maintenance and debugging**
- **Consistent calculation logic**
- **Better error handling**
- **Improved performance through caching**

## Files Summary After Restructuring:
- `config.py`: 150 lines (all constants/config)
- `utility_funcs.py`: 300 lines (pure utilities)
- `data_processing.py`: 800 lines (business logic)
- `app_main.py`: 1200 lines (UI/callbacks only)

**Total: ~2450 lines** (down from current ~3000+ lines across multiple files)
