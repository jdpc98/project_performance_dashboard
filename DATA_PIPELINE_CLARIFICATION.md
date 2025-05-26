# Smart Decon Data Processing Pipeline - Variable and Flow Clarification

## Overview
This document provides a comprehensive mapping of all variables, their purposes, and the data flow in the smart_decon project's data processing pipeline.

## Main Data Processing Pipeline Flow

### 1. Data Loading Phase

#### A. **Rates Data Loading** (`load_rates_from_single_sheet()`)
**Source**: `\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\RATES.xlsx`

**DataFrames Created**:
- `df_trm_vals` - TRM (presumably TRM exchange rate values)
- `df_actual_rates` - Employee rates by month/year with columns like:
  - `ID#` - Employee identifier
  - `Employee` - Employee name
  - `2022Whole_Year`, `2023Whole_Year` - Annual rates
  - `2024JAN`, `2024FEB`, etc. - Monthly rates for 2024
  - `2024JUL (1-15)`, `2024JUL (15-31)` - Partial July rates
  - `2025JAN`, `2025FEB`, etc. - Monthly rates for 2025
- `loaded_c` - Loaded coefficients
- `loaded_rates` - Additional loaded rates
- `df_sub_col` - Staff classification data from 'STAFF' sheet with `staff_type` (1=US, 2=Colombian)

#### B. **Timesheet Data Loading** (`load_timesheet_folder()`)
**Source**: `C:\Users\jose.pineda\Desktop\smart_decon\operations\tsheets\timesheet_report_*.csv`

**DataFrame Created**: `df_new`
**Key Columns**:
- `number` - Employee ID number
- `fname`, `lname` - Employee first and last names  
- `full_name` - Concatenated full name
- `local_date` - Date of work
- `hours` - Hours worked
- `jobcode_2` - Primary project code
- `jobcode_3` - Secondary project code
- `correct_number` - Mapped employee ID

#### C. **Project Log Data Loading** (`load_third_file_dynamic()`)
**Source**: `\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx`
**Sheet**: `4_Contracted Projects`

**DataFrame Created**: `df_projects`
**Key Columns**:
- `Project No` - Standardized project number
- `Clients` - Client name
- `Status` - Project status
- `PM` - Project Manager
- `Project Description` - Description
- `TL` - Team Lead
- `Service Line` - Service line classification
- `Market Segment` - Market segment
- `Type` - Project type
- `Contracted Amount` - Contract value
- `Month` - Month (derived if not present)

#### D. **Invoice Data Loading** (Multiple sheets)
**Source**: Same project log file
**Sheets**: `5_Invoice-2023`, `5_Invoice-2024`, `5_Invoice-2025`

**DataFrames Created**: `df_invoices_2023`, `df_invoices_2024`, `df_invoices_2025`
**Combined**: `df_invoices` and `raw_invoices`
**Key Columns**:
- `Project No` - Project number
- `Month` - Invoice month
- `Month_numeric` - Numeric month value
- `Invoice No` - Invoice number (cleaned)
- `Invoice Date` - Invoice date
- `Actual` - Invoice amount (cleaned and numeric)
- `Invoice_Year` - Year column (2023, 2024, 2025)

#### E. **Forecast Data Loading** (`import_forecast_invoicing()`)
**Source**: Same project log file
**Sheet**: `6_Summary Invoice`

**DataFrame Created**: `forecast_df`
**Columns**:
- `Month` - Month number (1-12)
- `MonthName` - Month name
- `Year` - 2025
- `ForecastValue` - Forecasted invoice amount

### 2. Data Processing Phase

#### A. **Employee ID Mapping**
- Maps `*` values in rates to unique IDs (starting from 1001)
- Creates mapping dictionary: `Employee Name -> ID#`
- Fills zero IDs in timesheet using name mapping

#### B. **Data Merging**
**Primary Merge**: `merged_df = merge(df_actual_rates + df_new + df_sub_col)`
- Merges rates + timesheet on `ID#` = `correct_number`
- Adds staff classification (`staff_type`)

#### C. **Cost Calculations**
**Function**: `calculate_day_cost(merged_df)`
- Calculates `day_cost` = `rate * hours` for each timesheet entry
- Uses appropriate rate column based on date:
  - Before 2022: `2022Whole_Year`
  - 2022: `2022Whole_Year` or partial July columns
  - 2023: `2023Whole_Year`
  - 2024+: Monthly columns (e.g., `2024JAN`) or partial July

**Function**: `assign_total_hours(merged_df)`
- Creates `total_hours_YYYY` columns for each year (2017-2025)

#### D. **Invoice Processing**
- Cleans and standardizes invoice data
- Converts `Actual` amounts to numeric
- Filters out future-dated invoices
- Creates summary: `global_invoices` (grouped by project)

