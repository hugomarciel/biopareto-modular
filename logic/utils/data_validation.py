# logic/utils/data_validation.py

def validate_json_structure(data):
    """
    Valida la estructura mínima del JSON de frente de Pareto.
    Retorna (True/False, mensaje).
    """
    if not isinstance(data, list) or len(data) == 0:
        return False, "File must contain a list of solutions"
    
    first_solution = data[0]
    
    # Check for required fields
    if 'selected_genes' not in first_solution:
        return False, "All solutions must have 'selected_genes' field"
    
    # Check for at least one numeric objective
    has_numeric = any(
        isinstance(value, (int, float)) 
        for key, value in first_solution.items() 
        if key not in ['selected_genes', 'solution_id']
    )
    
    if not has_numeric:
        return False, "No numeric objectives found"
    
    return True, "Valid"


def validate_objectives_match(new_objectives, main_objectives):
    """
    Valida que los objetivos de un nuevo frente coincidan con los objetivos principales.
    """
    # Se compara el set de objetivos para ignorar el orden
    return set(new_objectives) == set(main_objectives)