# logic/callbacks/consolidation.py

import dash
from dash import Output, Input, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def register_consolidation_callbacks(app):
    
    # 1. Callback para abrir/cerrar modal de confirmación
    @app.callback(
        [Output('consolidate-modal', 'is_open'),
         Output('consolidate-modal-info', 'children'),
         Output('consolidate-front-name-input', 'value')],
        [Input('consolidate-selection-btn', 'n_clicks'),
         Input('consolidate-cancel-btn', 'n_clicks'),
         Input('consolidate-confirm-btn', 'n_clicks')],
        [State('selected-solutions-store', 'data'),
         State('consolidate-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_consolidate_modal(consolidate_clicks, cancel_clicks, confirm_clicks, selected_solutions, is_open):
        """Toggle consolidation modal and populate initial data"""
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if trigger_id in ['consolidate-cancel-btn', 'consolidate-confirm-btn']:
            return False, dash.no_update, dash.no_update

        if trigger_id == 'consolidate-selection-btn' and consolidate_clicks:
            if not selected_solutions:
                raise PreventUpdate
                
            num_solutions = len(selected_solutions)
            front_names = set(sol['front_name'] for sol in selected_solutions)
            
            info = html.Div([
                html.P(f"You have selected {num_solutions} solution(s)."),
                html.P(f"These solutions come from the following front(s): {', '.join(front_names)}."),
                html.P("Confirm to create a new consolidated Pareto front with these solutions.")
            ])
            
            timestamp = datetime.now().strftime("%H%M")
            default_name = f"Consolidated_Front_{timestamp}"

            return True, info, default_name

        raise PreventUpdate

    # 2. Callback para realizar la consolidación (LÓGICA ROBUSTA / VISUAL INJECTION)
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('selected-solutions-store', 'data', allow_duplicate=True)], 
        Input('consolidate-confirm-btn', 'n_clicks'),
        [State('data-store', 'data'),
         State('selected-solutions-store', 'data'),
         State('consolidate-front-name-input', 'value'),
         State('x-axis-store', 'data'), 
         State('y-axis-store', 'data')], 
        prevent_initial_call=True
    )
    def perform_consolidation(n_clicks, current_data, selected_solutions, new_front_name, current_x_axis, current_y_axis):
        """Performs the consolidation of selected solutions into a new Pareto front."""
        if not n_clicks or not selected_solutions or not current_data:
            raise PreventUpdate
            
        updated_data = current_data.copy()
        
        # 1. Determinar nombres de ejes
        objectives = updated_data.get('main_objectives')
        
        # Intentar obtener los ejes del store visual primero, si no, de los metadatos
        if not current_x_axis or not current_y_axis:
            if objectives and len(objectives) >= 2:
                current_x_axis = objectives[0]
                current_y_axis = objectives[1]
            else:
                 explicit = updated_data.get('explicit_objectives', [])
                 if explicit and len(explicit) >= 2:
                     current_x_axis = explicit[0]
                     current_y_axis = explicit[1]

        # 2. Preparar datos del nuevo frente
        new_front_data = []
        
        for sol in selected_solutions:
            # Copia de los datos originales completos
            original_data = sol['full_data'].copy()
            
            # --- LÓGICA CRÍTICA: INYECCIÓN VISUAL ---
            # Tomamos lo que el usuario VEÍA en pantalla (x, y) y lo forzamos 
            # dentro del diccionario de datos con la etiqueta que el gráfico espera.
            # Esto arregla el problema de que "1-Auc" no coincida con "1_Auc".
            
            visual_x = sol.get('x')
            visual_y = sol.get('y')
            
            if current_x_axis and visual_x is not None:
                original_data[current_x_axis] = visual_x
                
            if current_y_axis and visual_y is not None:
                original_data[current_y_axis] = visual_y
            
            new_front_data.append(original_data)
        
        # 3. Ordenar (Ahora es seguro porque inyectamos las claves)
        if current_x_axis and current_y_axis:
            try:
                new_front_data.sort(key=lambda s: (s.get(current_x_axis, 0), s.get(current_y_axis, 0)))
            except TypeError:
                pass 
        
        # 4. Renumerar y nombrar
        final_front_name = new_front_name if new_front_name else f"Consolidated_Front_{datetime.now().strftime('%H%M')}"
        
        for i, sol in enumerate(new_front_data):
            # Guardamos el ID original por si acaso, pero generamos uno limpio para el gráfico
            sol['original_solution_id'] = sol.get('solution_id')
            sol['solution_id'] = f"Sol_{i+1}"
            sol['front_name'] = final_front_name

        # 5. Crear objeto frente
        new_front_id = f"consolidated_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        new_front = {
            "id": new_front_id,
            "name": final_front_name,
            "data": new_front_data,
            "objectives": objectives, 
            "visible": True,
            "is_main": True,
            "is_consolidated": True
        }
        
        # 6. Guardar historial para poder restaurar después
        import copy
        current_fronts_snapshot = copy.deepcopy(updated_data.get('fronts', []))
        updated_data.setdefault('fronts_history', []).append(current_fronts_snapshot)

        # 7. Reemplazar frentes actuales con el consolidado
        updated_data['fronts'] = [new_front]
        
        # Limpiar selección al finalizar
        return updated_data, []

    # 3. Callback para habilitar botón Restore
    @app.callback(
        Output('restore-original-btn', 'disabled'),
        [Input('data-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=False
    )
    def toggle_restore_button(data_store, active_tab):
        if not data_store: return True
        return not (data_store.get('fronts_history') and len(data_store['fronts_history']) > 0)

    # 4. Callback para ejecutar Restore
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('selected-solutions-store', 'data', allow_duplicate=True),
         Output('pareto-layout-store', 'data', allow_duplicate=True)],
        Input('restore-original-btn', 'n_clicks'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def restore_original_fronts(n_clicks, current_data):
        if not n_clicks or not current_data or not current_data.get('fronts_history'):
            raise PreventUpdate
        
        updated_data = current_data.copy()
        
        # Sacar el último estado del historial (stack pop)
        previous_fronts = updated_data['fronts_history'].pop()
        updated_data['fronts'] = previous_fronts
        
        # Restaurar objetivos principales
        main_objectives = None
        if previous_fronts:
            main_front = next((f for f in previous_fronts if f.get('is_main')), None)
            if main_front: 
                main_objectives = main_front['objectives']
            else: 
                main_objectives = previous_fronts[0].get('objectives')

        updated_data['main_objectives'] = main_objectives
        
        return updated_data, [], {}