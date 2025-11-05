# logic/callbacks/pareto_plot.py

import dash
from dash import Output, Input, State, ALL, callback_context, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
from collections import Counter, defaultdict
import json


# Lógica auxiliar para determinar las propiedades del marcador (movida de app.py)
def get_marker_properties_aux(row, selected_unique_ids, duplicate_coords, inter_front_duplicate_coords, current_front_color):
    """
    Determina las propiedades del marcador para el plot de Pareto.
    """
    is_selected = row['unique_id'] in selected_unique_ids
    coord = (row['x_coord'], row['y_coord'])
    is_duplicate = coord in duplicate_coords
    color = current_front_color
    
    # Base Marker: Normal, no-shared points
    size = 10 
    symbol = 'circle'
    marker_color = color
    line_width = 1.0
    line_color = color

    if is_duplicate:
        # Shared Marker: Diamond, Black
        size = 14
        symbol = 'diamond'
        marker_color = 'black' 
        line_width = 1.5
        line_color = 'gray'
    
    if is_selected:
        # Selected Marker: Filled Circle, Red (for emphasis), thick white border
        size = 16
        symbol = 'circle' 
        marker_color = 'red' 
        line_width = 2.5
        line_color = 'white'

    # Se retorna un flag para la robustez (inter-front duplicate)
    return size, symbol, marker_color, line_width, line_color, coord in inter_front_duplicate_coords


