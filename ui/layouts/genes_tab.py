# ui/layouts/genes_tab.py

import dash_bootstrap_components as dbc
from dash import html, dcc 

def create_genes_tab():
    """Create selected genes tab layout with In-Place Expansion (Accordion Style)"""
    return dbc.Container([
        
        # --- SECCIÓN 1: GLOBAL OVERVIEW (100% & Frequency) ---
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-bar-chart-line-fill me-2"),
                            html.H5("Gene Frequency Overview", className="d-inline-block m-0 fw-bold")
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom"),
                    
                    dbc.CardBody([
                        html.P("Overview of genes identified across all selected solutions. Click a bar to view detailed gene list below.", 
                               className="text-muted small mb-4"),
                        
                        # Aquí se renderizará:
                        # 1. Los Badges del 100%
                        # 2. El Gráfico de Frecuencia
                        # 3. EL NUEVO CONTENEDOR EXPANDIBLE (frequency-detail-wrapper)
                        html.Div(id="common-genes-analysis") 
                    ])
                ], className="shadow-sm border-0 mb-4")
            ], width=12),
        ]),
        
        # --- SECCIÓN 2: DETAILED EXPLORER (Table & Filter Graph) ---
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-table me-2"),
                            html.H5("Solution Explorer & Data Table", className="d-inline-block m-0 fw-bold")
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom"),
                    
                    dbc.CardBody([
                         html.P("Interactive exploration of specific solutions and gene metrics. Use the controls below to filter data.", 
                               className="text-muted small mb-3"),
                        html.Div(id="genes-table-container")
                    ])
                ], className="shadow-sm border-0")
            ], width=12),
        ]),
        
        # --- STORES Y MODALES ---
        dcc.Store(id='genes-analysis-internal-store'),
        dcc.Store(id='genes-graph-temp-store'),

        # Modal Acciones Gráfico
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
        
    ], fluid=True, className="py-3")