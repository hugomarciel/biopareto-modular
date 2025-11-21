# ui/layouts/pareto_tab.py

import dash_bootstrap_components as dbc
from dash import dcc, html

def create_pareto_tab():
    """Create Pareto front tab layout"""
    return dbc.Container([
        
        # Stores para los ejes
        dcc.Store(id='x-axis-store'),
        dcc.Store(id='y-axis-store'),
        
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            
                            # CardHeader con Título y Botón Swap
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            html.H4(id="pareto-plot-title", className="text-primary mb-0"),
                                            width="auto"
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                "⇄ Swap Axes",
                                                id="swap-axes-btn",
                                                color="info",
                                                outline=True,
                                                size="sm"
                                            ),
                                            width="auto",
                                            className="ms-auto" 
                                        )
                                    ],
                                    align="center",
                                    justify="between" 
                                )
                            ),
                            
                            dbc.CardBody([
                                dcc.Graph(id='pareto-plot', style={'height': '500px'}, config={'responsive': True, 'scrollZoom': True}),
                                html.Hr(),
                                
                                # --- INICIO DE DISEÑO MEJORADO DE BARRA DE HERRAMIENTAS ---
                                html.Div([
                                    html.Div([
                                        html.I(className="bi bi-sliders me-2 text-primary"),
                                        html.H6("Selection Toolkit", className="fw-bold m-0 text-dark")
                                    ], className="d-flex align-items-center mb-3"),

                                    dbc.Row([
                                        # GRUPO 1: Acciones Principales (Constructivas)
                                        dbc.Col([
                                            dbc.Label("Analysis Actions", className="small text-muted fw-bold text-uppercase mb-1"),
                                            dbc.Row([
                                                # Botón Consolidar
                                                dbc.Col([
                                                    dbc.Button([
                                                        html.I(className="bi bi-layers-half me-2"),
                                                        "Consolidate"
                                                    ],
                                                    id="consolidate-selection-btn",
                                                    color="success", # Verde sólido
                                                    size="sm",
                                                    className="w-100 d-flex align-items-center justify-content-center shadow-sm fw-bold",
                                                    disabled=True,
                                                    title="Create a new Pareto front from selected solutions"
                                                    )
                                                ], width=6),
                                                
                                                # Botón Añadir Todos
                                                dbc.Col([
                                                    dbc.Button([
                                                        html.I(className="bi bi-collection-fill me-2"),
                                                        "Add All"
                                                    ],
                                                    id="add-to-interest-btn",
                                                    color="primary", # Azul sólido
                                                    size="sm",
                                                    className="w-100 d-flex align-items-center justify-content-center shadow-sm fw-bold",
                                                    disabled=True,
                                                    title="Add all selected solutions to Interest Panel"
                                                    )
                                                ], width=6),
                                            ], className="g-2")
                                        ], width=12, lg=7, className="mb-3 mb-lg-0 border-end-lg pe-lg-3"), 

                                        # GRUPO 2: Acciones de Gestión (Reset/Clear)
                                        dbc.Col([
                                            dbc.Label("Reset Tools", className="small text-muted fw-bold text-uppercase mb-1"),
                                            dbc.ButtonGroup([
                                                # Botón Restaurar
                                                dbc.Button([
                                                    html.I(className="bi bi-arrow-counterclockwise me-1"),
                                                    "Restore"
                                                ],
                                                id="restore-original-btn",
                                                color="secondary",
                                                outline=True, 
                                                size="sm",
                                                disabled=True,
                                                title="Restore original data load"
                                                ),
                                                # Botón Limpiar
                                                dbc.Button([
                                                    html.I(className="bi bi-trash3-fill me-1"),
                                                    "Clear"
                                                ],
                                                id="clear-selection-btn",
                                                color="danger",
                                                outline=True, 
                                                size="sm",
                                                title="Clear current selection"
                                                ),
                                            ], className="d-flex w-100 shadow-sm")
                                        ], width=12, lg=5)
                                    ], className="align-items-end")
                                ], className="bg-light p-3 rounded border mb-3"),
                                # --- FIN DE DISEÑO MEJORADO ---
                                
                                html.Hr(),
                                
                                html.H6("Selected Solutions:", className="text-info mb-3"),
                                html.Small("Click on a point to select the solution. Also can use lasso/box to add more.",
                                         className="text-muted d-block mb-2"),
                                html.Div(id="selected-solutions-info")
                            ])
                        ])
                    ], width=12)
                ], className="mb-3"),
            ], width=12),
        ]),
        
        # Store y Modal para puntos múltiples
        dcc.Store(id='multi-solution-modal-store'),
        
        dbc.Modal(
            [
                dbc.ModalHeader(id="multi-solution-modal-header"),
                dbc.ModalBody(id="multi-solution-modal-body"),
                dbc.ModalFooter(
                    dbc.Button("Close", id="multi-solution-modal-close-btn", className="ms-auto")
                ),
            ],
            id="multi-solution-modal",
            size="xl", 
            is_open=False,
            scrollable=True, 
            centered=True,
        )

    ], fluid=True)