# ui/components/interest_panel.py

import dash_bootstrap_components as dbc
from dash import html, dcc

def create_interest_panel():
    """Create the interest panel with refined Pin styling."""
    return dbc.Card([
        # --- 1. HEADER MEJORADO ---
        dbc.CardHeader([
            html.Div([
                # Título e Icono
                html.Div([
                    html.I(className="bi bi-pin-angle-fill me-2"),
                    html.H5("Interest Panel", className="mb-0 fw-bold", style={'letterSpacing': '0.5px'}),
                ], className="d-flex align-items-center"),
                
                # Controles Derecha
                html.Div([
                    # --- CORRECCIÓN DE ALINEACIÓN PIN ---
                    html.Div([
                        # 1. Texto separado del switch para alineación perfecta
                        html.Span("Pin", className="text-white small me-5", style={'opacity': '0.9', 'fontWeight': '500'}),
                        
                        # 2. Switch sin label interno
                        dbc.Switch(
                            id="pin-interest-panel-switch",
                            value=False,
                            className="mb-0 p-0", # Sin márgenes extra
                            style={
                                "minHeight": "20px",
                                "cursor": "pointer",
                                "transform": "scale(1.1)" # Ligeramente más grande para que sea fácil de clickear
                            }
                        ),
                    ], className="d-flex align-items-center me-3 border-end pe-3 border-white border-opacity-25"), # Divisor vertical sutil

                    # Botón Borrar
                    dbc.Button(
                        html.I(className="bi bi-trash3-fill"),
                        id="clear-interest-panel-btn",
                        color="light", 
                        outline=True,
                        size="sm",
                        className="border-0 text-white hover-warning p-1",
                        title="Clear all items"
                    )
                ], className="d-flex align-items-center")
            ], className="d-flex justify-content-between align-items-center")
        ], className="bg-primary text-white border-0 rounded-top p-3"), 
        
        # --- 2. CUERPO (Sin cambios) ---
        dbc.CardBody([
            html.P("Collect solutions, genes, and groups here for comparison and export.",
                   className="text-muted small mb-3 fst-italic text-center opacity-75"),
            
            html.Div(id='interest-panel-content', children=[
                html.Div([
                    html.I(className="bi bi-inbox fs-1 text-muted opacity-25 mb-2"),
                    html.P("Panel is empty", className="text-muted fw-bold"),
                ], className="text-center py-5 d-flex flex-column align-items-center")
            ], className="pe-1") 
            
        ], 
        style={
            'maxHeight': 'calc(100vh - 180px)', 
            'overflowY': 'auto',
            'backgroundColor': '#f8f9fa' 
        }, 
        className="p-2 custom-scrollbar") 
        
    ], className="h-100 shadow-lg border-0 rounded-3")