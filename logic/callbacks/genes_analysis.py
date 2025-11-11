# logic/callbacks/genes_analysis.py

import dash
from dash import Output, Input, State, dcc, html, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from io import StringIO # <-- 1. IMPORTAR STRINGIO

def register_genes_analysis_callbacks(app):

    # --- CALLBACK 1: PROCESAR DATOS Y ANÁLISIS COMÚN (Sin Cambios) ---
    @app.callback(
        [Output('common-genes-analysis', 'children'),
         Output('genes-analysis-internal-store', 'data')],
        Input('data-store', 'data')
    )
    def prepare_data_and_common_analysis(data):
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

        # --- Contenido de Genes al 100% (sin cambios) ---
        genes_100_content = []
        if len(genes_100_percent) > 0:
            genes_100_content = [
                html.Div([
                    html.H5("🎯 Genes Present in 100% of Solutions", className="text-success mb-3", style={'display': 'inline-block'}),
                    dbc.Button(
                        [html.I(className="bi bi-plus-circle me-2"), "Add group to Interest Panel"],
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': '100pct'},
                        color="success",
                        size="sm",
                        className="ms-3",
                        style={'fontSize': '0.85rem'}
                    )
                ], className="d-flex align-items-center mb-3"),
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
                html.H5("🎯 Genes Present in 100% of Solutions", className="text-success mb-3"),
                dbc.Button(
                    [html.I(className="bi bi-plus-circle me-2"), "Add group to Interest Panel"],
                    id={'type': 'genes-tab-add-gene-group-btn', 'index': '100pct'},
                    color="success",
                    size="sm",
                    className="ms-3",
                    style={'display': 'none'}
                ),
                dbc.Alert("No genes appear in 100% of the solutions.", color="info", className="mb-4")
            ]
        
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

    
   # logic/callbacks/genes_analysis.py

    # --- CALLBACK 2: CONSTRUIR LAYOUT DETALLADO (MODIFICADO) ---
    @app.callback(
        Output('genes-table-container', 'children'),
        Input('genes-analysis-internal-store', 'data')
    )
    def build_detailed_layout(data_json):
        """
        Paso 2: Se activa cuando el 'genes_df' maestro está listo.
        - Construye el layout HTML para la sección detallada, incluyendo el Filtro Global.
        - Prepara la tabla y el gráfico con las columnas correctas.
        """
        if not data_json:
            return dbc.Alert("No data loaded.", color="info")
            
        genes_df = pd.read_json(StringIO(data_json), orient='split')
        
        # 1. Crear opciones para el Filtro Global
        front_names = genes_df['front_name'].unique()
        front_filter_options = [{'label': 'All Fronts', 'value': 'all'}] + \
                               [{'label': name, 'value': name} for name in front_names]
        
        # 2. Crear opciones para el Dropdown de Métricas
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

        # 3. Crear Columnas para la Tabla
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
        
        # --- 🔑 INICIO DEL CAMBIO ---
        
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
                ], width=12, md=6),
                
                # Columna para el Dropdown de Métricas
                dbc.Col([
                    dbc.Label("Select metric to plot:"),
                    dcc.Dropdown(
                        id='genes-table-graph-metric-select',
                        options=metric_options, 
                        value='gene' 
                    )
                ], width=12, md=6)
            ], className="mb-3"), # Cierre del dbc.Row
            
            dcc.Loading(
                dcc.Graph(id='genes-table-histogram')
            )
        ])
        
        # --- 🔑 FIN DEL CAMBIO ---
        
        
        table = dash_table.DataTable(
            id='detailed-genes-table', 
            data=genes_df.to_dict('records'), 
            columns=table_columns, 
            sort_action='native',
            filter_action='native',
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
                'border': '1px solid rgb(70, 130, 180)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
            ],
            tooltip_duration=None, 
        )

        # 5. Devolver el layout completo de la sección detallada
        # (El filtro global ya no se pone aquí)
        return html.Div([
            html.Hr(),
            new_graph_section, 
            html.Hr(),
            html.H5("📋 Detailed Gene Table by Solution", className="text-secondary mb-3"),
            table 
        ])
    
    # --- CALLBACK 3: FILTRAR TABLA (MODIFICADO) ---
    @app.callback(
        Output('detailed-genes-table', 'data'),
        Input('genes-global-front-filter', 'value'),
        State('genes-analysis-internal-store', 'data')
    )
    def filter_table_by_front(selected_front, data_json):
        """
        Paso 3: Filtra el 'data' de la tabla cuando el Filtro Global cambia.
        """
        if not data_json:
            raise PreventUpdate
            
        # --- 🔑 CAMBIO 3: USAR STRINGIO ---
        genes_df = pd.read_json(StringIO(data_json), orient='split')
        
        if selected_front == 'all':
            return genes_df.to_dict('records')
        
        filtered_df = genes_df[genes_df['front_name'] == selected_front]
        return filtered_df.to_dict('records')
        

    # 4. Callback para mostrar los genes al hacer clic en una barra del gráfico (Sin Cambios)
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

        return dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.H6(f"Genes with {clicked_percentage}% frequency", className="mb-0 text-primary", style={'display': 'inline-block'}),
                    dbc.Button(
                        [html.I(className="bi bi-plus-circle me-2"), "Add group to Interest Panel"],
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': str(clicked_percentage)},
                        color="primary",
                        size="sm",
                        className="ms-3",
                        style={'fontSize': '0.8rem'}
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


    # --- CALLBACK 5: ACTUALIZAR GRÁFICO (MODIFICADO) ---
    @app.callback(
        Output('genes-table-histogram', 'figure'),
        [Input('detailed-genes-table', 'derived_virtual_data'),
         Input('genes-table-graph-metric-select', 'value')]
    )
    def update_table_histogram(derived_virtual_data, selected_metric):
        """
        Paso 4: Actualiza el gráfico interactivo.
        """
        
        default_layout = go.Layout(
            title='Filter the table below to see analysis or select a metric',
            height=400,
            #plot_bgcolor='lightgray', # <-- Fondo gris
            #paper_bgcolor='lightgray' # <-- Fondo gris
        )
        
        if not derived_virtual_data or not selected_metric:
            return go.Figure(layout=default_layout)

        filtered_df = pd.DataFrame(derived_virtual_data)

        if selected_metric not in filtered_df.columns:
            default_layout.title = f"Metric '{selected_metric}' not in filtered data."
            return go.Figure(layout=default_layout)
        
        metric_name = selected_metric.replace('_', ' ').title()
        
        fig = go.Figure(layout=default_layout)
        
        # --- Lógica de Gráfico Categórico (Barras) ---
        if not pd.api.types.is_numeric_dtype(filtered_df[selected_metric]):
            
            counts = filtered_df[selected_metric].value_counts().reset_index()
            counts.columns = [selected_metric, 'count']
            counts = counts.sort_values('count', ascending=False) 

            default_items_to_show = 50
            max_range_index = min(default_items_to_show, len(counts))
            
            # --- 🔑 REVERSIÓN DE LÓGICA DE COLOR ---
            fig = px.bar(
                counts, 
                x=selected_metric, 
                y='count',
                color='count', # <-- DEVUELTO A 'count'
                color_continuous_scale='Blues', # <-- DEVUELTO A 'Blues'
                title=f"Counts for '{metric_name}' in Filtered Data (Top {max_range_index} shown by default)"
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
                coloraxis_showscale=False # Ocultar la barra de color sigue siendo buena idea
            )
        
        # --- Lógica de Gráfico Numérico (Histograma) ---
        else:
            valid_data = filtered_df[selected_metric].dropna()
            if valid_data.empty:
                default_layout.title = f"No valid numeric data for '{metric_name}'."
                return go.Figure(layout=default_layout)
                
            counts, bin_edges = np.histogram(valid_data, bins=20) 
            
            # Formato de etiqueta corregido para evitar el error '1-0.81'
            bin_labels = [f"{bin_edges[i]:.3g} - {bin_edges[i+1]:.3g}" for i in range(len(counts))]
            
            hist_df = pd.DataFrame({
                'count': counts,
                'bin_label': bin_labels
            })
            hist_df = hist_df[hist_df['count'] > 0]

            # --- 🔑 REVERSIÓN DE LÓGICA DE COLOR ---
            fig = px.bar(
                hist_df,
                x='bin_label', 
                y='count',
                color='count', # <-- DEVUELTO A 'count'
                color_continuous_scale='Blues', # <-- DEVUELTO A 'Blues'
                title=f"Distribution of '{metric_name}' in Filtered Data"
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
                coloraxis_showscale=False # Ocultar la barra de color
            )
        
        # --- Layout Común ---
        fig.update_layout(
            margin=dict(l=60, r=60, t=60, b=60),
            #plot_bgcolor='lightgray', # <-- Fondo gris
            #paper_bgcolor='lightgray' # <-- Fondo gris
        )
        return fig