def register_pareto_plot_callbacks(app):

    # 1. Callback para actualizar las opciones y visibilidad de los dropdowns de ejes
    @app.callback(
        [Output('x-axis-dropdown', 'options'),
         Output('y-axis-dropdown', 'options'),
         Output('x-axis-dropdown', 'value'), 
         Output('y-axis-dropdown', 'value'), 
         Output('x-axis-dropdown', 'style'),
         Output('y-axis-dropdown', 'style'),
         Output('x-axis-static-text', 'children'),
         Output('y-axis-static-text', 'children'),
         Output('x-axis-static-text', 'style'),
         Output('y-axis-static-text', 'style')],
        [Input('objectives-store', 'data'),
         Input('data-store', 'data'),
         Input('swap-axes-btn', 'n_clicks')],
        [State('x-axis-dropdown', 'value'),
         State('y-axis-dropdown', 'value'),
         State('x-axis-static-text', 'children'),
         State('y-axis-static-text', 'children')],
        prevent_initial_call=False
    )
    def update_axis_dropdowns(objectives, data_store, swap_clicks, current_x_value, current_y_value, current_x_text, current_y_text):
        """
        Update axis dropdown options and visibility based on available objectives.
        """
        ctx = dash.callback_context
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

        if not objectives:
            return [], [], None, None, {'display': 'none'}, {'display': 'none'}, "", "", {'display': 'none'}, {'display': 'none'}

        options = [{'label': obj.replace('_', ' ').title(), 'value': obj} for obj in objectives]

        # 1. Determinar valores por defecto/actuales
        explicit_objectives = data_store.get('explicit_objectives', [])
        default_x = explicit_objectives[0] if len(explicit_objectives) > 0 else (objectives[0] if objectives else None)
        default_y = explicit_objectives[1] if len(explicit_objectives) > 1 else (objectives[1] if len(objectives) > 1 else (objectives[0] if objectives else None))
        
        if triggered_id != 'swap-axes-btn' and current_x_value in objectives:
            final_x_value = current_x_value
        else:
            final_x_value = default_x
            
        if triggered_id != 'swap-axes-btn' and current_y_value in objectives:
            final_y_value = current_y_value
        else:
            final_y_value = default_y
        
        # 2. Configuración de visibilidad
        if len(objectives) > 2:
            dropdown_style = {'display': 'block'}
            static_text_style = {'display': 'none'}
            x_static_text = ""
            y_static_text = ""
        else:
            dropdown_style = {'display': 'none'}
            static_text_style = {'display': 'block', 'fontSize': '14px', 'padding': '8px 0'}
            
            x_static_text = final_x_value.replace('_', ' ').title() if final_x_value else ""
            y_static_text = final_y_value.replace('_', ' ').title() if final_y_value else ""

            if triggered_id == 'swap-axes-btn':
                x_static_text, y_static_text = current_y_text, current_x_text


        return options, options, final_x_value, final_y_value, dropdown_style, dropdown_style, x_static_text, y_static_text, static_text_style, static_text_style

    # 2. Callback para intercambiar ejes (Swap Axes)
    @app.callback(
        [Output('x-axis-dropdown', 'value', allow_duplicate=True),
         Output('y-axis-dropdown', 'value', allow_duplicate=True),
         Output('x-axis-static-text', 'children', allow_duplicate=True),
         Output('y-axis-static-text', 'children', allow_duplicate=True),
         Output('pareto-layout-store', 'data', allow_duplicate=True)],
        Input('swap-axes-btn', 'n_clicks'),
        [State('x-axis-dropdown', 'value'),
         State('y-axis-dropdown', 'value'),
         State('x-axis-static-text', 'children'),
         State('y-axis-static-text', 'children')],
        prevent_initial_call=True
    )
    def swap_axes(n_clicks, current_x, current_y, current_x_text, current_y_text):
        """Swap X and Y axis selections and static text, and reset graph zoom."""
        if not n_clicks:
            raise PreventUpdate

        new_x_val = current_y
        new_y_val = current_x
        
        new_x_text = current_y_text
        new_y_text = current_x_text

        return new_x_val, new_y_val, new_x_text, new_y_text, {}

    # 3. Callback para almacenar el layout (Zoom/Pan)
    @app.callback(
        Output('pareto-layout-store', 'data', allow_duplicate=True),
        Input('pareto-plot', 'relayoutData'),
        State('pareto-layout-store', 'data'),
        prevent_initial_call=True
    )
    def store_pareto_layout(relayoutData, current_layout):
        """
        Stores the graph's layout data (zoom/pan) and handles Plotly's 'Reset Axes'
        by clearing the store to force Autorange on next update.
        """
        if relayoutData:
            is_autoscale_or_reset = (
                relayoutData.get('xaxis.autorange') == True or
                relayoutData.get('yaxis.autorange') == True
            )
            
            is_double_click_autoscale = (
                 len(relayoutData) <= 2 and 
                 ('autosize' in relayoutData or 'dragmode' in relayoutData) and
                 'xaxis.range[0]' not in relayoutData and 
                 'yaxis.range[0]' not in relayoutData
            )
            
            if is_autoscale_or_reset or is_double_click_autoscale:
                return {}
            
            if 'xaxis.range[0]' in relayoutData or 'yaxis.range[0]' in relayoutData or 'dragmode' in relayoutData:
                
                keys_to_remove = ['lasso', 'box', 'click', 'xaxis.autorange', 'yaxis.autorange']
                filtered_relayout = {k: v for k, v in relayoutData.items() if not any(key in k for key in keys_to_remove)}
                
                updated_layout = current_layout.copy()
                updated_layout.update(filtered_relayout)
                return updated_layout

        raise PreventUpdate

    # 4. Callback principal para generar el gráfico de Pareto
    @app.callback(
        [Output('pareto-plot', 'figure'),
         Output('selected-solutions-info', 'children'),
         Output('pareto-plot-title', 'children')],
        [Input('data-store', 'data'),
         Input('selected-solutions-store', 'data'),
         Input('x-axis-dropdown', 'value'),
         Input('y-axis-dropdown', 'value'),
         Input({'type': 'main-front-checkbox', 'index': ALL}, 'value'),
         Input({'type': 'front-name-input', 'index': ALL}, 'value')],
        State('pareto-layout-store', 'data'), # Estado del layout para mantener zoom/pan
        prevent_initial_call=True
    )
    def update_pareto_plot(data_store, selected_solutions, x_axis_value, y_axis_value, main_front_checkboxes, front_name_inputs, layout_data):
        """
        Update Pareto plot with multiple fronts support, line connections,
        shared points highlighting, and persistent view (zoom/pan).
        """
        if not data_store:
            return {}, "", "Pareto Front"

        fronts = data_store.get("fronts", [])
        if not fronts:
            return {}, "", "Pareto Front"

        visible_fronts = [f for f in fronts if f.get("visible", True)]

        if not visible_fronts:
            return {}, "", "Pareto Front (No visible fronts)"

        # Determinar ejes
        explicit_objectives = data_store.get('explicit_objectives', [])
        objectives = data_store.get('main_objectives') or (explicit_objectives if explicit_objectives else (fronts[0]['objectives'] if fronts else []))

        x_axis = x_axis_value if x_axis_value else (explicit_objectives[0] if explicit_objectives else (objectives[0] if objectives else 'num_genes'))
        y_axis = y_axis_value if y_axis_value else (explicit_objectives[1] if len(explicit_objectives) > 1 else (objectives[1] if len(objectives) > 1 else 'accuracy'))

        if not x_axis or x_axis not in objectives:
            x_axis = objectives[0] if objectives else 'num_genes'
        if not y_axis or y_axis not in objectives:
            y_axis = objectives[1] if len(objectives) > 1 else (objectives[0] if objectives else 'accuracy')

        fig = go.Figure()

        colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        # --- Detección de Duplicados ---
        all_points_coords = []
        coord_to_fronts = defaultdict(set)
        
        for front in visible_fronts:
            df = pd.DataFrame(front["data"])

            if x_axis not in df.columns or y_axis not in df.columns:
                continue
                
            df['x_coord'] = df[x_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
            df['y_coord'] = df[y_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
            
            for index, row in df.iterrows():
                coord = (row['x_coord'], row['y_coord'])
                all_points_coords.append(coord)
                coord_to_fronts[coord].add(front['name'])
        
        coord_counts = Counter(all_points_coords)
        duplicate_coords = {coord for coord, count in coord_counts.items() if count >= 2}
        inter_front_duplicate_coords = {
            coord for coord, front_names in coord_to_fronts.items() if len(front_names) >= 2
        }
        # -------------------------------

        selected_unique_ids = {s['unique_id'] for s in (selected_solutions or [])}
        robustness_overlay_data = []
        duplicate_trace_added = False
        robustness_trace_added = False

        for idx, front in enumerate(visible_fronts):
            df = pd.DataFrame(front["data"])

            if x_axis not in df.columns or y_axis not in df.columns:
                continue

            df['front_name'] = front['name']
            df['unique_id'] = df['solution_id'] + '|' + df['front_name']
            df['x_coord'] = df[x_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
            df['y_coord'] = df[y_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)

            color = colors_palette[idx % len(colors_palette)]
            
            if front.get('is_consolidated'):
                 color = '#000080'

            x_format = "%{x}" if df[x_axis].dtype in ['int64', 'int32'] else "%{x:.3f}"
            y_format = "%{y}" if df[y_axis].dtype in ['int64', 'int32'] else "%{y:.3f}"

            # Llama a la lógica auxiliar para las propiedades del marcador
            marker_properties = df.apply(
                get_marker_properties_aux, 
                axis=1, 
                result_type='expand',
                args=(selected_unique_ids, duplicate_coords, inter_front_duplicate_coords, color)
            )

            marker_sizes = marker_properties[0].tolist()
            marker_symbols = marker_properties[1].tolist()
            marker_colors = marker_properties[2].tolist()
            marker_line_widths = marker_properties[3].tolist()
            marker_line_colors = marker_properties[4].tolist()
            is_inter_front_duplicate_list = marker_properties[5].tolist()

            # --- Main Trace (Lines + Markers) ---
            fig.add_trace(go.Scatter(
                x=df[x_axis],
                y=df[y_axis],
                mode='lines+markers',
                name=front["name"],
                line=dict(
                    color=color,
                    width=1.5
                ),
                marker=dict(
                    size=marker_sizes,
                    symbol=marker_symbols,
                    color=marker_colors, 
                    line=dict(
                        width=marker_line_widths,
                        color=marker_line_colors
                    )
                ),
                customdata=df[['solution_id', 'front_name']].values,
                hovertemplate="<b>%{customdata[0]}</b><br>" +
                             f"{x_axis.replace('_', ' ').title()}: {x_format}<br>" +
                             f"{y_axis.replace('_', ' ').title()}: {y_format}<br>" +
                             f"<i>{front['name']}</i><br>" +
                             "<extra></extra>"
            ))
            
            # --- Recolección de Puntos para Overlay de Robustez ---
            df_inter_front = df[df.index.to_series().apply(lambda i: is_inter_front_duplicate_list[i])]
            
            if not df_inter_front.empty:
                for index, row in df_inter_front.iterrows():
                     coord = (row['x_coord'], row['y_coord'])
                     if coord not in [d['coord'] for d in robustness_overlay_data]:
                         robustness_overlay_data.append({'x': row[x_axis], 'y': row[y_axis], 'coord': coord})

        
        # 1. Añadir Traza de Duplicados (Diamante Negro) - para Leyenda
        if duplicate_coords and not duplicate_trace_added:
            fig.add_trace(go.Scatter(
                x=[None],
                y=[None],
                mode='markers',
                name='Multiple solution point',
                legendgroup='shared-all-legend',
                marker=dict(
                    size=14,
                    symbol='diamond',
                    color='black',
                    line=dict(width=1.5, color='gray') 
                ),
                hovertemplate='<b>Shared Point (All)</b><extra></extra>',
                showlegend=True
            ))
            duplicate_trace_added = True

        
        # 2. Overlay de Robustez (Estrella Dorada)
        if robustness_overlay_data:
            df_robustness = pd.DataFrame(robustness_overlay_data)
            
            # A. Trazar los puntos reales (sin leyenda)
            fig.add_trace(go.Scatter(
                x=df_robustness['x'],
                y=df_robustness['y'],
                mode='markers',
                name='Robust Solution Overlay', 
                legendgroup="inter-front-robustness",
                marker=dict(
                    size=22,
                    symbol='star-dot',
                    color='gold', 
                    line=dict(
                        width=2,
                        color='red' 
                    )
                ),
                hovertemplate='<b>Robustness Shared Point</b><extra></extra>',
                showlegend=False
            ))
            
            # B. Añadir traza dummy para la Leyenda
            if not robustness_trace_added:
                 fig.add_trace(go.Scatter(
                    x=[None], 
                    y=[None],
                    mode='markers',
                    name='Solutions shared by fronts',
                    legendgroup='inter-front-robustness-legend',
                    marker=dict(
                        size=22,
                        symbol='star-dot',
                        color='gold',
                        line=dict(width=2, color='red')
                    ),
                    showlegend=True
                ))
                 robustness_trace_added = True

        # --- Aplicar Layout Almacenado ---
        if layout_data:
            layout_updates = {}
            xaxis_range_start = layout_data.get('xaxis.range[0]')
            xaxis_range_end = layout_data.get('xaxis.range[1]')
            yaxis_range_start = layout_data.get('yaxis.range[0]')
            yaxis_range_end = layout_data.get('yaxis.range[1]')
            
            if xaxis_range_start is not None and xaxis_range_end is not None:
                layout_updates['xaxis'] = {'range': [xaxis_range_start, xaxis_range_end], 'autorange': False}
            
            if yaxis_range_start is not None and yaxis_range_end is not None:
                layout_updates['yaxis'] = {'range': [yaxis_range_start, yaxis_range_end], 'autorange': False}
                
            fig.update_layout(layout_updates)


        fig.update_layout(
            title=f"Pareto Front: {y_axis.replace('_', ' ').title()} vs {x_axis.replace('_', ' ').title()}",
            xaxis_title=x_axis.replace('_', ' ').title(),
            yaxis_title=y_axis.replace('_', ' ').title(),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            height=500,
            margin=dict(l=60, r=60, t=60, b=60),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            ),
            clickmode='event+select',
            dragmode='lasso'
        )
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            automargin=True
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
            automargin=True
        )

        # --- Renderizado de soluciones seleccionadas ---
        selected_info = ""
        if selected_solutions and len(selected_solutions) > 0:
            solution_details = []
            
            # Recalcular la robustez de las soluciones seleccionadas para el display
            temp_coord_to_fronts = defaultdict(set)
            for front in visible_fronts:
                df = pd.DataFrame(front["data"])
                df['x_coord'] = df[x_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
                df['y_coord'] = df[y_axis].apply(lambda x: round(x, 3) if isinstance(x, float) else x)
                for index, row in df.iterrows():
                    coord = (row['x_coord'], row['y_coord'])
                    temp_coord_to_fronts[coord].add(front['name'])
            
            temp_inter_front_duplicate_coords = {
                coord for coord, front_names in temp_coord_to_fronts.items() if len(front_names) >= 2
            }
            
            for sel in selected_solutions:
                sol = sel['full_data']
                
                x_val = sol.get(x_axis, sel['x'])
                y_val = sol.get(y_axis, sel['y'])
                
                solution_details.append({
                    'id': sol['solution_id'],
                    'genes': sol.get('selected_genes', []),
                    'x': x_val,
                    'y': y_val,
                    'front': sel['front_name'],
                    'unique_id': sel['unique_id'],
                    'visible': True,
                    'is_inter_front_duplicate': (round(x_val, 3), round(y_val, 3)) in temp_inter_front_duplicate_coords
                })

            selected_info = html.Div([
                dbc.Alert([
                    html.Strong(f"Selected: {len(selected_solutions)} solution(s)"),
                    html.Br(),
                    html.Small("Click on a point to select the solution. Also can use lasso/box to add more.", className="text-muted")
                ], color="info", className="mb-2"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.Div([
                            html.Div([
                                html.Strong(f"{sol['id']}", className="text-primary"),
                                html.Span(f" ({sol['front']})", className="text-muted ms-2"),
                                html.Span(" [Robustness! ⭐]", className="text-success ms-1") 
                                if sol['is_inter_front_duplicate'] else None,
                                html.Span(" [Hidden]", className="text-warning ms-1") if not sol.get('visible', True) else None,
                            ], style={'flex': '1'}),
                            html.Div([
                                dbc.Button(
                                    "📌",
                                    id={'type': 'add-single-to-interest-btn', 'index': sol['unique_id']},
                                    color="success",
                                    size="sm",
                                    className="me-1",
                                    style={'padding': '0 6px', 'lineHeight': '1'},
                                    title="Add to Interest Panel"
                                ),
                                dbc.Button(
                                    "×",
                                    id={'type': 'remove-solution-btn', 'index': sol['unique_id']},
                                    color="danger",
                                    size="sm",
                                    style={'padding': '0 8px', 'lineHeight': '1'},
                                    title="Remove from selection"
                                )
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