# debug_project_record.py
def debug_project_assignment():
    """Debug para ver cómo se asignan los valores de forecast"""
    from data_processing import main, generate_monthly_report_data
    from datetime import datetime
    
    # Interceptar la función para ver qué está pasando
    # Vamos a revisar el código que asigna los valores
    
    print("Revisando la asignación de valores de forecast...")
    
    # Encontrar dónde está el problema en la asignación
    # El problema probablemente está en las líneas 745-755 de data_processing.py