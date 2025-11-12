# logic/callbacks/genes_analysis.py

import dash
from dash import Output, Input, State, dcc, html, dash_table, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from io import StringIO 
from datetime import datetime

def register_genes_analysis_callbacks(app):

    # --- CALLBACK 1: PROCESAR DATOS Y ANÁLISIS COMÚN (MODIFICADO) ---
    @app.callback(
        [Output('common-genes-analysis', 'children'),
         Output('genes-analysis-internal-store', 'data')],
        Input('data-store', 'data')
    )
    def prepare_data_and_common_analysis(data):
        # ... (código previo sin cambios) ...
        """
        Paso 1: Procesa los datos de 'data-store'.
        - Genera el análisis común (100% y gráfico de frecuencia).
        - Crea el 'genes_df' maestro con 'front_name' y 'unique_solution_id'.
        - Guarda el 'genes_df' maestro en el store interno.
        """
        if not data:
            return "", None

        all_solutions_list = []
        available_objectives = []
        genes_data = []

        # 1. Iterar sobre los frentes para construir la lista de soluciones Y el DF maestro
        for front in data.get("fronts", []):
            if not front.get("visible", True):
                continue
                
            front_name = front.get("name", "Unknown Front")
            solutions_data = front.get("data", [])
            all_solutions_list.extend(solutions_data) # Para análisis de frecuencia

            if not solutions_data:
                continue

            # 1.1. Obtener objetivos numéricos del primer frente
            if not available_objectives and solutions_data:
                sample_solution = solutions_data[0]
                for key in sample_solution.keys():
                    if key not in ['selected_genes', 'solution_id']:
                        value = sample_solution.get(key)
                        if isinstance(value, (int, float)):
                            available_objectives.append(key)

            # 1.2. Construir los datos para el DF maestro
            for solution in solutions_data:
                sol_id = solution.get('solution_id', 'N/A')
                unique_sol_id = f"{front_name} - {sol_id}"
                
                for gene in solution.get('selected_genes', []):
                    row = {
                        'front_name': front_name, 
                        'unique_solution_id': unique_sol_id, 
                        'solution_id': sol_id, 
                        'gene': gene
                    }
                    for objective in available_objectives:
                        row[objective] = solution.get(objective, None)
                    genes_data.append(row)

        if not all_solutions_list:
            return "", None
            
        genes_df = pd.DataFrame(genes_data)

        # 2. Calcular análisis de frecuencia (sin cambios)
        all_genes = [gene for solution in all_solutions_list for gene in solution.get('selected_genes', [])]
        gene_counts = pd.Series(all_genes).value_counts()
        total_solutions = len(all_solutions_list)
        genes_100_percent = gene_counts[gene_counts == total_solutions]
        genes_under_100 = gene_counts[gene_counts < total_solutions]

        # --- 🔑 INICIO DEL CAMBIO (Botón 100%) ---
        genes_100_content = []
        if len(genes_100_percent) > 0:
            genes_100_content = [
                html.Div([
                    html.H5("🎯 Genes Present in 100% of Solutions", className="text-success mb-3"),
                    dbc.Button(
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save 100% Group"], # Icono y texto cambiados
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': '100pct'},
                        color="info", # Color cambiado
                        size="sm"
                    )
                ], className="d-flex justify-content-between align-items-center mb-3"), # Alineación cambiada
                dbc.Card([
                    dbc.CardBody([
                        html.P(f"Found {len(genes_100_percent)} genes that appear in all {total_solutions} solutions:",
                               className="text-muted mb-3"),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    gene,
                                    id={'type': 'add-gene-individual-btn', 'gene_name': gene, 'source': '100pct'},
                                    color="success",
                                    size="sm",
                                    className="me-2 mb-2",
                                    style={'fontSize': '14px', 'padding': '8px 12px'}
                                )
                                for gene in sorted(genes_100_percent.index)
                            ])
                        ])
                    ])
                ], className="mb-4")
            ]
        else:
            genes_100_content = [
                html.Div([
                    html.H5("🎯 Genes Present in 100% of Solutions", className="text-success mb-3"),
                    dbc.Button(
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save 100% Group"], # Icono y texto cambiados
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': '100pct'},
                        color="info", # Color cambiado
                        size="sm",
                        style={'display': 'none'} # Sigue oculto
                    )
                ], className="d-flex justify-content-between align-items-center mb-3"), # Alineación cambiada
                dbc.Alert("No genes appear in 100% of the solutions.", color="info", className="mb-4")
            ]
        # --- 🔑 FIN DEL CAMBIO (Botón 100%) ---
        
        # --- Contenido de Distribución de Frecuencia (sin cambios) ---
        genes_under_100_content = []
        if len(genes_under_100) > 0:
            percentage_groups = {}
            for gene, count in genes_under_100.items():
                percentage = round((count / total_solutions) * 100, 1)
                if percentage not in percentage_groups:
                    percentage_groups[percentage] = []
                percentage_groups[percentage].append(gene)
            percentages = sorted(percentage_groups.keys())
            gene_counts_per_percentage = [len(percentage_groups[p]) for p in percentages]
            fig = go.Figure(data=[
                go.Bar(
                    x=percentages,
                    y=gene_counts_per_percentage,
                    marker=dict(color='rgb(70, 130, 180)', line=dict(color='rgb(50, 110, 160)', width=1)),
                    text=gene_counts_per_percentage,
                    textposition='outside',
                    hovertemplate='<b>%{x}% frequency</b><br>Number of genes: %{y}<extra></extra>'
                )
            ])
            fig.update_layout(
                title={'text': f'📊 Gene Frequency Distribution ({len(genes_under_100)} genes under 100%)', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16, 'color': 'rgb(70, 130, 180)'}},
                xaxis_title='Frequency (%)', yaxis_title='Number of Genes', height=400,
                margin=dict(l=60, r=60, t=60, b=60), plot_bgcolor='white', paper_bgcolor='white', font=dict(size=12),
                xaxis=dict(gridcolor='rgb(230, 230, 230)', showgrid=True, tickmode='array', tickvals=percentages, ticktext=[f'%{p}' for p in percentages]),
                yaxis=dict(gridcolor='rgb(230, 230, 230)', showgrid=True)
            )
            genes_under_100_content = [
                html.H5("📈 Gene Frequency Distribution", className="text-primary mb-3"),
                dcc.Graph(
                    id='gene-frequency-chart',
                    figure=fig,
                    config={'displayModeBar': True, 'displaylogo': True, 'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']}
                ),
                html.P(f"Distribution showing {len(genes_under_100)} genes across {len(percentages)} different frequency levels. Click on bars to see gene lists.",
                       className="text-muted mt-2", style={'fontSize': '12px'}),
                html.Div(id='clicked-genes-display', className="mt-3")
            ]
        else:
            genes_under_100_content = [
                html.H5("📈 Gene Frequency Distribution", className="text-primary mb-3"),
                dbc.Alert("All genes appear in 100% of the solutions.", color="info")
            ]

        combined_analysis = genes_100_content + genes_under_100_content

        # 3. Retornar el HTML de análisis común y el DF maestro
        return combined_analysis, genes_df.to_json(orient='split')


    
    # --- CALLBACK 2: CONSTRUIR LAYOUT DETALLADO (MODIFICADO CON AYUDA) ---
    @app.callback(
        Output('genes-table-container', 'children'),
        Input('genes-analysis-internal-store', 'data')
    )
    def build_detailed_layout(data_json):
        """
        Paso 2: Se activa cuando el 'genes_df' maestro está listo.
        - Se elimina 'clear_on_unhover' del dcc.Graph.
        - 🔑 CAMBIO: Popover de ayuda ahora está en inglés, incluye 'sort' y se cierra al 'clic-away'.
        """
        if not data_json:
            return dbc.Alert("No data loaded.", color="info")
            
        genes_df = pd.read_json(StringIO(data_json), orient='split')
        
        # 1. Crear opciones para el Filtro Global (sin cambios)
        front_names = genes_df['front_name'].unique()
        front_filter_options = [{'label': 'All Fronts', 'value': 'all'}] + \
                               [{'label': name, 'value': name} for name in front_names]
        
        # 2. Crear opciones para el Dropdown de Métricas (sin cambios)
        objective_options = []
        categorical_options = []
        
        categorical_cols = ['gene', 'front_name', 'unique_solution_id']
        excluded_cols = categorical_cols + ['solution_id']
        
        for col in genes_df.columns:
            if col in excluded_cols:
                continue
            if pd.api.types.is_numeric_dtype(genes_df[col]):
                objective_options.append({'label': col.replace('_', ' ').title(), 'value': col})

        categorical_options = [{'label': col.replace('_', ' ').title(), 'value': col} for col in categorical_cols]
        metric_options = categorical_options + objective_options

        # 3. Crear Columnas para la Tabla (sin cambios)
        table_columns = []
        for col in genes_df.columns:
            if col == 'solution_id':
                continue 
                
            column_name = col.replace('_', ' ').title()
            col_def = {'name': column_name, 'id': col}
            
            if col == 'front_name':
                col_def.update({'name': 'Front'})
            elif col == 'unique_solution_id':
                col_def.update({'name': 'Solution'})
            elif col == 'gene':
                col_def.update({'name': 'Gene'})
            
            if col in [o['value'] for o in objective_options]:
                col_def.update({
                    'type': 'numeric',
                    'format': {'specifier': '.3f'} if genes_df[col].dtype == 'float64' else None
                })
            
            table_columns.append(col_def)
            
        # 4. Construir el Layout
        
        # --- Sección del Gráfico (sin cambios) ---
        new_graph_section = html.Div([
            html.H5("📊 Analysis of Filtered Table Data", className="text-secondary mb-3"),
            html.P("This graph updates dynamically as you filter the table below.", className="text-muted small"),
            
            dbc.Row([
                # Columna para el Filtro Global de Frentes
                dbc.Col([
                    dbc.Label("Filter by Front:", className="fw-bold"),
                    dcc.Dropdown(
                        id='genes-global-front-filter',
                        options=front_filter_options,
                        value='all',
                        clearable=False
                    )
                ], width=12, lg=4, className="mb-2 mb-lg-0"),
                
                # Columna para el Dropdown de Métricas
                dbc.Col([
                    dbc.Label("Select metric to plot:"),
                    dcc.Dropdown(
                        id='genes-table-graph-metric-select',
                        options=metric_options,
                        value='gene'
                    )
                ], width=12, lg=5, className="mb-2 mb-lg-0"),

                # Columna para el botón de Guardar Grupo
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save Visible Group"],
                        id='save-graph-group-btn',
                        color="info",
                        size="sm",
                        className="w-100",
                        style={'display': 'block'}
                    )
                ], width=12, lg=3, className="d-flex align-items-end")

            ], className="mb-3"), # Cierre del dbc.Row
            
            dcc.Loading(
                dcc.Graph(id='genes-table-histogram')
            ),
            
        ])
        
        # --- 🔑 INICIO DEL CAMBIO: Popover de Ayuda (Inglés, Sort, Clic-Away) ---
        
        # Definición del Popover
        filter_help_popover = dbc.Popover(
            [
                dbc.PopoverHeader("Table Filtering & Sorting Help"), # <-- 🔑 CAMBIO (Inglés)
                dbc.PopoverBody([
                    html.P("You can filter or sort each column:", className="mb-2"),
                    
                    # --- 🔑 CAMBIO: Añadida sección de Sort ---
                    html.Strong("To Sort:"),
                    html.Ul([
                        html.Li("Click the arrows (▲/▼) in the column header to sort ascending or descending.")
                    ], className="mt-1 mb-3"),
                    # ---

                    html.Strong("To Filter Text Columns:"), # <-- 🔑 CAMBIO (Inglés)
                    html.Ul([
                        html.Li(["Type a value (e.g., ", html.Code("TP53"), ") for an exact match."]),
                        html.Li(["Use ", html.Code("contains ..."), " (e.g., ", html.Code("contains TP"), ") to find sub-strings."]),
                        html.Li(["Use ", html.Code("ne ..."), " or ", html.Code("!= ..."), " to exclude."]),
                    ], className="mt-1 mb-3"),
                    
                    html.Strong("To Filter Numeric Columns:"), # <-- 🔑 CAMBIO (Inglés)
                    html.Ul([
                        html.Li(["Use ", html.Code("> 0.8"), ", ", html.Code("< 10")]),
                        html.Li(["Use ", html.Code(">= 0.8"), ", ", html.Code("<= 10")]),
                        html.Li(["Use ", html.Code("= 5"), ", ", html.Code("!= 5")]),
                    ], className="mt-1 mb-3"),
                    
                    html.P("You can combine filters across multiple columns.", className="mb-0"), # <-- 🔑 CAMBIO (Inglés)
                    html.P("Use the 'Clear All Filters' button to reset.", className="mb-0") # <-- 🔑 CAMBIO (Inglés)
                ])
            ],
            id="filter-help-popover",
            target="genes-filter-help-icon", # El ID del icono
            trigger="legacy", # <-- 🔑 CAMBIO: "click" -> "legacy" para cerrar al clic-away
            placement="bottom-start",
        )
        
        # --- FIN DEL CAMBIO: Popover de Ayuda ---

        
        table = dash_table.DataTable(
            id='detailed-genes-table',
            data=genes_df.to_dict('records'),
            columns=table_columns,
            sort_action='native',
            filter_action='native',
            filter_query="",
            page_action='native',
            page_size=20,
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={
                'backgroundColor': 'rgb(70, 130, 180)',
                'color': 'white',
                'fontWeight': 'bold',
                'fontSize': '14px',
                'border': '1px solid rgb(50, 110, 160)'
            },
            style_filter={
                'backgroundColor': 'rgb(220, 235, 255)',
                'border': '1px solid rgb(7G0, 130, 180)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
            ],
            tooltip_duration=None,
        )

        # 5. Devolver el layout completo de la sección detallada
        return html.Div([
            html.Hr(),
            new_graph_section,
            html.Hr(),
            
            # --- Título de la Tabla con Icono (sin cambios) ---
            html.H5([
                "📋 Detailed Gene Table by Solution",
                html.I( 
                    id="genes-filter-help-icon", 
                    className="fa fa-question-circle ms-2", 
                    style={
                        'cursor': 'pointer', 
                        'fontSize': '16px', 
                        'color': 'var(--bs-info)' 
                    }
                )
            ], className="text-secondary mb-3 d-flex align-items-center"),
            
            filter_help_popover, # <-- Se incluye el Popover en el layout
            
            # Botón Limpiar (sin cambios)
            dbc.Row([
                dbc.Col(
                    html.Div(id='genes-table-summary-panel'),
                    width=12, lg=9, xl=10, className="mb-2 mb-lg-0"
                ),
                dbc.Col(
                    dbc.Button(
                        [html.I(className="bi bi-eraser me-2"), "Clear All Filters"],
                        id='genes-table-clear-filters-btn',
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="w-100"
                    ),
                    width=12, lg=3, xl=2,
                    className="d-flex align-items-center"
                )
            ], className="mb-3", align="center"),
            
            table
        ])
    # --- CALLBACK 3: FILTRAR TABLA (Sin Cambios) ---
    @app.callback(
        Output('detailed-genes-table', 'data'),
        Input('genes-global-front-filter', 'value'),
        State('genes-analysis-internal-store', 'data')
    )
    def filter_table_by_front(selected_front, data_json):
        # ... (código sin cambios) ...
        """
        Paso 3: Filtra el 'data' de la tabla cuando el Filtro Global cambia.
        """
        if not data_json:
            raise PreventUpdate
            
        genes_df = pd.read_json(StringIO(data_json), orient='split')
        
        if selected_front == 'all':
            return genes_df.to_dict('records')
        
        filtered_df = genes_df[genes_df['front_name'] == selected_front]
        return filtered_df.to_dict('records')
        

    # --- CALLBACK 4: MOSTRAR GENES AL CLICAR EN GRÁFICO DE FRECUENCIA (MODIFICADO) ---
    @app.callback(
        Output('clicked-genes-display', 'children'),
        [Input('gene-frequency-chart', 'clickData')],
        [State('data-store', 'data')]
    )
    def display_clicked_genes(clickData, data):
        """Display genes for clicked frequency bar, along with Add to Panel button."""
        if not clickData or not data:
            return ""

        all_solutions_list = []
        for front in data.get("fronts", []):
            if front.get("visible", True):
                all_solutions_list.extend(front["data"])

        if not all_solutions_list:
            return ""

        clicked_percentage = clickData['points'][0]['x']

        all_genes = [gene for solution in all_solutions_list for gene in solution.get('selected_genes', [])]
        gene_counts = pd.Series(all_genes).value_counts()
        total_solutions = len(all_solutions_list)
        
        genes_under_100 = gene_counts[gene_counts < total_solutions]
        gene_counts_filtered = genes_under_100

        genes_at_percentage = []
        for gene, count in gene_counts_filtered.items():
            percentage = round((count / total_solutions) * 100, 1)
            if percentage == clicked_percentage:
                genes_at_percentage.append(gene)

        if not genes_at_percentage:
            return ""

        genes_at_percentage.sort(key=lambda x: (-gene_counts[x], x))

        # --- 🔑 INICIO DEL CAMBIO (Botón <100%) ---
        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.H6(f"Genes with {clicked_percentage}% frequency", className="mb-0 text-primary"),
                    dbc.Button(
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save Group"], # Icono y texto cambiados
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': str(clicked_percentage)},
                        color="info", # Color cambiado
                        size="sm"
                    )
                ], className="d-flex align-items-center justify-content-between")
            ]),
            dbc.CardBody([
                html.P(f"Found {len(genes_at_percentage)} genes appearing in {gene_counts[genes_at_percentage[0]]} out of {total_solutions} solutions:",
                       className="text-muted mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            f"{gene} ({gene_counts[gene]})",
                            id={'type': 'add-gene-individual-btn', 'gene_name': gene, 'source': f"freq_{clicked_percentage}"},
                            color="primary",
                            size="sm",
                            className="me-2 mb-2",
                            style={'fontSize': '14px', 'padding': '8px 12px'}
                        )
                        for gene in genes_at_percentage
                    ], width=12)
                ])
            ])
        ], className="mt-3")
        # --- 🔑 FIN DEL CAMBIO (Botón <100%) ---


    # --- CALLBACK 5: ACTUALIZAR GRÁFICO Y PANEL DE RESUMEN (Sin Cambios) ---
    @app.callback(
        [Output('genes-table-histogram', 'figure'),
         Output('save-graph-group-btn', 'style'), 
         Output('genes-table-summary-panel', 'children')], 
        [Input('detailed-genes-table', 'derived_virtual_data'),
         Input('genes-table-graph-metric-select', 'value')]
    )
    def update_table_histogram_and_summary(derived_virtual_data, selected_metric):
        # ... (código sin cambios) ...
        """
        Paso 4: Actualiza el gráfico, el panel de resumen y la visibilidad del botón "Save Group".
        """
        
        default_layout = go.Layout(
            title='Filter the table below to see analysis or select a metric',
            height=400,
        )
        
        default_summary = dbc.Alert(
            "Filter the table to see summary statistics.",
            color="info",
            className="border-start border-info border-4"
        )
        
        # Estilo por defecto para el botón (oculto)
        save_btn_style = {'display': 'none'}

        if not derived_virtual_data or not selected_metric:
            return go.Figure(layout=default_layout), save_btn_style, default_summary

        filtered_df = pd.DataFrame(derived_virtual_data)

        # Calcular estadísticas (sin cambios)
        total_rows = len(filtered_df)
        unique_solutions = filtered_df['unique_solution_id'].nunique()
        unique_genes = filtered_df['gene'].nunique()

        summary_panel = dbc.Alert(
            dbc.Row([
                dbc.Col(html.Div([
                    html.Strong("Total Rows (Gene-Solution pairs): "),
                    dbc.Badge(f"{total_rows:,}", color="secondary", pill=True, className="ms-1")
                ]), width="auto", className="me-3"),
                dbc.Col(html.Div([
                    html.Strong("Unique Solutions: "),
                    dbc.Badge(f"{unique_solutions:,}", color="primary", pill=True, className="ms-1")
                ]), width="auto", className="me-3"),
                dbc.Col(html.Div([
                    html.Strong("Unique Genes: "),
                    dbc.Badge(f"{unique_genes:,}", color="success", pill=True, className="ms-1")
                ]), width="auto"),
            ], justify="start"),
            color="light",
            className="border"
        )


        if selected_metric not in filtered_df.columns:
            default_layout.title = f"Metric '{selected_metric}' not in filtered data."
            return go.Figure(layout=default_layout), save_btn_style, summary_panel
        
        metric_name = selected_metric.replace('_', ' ').title()
        
        fig = go.Figure(layout=default_layout)
        
        # --- Lógica de Gráfico Categórico (Barras) ---
        if not pd.api.types.is_numeric_dtype(filtered_df[selected_metric]):
            
            save_btn_style = {'display': 'block'}

            counts = filtered_df[selected_metric].value_counts().reset_index()
            counts.columns = [selected_metric, 'count']
            counts = counts.sort_values('count', ascending=False)

            default_items_to_show = 50
            max_range_index = min(default_items_to_show, len(counts))
            
            fig = px.bar(
                counts,
                x=selected_metric,
                y='count',
                color='count',
                color_continuous_scale='Blues',
                title=f"Counts for '{metric_name}' in Filtered Data (Top {max_range_index} shown by default)",
                custom_data=[selected_metric]
            )
            
            fig.update_layout(
                xaxis_title=metric_name,
                yaxis_title='Count',
                xaxis_tickangle=-45,
                xaxis_range=[-0.5, max_range_index - 0.5],
                xaxis_rangeslider=dict(
                    visible=True,
                    bgcolor="#EEEEEE",
                    bordercolor="#444",
                    borderwidth=2,
                    thickness=0.15
                ),
                coloraxis_showscale=False,
                margin=dict(l=60, r=60, t=60, b=60)
            )
            
            return fig, save_btn_style, summary_panel
        
        # --- Lógica de Gráfico Numérico (Histograma) ---
        else:
            # save_btn_style ya está {'display': 'none'}
            
            valid_data = filtered_df[selected_metric].dropna()
            if valid_data.empty:
                default_layout.title = f"No valid numeric data for '{metric_name}'."
                return go.Figure(layout=default_layout), save_btn_style, summary_panel
                
            counts, bin_edges = np.histogram(valid_data, bins=20)
            
            bin_data_to_plot = []
            for i in range(len(counts)):
                if counts[i] > 0:
                    bin_data_to_plot.append({
                        'count': counts[i],
                        'bin_label': f"{bin_edges[i]:.3g} - {bin_edges[i+1]:.3g}",
                        'bin_start': bin_edges[i],
                        'bin_end': bin_edges[i+1]
                    })
            
            if not bin_data_to_plot:
                default_layout.title = f"No data to plot for '{metric_name}'."
                return go.Figure(layout=default_layout), save_btn_style, summary_panel

            hist_df = pd.DataFrame(bin_data_to_plot)
            
            fig = px.bar(
                hist_df,
                x='bin_label',
                y='count',
                color='count',
                color_continuous_scale='Blues',
                title=f"Distribution of '{metric_name}' in Filtered Data",
                custom_data=['bin_start', 'bin_end', 'bin_label']
            )

            fig.update_layout(
                xaxis_title=metric_name + " (Binned)",
                yaxis_title='Frequency (count)',
                xaxis_tickangle=-45,
                xaxis_rangeslider=dict(
                    visible=True,
                    bgcolor="#EEEEEE",
                    bordercolor="#444",
                    borderwidth=2,
                    thickness=0.15
                ),
                xaxis_type='category',
                coloraxis_showscale=False,
                margin=dict(l=60, r=60, t=60, b=60)
            )
            
            return fig, save_btn_style, summary_panel


    # --- CALLBACK 6: MANEJAR INTERACCIONES DEL GRÁFICO (Sin Cambios) ---
    @app.callback(
        [Output('genes-graph-action-modal', 'is_open'),
         Output('genes-graph-modal-title', 'children'),
         Output('genes-graph-modal-body', 'children'),
         Output('genes-graph-modal-footer', 'children'),
         Output('genes-graph-temp-store', 'data')],
        [Input('genes-table-histogram', 'clickData'),
         Input('save-graph-group-btn', 'n_clicks')],
        [State('genes-table-graph-metric-select', 'value'),
         State('detailed-genes-table', 'derived_virtual_data')],
        prevent_initial_call=True
    )
    def handle_graph_interactions(clickData, group_n_clicks, selected_metric, derived_virtual_data):
        # ... (código sin cambios) ...
        """
        Paso 5: Maneja los clics en el gráfico y el botón "Save Visible Group".
        """
        
        triggered_id = ctx.triggered_id
        
        if not triggered_id or derived_virtual_data is None:
            raise PreventUpdate
            
        filtered_df = pd.DataFrame(derived_virtual_data)
        
        if filtered_df.empty:
            raise PreventUpdate

        # Componentes estándar del modal (sin cambios)
        cancel_button = dbc.Button("Cancel", id='genes-graph-modal-cancel-btn', color="secondary", className="me-2")
        confirm_button = dbc.Button("Add to Panel", id="genes-graph-modal-confirm-btn", color="primary")
        footer = html.Div([cancel_button, confirm_button])
        
        # --- Lógica para "Save Visible Group" (Opción B Categórica) ---
        if triggered_id == 'save-graph-group-btn':
            
            genes_in_group = sorted(filtered_df['gene'].unique())
            
            group_name = f"Visible Group ({selected_metric})"
            source_display = f"Visible group from '{selected_metric}' analysis"
            
            title = "Add Genes to Interest Panel"
            body = html.Div([
                html.P([html.Strong("Type: "), html.Span("🧬 Gene Group", className="text-success")]),
                html.P([html.Strong("Group Name: "), html.Code(group_name, className="text-primary")]),
                html.P([html.Strong("Source: "), html.Span(source_display, className="text-muted")]),
                html.P([html.Strong("Number of genes: "), html.Span(f"{len(genes_in_group)}")]),
                dbc.Label("Add a comment or note:", className="fw-bold mt-3"),
                dbc.Textarea(
                    id='genes-graph-modal-comment-input',
                    placeholder="e.g., 'Top genes from filtered table'...",
                    style={'height': '100px'},
                    className='mb-2',
                    value=f"Group of {len(genes_in_group)} genes from filtered table analysis."
                )
            ])
            
            temp_data = {
                'type': 'gene_set',
                'name': group_name,
                'source': source_display,
                'genes': genes_in_group,
                'count': len(genes_in_group)
            }
            
            return True, title, body, footer, temp_data

        # --- Lógica para Clic en una Barra (Opción A Categórica y Numérica) ---
        if triggered_id == 'genes-table-histogram':
            if not clickData:
                raise PreventUpdate 
            
            is_numeric = pd.api.types.is_numeric_dtype(filtered_df[selected_metric])
            
            # --- 1. Clic en Métrica Categórica (Opción A) ---
            if not is_numeric:
                clicked_category = clickData['points'][0]['customdata'][0]
                
                # Caso especial: Si la métrica es 'gene'
                if selected_metric == 'gene':
                    gene_name = clicked_category
                    source_display = "Graph click (Gene metric)"
                    
                    title = "Add Genes to Interest Panel"
                    body = html.Div([
                        html.P([html.Strong("Type: "), html.Span("🔬 Individual Gene", className="text-info")]),
                        html.P([html.Strong("Gene: "), html.Code(gene_name, className="text-primary")]),
                        html.P([html.Strong("Source: "), html.Span(source_display, className="text-muted")]),
                        dbc.Label("Add a comment or note:", className="fw-bold mt-3"),
                        dbc.Textarea(
                            id='genes-graph-modal-comment-input',
                            placeholder="e.g., 'Key gene identified in analysis'...",
                            style={'height': '100px'},
                            className='mb-2',
                            value=f"Individual gene {gene_name} from filtered table analysis."
                        )
                    ])
                    
                    temp_data = {
                        'type': 'individual_gene',
                        'gene': gene_name,
                        'source': source_display
                    }
                    
                    return True, title, body, footer, temp_data
                
                # Otro caso categórico (ej. 'front_name')
                else:
                    category_df = filtered_df[filtered_df[selected_metric] == clicked_category]
                    genes_in_category = sorted(category_df['gene'].unique())
                    
                    group_name = f"Genes from '{clicked_category}'"
                    source_display = f"Graph click ({selected_metric} = {clicked_category})"
                    
                    title = "Add Genes to Interest Panel"
                    body = html.Div([
                        html.P([html.Strong("Type: "), html.Span("🧬 Gene Group", className="text-success")]),
                        html.P([html.Strong("Group Name: "), html.Code(group_name, className="text-primary")]),
                        html.P([html.Strong("Source: "), html.Span(source_display, className="text-muted")]),
                        html.P([html.Strong("Number of genes: "), html.Span(f"{len(genes_in_category)}")]),
                        dbc.Label("Add a comment or note:", className="fw-bold mt-3"),
                        dbc.Textarea(
                            id='genes-graph-modal-comment-input',
                            placeholder="e.g., 'Genes from selected category'...",
                            style={'height': '100px'},
                            className='mb-2',
                            value=f"Group of {len(genes_in_category)} genes from category '{clicked_category}'."
                        )
                    ])

                    temp_data = {
                        'type': 'gene_set',
                        'name': group_name,
                        'source': source_display,
                        'genes': genes_in_category,
                        'count': len(genes_in_category)
                    }
                    
                    return True, title, body, footer, temp_data

            # --- 2. Clic en Métrica Numérica (Histograma) ---
            else:
                
                valid_data = filtered_df[selected_metric].dropna()
                if valid_data.empty:
                    return True, "No Data", dbc.Alert("No valid data in this bin to analyze.", color="warning"), footer, None

                try:
                    customdata = clickData['points'][0]['customdata']
                    bin_start = customdata[0]
                    bin_end = customdata[1]
                    clicked_bin_label = customdata[2]
                except (IndexError, TypeError):
                    return True, "Error", dbc.Alert("Could not read bin data.", color="danger"), footer, None

                try:
                    is_last_bin = (bin_end == valid_data.max())

                    if is_last_bin:
                         bin_data = filtered_df[
                             (filtered_df[selected_metric] >= bin_start) & 
                             (filtered_df[selected_metric] <= bin_end)
                         ]
                    else:
                        bin_data = filtered_df[
                             (filtered_df[selected_metric] >= bin_start) & 
                             (filtered_df[selected_metric] < bin_end)
                         ]
                    
                    genes_in_bin = sorted(bin_data['gene'].unique())

                    group_name = f"Genes from Bin '{clicked_bin_label}'"
                    source_display = f"Graph click ({selected_metric} bin: {clicked_bin_label})"
                    
                    title = "Add Genes to Interest Panel"
                    body = html.Div([
                        html.P([html.Strong("Type: "), html.Span("🧬 Gene Group", className="text-success")]),
                        html.P([html.Strong("Group Name: "), html.Code(group_name, className="text-primary")]),
                        html.P([html.Strong("Source: "), html.Span(source_display, className="text-muted")]),
                        html.P([html.Strong("Number of genes: "), html.Span(f"{len(genes_in_bin)}")]),
                        dbc.Label("Add a comment or note:", className="fw-bold mt-3"),
                        dbc.Textarea(
                            id='genes-graph-modal-comment-input',
                            placeholder="e.g., 'High-performing genes'...",
                            style={'height': '100px'},
                            className='mb-2',
                            value=f"Group of {len(genes_in_bin)} genes from {selected_metric} bin [{bin_start:.3g}, {bin_end:.3g}]."
                        )
                    ])

                    temp_data = {
                        'type': 'gene_set',
                        'name': group_name,
                        'source': source_display,
                        'genes': genes_in_bin,
                        'count': len(genes_in_bin)
                    }
                    
                    return True, title, body, footer, temp_data

                except Exception as e:
                    title = "Error"
                    body = dbc.Alert(f"Error processing bin click: {e}", color="danger")
                    footer = html.Div([cancel_button])
                    return True, title, body, footer, None

        return False, "", "", "", None

    
    # --- CALLBACK 7: CERRAR MODAL CON BOTÓN "CANCELAR" (MODIFICADO) ---
    @app.callback(
        [Output('genes-graph-action-modal', 'is_open', allow_duplicate=True),
         Output('genes-table-histogram', 'clickData', allow_duplicate=True)], # <--- 🔑 Output de reseteo
        Input('genes-graph-modal-cancel-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_genes_modal_on_cancel(n_clicks):
        """
        Paso 6: Cierra el modal si se hace clic en "Cancelar".
        - CORRECCIÓN: Resetea clickData a None para permitir clics repetidos.
        """
        if n_clicks:
            return False, None # Cierra el modal Y resetea el clickData
        raise PreventUpdate

    
    # --- CALLBACK 8: GUARDAR EN EL PANEL DESDE EL NUEVO MODAL (MODIFICADO) ---
    @app.callback(
        [Output('interest-panel-store', 'data', allow_duplicate=True),
         Output('genes-graph-action-modal', 'is_open', allow_duplicate=True),
         Output('genes-graph-temp-store', 'data', allow_duplicate=True),
         Output('genes-table-histogram', 'clickData', allow_duplicate=True)], # <--- 🔑 Output de reseteo
        Input('genes-graph-modal-confirm-btn', 'n_clicks'),
        [State('genes-graph-temp-store', 'data'),
         State('genes-graph-modal-comment-input', 'value'),
         State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def save_from_graph_modal_to_panel(n_clicks, temp_data, comment, current_items):
        """
        Paso 7: Guarda el ítem (gen o grupo) del modal del gráfico en el panel de interés.
        - CORRECCIÓN: Resetea clickData a None para permitir clics repetidos.
        """
        
        # Valor de reseteo para clickData
        click_data_reset = None

        if n_clicks is None or n_clicks == 0:
            raise PreventUpdate
            
        if not temp_data:
            return dash.no_update, False, None, click_data_reset
            
        if current_items is None:
            current_items = []
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Caso 1: Guardar un Grupo de Genes (gene_set)
        if temp_data.get('type') == 'gene_set':
            new_item = {
                'type': 'gene_set',
                'id': f"gene_set_{len(current_items)}_{timestamp}",
                'name': temp_data['name'],
                'comment': comment or "",
                'data': temp_data,
                'timestamp': timestamp
            }
            return current_items + [new_item], False, None, click_data_reset

        # Caso 2: Guardar un Gen Individual
        elif temp_data.get('type') == 'individual_gene':
            new_item = {
                'type': 'individual_gene',
                'id': f"gene_{temp_data['gene']}_{timestamp}",
                'name': f"Gene: {temp_data['gene']}",
                'comment': comment or "",
                'data': temp_data,
                'timestamp': timestamp
            }
            return current_items + [new_item], False, None, click_data_reset

        # Si algo falla
        return dash.no_update, False, None, click_data_reset

    
    # --- CALLBACK 9: LIMPIAR FILTRO GLOBAL (Sin Cambios) ---
    @app.callback(
        [Output('genes-global-front-filter', 'value'),
         Output('detailed-genes-table', 'filter_query')], 
        Input('genes-table-clear-filters-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_global_filter(n_clicks):
        """
        Paso 8: Resetea el dropdown de filtro global y los filtros internos
        de la tabla. El gráfico se actualizará automáticamente.
        """
        if n_clicks:
            # Resetea el filtro global y la query de filtros de la tabla
            return 'all', ""
        raise PreventUpdate

    
    # --- 🔑 INICIO DEL CAMBIO (NUEVO CALLBACK) ---
    # --- CALLBACK 10: MANEJAR CIERRE DE MODAL POR 'X' O BACKDROP ---
    @app.callback(
        Output('genes-table-histogram', 'clickData', allow_duplicate=True),
        Input('genes-graph-action-modal', 'is_open'),
        State('genes-graph-action-modal', 'id'), # Usamos un State para que este callback tenga menor prioridad
        prevent_initial_call=True
    )
    def reset_clickdata_on_modal_close(is_open, modal_id):
        """
        Paso 9: Escucha el estado 'is_open' del modal. Si se cierra (is_open=False)
        por cualquier razón, resetea el clickData del gráfico.
        Esto soluciona el bug del clic repetido para la 'X' y el backdrop.
        """
        if not is_open:
            # Si el modal se cierra, resetea clickData
            return None
        # Si se está abriendo (is_open=True), no hagas nada
        raise PreventUpdate
    # --- 🔑 FIN DEL CAMBIO (NUEVO CALLBACK) ---