# ui/layouts/pareto_tab.py

import dash_bootstrap_components as dbc
from dash import dcc, html

def create_pareto_tab():
    """Create Pareto front tab layout with Standardized UI and Contextual Help"""
    
    # --- 1. Popover de Ayuda: Gráfico Pareto ---
    pareto_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Pareto Graph Controls"),
            dbc.PopoverBody([
                html.Div([
                    html.Strong("Navigation:"),
                    html.Ul([
                        html.Li("Scroll Mouse: Zoom In/Out."),
                        html.Li("Click & Drag: Pan (move) across the plot."),
                        html.Li("Double Click: Reset view to default."),
                    ], className="mb-2 ps-3 small text-muted")
                ]),
                html.Div([
                    html.Strong("Selection Tools:"),
                    html.Ul([
                        html.Li("Click Point: Select/Deselect a single solution."),
                        html.Li("Box/Lasso Select: Drag to capture multiple points."),
                        html.Li("Shift + drag mouse: zoom by sections."),
                    ], className="mb-0 ps-3 small text-muted")
                ])
            ], style={'maxWidth': '300px'})
        ],
        id="pareto-plot-help-popover",
        target="pareto-plot-help-icon",
        trigger="legacy",
        placement="right",
    )

    # --- 2. Popover de Ayuda: Selection Toolkit ---
    toolkit_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Selection Toolkit Guide"),
            dbc.PopoverBody([
                html.Div([
                    html.Code("Consolidate", className="text-success fw-bold"),
                    html.Span(": Create a new 'Best of' front merging selected solutions from multiple files.", className="small text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Code("Add All", className="text-primary fw-bold"),
                    html.Span(": Send ALL currently selected solutions to the Interest Panel for further analysis.", className="small text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Code("Restore", className="text-secondary fw-bold"),
                    html.Span(": Revert to original data if you made consolidations or deletions.", className="small text-muted")
                ], className="mb-2"),
                
                html.Div([
                    html.Code("Clear", className="text-danger fw-bold"),
                    html.Span(": Deselect all points in the graph.", className="small text-muted")
                ], className="mb-0")
            ], style={'maxWidth': '350px'})
        ],
        id="toolkit-help-popover",
        target="toolkit-help-icon",
        trigger="legacy",
        placement="right",
    )

    return dbc.Container([
        
        # Stores para los ejes
        dcc.Store(id='x-axis-store'),
        dcc.Store(id='y-axis-store'),
        
        dbc.Row([
            dbc.Col([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            
                            # --- Header Estandarizado ---
                            dbc.CardHeader(
                                dbc.Row(
                                    [
                                        dbc.Col([
                                            html.Div([
                                                html.I(className="bi bi-bar-chart-fill me-2"), # Icono Título
                                                html.H5(id="pareto-plot-title", className="d-inline-block m-0 fw-bold"),
                                                
                                                # Icono Ayuda Gráfico
                                                html.I(
                                                    id="pareto-plot-help-icon",
                                                    className="bi bi-question-circle-fill text-muted ms-2",
                                                    style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                                    title="Graph interaction guide"
                                                )
                                            ], className="d-flex align-items-center text-primary")
                                        ], width="auto"),
                                        
                                        # Botón Swap
                                        dbc.Col(
                                            dbc.Button(
                                                [html.I(className="bi bi-arrow-left-right me-2"), "Swap Axes"],
                                                id="swap-axes-btn",
                                                color="info",
                                                outline=True,
                                                size="sm",
                                                className="shadow-sm"
                                            ),
                                            width="auto",
                                            className="ms-auto" 
                                        )
                                    ],
                                    align="center",
                                    justify="between" 
                                ),
                                className="bg-white border-bottom position-relative"
                            ),
                            
                            dbc.CardBody([
                                # Insertar Popover Gráfico
                                pareto_help_popover,
                                
                                dcc.Graph(id='pareto-plot', style={'height': '500px'}, config={'responsive': True, 'scrollZoom': True}),
                                html.Hr(className="my-4"),
                                
                                # --- BARRA DE HERRAMIENTAS (TOOLKIT) ---
                                html.Div([
                                    # Encabezado Toolkit con Ayuda
                                    html.Div([
                                        html.I(className="bi bi-sliders me-2 text-primary"),
                                        html.H6("Selection Toolkit", className="fw-bold m-0 text-dark"),
                                        
                                        # Icono Ayuda Toolkit
                                        html.I(
                                            id="toolkit-help-icon",
                                            className="bi bi-question-circle-fill text-muted ms-2",
                                            style={'cursor': 'pointer', 'fontSize': '1rem'},
                                            title="Toolkit guide"
                                        ),
                                        # Insertar Popover Toolkit
                                        toolkit_help_popover
                                        
                                    ], className="d-flex align-items-center mb-3"),

                                    dbc.Row([
                                        # GRUPO 1: Acciones Principales
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
                                                    color="success",
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
                                                    color="primary",
                                                    size="sm",
                                                    className="w-100 d-flex align-items-center justify-content-center shadow-sm fw-bold",
                                                    disabled=True,
                                                    title="Add all selected solutions to Interest Panel"
                                                    )
                                                ], width=6),
                                            ], className="g-2")
                                        ], width=12, lg=7, className="mb-3 mb-lg-0 border-end-lg pe-lg-3"), 

                                        # GRUPO 2: Acciones de Gestión
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
                                ], className="bg-light p-3 rounded border mb-4"),
                                
                                html.Hr(),
                                
                                # --- LISTA DE SELECCIÓN ---
                                html.Div([
                                    html.I(className="bi bi-check-circle-fill text-success me-2"),
                                    html.H6("Selected Solutions", className="text-success fw-bold d-inline-block m-0"),
                                    html.Small(" (Click points to populate list)", className="text-muted ms-2")
                                ], className="d-flex align-items-center mb-3"),
                                
                                html.Div(id="selected-solutions-info")
                            ])
                        ], className="shadow-sm border-0")
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

    ], fluid=True, className="py-3")