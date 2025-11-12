# ui/layouts/genes_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc 


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
        
        # Store para el dataframe maestro
        dcc.Store(id='genes-analysis-internal-store'),
        
        # --- 🔑 INICIO DEL CAMBIO ---
        
        # 1. Almacén temporal para este modal
        dcc.Store(id='genes-graph-temp-store'),
        
        # 2. El Store 'genes-graph-click-counter' se ha eliminado.

        # 3. Modal genérico para todas las acciones del gráfico
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id='genes-graph-modal-title')),
                dbc.ModalBody(id='genes-graph-modal-body'),
                dbc.ModalFooter(id='genes-graph-modal-footer'),
            ],
            id='genes-graph-action-modal',
            is_open=False,
            centered=True,
        )
        # --- FIN DEL CAMBIO ---
        
    ], fluid=True)