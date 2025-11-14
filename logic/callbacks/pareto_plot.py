# logic/callbacks/pareto_plot.py

import dash
from dash import Output, Input, State, ALL, callback_context, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from collections import Counter, defaultdict
import json

# La función get_marker_properties_aux() ha sido eliminada
# ya que la lógica de renderizado se manejará de forma diferente.

def register_pareto_plot_callbacks(app):

    # 1. Callback para actualizar los STORES de ejes (SIN CAMBIOS)
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
        """
        Update axis stores based on available objectives or swap button.
        """
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

    # 2. Callback para almacenar el layout (Zoom/Pan) (SIN CAMBIOS)
    @app.callback(
        Output('pareto-layout-store', 'data', allow_duplicate=True),
        Input('pareto-plot', 'relayoutData'),
        State('pareto-layout-store', 'data'),
        prevent_initial_call=True
    )
    def store_pareto_layout(relayoutData, current_layout):
        if relayoutData:
            is_autorange_reset = (
                relayoutData.get('xaxis.autorange') == True or
                relayoutData.get('yaxis.autorange') == True
            )
            is_autosize_reset = (
                'autosize' in relayoutData and
                'xaxis.range[0]' not in relayoutData and
                'yaxis.range[0]' not in relayoutData
            )

            if is_autorange_reset or is_autosize_reset:
                return {} 

            if ('dragmode' in relayoutData and 
                'xaxis.range[0]' not in relayoutData and 
                'yaxis.range[0]' not in relayoutData):
                raise PreventUpdate 

            if 'xaxis.range[0]' in relayoutData or 'yaxis.range[0]' in relayoutData:
                keys_to_remove = ['lasso', 'box', 'click', 'xaxis.autorange', 'yaxis.autorange', 'autosize', 'dragmode']
                filtered_relayout = {k: v for k, v in relayoutData.items() if not any(key in k for key in keys_to_remove)}
                
                updated_layout = (current_layout or {}).copy()
                updated_layout.update(filtered_relayout)
                return updated_layout
                
        raise PreventUpdate

    # 4. Callback principal para generar el gráfico de Pareto (MODIFICADO)
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
        State('pareto-layout-store', 'data'),
        prevent_initial_call=True
    )
    def update_pareto_plot(data_store, selected_solutions, x_axis_value, y_axis_value, main_front_checkboxes, front_name_inputs, layout_data):
        """
        Update Pareto plot with grouped bubble markers for multiple solutions
        and separate line traces for each front.
        """
        if not data_store or not data_store.get("fronts"):
            return {}, "", "Pareto Front"

        visible_fronts = [f for f in data_store.get("fronts", []) if f.get("visible", True)]
        if not visible_fronts:
            return {}, "", "Pareto Front (No visible fronts)"

        # --- 1. Determinar Ejes --- (Sin cambios)
        explicit_objectives = data_store.get('explicit_objectives', [])
        objectives = data_store.get('main_objectives') or (explicit_objectives if explicit_objectives else (visible_fronts[0]['objectives'] if visible_fronts else []))
        
        x_axis = x_axis_value or (explicit_objectives[0] if explicit_objectives else (objectives[0] if objectives else 'num_genes'))
        y_axis = y_axis_value or (explicit_objectives[1] if len(explicit_objectives) > 1 else (objectives[1] if len(objectives) > 1 else 'accuracy'))

        if x_axis not in objectives: x_axis = objectives[0]
        if y_axis not in objectives: y_axis = objectives[1]

        fig = go.Figure()
        colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        selected_unique_ids = {s['unique_id'] for s in (selected_solutions or [])}

        # --- 2. Pre-procesar y Agrupar Soluciones --- (Sin cambios)
        coord_to_solutions = defaultdict(list)
        all_objectives = set(objectives) 

        for idx, front in enumerate(visible_fronts):
            df = pd.DataFrame(front["data"])
            if x_axis not in df.columns or y_axis not in df.columns:
                continue
            
            color = colors_palette[idx % len(colors_palette)]
            if front.get('is_consolidated'):
                 color = '#000080'
            
            df['x_coord'] = df[x_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
            df['y_coord'] = df[y_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)

            for _, row in df.iterrows():
                coord = (row['x_coord'], row['y_coord'])
                unique_id = f"{row['solution_id']}|{front['name']}"
                
                sol_data = row.to_dict()
                sol_data['front_name'] = front['name']
                sol_data['color'] = color
                sol_data['unique_id'] = unique_id
                sol_data['current_x'] = row[x_axis]
                sol_data['current_y'] = row[y_axis]
                
                coord_to_solutions[coord].append(sol_data)
                all_objectives.update(sol_data.keys())

            # --- 3. Dibujar Líneas (Traza por cada frente) --- (Sin cambios)
            df_sorted = df.sort_values(by=[x_axis, y_axis], ascending=True)
            fig.add_trace(go.Scatter(
                x=df_sorted[x_axis],
                y=df_sorted[y_axis],
                mode='lines',
                name=front["name"],
                line=dict(color=color, width=1.5),
                hoverinfo='none', 
                legendgroup=front["name"]
            ))

        # --- 4. Preparar Datos para Burbujas --- (MODIFICADO)
        plot_data = []
        for coord, solutions in coord_to_solutions.items():
            count = len(solutions)
            is_selected = any(s['unique_id'] in selected_unique_ids for s in solutions)

            # ⭐️ --- INICIO DE LA CORRECCIÓN --- ⭐️
            x_to_plot = coord[0] # Default to rounded coord
            y_to_plot = coord[1] # Default to rounded coord

            if count == 1:
                sol = solutions[0]
                hover_text = (f"<b>{sol['solution_id']}</b> ({sol['front_name']})<br>"
                              f"{x_axis.replace('_', ' ').title()}: {sol['current_x']}<br>"
                              f"{y_axis.replace('_', ' ').title()}: {sol['current_y']}<br><extra></extra>")
                marker_color = sol['color']
                front_name_para_df = sol['front_name']
                
                # Usar el valor original y sin redondear para el punto
                x_to_plot = sol['current_x'] 
                y_to_plot = sol['current_y']

            else:
                hover_text = (f"<b>{count} Solutions (Multiple)</b><br>"
                              f"{x_axis.replace('_', ' ').title()}: {coord[0]}<br>"
                              f"{y_axis.replace('_', ' ').title()}: {coord[1]}<br>"
                              "<i>Click to inspect</i><extra></extra>")
                marker_color = 'black'
                front_name_para_df = 'Multiple'
                
                # Para puntos múltiples, SÍ usamos el valor redondeado
                x_to_plot = coord[0]
                y_to_plot = coord[1]

            plot_data.append({
                'x': x_to_plot, # <-- Corregido
                'y': y_to_plot, # <-- Corregido
                'count': count,
                'color': marker_color,
                'size': 10 + count * 2.5, 
                'hover': hover_text,
                'line_color': 'red' if is_selected else 'white',
                'line_width': 3 if is_selected else 1,
                'front_name': front_name_para_df,
                'solutions_json': json.dumps(solutions) 
            })
            # ⭐️ --- FIN DE LA CORRECCIÓN --- ⭐️

        if not plot_data:
             return {}, "", "Pareto Front (No data for selected axes)"

        plot_df = pd.DataFrame(plot_data)

        # --- 5. Dibujar Burbujas (SIN CAMBIOS) ---
        
        # 5a. Dibujar Puntos Únicos (uno por frente)
        for idx, front in enumerate(visible_fronts):
            front_name = front["name"]
            color = colors_palette[idx % len(colors_palette)]
            if front.get('is_consolidated'):
                 color = '#000080'
            
            front_points_df = plot_df[
                (plot_df['count'] == 1) & (plot_df['front_name'] == front_name)
            ]

            if not front_points_df.empty:
                fig.add_trace(go.Scatter(
                    x=front_points_df['x'],
                    y=front_points_df['y'],
                    mode='markers',
                    name=f"{front_name} solutions", 
                    customdata=front_points_df['solutions_json'],
                    hovertemplate=front_points_df['hover'],
                    marker=dict(
                        color=color, 
                        size=front_points_df['size'],
                        sizemode='diameter',
                        line=dict(
                            color=front_points_df['line_color'],
                            width=front_points_df['line_width']
                        )
                    ),
                    legendgroup=front_name,  
                    showlegend=False           
                ))

        # 5b. Dibujar Puntos Múltiples (una traza para todos)
        multiple_points_df = plot_df[plot_df['count'] > 1]
        
        if not multiple_points_df.empty:
            fig.add_trace(go.Scatter(
                x=multiple_points_df['x'],
                y=multiple_points_df['y'],
                mode='markers',
                name='Multiple solutions', 
                customdata=multiple_points_df['solutions_json'],
                hovertemplate=multiple_points_df['hover'],
                marker=dict(
                    color='black', 
                    size=multiple_points_df['size'],
                    sizemode='diameter',
                    line=dict(
                        color=multiple_points_df['line_color'],
                        width=multiple_points_df['line_width']
                    )
                ),
                legendgroup='Multiple solutions_group', 
                showlegend=True                    
            ))

     

        # --- 7. Layout y Renderizado de Selección --- (Sin cambios)
        if layout_data:
            layout_updates = {}
            if 'xaxis.range[0]' in layout_data:
                layout_updates['xaxis'] = {'range': [layout_data['xaxis.range[0]'], layout_data['xaxis.range[1]']], 'autorange': False}
            if 'yaxis.range[0]' in layout_data:
                layout_updates['yaxis'] = {'range': [layout_data['yaxis.range[0]'], layout_data['yaxis.range[1]']], 'autorange': False}
            fig.update_layout(layout_updates)

        fig.update_layout(
            title=f"Pareto Front: {y_axis.replace('_', ' ').title()} vs {x_axis.replace('_', ' ').title()}",
            xaxis_title=x_axis.replace('_', ' ').title(),
            yaxis_title=y_axis.replace('_', ' ').title(),
            plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
            height=500, margin=dict(l=60, r=60, t=60, b=60),
            showlegend=True,
            legend=dict(
                yanchor="top", y=0.99, xanchor="right", x=0.99, 
                groupclick="togglegroup" 
            ),
            clickmode='event+select', 
            dragmode='lasso'
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray', automargin=True)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray', automargin=True)

        selected_info = ""
        if selected_solutions and len(selected_solutions) > 0:
            solution_details = []
            for sel in selected_solutions:
                sol = sel['full_data']
                x_val = sol.get(x_axis, sel['x'])
                y_val = sol.get(y_axis, sel['y'])
                solution_details.append({
                    'id': sol['solution_id'],
                    'genes': sol.get('selected_genes', []),
                    'x': x_val, 'y': y_val, 'front': sel['front_name'],
                    'unique_id': sel['unique_id'], 'visible': True
                })
            selected_info = html.Div([
                dbc.Alert(f"Selected: {len(selected_solutions)} solution(s)", color="info", className="mb-2"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.Div([
                            html.Div([
                                html.Strong(f"{sol['id']}", className="text-primary"),
                                html.Span(f" ({sol['front']})", className="text-muted ms-2"),
                            ], style={'flex': '1'}),
                            html.Div([
                                dbc.Button("📌", id={'type': 'add-single-to-interest-btn', 'index': sol['unique_id']}, color="success", size="sm", className="me-1", style={'padding': '0 6px', 'lineHeight': '1'}, title="Add to Interest Panel"),
                                dbc.Button("×", id={'type': 'remove-solution-btn', 'index': sol['unique_id']}, color="danger", size="sm", style={'padding': '0 8px', 'lineHeight': '1'}, title="Remove from selection")
                            ])
                        ], className="d-flex align-items-center justify-content-between"),
                        html.Small([
                            f"{x_axis}: {int(sol['x']) if isinstance(sol['x'], (int, float)) and sol['x'] == int(sol['x']) else '{:.3f}'.format(sol['x']) if isinstance(sol['x'], float) else sol['x']}, "
                            f"{y_axis}: {int(sol['y']) if isinstance(sol['y'], (int, float)) and sol['y'] == int(sol['y']) else '{:.3f}'.format(sol['y']) if isinstance(sol['y'], float) else sol['y']}"
                        ], className="text-muted d-block mt-1"),
                        
                        html.Details([
                            html.Summary(
                                "Ver genes",
                                style={'cursor': 'pointer', 'fontSize': '0.85rem', 'color': '#0d6efd', 'marginTop': '0.25rem'}
                            ),
                            html.Div([
                                html.Strong("Genes: ", className="text-secondary"),
                                html.Span(', '.join(sol['genes']) if sol['genes'] else 'N/A', className="text-dark")
                            ], className="mt-2 p-2", style={'fontSize': '0.85rem', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px'})
                        ], style={'marginTop': '0.5rem'}) if sol.get('genes') else None
                        
                    ]) for sol in solution_details
                ], className="mt-2")
            ])
        
        plot_title = f"Pareto Front: {y_axis.replace('_', ' ').title()} vs {x_axis.replace('_', ' ').title()}"
        return fig, selected_info, plot_title

    # --- 5. Callback para abrir/cerrar el modal --- (SIN CAMBIOS)
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

    # --- 6. Callback para poblar el contenido del modal --- (SIN CAMBIOS)
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