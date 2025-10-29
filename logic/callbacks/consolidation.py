# logic/callbacks/consolidation.py

import dash
from dash import Output, Input, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import datetime
import pandas as pd


def register_consolidation_callbacks(app):
    
    # 1. Callback para abrir/cerrar modal de confirmación de consolidación
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

        # Cierre del modal (Cancel o Confirm)
        if trigger_id in ['consolidate-cancel-btn', 'consolidate-confirm-btn']:
            return False, dash.no_update, dash.no_update

        # Apertura del modal
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

    # 2. Callback para realizar la consolidación
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('selected-solutions-store', 'data', allow_duplicate=True)], # Limpiar selección
        Input('consolidate-confirm-btn', 'n_clicks'),
        [State('data-store', 'data'),
         State('selected-solutions-store', 'data'),
         State('consolidate-front-name-input', 'value'),
         State('x-axis-dropdown', 'value'),
         State('y-axis-dropdown', 'value')],
        prevent_initial_call=True
    )
    def perform_consolidation(n_clicks, current_data, selected_solutions, new_front_name, current_x_axis, current_y_axis):
        """Performs the consolidation of selected solutions into a new Pareto front."""
        if not n_clicks or not selected_solutions or not current_data:
            raise PreventUpdate
            
        updated_data = current_data.copy()
        
        if not selected_solutions:
            raise PreventUpdate

        # 1. Determinar objetivos (Deben ser los del frente principal)
        objectives = updated_data.get('main_objectives')

        # 2. Preparar los datos del nuevo frente
        new_front_data = [sol['full_data'].copy() for sol in selected_solutions]
        
        # 3. Ordenar las soluciones
        if objectives:
            sort_keys = []
            if current_x_axis in objectives:
                sort_keys.append(current_x_axis)
            if current_y_axis in objectives:
                sort_keys.append(current_y_axis)
            
            if not sort_keys:
                 explicit_objectives = [obj for obj in objectives if obj not in ['num_genes']]
                 if len(explicit_objectives) >= 2:
                     sort_keys = [explicit_objectives[0], explicit_objectives[1]]
                 elif len(objectives) >= 2:
                     sort_keys = [objectives[0], objectives[1]]
                 elif objectives:
                     sort_keys = [objectives[0]]
                
            if sort_keys:
                # Ordenamiento lambda para asegurar que el frente se dibuje correctamente
                new_front_data.sort(key=lambda sol: [sol.get(k, 0) for k in sort_keys])

        # 4. Renumerar las soluciones
        final_front_name = new_front_name if new_front_name else f"Consolidated_Front_{datetime.now().strftime('%H%M')}"
        
        for i, sol in enumerate(new_front_data):
            sol['solution_id'] = f"Sol_{i+1}"
            sol['front_name'] = final_front_name

        # 5. Crear el nuevo objeto frente
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
        
        # 6. Deshabilitar is_main en los frentes actuales y guardar el estado en el historial
        for front in updated_data.get('fronts', []):
            front['is_main'] = False
            
        updated_data.setdefault('fronts_history', []).append(updated_data['fronts'])

        # 7. Reemplazar los frentes existentes con solo el nuevo frente consolidado
        updated_data['fronts'] = [new_front]
        
        # 8. Limpiar la selección actual
        new_selection = []
        
        return updated_data, new_selection

    # 3. Callback para habilitar/deshabilitar el botón de restauración
    @app.callback(
        Output('restore-original-btn', 'disabled'),
        [Input('data-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=False
    )
    def toggle_restore_button(data_store, active_tab):
        """Enable/disable Restore Original button based on history size"""
        if not data_store:
            return True
        
        return not (data_store.get('fronts_history') and len(data_store['fronts_history']) > 0)

    # 4. Callback para restaurar el estado anterior
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('selected-solutions-store', 'data', allow_duplicate=True),
         Output('pareto-layout-store', 'data', allow_duplicate=True)],
        Input('restore-original-btn', 'n_clicks'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def restore_original_fronts(n_clicks, current_data):
        """Restores the previous state of the Pareto fronts from history."""
        if not n_clicks or not current_data or not current_data.get('fronts_history'):
            raise PreventUpdate
            
        updated_data = current_data.copy()

        # 1. Obtener el estado anterior (el último en el historial)
        previous_fronts = updated_data['fronts_history'].pop()
        
        # 2. Restaurar el estado de los frentes
        updated_data['fronts'] = previous_fronts
        
        # 3. Determinar los objetivos principales del estado restaurado
        main_objectives = None
        if previous_fronts:
            main_front = next((f for f in previous_fronts if f.get('is_main')), None)
            if main_front:
                main_objectives = main_front['objectives']
            else:
                previous_fronts[0]['is_main'] = True 
                main_objectives = previous_fronts[0]['objectives']

        updated_data['main_objectives'] = main_objectives
        
        # 4. Limpiar selección y layout (zoom/pan)
        return updated_data, [], {}