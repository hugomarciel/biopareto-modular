# ui/components/interest_panel.py

import dash_bootstrap_components as dbc
from dash import html

def create_interest_panel():
    """Create the interest panel with improved styling."""
    return dbc.Card([
        # --- 1. HEADER MEJORADO: Fondo Azul Sólido y Texto Blanco ---
        dbc.CardHeader([
            html.Div([
                html.Div([
                    html.I(className="bi bi-pin-angle-fill me-2"),
                    html.H5("Interest Panel", className="mb-0 fw-bold", style={'letterSpacing': '0.5px'}),
                ], className="d-flex align-items-center"),
                
                dbc.Button(
                    html.I(className="bi bi-trash3-fill"),
                    id="clear-interest-panel-btn",
                    color="light", # Botón claro sobre fondo azul
                    outline=True,
                    size="sm",
                    className="border-0 text-white hover-warning",
                    style={'opacity': '0.9'},
                    title="Clear all items"
                )
            ], className="d-flex justify-content-between align-items-center")
        ], className="bg-primary text-white border-0 rounded-top p-3"), # bg-primary = Azul BioPareto
        
        # --- 2. CUERPO CON CONTRASTE: Fondo gris suave ---
        dbc.CardBody([
            html.P("Collect solutions, genes, and groups here for comparison and export.",
                   className="text-muted small mb-3 fst-italic text-center opacity-75"),
            
            html.Div(id='interest-panel-content', children=[
                # Estado vacío más estético
                html.Div([
                    html.I(className="bi bi-inbox fs-1 text-muted opacity-25 mb-2"),
                    html.P("Panel is empty", className="text-muted fw-bold"),
                ], className="text-center py-5 d-flex flex-column align-items-center")
            ], className="pe-1") 
            
        ], 
        # Estilos del área scrollable
        style={
            'maxHeight': 'calc(100vh - 180px)', 
            'overflowY': 'auto',
            'backgroundColor': '#f8f9fa' # Gris muy claro para resaltar las tarjetas blancas internas
        }, 
        className="p-2 custom-scrollbar") # Scrollbar fino
        
    ], className="h-100 shadow-lg border-0 rounded-3") # Sombra grande y sin bordes