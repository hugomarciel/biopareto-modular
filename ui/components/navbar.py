"""
Navigation Bar Component
"""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar():
    """Create navigation bar with logos and title"""
    return dbc.Navbar(
        dbc.Container([
            dbc.Row(
                [
                    # Left column for original logo and title
                    dbc.Col(
                        [
                            html.Img(src="/assets/logo.png", height="60px", className="me-2") if True else None,
                            dbc.NavbarBrand("🧬 BioPareto Analyzer", className="ms-2", 
                                          style={"fontSize": "2.0rem", "fontWeight": "bold"})
                        ],
                        width="auto"
                    ),

                    # Right column for new logo
                    dbc.Col(
                        html.Img(src="/assets/LAI2B.png", height="40px"),
                        width="auto",
                        className="ms-auto"
                    )
                ],
                align="center",
                className="g-0 w-100"
            ),
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-4"
    )
