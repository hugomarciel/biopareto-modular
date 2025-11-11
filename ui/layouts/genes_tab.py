# ui/layouts/genes_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc # <-- Asegúrate de que dcc esté importado


def create_genes_tab():
    """Create selected genes tab layout"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.H4("Selected Genes by Solution", className="text-primary mb-0")
                    ]),
                    dbc.CardBody([
                        html.Div([
                            html.Div(id="common-genes-analysis") # Contiene el gráfico y los botones 100%
                        ]),
                        html.Hr(),
                        html.Div(id="genes-table-container") # Contiene el Filtro Global, el Gráfico y la Tabla
                    ])
                ])
            ], width=12),
        ]),
        
        # --- 🔑 CAMBIO AQUÍ ---
        # Añadimos un Store para guardar el dataframe maestro
        dcc.Store(id='genes-analysis-internal-store')
        # --- FIN DEL CAMBIO ---
        
    ], fluid=True)