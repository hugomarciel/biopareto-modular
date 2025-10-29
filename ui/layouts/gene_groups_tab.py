# ui/layouts/gene_groups_tab.py

import dash_bootstrap_components as dbc
from dash import html


def create_gene_groups_tab():
    """Create the Gene Groups Analysis tab with visual card selection"""
    return dbc.Container([
        html.H4("🧬 Gene Groups Analysis", className="mb-4"),
        html.P("Select items from your Interest Panel to analyze their genes together",
               className="text-muted mb-4"),

        html.Hr(),

        html.Div([
            html.H5("Select Items to Analyze:", className="mb-3"),
            # Contenedor para los cards de selección visual (Input dinámico)
            html.Div(id='gene-groups-visual-selector', children=[
                html.P("Loading items...", className="text-muted text-center py-4")
            ])
        ], className="mb-4"),

        html.Hr(),

        # Contenedor para resultados (Venn, frecuencia y tabla)
        html.Div(id='combined-genes-analysis-results')
    ], fluid=True, className="py-4")