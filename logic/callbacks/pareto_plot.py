# logic/callbacks/pareto_plot.py

import dash
from dash import Output, Input, State, ALL, callback_context, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)

def register_pareto_plot_callbacks(app):

    # 1. Callback para actualizar los STORES de ejes
    @app.callback(
        [Output('x-axis-store', 'data'),
         Output('y-axis-store', 'data')],
        [Input('objectives-store', 'data'),
         Input('data-store', 'data'),
         Input('swap-axes-btn', 'n_clicks')],
        [State('x-axis-store', 'data'),
         State('y-axis-store', 'data')],
        prevent_initial_call=False 
    )
    def update_axis_stores(objectives_from_store, data_store, swap_clicks, current_x_value, current_y_value):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        if not data_store:
            data_store = {} 
        
        objectives = data_store.get('explicit_objectives', [])
        
        if not objectives or len(objectives) < 2:
            raise PreventUpdate

        objectives = objectives[:2]
        default_x = objectives[0]
        default_y = objectives[1]

        if triggered_id == 'swap-axes-btn':
            if current_x_value and current_y_value:
                return current_y_value, current_x_value
            else:
                return default_y, default_x

        if current_x_value in objectives and current_y_value in objectives:
             if triggered_id == 'data-store':
                 raise PreventUpdate
             return current_x_value, current_y_value

        return default_x, default_y

    # 2. Callback principal para generar el gráfico de Pareto
    @app.callback(
        [Output('pareto-plot', 'figure'),
         Output('selected-solutions-info', 'children'),
         Output('pareto-plot-title', 'children')],
        [Input('data-store', 'data'),
         Input('selected-solutions-store', 'data'),
         Input('x-axis-store', 'data'), 
         Input('y-axis-store', 'data'), 
         Input({'type': 'main-front-checkbox', 'index': ALL}, 'value'),
         Input({'type': 'front-name-input', 'index': ALL}, 'value')],
        prevent_initial_call=True
    )
    def update_pareto_plot(data_store, selected_solutions, x_axis_value, y_axis_value, main_front_checkboxes, front_name_inputs):
        """
        Update Pareto plot with FULL EXPLORATION TOOLS enabled (Spikes, Slider, etc).
        """
        if not data_store or not data_store.get("fronts"):
            return {}, "", "Pareto Front"

        visible_fronts = [f for f in data_store.get("fronts", []) if f.get("visible", True)]
        if not visible_fronts:
            return {}, "", "Pareto Front (No visible fronts)"

        # --- 1. Determinar Ejes ---
        explicit_objectives = data_store.get('explicit_objectives', [])
        objectives = data_store.get('main_objectives') or (explicit_objectives if explicit_objectives else (visible_fronts[0]['objectives'] if visible_fronts else []))
        
        x_axis = x_axis_value or (explicit_objectives[0] if explicit_objectives else (objectives[0] if objectives else 'num_genes'))
        y_axis = y_axis_value or (explicit_objectives[1] if len(explicit_objectives) > 1 else (objectives[1] if len(objectives) > 1 else 'accuracy'))

        plot_title = f"Pareto Front:   {x_axis.replace('_', ' ').title()}  vs  {y_axis.replace('_', ' ').title()}"
        ui_revision_key = f"{x_axis}-{y_axis}"

        fig = go.Figure()
        colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        selected_unique_ids = {s['unique_id'] for s in (selected_solutions or [])}

        # --- FUNCIÓN HELPER: Normalización de Columnas ---
        def standardize_df_columns(df, target_x, target_y):
            found_x = False
            found_y = False
            col_map = {c.lower().replace('-', '').replace('_', '').replace(' ', ''): c for c in df.columns}
            
            search_x = target_x.lower().replace('-', '').replace('_', '').replace(' ', '')
            if target_x in df.columns:
                found_x = True
            elif search_x in col_map:
                df[target_x] = df[col_map[search_x]]
                found_x = True
                
            search_y = target_y.lower().replace('-', '').replace('_', '').replace(' ', '')
            if target_y in df.columns:
                found_y = True
            elif search_y in col_map:
                df[target_y] = df[col_map[search_y]]
                found_y = True
                
            return df, found_x, found_y

        # --- 2. Pre-procesar y Agrupar Soluciones ---
        coord_to_solutions = defaultdict(list)
        all_objectives = set(objectives) 

        for idx, front in enumerate(visible_fronts):
            df = pd.DataFrame(front["data"])
            df, has_x, has_y = standardize_df_columns(df, x_axis, y_axis)
            
            if not has_x or not has_y:
                continue
            
            color = colors_palette[idx % len(colors_palette)]
            if front.get('is_consolidated'):
                 color = '#000080'
            
            for _, row in df.iterrows():
                coord = (row[x_axis], row[y_axis])
                unique_id = f"{row['solution_id']}|{front['name']}"
                
                sol_data = row.to_dict()
                sol_data['front_name'] = front['name']
                sol_data['color'] = color
                sol_data['unique_id'] = unique_id
                sol_data['current_x'] = row[x_axis]
                sol_data['current_y'] = row[y_axis]
                
                coord_to_solutions[coord].append(sol_data)
                all_objectives.update(sol_data.keys())

            # --- 3. Dibujar Líneas ---
            df_line = df.drop_duplicates(subset=[x_axis, y_axis], keep='first') 
            df_sorted = df_line.sort_values(by=[x_axis, y_axis], ascending=True)
            
            fig.add_trace(go.Scatter(
                x=df_sorted[x_axis],
                y=df_sorted[y_axis],
                mode='lines',
                name=front["name"],
                line=dict(color=color, width=1.5),
                hoverinfo='none', 
                legendgroup=front["name"]
            ))

        # --- 4. Dibujar Puntos ---
        highlight_traces = [] 

        for idx, front in enumerate(visible_fronts):
            front_name = front["name"]
            color = colors_palette[idx % len(colors_palette)]
            if front.get('is_consolidated'):
                 color = '#000080'

            front_points_data = []
            front_multiple_data = [] 

            for coord, solutions in coord_to_solutions.items():
                sol_in_front = next((s for s in solutions if s['front_name'] == front_name), None)
                
                if sol_in_front:
                    is_selected = sol_in_front['unique_id'] in selected_unique_ids
                    
                    hover_text = (f"<b>{sol_in_front['solution_id']}</b> ({sol_in_front['front_name']})<br>"
                                  f"{x_axis.replace('_', ' ').title()}: {sol_in_front['current_x']}<br>"
                                  f"{y_axis.replace('_', ' ').title()}: {sol_in_front['current_y']}<br><extra></extra>")
                    
                    point_data = {
                        'x': sol_in_front['current_x'],
                        'y': sol_in_front['current_y'],
                        'customdata': json.dumps(solutions),
                        'hover': hover_text,
                        'size': 10 + len(solutions) * 2.5,
                        'line_color': 'red' if is_selected else 'white',
                        'line_width': 3 if is_selected else 1
                    }
                    
                    front_points_data.append(point_data)

                    if len(solutions) > 1:
                        highlight_hover = (f"<b>{len(solutions)} Solutions (Multiple)</b><br>"
                                          f"Includes {sol_in_front['solution_id']} from {front_name}<br>"
                                          f"{x_axis.replace('_', ' ').title()}: {sol_in_front['current_x']}<br>"
                                          f"{y_axis.replace('_', ' ').title()}: {sol_in_front['current_y']}<br>"
                                          "<i>Click to inspect</i><extra></extra>")
                        
                        multi_point = point_data.copy()
                        multi_point['hover'] = highlight_hover
                        front_multiple_data.append(multi_point)

            # A. Trazar Puntos Normales
            if front_points_data:
                f_df = pd.DataFrame(front_points_data)
                fig.add_trace(go.Scatter(
                    x=f_df['x'],
                    y=f_df['y'],
                    mode='markers',
                    name=f"{front_name} solutions", 
                    customdata=f_df['customdata'],
                    hovertemplate=f_df['hover'],
                    marker=dict(
                        color=color,
                        size=f_df['size'],
                        sizemode='diameter',
                        line=dict(color=f_df['line_color'], width=f_df['line_width'])
                    ),
                    selected=dict(marker=dict(opacity=1)),   
                    unselected=dict(marker=dict(opacity=1)), 
                    legendgroup=front_name, 
                    showlegend=False 
                ))

            # B. Guardar Puntos Amarillos
            if front_multiple_data:
                m_df = pd.DataFrame(front_multiple_data)
                highlight_traces.append(go.Scatter(
                    x=m_df['x'],
                    y=m_df['y'],
                    mode='markers',
                    name=f"{front_name} multiple", 
                    customdata=m_df['customdata'],
                    hovertemplate=m_df['hover'],
                    marker=dict(
                        color='gold', 
                        size=m_df['size'],
                        sizemode='diameter',
                        opacity=0.8, 
                        line=dict(color='white', width=1)
                    ),
                    selected=dict(marker=dict(opacity=0.8)),   
                    unselected=dict(marker=dict(opacity=0.8)), 
                    legendgroup=front_name, 
                    showlegend=False 
                ))

        # C. Trazar Puntos Amarillos
        for trace in highlight_traces:
            fig.add_trace(trace)

        # --- 7. Layout Final (CON HERRAMIENTAS ACTIVADAS) ---
        fig.update_layout(
            title=plot_title,
            xaxis_title=x_axis.replace('_', ' ').title(),
            yaxis_title=y_axis.replace('_', ' ').title(),
            plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
            height=500, margin=dict(l=60, r=60, t=60, b=60),
            showlegend=True,
            uirevision=ui_revision_key, 
            legend=dict(
                yanchor="top", y=0.99, xanchor="right", x=0.99, 
                groupclick="togglegroup" 
            ),
            clickmode='event+select', 
            dragmode='pan', # Herramienta por defecto: Zoom
            hovermode='closest' # Mejor para Scatter que 'x unified'
        )
        
        # --- ACTIVAR SPIKE LINES Y RANGE SLIDER ---
        """
        fig.update_xaxes(
            showgrid=True, gridwidth=1, gridcolor='lightgray', automargin=True,
            # Range Slider (Barra inferior)
            rangeslider=dict(visible=True),
            # Spike Lines (Guías visuales)
            showspikes=True, 
            spikethickness=1, 
            spikedash='dot', 
            spikemode='across', # Línea cruza todo el gráfico
            spikecolor='#888888'
        )
        """
        
        fig.update_yaxes(
            showgrid=True, gridwidth=1, gridcolor='lightgray', automargin=True,
            # Spike Lines en Y
            showspikes=True, 
            spikethickness=1, 
            spikedash='dot', 
            spikemode='across',
            spikecolor='#888888'
        )

        # --- Generación de información de selección ---
        selected_info = ""
        if selected_solutions and len(selected_solutions) > 0:
            solution_details = []
            for sel in selected_solutions:
                sol = sel['full_data']
                x_val = sol.get(x_axis, sel['x'])
                y_val = sol.get(y_axis, sel['y'])
                
                genes_list = sol.get('selected_genes', [])
                if isinstance(genes_list, str):
                    genes_list = [genes_list]
                genes_count = len(genes_list)

                card_content = dbc.ListGroupItem([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.I(className="bi bi-bullseye text-primary me-2"), 
                                html.Strong(f"{sol['solution_id']}", className="text-dark", style={'fontSize': '1.1rem'}),
                                dbc.Badge(
                                    sel['front_name'], 
                                    color="light", 
                                    text_color="secondary", 
                                    className="ms-2 border small"
                                ),
                            ], className="d-flex align-items-center"),
                        ], width=True), 
                        
                        dbc.Col([
                            dbc.ButtonGroup([
                                dbc.Button(
                                    html.I(className="bi bi-pin-angle-fill"), 
                                    id={'type': 'add-single-to-interest-btn', 'index': sel['unique_id']},
                                    color="outline-success",
                                    size="sm",
                                    title="Add to Interest Panel"
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-x-lg"), 
                                    id={'type': 'remove-solution-btn', 'index': sel['unique_id']},
                                    color="outline-danger",
                                    size="sm",
                                    title="Remove from selection"
                                ),
                            ], size="sm")
                        ], width="auto"), 
                    ], align="center", className="mb-2"),

                    html.Div([
                        dbc.Row([
                            dbc.Col([
                                html.Div(x_axis.replace('_', ' ').upper(), className="text-muted small fw-bold", style={'fontSize': '0.7rem'}),
                                html.Div(f"{x_val}", className="font-monospace text-dark", style={'fontWeight': '500'})
                            ], width=6, className="border-end"), 
                            
                            dbc.Col([
                                html.Div(y_axis.replace('_', ' ').upper(), className="text-muted small fw-bold", style={'fontSize': '0.7rem'}),
                                html.Div(f"{y_val}", className="font-monospace text-dark", style={'fontWeight': '500'})
                            ], width=6, className="ps-3"),
                        ], className="g-0")
                    ], className="bg-light rounded p-2 mb-2 border"),

                    html.Details([
                        html.Summary([
                            html.I(className="bi bi-dna me-1 text-info"),
                            f"View {genes_count} Genes",
                        ], style={'cursor': 'pointer', 'fontSize': '0.85rem', 'color': '#0d6efd', 'fontWeight': 'bold'}),
                        
                        html.Div(
                            ', '.join(genes_list) if genes_list else 'N/A', 
                            className="mt-2 p-2 font-monospace small bg-white border rounded", 
                            style={'maxHeight': '100px', 'overflowY': 'auto', 'color': '#555'}
                        )
                    ]) if genes_list else None

                ], className="shadow-sm mb-3 border rounded border-start border-4 border-start-primary p-3")
                
                solution_details.append(card_content)

            selected_info = html.Div([
                dbc.Row([
                    dbc.Col(dbc.Alert(f"Selected: {len(selected_solutions)} solution(s)", color="primary", className="py-2 mb-3 fw-bold text-center"), width=12)
                ]),
                dbc.ListGroup(solution_details, flush=True, className="bg-transparent")
            ])
        
        return fig, selected_info, plot_title

    # 3. Callbacks del Modal (SIN CAMBIOS)
    @app.callback(
        Output('multi-solution-modal', 'is_open'),
        [Input('multi-solution-modal-store', 'data'),
         Input('multi-solution-modal-close-btn', 'n_clicks')],
        State('multi-solution-modal', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_multi_solution_modal(store_data, n_close, is_open):
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if triggered_id == 'multi-solution-modal-close-btn':
            return False
        if triggered_id == 'multi-solution-modal-store' and store_data:
            return True
        return is_open

    @app.callback(
        [Output('multi-solution-modal-header', 'children'),
         Output('multi-solution-modal-body', 'children')],
        Input('multi-solution-modal-store', 'data'),
        [State('x-axis-store', 'data'), 
         State('y-axis-store', 'data'), 
         State('objectives-store', 'data'),
         State('selected-solutions-store', 'data')],
        prevent_initial_call=True
    )
    def update_multi_solution_modal_content(store_data, x_axis, y_axis, all_objectives, selected_solutions):
        if not store_data:
            raise PreventUpdate

        try:
            solutions = json.loads(store_data)
        except json.JSONDecodeError:
            return "Error", "Error al leer los datos de la solución."
            
        if not solutions:
            raise PreventUpdate

        count = len(solutions)
        sol_sample = solutions[0]
        
        if not x_axis or not y_axis:
            if all_objectives and len(all_objectives) >= 2:
                x_axis = x_axis or all_objectives[0]
                y_axis = y_axis or all_objectives[1]
            else:
                return "Error", "No se han definido los ejes."

        x_val = sol_sample.get('current_x')
        y_val = sol_sample.get('current_y')
        
        header = f"Inspecting {count} Solutions at ({x_axis}: {x_val}, {y_axis}: {y_val})"

        internal_keys = ['front_name', 'color', 'unique_id', 'current_x', 'current_y', 'x_coord', 'y_coord', 'solution_id', 'selected_genes']
        other_objectives = [obj for obj in all_objectives if obj not in [x_axis, y_axis] and obj not in internal_keys and obj in sol_sample]

        selected_ids = {s['unique_id'] for s in (selected_solutions or [])}

        cards = []
        for sol in solutions:
            is_selected = sol['unique_id'] in selected_ids
            
            other_obj_items = []
            for obj_key in other_objectives:
                val = sol.get(obj_key)
                if val is not None:
                     other_obj_items.append(
                         html.Li(f"{obj_key.replace('_', ' ').title()}: {val}", className="list-group-item py-1")
                     )

            card_body = [
                dbc.Row([
                    dbc.Col(html.H5(f"ID: {sol['solution_id']}", className="mb-0 text-primary"), width=8),
                    dbc.Col(dbc.Badge(sol['front_name'], color=sol.get('color', 'secondary'), className="ms-2"), width=4, className="text-end")
                ]),
                html.Hr(className="my-2"),
                
                dbc.Row([
                    dbc.Col(dbc.Button(
                        "Select" if not is_selected else "Deselect",
                        id={'type': 'modal-select-solution', 'index': sol['unique_id']},
                        color="primary" if not is_selected else "danger",
                        outline=True,
                        size="sm"
                    ), width="auto"),
                    dbc.Col(dbc.Button(
                        "📌 Add to Panel",
                        id={'type': 'add-single-to-interest-btn', 'index': sol['unique_id']},
                        color="success",
                        size="sm"
                    ), width="auto"),
                ], className="mb-3"),

                dbc.Accordion([
                    dbc.AccordionItem(
                        html.Ul(other_obj_items, className="list-group list-group-flush"),
                        title=f"Other Objectives ({len(other_obj_items)})",
                    ) if other_obj_items else None,
                    
                    dbc.AccordionItem(
                        html.Div(
                            ', '.join(sol.get('selected_genes', [])), 
                            className="p-2", 
                            style={'fontSize': '0.85rem', 'maxHeight': '150px', 'overflowY': 'auto', 'backgroundColor': '#f9f9f9'}
                        ),
                        title=f"Genes ({len(sol.get('selected_genes', []))})",
                    )
                ], start_collapsed=True, flush=True)
            ]
            
            cards.append(dbc.Card(dbc.CardBody(card_body), className="mb-3"))

        return header, html.Div(cards)