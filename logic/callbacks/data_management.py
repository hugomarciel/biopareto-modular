# logic/callbacks/data_management.py
# Modulo optimizado: Corrección de estilo de tarjetas y bug de recarga tras limpiar.

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
import pathlib

# Importar la lógica de procesamiento
from logic.utils.data_processing import validate_and_process_fronts 


def register_data_management_callbacks(app):
    
    # 1. Callback principal de carga y borrado (CORREGIDO: Resetea el Uploader)
    @app.callback(
        [Output('data-store', 'data'),
         Output('upload-status', 'children'),
         Output('objectives-store', 'data'),
         Output('upload-data', 'contents')], # <--- 💡 NUEVO OUTPUT PARA RESETEAR EL UPLOADER
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
            # Reseteamos data, status, objetivos y EL UPLOADER (None)
            empty_store = {'fronts': [], 'fronts_history': [], 'main_objectives': None, 'explicit_objectives': []}
            success_msg = dbc.Alert("All data cleared successfully", color="info", dismissable=True)
            return empty_store, success_msg, None, None 

        # Load new front(s)
        elif trigger_id == 'upload-data' and contents_list:
            # Procesamos los datos
            new_data_store, msg, new_objectives = validate_and_process_fronts(contents_list, filename_list, updated_data)
            
            # Retornamos los datos procesados y RESETEAMOS el uploader a None 
            # para permitir volver a cargar el mismo archivo si fuera necesario
            return new_data_store, msg, new_objectives, None

        raise PreventUpdate

    # 2. Callback visual de lista de frentes (ESTILO CORREGIDO: Gris sutil)
    @app.callback(
        Output('fronts-list', 'children'),
        Input('data-store', 'data'),
        Input('main-tabs', 'active_tab')
    )
    def update_fronts_list(current_data, active_tab):
        """Update the display of loaded fronts. Removed 'Main Front' checkbox logic."""
        if active_tab != 'upload-tab':
            raise PreventUpdate

        if not current_data or not current_data.get('fronts'):
            return dbc.Alert("No fronts loaded yet. Upload files to see them here.", color="light", className="text-center small text-muted border-0")

        explicit_objectives = current_data.get('explicit_objectives', [])
        objectives_str = ', '.join(explicit_objectives) if explicit_objectives else "Auto-detected"

        fronts_items = []
        for front in current_data['fronts']:
            
            # --- 💡 CAMBIO DE ESTILO: Usar 'border-secondary' (Gris) en lugar de 'primary' ---
            card_border = "border-secondary" if not front.get('is_consolidated') else "border-info"
            icon_class = "bi-file-earmark-bar-graph" if not front.get('is_consolidated') else "bi-layers-fill"
            
            front_card = dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        # Columna Nombre
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText(html.I(className=icon_class)),
                                dbc.Input(
                                    id={'type': 'front-name-input', 'index': front['id']},
                                    value=front['name'],
                                    placeholder="Enter front name",
                                    disabled=front.get('is_consolidated', False)
                                )
                            ], size="sm")
                        ], width=10), 
                        
                        # Columna Eliminar
                        dbc.Col([
                            dbc.Button(
                                html.I(className="bi bi-x-lg"),
                                id={'type': 'delete-front-btn', 'index': front['id']},
                                color="outline-danger",
                                size="sm",
                                className="w-100",
                                title="Remove Front",
                                disabled=front.get('is_consolidated', False)
                            )
                        ], width=2)
                    ], align="center"),
                    
                    html.Div([
                        html.Span(f"Solutions: {len(front['data'])}", className="badge bg-light text-dark border me-2"),
                        html.Span(f"Objectives: {objectives_str}", className="badge bg-light text-dark border me-2"),
                        html.Span("CONSOLIDATED", className="badge bg-info text-white") if front.get('is_consolidated') else None
                    ], className="mt-2 small")
                ])
            ], className=f"mb-2 shadow-sm border-start border-3 {card_border}")
            
            fronts_items.append(front_card)

        return fronts_items

    # 3. Callback nombres (SIN CAMBIOS)
    @app.callback(
        Output('data-store', 'data', allow_duplicate=True),
        Input({'type': 'front-name-input', 'index': ALL}, 'value'),
        State({'type': 'front-name-input', 'index': ALL}, 'id'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def update_front_names(names, ids, current_data):
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

    # 4. Callback Eliminar Frente (SIN CAMBIOS)
    @app.callback(
        [Output('data-store', 'data', allow_duplicate=True),
         Output('objectives-store', 'data', allow_duplicate=True)],
        Input({'type': 'delete-front-btn', 'index': ALL}, 'n_clicks'),
        State({'type': 'delete-front-btn', 'index': ALL}, 'id'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def delete_front(n_clicks, ids, current_data):
        """Deletes a front."""
        if not current_data or not any(n_clicks):
            return dash.no_update, dash.no_update

        updated_data = current_data.copy()
        ctx = dash.callback_context
        
        triggered_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            triggered_id_dict = json.loads(re.search(r'\{.*\}', triggered_id_str).group(0))
            front_id_to_delete = triggered_id_dict['index']
        except (json.JSONDecodeError, AttributeError):
            return dash.no_update, dash.no_update

        updated_data['fronts'] = [f for f in updated_data['fronts'] if f['id'] != front_id_to_delete]

        if not updated_data['fronts']:
             updated_data['explicit_objectives'] = []
             updated_data['main_objectives'] = None 

        return updated_data, None

    # 5. Descargar Test (SIN CAMBIOS)
    @app.callback(
        Output('download-test-file', 'data'),
        Input('download-test-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def download_test_file(n_clicks):
        if not n_clicks: return None
        filename = "json V2.1.rar" 
        root_dir = pathlib.Path(__file__).parent.parent.parent
        file_path = root_dir / "assets" / filename
        try:
            return dict(content=base64.b64encode(file_path.read_bytes()).decode('utf-8'), filename=filename, base64=True)
        except Exception:
            return dash.no_update

    # 6. Toggle Format Info (SIN CAMBIOS)
    @app.callback(
        Output("format-info-collapse", "is_open"),
        Input("toggle-format-info", "n_clicks"),
        State("format-info-collapse", "is_open")
    )
    def toggle_format_info(n_clicks, is_open):
        if n_clicks: return not is_open
        return is_open