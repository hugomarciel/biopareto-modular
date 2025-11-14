# ui/layouts/pareto_tab.py

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_pareto_tab():
    """Create Pareto front tab layout"""
    return dbc.Container([
        
        # --- AÑADIDO: Stores para los ejes ---
        dcc.Store(id='x-axis-store'),
        dcc.Store(id='y-axis-store'),
        
        dbc.Row([
            dbc.Col([
                
                # --- ELIMINADO: Row de Configuración de Ejes ---
                # La dbc.Row que contenía la Card "Axis Configuration" ha sido eliminada.

                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            
                            # --- MODIFICADO: CardHeader con Título y Botón Swap ---
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
                                            className="ms-auto" # Alinea a la derecha
                                        )
                                    ],
                                    align="center",
                                    justify="between" # Asegura que uno esté a la izq y otro a la der
                                )
                            ),
                            # --- FIN DE LA MODIFICACIÓN ---
                            
                            dbc.CardBody([
                                dcc.Graph(id='pareto-plot', style={'height': '500px'}, config={'responsive': True}),
                                html.Hr(),
                                html.Div([
                                    html.H6("Selection Actions:", className="text-info mb-3"),
                                    dbc.Row([
                                        dbc.Col([
                                            dbc.Button("🗑️ Clear Selection",
                                                 id="clear-selection-btn",
                                                 color="danger",
                                                 size="sm",
                                                 className="w-100 mb-2"
                                            ),
                                        ], width=4),
                                        dbc.Col([
                                            dbc.Button("💾 Consolidate Selection To a New Front",
                                                 id="consolidate-selection-btn",
                                                 color="success",
                                                 size="sm",
                                                 disabled=True,
                                                 className="w-100 mb-2"
                                            ),
                                        ], width=4),
                                        dbc.Col([
                                            dbc.Button("↩️ Restore The Original Load",
                                                 id="restore-original-btn",
                                                 color="warning",
                                                 size="sm",
                                                 disabled=True,
                                                 className="w-100 mb-2"
                                            ),
                                        ], width=4)
                                    ], className="mb-3"),
                                    
                                    dbc.Button(
                                        "📌 Add All to Interest Panel",
                                        id="add-to-interest-btn",
                                        color="info",
                                        size="sm",
                                        disabled=True,
                                        className="w-100 mb-3"
                                    ),
                                    
                                    html.Hr(),
                                    
                                    html.H6("Selected Solutions:", className="text-info mb-3"),
                                    html.Small("Click on a point to select the solution. Also can use lasso/box to add more.",
                                             className="text-muted d-block mb-2"),
                                    html.Div(id="selected-solutions-info")
                                ])
                            ])
                        ])
                    ], width=12)
                ], className="mb-3"),
            ], width=12),
        ]),
        
        # --- Sin cambios: Store y Modal para puntos múltiples ---
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
        # --- FIN DE LO AÑADIDO ---

    ], fluid=True)