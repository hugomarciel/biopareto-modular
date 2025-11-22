# logic/utils/data_processing.py

import dash_bootstrap_components as dbc
import json
import base64
import os  # <--- 1. Import necesario añadido para limpiar extensiones
from datetime import datetime
from logic.utils.data_validation import validate_json_structure, validate_objectives_match

def validate_and_process_fronts(contents_list, filename_list, current_data):
    """
    Procesa los archivos JSON subidos, valida, extrae objetivos y crea los objetos de frente.
    Asigna el nombre del archivo como nombre del frente.
    Retorna (updated_data, status_children, main_objectives).
    """
    updated_data = current_data.copy()

    new_fronts_count = 0
    errors = []

    # Inicializar estructuras si no existen
    if 'fronts' not in updated_data: updated_data['fronts'] = []
    if 'fronts_history' not in updated_data: updated_data['fronts_history'] = []
    if 'main_objectives' not in updated_data: updated_data['main_objectives'] = None
    if 'explicit_objectives' not in updated_data: updated_data['explicit_objectives'] = []
    
    # Asegurar que sean listas para iterar, incluso si es un solo archivo
    if not isinstance(contents_list, list): contents_list = [contents_list]
    if not isinstance(filename_list, list): filename_list = [filename_list]

    # Procesar cada archivo subido (zip une contenido con su nombre)
    for contents, filename in zip(contents_list, filename_list):
        if not filename.endswith('.json'):
            errors.append(f"{filename}: Only JSON files accepted")
            continue

        data = None
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            data = json.loads(decoded.decode('utf-8'))
        except Exception as e:
            errors.append(f"{filename}: Error reading/decoding file - {str(e)}")
            continue

        # 1. Validación de estructura (usando tu utilidad existente)
        is_valid, msg = validate_json_structure(data)
        if not is_valid:
            errors.append(f"{filename}: {msg}")
            continue

        # 2. Extracción y procesamiento de objetivos
        objectives = []
        explicit_objectives = []
        
        # Aseguramos que data no esté vacío antes de acceder a data[0]
        if not data:
            errors.append(f"{filename}: The file is empty.")
            continue
            
        first_solution = data[0]

        for key, value in first_solution.items():
            if key not in ['selected_genes', 'solution_id'] and isinstance(value, (int, float)):
                objectives.append(key)
                explicit_objectives.append(key)
        
        # Procesar soluciones y añadir 'num_genes' si es necesario
        for i, solution in enumerate(data):
            if 'solution_id' not in solution:
                solution['solution_id'] = f"Sol_{i+1}"

            if 'num_genes' not in solution and 'selected_genes' in solution:
                solution['num_genes'] = len(solution['selected_genes'])
        
        # Asegurarse de que 'num_genes' esté en la lista de objetivos si se generó
        if any('num_genes' in s for s in data) and 'num_genes' not in objectives:
            objectives.append('num_genes')

        # 3. Validación de consistencia de objetivos (usando tu utilidad existente)
        if updated_data["main_objectives"] is None or not updated_data["fronts"]: 
            updated_data["main_objectives"] = objectives
            updated_data["explicit_objectives"] = explicit_objectives
            for front in updated_data["fronts"]:
                front['is_main'] = False
        else:
            if not validate_objectives_match(objectives, updated_data["main_objectives"]):
                errors.append(f"{filename}: Objectives mismatch. Expected {updated_data['main_objectives']}, got {objectives}")
                continue

        # 4. Agregar nuevo frente con NOMBRE DEL ARCHIVO
        front_number = len(updated_data["fronts"]) + 1
        
        # --- LÓGICA MODIFICADA AQUÍ ---
        # Extrae el nombre base sin extensión (ej: 'experimento_1.json' -> 'experimento_1')
        front_name = os.path.splitext(filename)[0]
        # ------------------------------
        
        new_front = {
            "id": f"front_{front_number}_{datetime.now().strftime('%H%M%S')}", # ID interno único sigue usando timestamp
            "name": front_name, # Nombre visible asignado desde el archivo
            "data": data,
            "objectives": objectives,
            "visible": True,
            "is_main": len(updated_data["fronts"]) == 0 
        }
        
        if len(updated_data["fronts"]) == 0:
            new_front['is_main'] = True

        updated_data["fronts"].append(new_front)
        new_fronts_count += 1

    # 5. Generar mensaje de estado y retornar
    if new_fronts_count > 0:
        success_msg = f"Successfully loaded {new_fronts_count} front(s). Total fronts: {len(updated_data['fronts'])}"
        if errors:
            success_msg += f" | Errors: {'; '.join(errors)}"
        
        return updated_data, dbc.Alert(success_msg, color="success", dismissable=True), updated_data["main_objectives"]
    else:
        error_msg = "Failed to load any fronts. " + "; ".join(errors)
        return updated_data, dbc.Alert(error_msg, color="danger", dismissable=True), updated_data.get("main_objectives")