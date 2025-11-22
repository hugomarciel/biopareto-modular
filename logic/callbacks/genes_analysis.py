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

    # --- CALLBACK 1: PROCESAR DATOS Y ANÁLISIS COMÚN (SIN CAMBIOS) ---
    @app.callback(
        [Output('common-genes-analysis', 'children'),
         Output('genes-analysis-internal-store', 'data')],
        Input('data-store', 'data')
    )
    def prepare_data_and_common_analysis(data):
        if not data:
            return "", None

        all_solutions_list = []
        available_objectives = []
        genes_data = []

        for front in data.get("fronts", []):
            if not front.get("visible", True):
                continue
                
            front_name = front.get("name", "Unknown Front")
            solutions_data = front.get("data", [])
            all_solutions_list.extend(solutions_data)

            if not solutions_data:
                continue

            if not available_objectives:
                available_objectives = data.get('explicit_objectives', [])

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

        all_genes = [gene for solution in all_solutions_list for gene in solution.get('selected_genes', [])]
        gene_counts = pd.Series(all_genes).value_counts()
        total_solutions = len(all_solutions_list)
        genes_100_percent = gene_counts[gene_counts == total_solutions]
        genes_under_100 = gene_counts[gene_counts < total_solutions]

        genes_100_content = []
        if len(genes_100_percent) > 0:
            genes_100_content = [
                html.Div([
                    html.H5("🎯 Genes Present in 100% of Solutions", className="text-success mb-3"),
                    dbc.Button(
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save 100% Group"],
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': '100pct'},
                        color="info",
                        size="sm"
                    )
                ], className="d-flex justify-content-between align-items-center mb-3"),
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
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save 100% Group"],
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': '100pct'},
                        color="info",
                        size="sm",
                        style={'display': 'none'}
                    )
                ], className="d-flex justify-content-between align-items-center mb-3"),
                dbc.Alert("No genes appear in 100% of the solutions.", color="info", className="mb-4")
            ]
        
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
                xaxis=dict(gridcolor='rgb(230, 230, 230)', showgrid=True, tickmode='array', tickvals=percentages, ticktext=[f'{p}%' for p in percentages]),
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

        return combined_analysis, genes_df.to_json(orient='split')


    # --- CALLBACK 2: CONSTRUIR LAYOUT DETALLADO (CORREGIDO: TIPO DE LOADING) ---
    # --- CALLBACK 2: CONSTRUIR LAYOUT DETALLADO (CORREGIDO: Clean Solution Name) ---
    @app.callback(
        Output('genes-table-container', 'children'),
        Input('genes-analysis-internal-store', 'data')
    )
    def build_detailed_layout(data_json):
        if not data_json:
            return dbc.Alert("No data loaded.", color="info")
            
        genes_df = pd.read_json(StringIO(data_json), orient='split')
        
        front_names = genes_df['front_name'].unique()
        front_filter_options = [{'label': 'All Fronts', 'value': 'all'}] + \
                               [{'label': name, 'value': name} for name in front_names]
        
        objective_options = []
        categorical_options = []
        
        # Definimos columnas categóricas. Mantenemos 'unique_solution_id' aquí para que
        # el dropdown del gráfico la siga reconociendo como opción válida si se desea.
        categorical_cols = ['gene', 'front_name', 'unique_solution_id']
        excluded_cols = categorical_cols + ['solution_id']
        
        for col in genes_df.columns:
            if col in excluded_cols:
                continue
            if pd.api.types.is_numeric_dtype(genes_df[col]):
                objective_options.append({'label': col.replace('_', ' ').title(), 'value': col})

        categorical_options = [{'label': col.replace('_', ' ').title(), 'value': col} for col in categorical_cols]
        metric_options = categorical_options + objective_options

        table_columns = []
        for col in genes_df.columns:
            # --- 💡 CAMBIO 1: Ocultar la columna combinada (Redundante) ---
            # Aunque la ocultamos de la vista, los datos siguen en el 'data' de la tabla
            # por lo que el gráfico podrá seguir usándola internamente.
            if col == 'unique_solution_id':
                continue 
                
            column_name = col.replace('_', ' ').title()
            
            # Configuración base con Toggle habilitado
            col_def = {'name': column_name, 'id': col, 'hideable': True}
            
            # Personalización de nombres de cabecera
            if col == 'front_name':
                col_def.update({'name': 'Front'})
            
            # --- 💡 CAMBIO 2: Mostrar el ID corto pero llamarlo 'Solution' ---
            elif col == 'solution_id':
                col_def.update({'name': 'Solution'})
                
            elif col == 'gene':
                col_def.update({'name': 'Gene', 'presentation': 'markdown'}) 
            
            # Formateo numérico
            if col in [o['value'] for o in objective_options]:
                col_def.update({
                    'type': 'numeric',
                    'format': {'specifier': '.3f'} if genes_df[col].dtype == 'float64' else None
                })
            
            table_columns.append(col_def)
            
        new_graph_section = html.Div([
            html.H5("📊 Analysis of Filtered Table Data", className="text-secondary mb-3"),
            html.P("This graph updates dynamically as you filter the table below.", className="text-muted small"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Filter by Front:", className="fw-bold"),
                    dcc.Dropdown(
                        id='genes-global-front-filter',
                        options=front_filter_options,
                        value='all',
                        clearable=False
                    )
                ], width=12, lg=4, className="mb-2 mb-lg-0"),
                
                dbc.Col([
                    dbc.Label("Select metric to plot:"),
                    dcc.Dropdown(
                        id='genes-table-graph-metric-select',
                        options=metric_options,
                        value='gene'
                    )
                ], width=12, lg=5, className="mb-2 mb-lg-0"),

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

            ], className="mb-3"),
            
            dcc.Loading(
                id="loading-genes-histogram",
                type="default",
                children=dcc.Graph(id='genes-table-histogram')
            ),
        ])
        
        # Popover de ayuda (sin cambios)
        filter_help_popover = dbc.Popover(
            [
                dbc.PopoverHeader("Table Filtering & Sorting Help"), 
                dbc.PopoverBody([
                    html.P("You can filter and sort each column using filters in the first row of the table:", className="mb-2"),
                    html.Strong("To Sort:"),
                    html.Ul([html.Li("Click the arrows (▲/▼) in the column header to sort ascending or descending.")], className="mt-1 mb-3"),
                    html.Strong("To Filter Text Columns:"), 
                    html.Ul([
                        html.Li(["Type a value (e.g., ", html.Code("TP53"), ") for an exact match."]),
                        html.Li(["Use ", html.Code("contains ..."), " (e.g., ", html.Code("contains TP"), ") to find sub-strings."]),
                        html.Li(["Use ", html.Code("ne ..."), " or ", html.Code("!= ..."), " to exclude."]),
                    ], className="mt-1 mb-3"),
                    html.Strong("To Filter Numeric Columns:"), 
                    html.Ul([
                        html.Li(["Use ", html.Code("> 0.8"), ", ", html.Code("<= 10")]),
                        html.Li(["Use ", html.Code("= 5"), " (ideal for integers)."]),
                        html.Li(["For decimals (e.g., 0.089), it's safer to use ranges: ", html.Code("> 0.0885"), " or ", html.Code("< 0.0895")]),
                    ], className="mt-1 mb-3"),
                    html.P("You can combine filters across multiple columns.", className="mb-0"), 
                    html.P("Use the 'Clear All Filters' button to reset.", className="mb-0") 
                ])
            ],
            id="filter-help-popover",
            target="genes-filter-help-icon",
            trigger="legacy", 
            placement="bottom-start",
        )
        
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
                'border': '1px solid rgb(70, 130, 180)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
            ],
            tooltip_duration=None,
        )

        return html.Div([
            html.Hr(),
            new_graph_section,
            html.Hr(),
            html.H5([
                "📋 Detailed Gene Table by Solution",
                html.I( 
                    id="genes-filter-help-icon", 
                    className="fa fa-question-circle ms-2", 
                    style={'cursor': 'pointer', 'fontSize': '16px', 'color': 'var(--bs-info)'}
                )
            ], className="text-secondary mb-3 d-flex align-items-center"),
            filter_help_popover,
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        id="loading-summary-panel",
                        type="circle", 
                        color="#0d6efd", 
                        children=html.Div(id='genes-table-summary-panel')
                    ),
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
    

    # --- CALLBACK 3: FILTRAR TABLA (SIN CAMBIOS) ---
    @app.callback(
        Output('detailed-genes-table', 'data'),
        Input('genes-global-front-filter', 'value'),
        State('genes-analysis-internal-store', 'data')
    )
    def filter_table_by_front(selected_front, data_json):
        if not data_json:
            raise PreventUpdate
            
        genes_df = pd.read_json(StringIO(data_json), orient='split')
        
        if selected_front == 'all':
            return genes_df.to_dict('records')
        
        filtered_df = genes_df[genes_df['front_name'] == selected_front]
        return filtered_df.to_dict('records')
        

    # --- CALLBACK 4: MOSTRAR GENES AL CLICAR EN GRÁFICO DE FRECUENCIA (SIN CAMBIOS) ---
    @app.callback(
        Output('clicked-genes-display', 'children'),
        [Input('gene-frequency-chart', 'clickData')],
        [State('data-store', 'data')]
    )
    def display_clicked_genes(clickData, data):
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
                    html.H6(f"Genes with {clicked_percentage}% frequency", className="mb-0 text-primary"),
                    dbc.Button(
                        [html.I(className="bi bi-bookmark-plus me-2"), "Save Group"],
                        id={'type': 'genes-tab-add-gene-group-btn', 'index': str(clicked_percentage)},
                        color="info",
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


    # --- CALLBACK 5: ACTUALIZAR GRÁFICO Y PANEL DE RESUMEN (MODIFICADO: TAMAÑO DE TARJETAS) ---
    @app.callback(
        [Output('genes-table-histogram', 'figure'),
        Output('save-graph-group-btn', 'style'), 
        Output('genes-table-summary-panel', 'children')], 
        [Input('detailed-genes-table', 'derived_virtual_data'),
        Input('genes-table-graph-metric-select', 'value'),
        Input('genes-analysis-internal-store', 'data')], 
        [State('genes-analysis-internal-store', 'data')] 
    )
    def update_table_histogram_and_summary(derived_virtual_data, selected_metric, internal_store_data_input, internal_store_data_state):
        
        default_layout = go.Layout(
            title='Filter the table below to see analysis or select a metric',
            height=400,
        )
        
        # Resumen por defecto vacío, se llena luego
        default_summary = dbc.Alert("Loading statistics...", color="light")
        
        save_btn_style = {'display': 'none'}
        
        final_df = None
        
        if internal_store_data_state:
            try:
                full_genes_df = pd.read_json(StringIO(internal_store_data_state), orient='split')
            except Exception as e:
                print(f"Error reading internal store for graph update: {e}")
                return go.Figure(layout=default_layout), save_btn_style, default_summary

            if derived_virtual_data is not None and len(derived_virtual_data) > 0:
                final_df = pd.DataFrame(derived_virtual_data)
            elif full_genes_df is not None and not full_genes_df.empty:
                final_df = full_genes_df
            
        if final_df is None or final_df.empty or not selected_metric:
            if derived_virtual_data is not None and len(derived_virtual_data) == 0:
                layout_empty = go.Layout(
                    title='No data matches the current filter selection.',
                    height=400,
                )
                return go.Figure(layout=layout_empty), save_btn_style, dbc.Alert("No data matching filters.", color="warning")

            return go.Figure(layout=default_layout), save_btn_style, default_summary

        total_rows = len(final_df)
        unique_solutions = final_df['unique_solution_id'].nunique()
        unique_genes = final_df['gene'].nunique()

        # 💡 MODIFICACIÓN: Reducción del tamaño del icono (fs-1 -> fs-4) y del número (H3 -> H4/fs-3)
        summary_panel = dbc.Row([
            # Card 1: Total Rows
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    # Icono más pequeño
                    html.Div(html.I(className="bi bi-list-columns fs-4 text-secondary"), className="me-3"),
                    html.Div([
                        # Número más compacto
                        html.H4(f"{total_rows:,}", className="mb-0 text-secondary fw-bold fs-3"),
                        html.Small("Total Rows (Gene-Solution)", className="text-muted fw-bold text-uppercase", style={'fontSize': '0.7rem'})
                    ])
                ], className="d-flex align-items-center")
            ]), className="h-100 shadow-sm border-start border-secondary border-5"), width=12, md=4, className="mb-2"),
            
            # Card 2: Unique Solutions
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    # Icono más pequeño
                    html.Div(html.I(className="bi bi-diagram-3-fill fs-4 text-primary"), className="me-3"),
                    html.Div([
                        # Número más compacto
                        html.H4(f"{unique_solutions:,}", className="mb-0 text-primary fw-bold fs-3"),
                        html.Small("Unique Solutions", className="text-muted fw-bold text-uppercase", style={'fontSize': '0.7rem'})
                    ])
                ], className="d-flex align-items-center")
            ]), className="h-100 shadow-sm border-start border-primary border-5"), width=12, md=4, className="mb-2"),

            # Card 3: Unique Genes
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    # Icono más pequeño
                    html.Div(html.I(className="bi bi-dna fs-4 text-success"), className="me-3"),
                    html.Div([
                        # Número más compacto
                        html.H4(f"{unique_genes:,}", className="mb-0 text-success fw-bold fs-3"),
                        html.Small("Unique Genes", className="text-muted fw-bold text-uppercase", style={'fontSize': '0.7rem'})
                    ])
                ], className="d-flex align-items-center")
            ]), className="h-100 shadow-sm border-start border-success border-5"), width=12, md=4, className="mb-2"),
        ])

        if selected_metric not in final_df.columns:
            default_layout.title = f"Metric '{selected_metric}' not in data."
            return go.Figure(layout=default_layout), save_btn_style, summary_panel
        
        metric_name = selected_metric.replace('_', ' ').title()
        
        if not pd.api.types.is_numeric_dtype(final_df[selected_metric]):
            
            save_btn_style = {'display': 'block'}

            counts = final_df[selected_metric].value_counts().reset_index()
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
        
        else:
            valid_data = final_df[selected_metric].dropna()
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


    # --- CALLBACK 6: MANEJAR INTERACCIONES DEL GRÁFICO (SIN CAMBIOS) ---
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
        """
        Maneja interacciones.
        🔑 CAMBIO: Soporte especial para 'unique_solution_id' como solución individual.
        """
        
        triggered_id = ctx.triggered_id
        
        if not triggered_id or derived_virtual_data is None:
            raise PreventUpdate
            
        filtered_df = pd.DataFrame(derived_virtual_data)
        
        if filtered_df.empty:
            raise PreventUpdate

        cancel_button = dbc.Button("Cancel", id='genes-graph-modal-cancel-btn', color="secondary", className="me-2")
        confirm_button = dbc.Button("Add to Panel", id="genes-graph-modal-confirm-btn", color="primary")
        footer = html.Div([cancel_button, confirm_button])
        
        # --- Opción B: Guardar Grupo Visible (Sin cambios) ---
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

        # --- Opción A: Clic en el Gráfico ---
        if triggered_id == 'genes-table-histogram':
            if not clickData:
                raise PreventUpdate 
            
            is_numeric = pd.api.types.is_numeric_dtype(filtered_df[selected_metric])
            
            # --- 1. Clic en Métrica Categórica ---
            if not is_numeric:
                clicked_category = clickData['points'][0]['customdata'][0]
                
                # Caso 1.1: Gen Individual
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
                
                # 🔑 Caso 1.2: Solución Única (CAMBIO NUEVO)
                elif selected_metric == 'unique_solution_id':
                    full_sol_id_str = clicked_category # e.g. "Front 1 - sol_0"
                    
                    # Filtrar para obtener datos solo de esta solución
                    sol_df = filtered_df[filtered_df['unique_solution_id'] == full_sol_id_str]
                    
                    if sol_df.empty:
                         return True, "Error", dbc.Alert("Could not find solution data.", color="danger"), footer, None

                    # Extraer datos
                    genes_in_sol = sorted(sol_df['gene'].unique())
                    front_name = sol_df['front_name'].iloc[0]
                    sol_id = sol_df['solution_id'].iloc[0]
                    
                    # Intentar extraer objetivos (columnas numéricas que no son gene, id, etc)
                    ignored_cols = ['gene', 'front_name', 'unique_solution_id', 'solution_id']
                    objectives_data = {col: sol_df[col].iloc[0] for col in sol_df.columns if col not in ignored_cols}
                    
                    # Formatear objetivos para mostrar
                    objs_display = ", ".join([f"{k}: {v}" for k, v in objectives_data.items()])
                    
                    title = "Add Solution to Interest Panel"
                    body = html.Div([
                        html.P([html.Strong("Type: "), html.Span("💎 Single Solution", className="text-primary")]),
                        html.P([html.Strong("Solution: "), html.Code(f"{sol_id} ({front_name})")]),
                        html.P([html.Strong("Genes: "), html.Span(f"{len(genes_in_sol)}")]),
                        html.P([html.Strong("Data: "), html.Span(objs_display, className="small text-muted")]),
                        dbc.Label("Add a comment or note:", className="fw-bold mt-3"),
                        dbc.Textarea(
                            id='genes-graph-modal-comment-input',
                            placeholder="e.g., 'Solution found via gene analysis'...",
                            style={'height': '100px'},
                            className='mb-2',
                            value=f"Solution {sol_id} selected from table analysis. {objs_display}"
                        )
                    ])
                    
                    # Preparamos un objeto tipo 'solution'
                    temp_data = {
                        'type': 'solution',
                        'front_name': front_name,
                        'solution_id': sol_id,
                        'unique_id': full_sol_id_str,
                        'selected_genes': genes_in_sol,
                        # Guardamos los objetivos extraídos
                        'objectives_data': objectives_data 
                    }
                    
                    return True, title, body, footer, temp_data

                # Caso 1.3: Grupo Genérico (e.g., 'front_name')
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

    
    # --- CALLBACK 7: CERRAR MODAL CON BOTÓN "CANCELAR" (SIN CAMBIOS) ---
    @app.callback(
        [Output('genes-graph-action-modal', 'is_open', allow_duplicate=True),
         Output('genes-table-histogram', 'clickData', allow_duplicate=True)], 
        Input('genes-graph-modal-cancel-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def close_genes_modal_on_cancel(n_clicks):
        if n_clicks:
            return False, None
        raise PreventUpdate

    
    # --- CALLBACK 8: GUARDAR EN EL PANEL DESDE EL NUEVO MODAL (SIN CAMBIOS EN LÓGICA) ---
    @app.callback(
        [Output('interest-panel-store', 'data', allow_duplicate=True),
         Output('genes-graph-action-modal', 'is_open', allow_duplicate=True),
         Output('genes-graph-temp-store', 'data', allow_duplicate=True),
         Output('genes-table-histogram', 'clickData', allow_duplicate=True)], 
        Input('genes-graph-modal-confirm-btn', 'n_clicks'),
        [State('genes-graph-temp-store', 'data'),
         State('genes-graph-modal-comment-input', 'value'),
         State('interest-panel-store', 'data')],
        prevent_initial_call=True
    )
    def save_from_graph_modal_to_panel(n_clicks, temp_data, comment, current_items):
        """
        Guarda el ítem.
        """
        
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

        # Caso 3: Guardar una Solución
        elif temp_data.get('type') == 'solution':
            sol_data_struct = {
                'solution_id': temp_data['solution_id'],
                'front_name': temp_data['front_name'],
                'unique_id': temp_data['unique_id'],
                'selected_genes': temp_data['selected_genes'],
                **temp_data.get('objectives_data', {})
            }

            new_item = {
                'type': 'solution',
                'id': f"sol_{temp_data['solution_id']}_{timestamp}",
                'name': f"{temp_data['solution_id']} (from {temp_data['front_name']})",
                'comment': comment or "",
                'data': sol_data_struct,
                'timestamp': timestamp
            }
            return current_items + [new_item], False, None, click_data_reset

        return dash.no_update, False, None, click_data_reset

    
    # --- CALLBACK 9: LIMPIAR FILTRO GLOBAL (SIN CAMBIOS) ---
    @app.callback(
        [Output('genes-global-front-filter', 'value'),
         Output('detailed-genes-table', 'filter_query')], 
        Input('genes-table-clear-filters-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_global_filter(n_clicks):
        if n_clicks:
            return 'all', ""
        raise PreventUpdate

    
    # --- CALLBACK 10: MANEJAR CIERRE DE MODAL POR 'X' O BACKDROP (SIN CAMBIOS) ---
    @app.callback(
        Output('genes-table-histogram', 'clickData', allow_duplicate=True),
        Input('genes-graph-action-modal', 'is_open'),
        State('genes-graph-action-modal', 'id'),
        prevent_initial_call=True
    )
    def reset_clickdata_on_modal_close(is_open, modal_id):
        if not is_open:
            return None
        raise PreventUpdate