### 3. Report Generation Phase

#### **Function**: `generate_monthly_report_data()`
**Purpose**: Creates monthly project reports with calculated metrics

**Key Variables and Calculations**:

##### A. **Basic Project Data**
- `project_no` - Standardized project number
- `project_row` - Single project record from projects DataFrame
- `project_costs` - Filtered timesheet costs for the project
- `project_invoices` - Filtered invoices for the project

##### B. **Financial Calculations**
- `total_cost` - Sum of `day_cost` for the project
- `total_invoice` - Sum of invoice `Actual` amounts
- `contracted_amount` - Contract value (parsed from string)

##### C. **ER (Efficiency Ratio) Calculations**
- `er_contract` = `contracted_amount / total_cost`
- `er_invoiced` = `total_invoice / total_cost`
- `new_er` = **ER DECON LLC** (calculated by `calculate_new_er()`)
- `decon_llc_invoiced` = **DECON LLC Invoiced** (calculated by `calculate_decon_llc_invoiced()`)

##### D. **Invoiced Percentage**
- `invoiced_percent_num` = `(total_invoice / contracted_amount) * 100`
- `invoiced_percent` = Formatted string version (e.g., "85.5%")

##### E. **Monthly Data from Invoice Sheets**
From the specific month's invoice sheet:
- `projected_value` - Projected amount for the month
- `actual_value` - Actual invoice amount for the month  
- `acummulative_value` - Cumulative amount

## Key Variable Definitions and Purposes

### **Staff Type Classification**
- `staff_type = 1` - US employees (DECON LLC)
- `staff_type = 2` - Colombian employees (DECON Colombia)

### **ER DECON LLC Calculation**
```python
new_er = (contracted_amount - type_2_cost) / type_1_cost
```
Where:
- `type_1_cost` = Sum of costs for US employees (staff_type=1)
- `type_2_cost` = Sum of costs for Colombian employees (staff_type=2)

**Business Logic**:
- Shows efficiency ratio excluding Colombian staff costs
- Returns `None` (displayed as "N/A") if no US employees
- Returns `0` for 0% invoiced projects
- Returns `None` for 100% invoiced projects (displayed as "N/A")

### **DECON LLC Invoiced Calculation**
```python
decon_llc_invoiced = (invoiced_amount - type_2_cost) / type_1_cost
```
Where:
- `invoiced_amount` = Total invoiced amount for the project
- `type_2_cost` = Sum of costs for Colombian employees
- `type_1_cost` = Sum of costs for US employees

**Business Logic**:
- Shows invoiced ratio excluding Colombian staff costs
- Returns `None` (displayed as "N/A") if no US employees
- Returns `0` for 0% invoiced projects
- Returns `None` for 100% invoiced projects (displayed as "N/A")

### **Display Logic for ER Values**
- **"N/A"** - No worked hours OR no US employees OR 100% invoiced projects
- **"0.00"** - Projects with worked hours but zero calculated value
- **Calculated Value** - Valid calculation possible

## Data Flow Summary

```
1. RATES.xlsx → Employee rates by month/year
2. Timesheet CSVs → Hours worked by employee/project/date
3. Project Log → Project details and contract amounts
4. Invoice Sheets → Invoice amounts by project/month
5. Forecast Sheet → Projected 2025 values

                     ↓ MERGE ↓

6. merged_df → Timesheet + Rates + Staff Classification
   - Calculate day_cost = rate × hours
   - Add total_hours by year

7. Invoice Processing → Clean and standardize invoice data

8. Monthly Report Generation:
   - Filter projects for selected month/year
   - Calculate total costs and invoices per project
   - Calculate ER values (Contract, Invoiced, DECON LLC)
   - Calculate invoiced percentages
   - Apply display logic for special cases

                     ↓ OUTPUT ↓

9. Monthly Report Table with all metrics
```

## File Locations

- **Rates**: `\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\RATES.xlsx`
- **Project Log**: `\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx`
- **Timesheets**: `C:\Users\jose.pineda\Desktop\smart_decon\operations\tsheets\`
- **Pickles**: `C:\Users\jose.pineda\Desktop\smart_decon\operations\pickles\`

## Global Variables Used in App

- `global_merged_df` - Master timesheet+rates data
- `global_projects_df` - Project information  
- `global_invoices` - Summarized invoice data by project
- `global_raw_invoices` - Raw invoice data for calculations
- `forecast_df` - 2025 forecast data

This pipeline ensures accurate cost tracking, invoice management, and efficiency ratio calculations while properly handling the distinction between US and Colombian staff for DECON LLC-specific metrics.
