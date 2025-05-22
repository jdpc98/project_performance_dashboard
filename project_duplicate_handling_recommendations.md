# Project Duplicate Handling Recommendations

## Overview
This document provides recommendations for handling projects with identical Project No (ID) but different names in the jobcode_2 field.

## Current Implementation
The current implementation:
1. Detects duplicate Project No entries
2. Merges descriptions with " + " separator
3. Sums numerical values (hours, costs, etc.)
4. Uses the most common value for categorical fields
5. Preserves jobcode_3 values from all duplicates

## ER DECON LLC Calculation
The ER DECON LLC field is calculated as: `(contracted_amount - type_2_cost) / type_1_cost`

Where:
- type_1_cost = sum of costs for US employees (staff_type=1)
- type_2_cost = sum of costs for Colombian employees (staff_type=2)

### Division by Zero Cases
When type_1_cost = 0, the division would result in an error. The current handling:

1. For projects with 0% invoiced percentage, ER DECON LLC is set to 0
2. For projects with 100% invoiced percentage, ER DECON LLC is set to "N/A"
3. For all other cases with worked hours but no calculated value, ER DECON LLC is "0.00"

## Recommendations

### For Data Preservation
- Continue summing numerical fields (hours, costs) to ensure no data is lost
- For descriptive fields, concatenate with a separator
- For categorical fields, use the most frequent value or a business-defined rule

### For ER DECON LLC
- When merging data, ensure staff_type is preserved correctly
- After merging, recalculate ER DECON LLC based on the merged data
- Consider adding a flag or note to indicate when values have been merged

### For Long-term Solution
1. Implement a data validation process to catch duplicate Project No entries early
2. Consider a more sophisticated merge logic based on business rules:
   - Different merge strategies for different field types
   - User-guided merging for critical projects

### For UI Presentation
- Indicate merged projects with a visual cue
- Provide a way to see the original data before merging
- Show a breakdown of costs by staff_type after merging
