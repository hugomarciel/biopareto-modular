# logic/callbacks/data_management.py
# Este archivo contiene los callbacks de carga, limpieza, renombrado y eliminación de frentes.

import dash
from dash import Output, Input, State, callback_context, dcc, html, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import json
import base64
import re
from datetime import datetime
import pandas as pd
import io

# Importar la lógica de procesamiento (requiere que logic/utils/data_processing.py exista)
from logic.utils.data_processing import validate_and_process_fronts 


def register_data_management_callbacks(app):
    
    # 1. Callback principal para manejo de carga y borrado (SIN CAMBIOS)
    @app.callback(
        [Output('data-store', 'data'),
         Output('upload-status', 'children'),
         Output('objectives-store', 'data')],
        [Input('upload-data', 'contents'),
         Input('upload-data', 'filename'),
         Input('clear-data-btn', 'n_clicks')],
        [State('data-store', 'data')]
    )
    def handle_data_operations(contents_list, filename_list, clear_clicks, current_data):
        """Handle loading multiple Pareto fronts and clear operation."""
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        updated_data = current_data.copy() if current_data else {}

        # Clear all data
        if trigger_id == 'clear-data-btn' and clear_clicks:
            return {'fronts': [], 'fronts_history': [], 'main_objectives': None, 'explicit_objectives': []}, \
                   dbc.Alert("All data cleared successfully", color="info", dismissable=True), None

        # Load new front(s) (utiliza la función de procesamiento)
        elif trigger_id == 'upload-data' and contents_list:
            return validate_and_process_fronts(contents_list, filename_list, updated_data)

        raise PreventUpdate

    # 2. Callback para el despliegue visual de los frentes cargados (MODIFICADO)
    @app.callback(
        Output('fronts-list', 'children'),
        Input('data-store', 'data'),
        Input('main-tabs', 'active_tab')
    )
    def update_fronts_list(current_data, active_tab):
        """Update the display of loaded fronts, including edit and delete buttons."""
        if active_tab != 'upload-tab':
            raise PreventUpdate

        if not current_data or not current_data.get('fronts'):
            return html.P("No fronts loaded yet.", className="text-muted")

        # --- INICIO DE LA MODIFICACIÓN ---
        # Obtener los 2 objetivos explícitos del data-store principal.
        # Esta lista (ej: ['auc', 'accuracy']) será usada para el display.
        explicit_objectives = current_data.get('explicit_objectives', [])
        objectives_str = ', '.join(explicit_objectives)
        # --- FIN DE LA MODIFICACIÓN ---

        fronts_items = []
        for front in current_data['fronts']:
            front_card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("Name:"),
                                dbc.Input(
                                    id={'type': 'front-name-input', 'index': front['id']},
                                    value=front['name'],
                                    placeholder="Enter front name",
                                    disabled=front.get('is_consolidated', False)
                                )
                            ])
                        ], width=6),
                        dbc.Col([
                            dbc.Checkbox(
                                id={'type': 'main-front-checkbox', 'index': front['id']},
                                label="Main Front (defines objectives)",
                                value=front.get('is_main', False),
                                className="mt-2"
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Button(
                                "✕ Remove",
                                id={'type': 'delete-front-btn', 'index': front['id']},
                                color="secondary",
                                outline=True,
                                size="sm",
                                className="mt-1",
                                disabled=front.get('is_consolidated', False)
                            )
                        ], width=2)
                    ]),
                    html.Small(
                        # --- MODIFICACIÓN: Usar objectives_str en lugar de front['objectives'] ---
                        f"Solutions: {len(front['data'])} | Objectives: {objectives_str}" +
                        (f" | (CONSOLIDATED)" if front.get('is_consolidated') else ""),
                        className="text-muted mt-2 d-block"
                    )
                ])
            ], className="mb-2")
            fronts_items.append(front_card)

        return fronts_items

    # 3. Callback para actualizar los nombres de los frentes (Input dinámico) (SIN CAMBIOS)
    @app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input({'type': 'front-name-input', 'index': ALL}, 'value'),
        State({'type': 'front-name-input', 'index': ALL}, 'id'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def update_front_names(names, ids, current_data):
        """Update front names when user edits them in the UI."""
        if not current_data or not names:
            return dash.no_update

        updated_data = current_data.copy()

        for name, id_dict in zip(names, ids):
            front_id = id_dict['index']
            for front in updated_data['fronts']:
                if front['id'] == front_id:
                    front['name'] = name
                    break

        return updated_data

    # 4. Callback para definir el frente principal (SIN CAMBIOS)
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('objectives-store', 'data', allow_duplicate=True)],
        Input({'type': 'main-front-checkbox', 'index': ALL}, 'value'),
        State({'type': 'main-front-checkbox', 'index': ALL}, 'id'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def update_main_front(checked_values, ids, current_data):
        """Update which front is designated as the main front, setting global objectives."""
        if not current_data or not ids:
            return dash.no_update, dash.no_update

        updated_data = current_data.copy()

        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update

        # Extraer el ID del frente clicado
        triggered_prop_id = ctx.triggered[0]['prop_id']
        match = re.search(r'\{.*\}', triggered_prop_id)
        if not match:
            return dash.no_update, dash.no_update

        try:
            triggered_id_dict = json.loads(match.group(0))
            clicked_front_id = triggered_id_dict['index']
        except json.JSONDecodeError:
            return dash.no_update, dash.no_update

        clicked_index = None
        for i, id_dict in enumerate(ids):
            if id_dict['index'] == clicked_front_id:
                clicked_index = i
                break

        if clicked_index is None:
            return dash.no_update, dash.no_update

        new_value = checked_values[clicked_index]

        main_objectives = None
        if new_value:
            for front in updated_data['fronts']:
                if front['id'] == clicked_front_id:
                    front['is_main'] = True
                    main_objectives = front['objectives']
                else:
                    front['is_main'] = False
        else:
            for front in updated_data['fronts']:
                front['is_main'] = False
            if updated_data['fronts']:
                updated_data['fronts'][0]['is_main'] = True
                main_objectives = updated_data['fronts'][0]['objectives']
            else:
                main_objectives = None

        return updated_data, main_objectives

    # 5. Callback para eliminar un frente (SIN CAMBIOS)
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('objectives-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-front-btn', 'index': ALL}, 'n_clicks'),
        State({'type': 'delete-front-btn', 'index': ALL}, 'id'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def delete_front(n_clicks, ids, current_data):
        """Deletes a front and ensures a remaining front is set as main if needed."""
        if not current_data or not any(n_clicks):
            return dash.no_update, dash.no_update

        updated_data = current_data.copy()

        ctx = dash.callback_context
        if not ctx.triggered:
            return dash.no_update, dash.no_update

        # Extraer el ID del frente a eliminar
        triggered_id_str = ctx.triggered[0]['prop_id'].split('.')[0] 
        match = re.search(r'\{.*\}', triggered_id_str)
        if not match:
            return dash.no_update, dash.no_update

        try:
            triggered_id_dict = json.loads(match.group(0))
            front_id_to_delete = triggered_id_dict['index']
        except json.JSONDecodeError:
            return dash.no_update, dash.no_update

        updated_data['fronts'] = [f for f in updated_data['fronts'] if f['id'] != front_id_to_delete]

        main_objectives = None
        if updated_data['fronts']:
            has_main = any(f.get('is_main', False) for f in updated_data['fronts'])
            if not has_main:
                updated_data['fronts'][0]['is_main'] = True
                main_objectives = updated_data['fronts'][0]['objectives']
            else:
                main_objective_front = next(f for f in updated_data['fronts'] if f.get('is_main', False))
                main_objectives = main_objective_front['objectives']
        else:
            main_objectives = None

        return updated_data, main_objectives

    # 6. Callback para descargar archivo de prueba (SIN CAMBIOS)
    @app.callback(
        Output('download-test-file', 'data'),
        Input('download-test-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_test_file(n_clicks):
        """Download a basic test JSON file."""
        if not n_clicks:
            return None

        # Contenido del archivo de prueba
        test_data = [
            {
                "selected_genes": ["BRCA1", "TP53", "EGFR"],
                "accuracy": 0.92,
                "num_genes": 3,
                "solution_id": "Sol_1"
            },
            {
                "selected_genes": ["BRCA1", "TP53", "EGFR", "MYC"],
                "accuracy": 0.94,
                "num_genes": 4,
                "solution_id": "Sol_2"
            }
        ]
        return dict(
            content=json.dumps(test_data, indent=2),
            filename="test.json"
        )

    # 7. Callback para alternar la visibilidad de la información de formato (SIN CAMBIOS)
    @app.callback(
        Output("format-info-collapse", "is_open"),
        Input("toggle-format-info", "n_clicks"),
        State("format-info-collapse", "is_open")
    )
    def toggle_format_info(n_clicks, is_open):
        """Toggle the visibility of the expected file format info."""
        if n_clicks:
            return not is_open
        return is_open