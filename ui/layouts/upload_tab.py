"""
Upload Tab Layout - Optimized UX/UI
"""

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_upload_tab():
    """Create data upload tab with improved UX and Help Guide"""
    
    # --- Popover de Ayuda para Carga de Datos ---
    upload_help_popover = dbc.Popover(
        [
            dbc.PopoverHeader("Data Upload Guide"),
            dbc.PopoverBody([
                # 1. Carga de Archivos
                html.Div([
                    html.Strong("1. File Selection:"), 
                    html.Span(" You can upload a ", className="small text-muted"),
                    html.Strong("single JSON file", className="small text-dark"),
                    html.Span(" or ", className="small text-muted"),
                    html.Strong("multiple files", className="small text-dark"),
                    html.Span(" simultaneously.", className="small text-muted")
                ], className="mb-2"),

                # 2. Métodos de Carga
                html.Div([
                    html.Strong("2. How to Upload:"),
                    html.Ul([
                        html.Li("Drag and drop files into the dashed area.", className="small text-muted"),
                        html.Li("Click the area to open the file browser.", className="small text-muted"),
                    ], className="mb-0 ps-3")
                ], className="mb-2"),

                # 3. Nombres
                html.Div([
                    html.Strong("3. Naming Convention:"), 
                    html.Span(" Fronts are automatically named after their ", className="small text-muted"),
                    html.Code("filename", className="small text-dark"),
                    html.Span(". It is recommended to use meaningful names (e.g., 'Experiment_A.json').", className="small text-muted")
                ], className="mb-2"),

                # 4. Validación
                html.Div([
                    html.Strong("4. Validation:"), 
                    html.Span(" When uploading multiple files, the system verifies that they share the ", className="small text-muted"),
                    html.Strong("same optimization objectives", className="small text-danger"),
                    html.Span(" (e.g., 1-Auc, Gene Ratio) to ensure comparability.", className="small text-muted")
                ], className="mb-0")
            ], style={'maxWidth': '350px'})
        ],
        id="upload-help-popover",
        target="upload-help-icon",
        trigger="legacy",
        placement="right",
    )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    # --- Header Estilizado (Igual a Genes Tab) ---
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-cloud-arrow-up-fill me-2"),
                            html.H5("Load Pareto Front Data", className="d-inline-block m-0 fw-bold"),
                            
                            # Icono de Ayuda
                            html.I(
                                id="upload-help-icon",
                                className="bi bi-question-circle-fill text-muted ms-2",
                                style={'cursor': 'pointer', 'fontSize': '1.1rem'},
                                title="Click for upload guide"
                            )
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom position-relative"),

                    dbc.CardBody([
                        # Insertamos el Popover
                        upload_help_popover,

                        html.P("Upload JSON files containing Pareto front solutions to begin analysis.",
                               className="text-muted small mb-3"),

                        # --- Zona de Carga (Drag & Drop) ---
                        dcc.Upload(
                            id='upload-data',
                            children=html.Div([
                                html.I(className="bi bi-cloud-upload fs-2 text-primary mb-2"),
                                html.Div(['Drag and Drop or ', html.A('Select JSON Files', className="fw-bold text-decoration-none")]),
                                html.Small("Supported format: .json", className="text-muted")
                            ], className="d-flex flex-column align-items-center justify-content-center h-100"),
                            style={
                                'width': '100%',
                                'height': '120px', # Un poco más alto para mejor visibilidad
                                'lineHeight': 'normal',
                                'borderWidth': '2px',
                                'borderStyle': 'dashed',
                                'borderRadius': '10px',
                                'textAlign': 'center',
                                'borderColor': '#dee2e6',
                                'backgroundColor': '#f8f9fa',
                                'cursor': 'pointer',
                                'transition': 'all 0.3s ease-in-out'
                            },
                            className="mb-4 hover-shadow", # Clase CSS para efecto hover si existe, sino no afecta
                            multiple=True,
                            accept='.json'
                        ),

                        # --- BOTONES DE ACCIÓN (MOVIDOS ARRIBA) ---
                        dbc.Row([
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="bi bi-download me-2"), "Download Test File"
                                ], id="download-test-btn", color="info", outline=True, className="w-100 shadow-sm")
                            ], width=12, md=6, className="mb-2 mb-md-0"),
                            
                            dbc.Col([
                                dbc.Button([
                                    html.I(className="bi bi-trash3 me-2"), "Clear All Data"
                                ], id="clear-data-btn", color="danger", outline=True, className="w-100 shadow-sm")
                            ], width=12, md=6)
                        ], className="mb-4"),

                        dcc.Download(id="download-test-file"),
                        html.Div(id="upload-status"), # Mensajes de alerta

                        html.Hr(className="my-4"),

                        # --- Lista de Frentes Cargados ---
                        html.Div([
                            html.Div([
                                html.I(className="bi bi-list-check me-2 text-primary"),
                                html.H6("Loaded Fronts", className="fw-bold d-inline-block m-0")
                            ], className="d-flex align-items-center mb-3"),
                            
                            html.Div(id='fronts-list', children=[
                                dbc.Alert("No fronts loaded yet. Upload files to see them here.", color="light", className="text-center small text-muted border-0")
                            ], style={'maxHeight': '400px', 'overflowY': 'auto', 'paddingRight': '5px'}) # Scroll interno si hay muchos
                        ]),

                        html.Hr(className="my-4"),

                        # --- Información de Formato (Collapse) ---
                        dbc.Button(
                            [html.I(className="bi bi-code-square me-2"), "View Expected JSON Format"],
                            id="toggle-format-info",
                            color="link",
                            size="sm",
                            className="text-decoration-none ps-0"
                        ),
                        
                        dbc.Collapse([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("📋 JSON Structure Example:", className="text-info small fw-bold mb-2"),
                                    html.Pre('''[
  {
    "selected_genes": ["BRCA1", "TP53", "EGFR"],
    "accuracy": 0.92,
    "num_genes": 3,
    "solution_id": "Sol_1"
  },
  {
    "selected_genes": ["BRCA1", "TP53", "EGFR", "MYC"],
    "accuracy": 0.94,
    "num_genes": 4,
    "solution_id": "Sol_2"
  }
]''', style={'fontSize': '11px', 'backgroundColor': '#f1f3f5', 'padding': '15px', 'borderRadius': '1px', 'border': '1px solid #dee2e6'})
                                ])
                            ], className="mt-2 border-0 bg-light")
                        ], id="format-info-collapse", is_open=False),

                    ])
                ], className="shadow-sm border-0")
            ], width=12)
        ])
    ], fluid=True, className="py-3")