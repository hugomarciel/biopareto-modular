# logic/callbacks/genes_analysis.py

import dash
from dash import Output, Input, State, dcc, html, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def register_genes_analysis_callbacks(app):

    # 1. Callback para actualizar la tabla y el análisis de frecuencia de genes
    @app.callback(
        [Output('genes-table-container', 'children'),
         Output('common-genes-analysis', 'children')],
        Input('data-store', 'data')
    )
    def update_genes_table(data):
        """Actualizar tabla de genes con separación de grupos y generar gráfico de frecuencia"""
        if not data:
            return "", ""

        # Handle data structure
        all_solutions_list = []
        for front in data.get("fronts", []):
            if front.get("visible", True):
                all_solutions_list.extend(front["data"])

        if not all_solutions_list:
            return "", ""

        # Calcular frecuencias de genes
        all_genes = [gene for solution in all_solutions_list for gene in solution.get('selected_genes', [])]
        gene_counts = pd.Series(all_genes).value_counts()
        total_solutions = len(all_solutions_list)

        genes_100_percent = gene_counts[gene_counts == total_solutions]
        genes_under_100 = gene_counts[gene_counts < total_solutions]

        # --- Contenido de Genes al 100% ---
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
        
        # --- Contenido de Distribución de Frecuencia (Gráfico y Display) ---
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

            # Crear gráfico de barras con porcentajes exactos
            fig = go.Figure(data=[
                go.Bar(
                    x=percentages,
                    y=gene_counts_per_percentage,
                    marker=dict(
                        color='rgb(70, 130, 180)',
                        line=dict(color='rgb(50, 110, 160)', width=1)
                    ),
                    text=gene_counts_per_percentage,
                    textposition='outside',
                    hovertemplate='<b>%{x}% frequency</b><br>Number of genes: %{y}<extra></extra>'
                )
            ])

            fig.update_layout(
                title={
                    'text': f'📊 Gene Frequency Distribution ({len(genes_under_100)} genes under 100%)',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 16, 'color': 'rgb(70, 130, 180)'}
                },
                xaxis_title='Frequency (%)',
                yaxis_title='Number of Genes',
                height=400,
                margin=dict(l=60, r=60, t=60, b=60),
                plot_bgcolor='white',
                paper_bgcolor='white',
                font=dict(size=12),
                xaxis=dict(
                    gridcolor='rgb(230, 230, 230)',
                    showgrid=True,
                    tickmode='array',
                    tickvals=percentages,
                    ticktext=[f'%{p}' for p in percentages]
                ),
                yaxis=dict(
                    gridcolor='rgb(230, 230, 230)',
                    showgrid=True
                )
            )

            genes_under_100_content = [
                html.H5("📈 Gene Frequency Distribution", className="text-primary mb-3"),
                dcc.Graph(
                    id='gene-frequency-chart',
                    figure=fig,
                    config={
                        'displayModeBar': True,
                        'displaylogo': True,
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d']
                    }
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

        # --- Tabla Detallada por Solución ---
        available_objectives = []
        if all_solutions_list and len(all_solutions_list) > 0:
            sample_solution = all_solutions_list[0]
            for key in sample_solution.keys():
                if key not in ['selected_genes', 'solution_id']:
                    value = sample_solution.get(key)
                    if isinstance(value, (int, float)):
                        available_objectives.append(key)

        genes_data = []
        for solution in all_solutions_list:
            for gene in solution.get('selected_genes', []):
                row = {
                    'solution_id': solution.get('solution_id', 'N/A'),
                    'gene': gene
                }
                for objective in available_objectives:
                    row[objective] = solution.get(objective, None)
                genes_data.append(row)

        genes_df = pd.DataFrame(genes_data)

        # Build table columns dynamically
        table_columns = [
            {'name': 'Solution', 'id': 'solution_id'},
            {'name': 'Gen', 'id': 'gene'}
        ]

        for objective in available_objectives:
            column_name = objective.replace('_', ' ').title()

            if objective in genes_df.columns and genes_df[objective].dtype in ['float64', 'int64']:
                table_columns.append({
                    'name': column_name,
                    'id': objective,
                    'type': 'numeric',
                    'format': {'specifier': '.3f'} if genes_df[objective].dtype == 'float64' else None
                })
            else:
                table_columns.append({
                    'name': column_name,
                    'id': objective
                })

        table = dash_table.DataTable(
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
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            tooltip_duration=None, # Mantener la configuración de tooltip para el estilo
        )

        combined_analysis = genes_100_content + genes_under_100_content

        table_section = [
            html.Hr(),
            html.H5("📋 Detailed Gene Table by Solution", className="text-secondary mb-3"),
            table
        ]

        return table_section, combined_analysis

    # 2. Callback para mostrar los genes al hacer clic en una barra del gráfico
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

        # Find genes with the clicked percentage
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