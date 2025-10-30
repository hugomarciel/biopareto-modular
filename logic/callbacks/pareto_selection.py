# logic/callbacks/pareto_selection.py

import dash
from dash import Output, Input, State, ALL, callback_context
from dash.exceptions import PreventUpdate
import pandas as pd
from collections import defaultdict
import json


def register_pareto_selection_callbacks(app):
    
    # 1. Callback de selección de soluciones (click, lasso/box, remoción)
    @app.callback(
        [Output('selected-solutions-store', 'data'),
         Output('pareto-layout-store', 'data', allow_duplicate=True)], 
        [Input('pareto-plot', 'selectedData'),
         Input('pareto-plot', 'clickData'),
         Input('clear-selection-btn', 'n_clicks'),
         Input({'type': 'remove-solution-btn', 'index': ALL}, 'n_clicks')],
        [State('selected-solutions-store', 'data'),
         State('data-store', 'data'),
         State({'type': 'remove-solution-btn', 'index': ALL}, 'id'),
         State('x-axis-dropdown', 'value'),
         State('y-axis-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_selected_solutions(selected_data, click_data, clear_clicks, remove_clicks,
                                  current_selection, data_store, remove_btn_ids, x_axis, y_axis):
        """Handle solution selection from lasso/box select, individual clicks, and remove buttons"""

        ctx = dash.callback_context
        if not ctx.triggered:
            return current_selection or [], dash.no_update

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # A. Clear selection
        if trigger_id == 'clear-selection-btn':
            return [], {} 

        # B. Handle individual remove button click
        if 'remove-solution-btn' in trigger_id:
            if remove_clicks and any(click is not None and click > 0 for click in remove_clicks):
                try:
                    triggered_id_dict = ctx.triggered_id
                    if triggered_id_dict and 'index' in triggered_id_dict:
                        triggered_index = triggered_id_dict['index']
                        return [s for s in current_selection if s['unique_id'] != triggered_index], dash.no_update
                    else:
                        return current_selection, dash.no_update
                except Exception:
                    return current_selection, dash.no_update
            else:
                return current_selection, dash.no_update

        # C. Lógica de Adición/Selección de Soluciones
        all_solutions_for_lookup = {}
        fronts = data_store.get("fronts", []) if data_store else []
        
        coord_to_solutions = defaultdict(list)
        
        for front in fronts:
            df = pd.DataFrame(front["data"])
            if x_axis not in df.columns or y_axis not in df.columns:
                continue
                
            df['x_coord'] = df[x_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
            df['y_coord'] = df[y_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
            
            for index, row in df.iterrows():
                coord = (row['x_coord'], row['y_coord'])
                unique_id = f"{row['solution_id']}|{front['name']}"
                
                sol_data = row.to_dict()
                sol_data['front_name'] = front['name']
                sol_data['unique_id'] = unique_id
                sol_data['x'] = row[x_axis]
                sol_data['y'] = row[y_axis]
                sol_data['objectives'] = front.get('objectives', [])
                all_solutions_for_lookup[unique_id] = sol_data
                
                coord_to_solutions[coord].append(sol_data)

        def process_point(point, selection_type):
            x_val = point['x']
            y_val = point['y']
            
            coord = (round(x_val, 3) if isinstance(x_val, float) else x_val,
                     round(y_val, 3) if isinstance(y_val, float) else y_val)

            solutions_at_coord = coord_to_solutions.get(coord, [])
            solutions_to_add_remove = []

            if selection_type == 'click':
                if not solutions_at_coord:
                    sol_id = point.get('customdata', [None])[0]
                    front_name = point.get('customdata', [None, None])[1]
                    unique_id = f"{sol_id}|{front_name}"
                    if unique_id in all_solutions_for_lookup:
                         solutions_at_coord.append(all_solutions_for_lookup[unique_id])
                    else:
                        return []

                all_selected = all(s['unique_id'] in [cs['unique_id'] for cs in current_selection] for s in solutions_at_coord)
                
                if all_selected:
                    current_ids = set([cs['unique_id'] for cs in current_selection])
                    coord_ids = set([sas['unique_id'] for sas in solutions_at_coord])
                    return [s for s in current_selection if s['unique_id'] not in coord_ids]

                else:
                    existing_unique_ids = [s['unique_id'] for s in current_selection]
                    solutions_to_add_remove.extend(
                        [s for s in solutions_at_coord if s['unique_id'] not in existing_unique_ids]
                    )
                    
            elif selection_type == 'select':
                existing_unique_ids = [s['unique_id'] for s in current_selection]

                for sol in solutions_at_coord:
                    if sol['unique_id'] not in existing_unique_ids:
                        solutions_to_add_remove.append(sol)
            
            # Mapeamos la estructura de los diccionarios de soluciones completas a la estructura simplificada de selected_solutions_store
            simplified_results = [{
                'id': s['solution_id'],
                'front_name': s['front_name'],
                'unique_id': s['unique_id'],
                'x': s['x'], 
                'y': s['y'],
                'objectives': s['objectives'],
                'full_data': s
            } for s in solutions_to_add_remove]
            
            return simplified_results


        # Procesar datos seleccionados (lasso/box)
        if trigger_id == 'pareto-plot' and ctx.triggered[0]['prop_id'].endswith('selectedData'):
            if selected_data and 'points' in selected_data:
                new_selections_to_add = []
                
                for point in selected_data['points']:
                    new_solutions = process_point(point, 'select')
                    # Ya que process_point ahora retorna la data simplificada, la usamos directamente
                    new_selections_to_add.extend(new_solutions)
                
                existing_ids = {s['unique_id'] for s in current_selection}
                filtered_new = [s for s in new_selections_to_add if s['unique_id'] not in existing_ids]

                return current_selection + filtered_new, dash.no_update

        # Procesar dato clicado (individual click)
        if trigger_id == 'pareto-plot' and ctx.triggered[0]['prop_id'].endswith('clickData'):
            if click_data and 'points' in click_data:
                point = click_data['points'][0]
                
                # Para un click, process_point devuelve la lista final (toggle)
                final_selection_list = process_point(point, 'click') 
                
                return final_selection_list, dash.no_update

        return current_selection, dash.no_update

    # 2. Callback para habilitar/deshabilitar botones de acción
    @app.callback(
        [Output('add-to-interest-btn', 'disabled'),
         Output('consolidate-selection-btn', 'disabled')],
        Input('selected-solutions-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_buttons_on_selection(selected_solutions):
        """Enable/disable Add All and Consolidate buttons based on selection"""
        is_disabled = not (selected_solutions and len(selected_solutions) > 0)
        return is_disabled, is_disabled
        
    # 3. Callback auxiliar para limpiar selección al cargar nueva data
    @app.callback(
        Output('selected-solutions-store', 'data', allow_duplicate=True),
        Input('data-store', 'data'),
        State('selected-solutions-store', 'data'),
        prevent_initial_call=True
    )
    def clear_selected_on_new_data(data_store, current_selection):
        """Clear selected solutions when data is reset (full clear, consolidation, or restore)"""
        # La lógica de clear_selected_on_new_data está en consolidation.py para evitar duplicidad de triggers.
        # Este callback actúa como fallback de limpieza si el data-store se vacía.
        
        if data_store is None or not data_store.get('fronts'):
            return []
        
        # Dejamos la lógica de limpieza de Consolidation/Restore en el archivo consolidation.py
        
        return current_selection
    
    