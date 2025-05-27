#!/usr/bin/env python3
# complete_data_generation.py (CORREGIDO)

from data_processing import main, generate_monthly_report_data
from datetime import datetime
import sqlite3
import os
import pandas as pd
def run_complete_process():
    try:
        print("=== EJECUTANDO PROCESO COMPLETO =====")
        
        # Paso 1: Ejecutar main() para cargar todos los datos
        print("Paso 1: Ejecutando main()...")
        # main() returns: global_merged_df, global_projects_df, global_invoices, global_raw_invoices, last_update, last_data_update
        main_results = main()
        print(f"main() retornó {len(main_results)} elementos")
        
        global_merged_df = main_results[0]
        global_projects_df = main_results[1]
        # invoices_summary was previously used for global_invoices
        global_invoices_summary = main_results[2] 
        global_raw_invoices = main_results[3]
        # main_results[4] is last_update, main_results[5] is last_data_update (not used here)
        
        print(f"✅ Datos cargados:")
        print(f"  - Merged DF: {len(global_merged_df)} filas")
        print(f"  - Projects DF: {len(global_projects_df)} filas") 
        print(f"  - Raw Invoices: {len(global_raw_invoices)} filas")
        print(f"  - Summary Invoices (from global_invoices): {len(global_invoices_summary)} filas")
        print(f"  - Projects DF columnas: {list(global_projects_df.columns)[:5]}")
        
        # Paso 2: Generar datos del reporte mensual para enero 2025
        print("Paso 2: Generando datos del reporte mensual...")
        selected_date = datetime(2025, 5, 15)
        project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
        
        # generate_monthly_report_data returns: project_data_list, column_definitions
        generated_project_data, generated_column_info = generate_monthly_report_data(
            selected_date, global_projects_df, global_merged_df, global_raw_invoices, project_log_path
        )
        
        print(f"✅ Datos generados - Proyectos (filas de datos): {len(generated_project_data)}, Definiciones de columna: {len(generated_column_info)}")
        
        # Paso 3: Verificar que los datos tengan valores de forecast
        print("Paso 3: Verificando valores de forecast en los datos generados...")
        forecast_projects_found = 0
        # Iterate over the actual project data (generated_project_data)
        for i, project_record in enumerate(generated_project_data[:10]):  # Primeros 10 registros de proyectos
            proj_no = project_record.get('Project No', 'Unknown')
            projected = project_record.get('Projected', 'N/A')
            actual = project_record.get('Actual', 'N/A')
            accum = project_record.get('Acummulative', 'N/A')
            print(f"  Proyecto {proj_no}: Projected={projected}, Actual={actual}, Acummulative={accum}")
            
            # Contar proyectos con datos de forecast
            if projected != 'N/A' and projected != 0 and projected is not None:
                forecast_projects_found += 1
        
        print(f"  Proyectos con datos de forecast encontrados en datos generados: {forecast_projects_found}/{len(generated_project_data) if generated_project_data else 0}")
        
        return generated_project_data
            
    except Exception as e:
        print(f"❌ Error en run_complete_process: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_project_in_excel():
    """Función para verificar qué proyectos están en el Excel"""
    print(f"\n=== VERIFICANDO PROYECTOS EN EXCEL =====")
    
    try:
        project_log_path = r"\\192.168.39.20\Confidential\12 Invoicing\Contracted Projects\00_Project Log\2025 Projects Log.xlsx"
        
        
        df_sheet = pd.read_excel(project_log_path, sheet_name='5_Invoice-2025')
        
        # Filtrar enero 2025
        df_month = df_sheet[pd.to_numeric(df_sheet['Month'], errors='coerce') == 1]
        
        print(f"Proyectos encontrados en enero 2025:")
        projects = df_month['Project No'].dropna().unique()
        for i, proj in enumerate(projects[:10]):
            row = df_month[df_month['Project No'] == proj].iloc[0]
            print(f"  {i+1}. Proyecto {proj}: Projected={row.get('Projected', 'N/A')}, Actual={row.get('Actual', 'N/A')}")
            
        return projects
            
    except Exception as e:
        print(f"  Error verificando Excel: {e}")
        return []

if __name__ == "__main__":
    print("=== SCRIPT DE GENERACIÓN COMPLETA DE DATOS ===")
    print("Este script ejecuta todo el pipeline de datos y verifica los resultados")
    print()
    
    # Primero verificar qué proyectos están en Excel
    excel_projects = test_project_in_excel()
    
    print("\n" + "="*60)
    
    # Ejecutar el proceso completo
    project_details_output = run_complete_process()
    
    # DEBUG: Print Projected and Actual for May 2025 from the output
    if project_details_output:
        print("\n=== DEBUG: Checking 'Projected' and 'Actual' from project_details_output (May 2025) ===")
        total_projected_debug = 0
        total_actual_debug = 0
        may_projects_found = 0
        
        # Assuming selected_date in run_complete_process was for May 2025
        # The output itself doesn't contain month, but it's generated for a specific month
        # So we just sum what we get if it was run for May.
        
        for record in project_details_output:
            proj_no = record.get('Project No', 'Unknown')
            projected = record.get('Projected', 0) # Default to 0 if missing, as per logic
            actual = record.get('Actual', 0)       # Default to 0 if missing
            
            print(f"  Project: {proj_no}, Projected: {projected}, Actual: {actual}")
            
            if isinstance(projected, (int, float)):
                total_projected_debug += projected
            if isinstance(actual, (int, float)):
                total_actual_debug += actual
            may_projects_found +=1

        if may_projects_found > 0:
            print(f"  --------------------------------------------------")
            print(f"  TOTALS from DEBUG: Projected = ${total_projected_debug:,.2f}, Actual = ${total_actual_debug:,.2f}")
            print(f"  (Based on {may_projects_found} projects returned by run_complete_process for the selected month)")
        else:
            print("  No project records found in project_details_output to debug.")
    else:
        print("\n=== DEBUG: project_details_output is empty or None. ===")
    
    print("\n=== FIN DEL SCRIPT =====")