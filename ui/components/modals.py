"""
Modal Components
"""

import dash_bootstrap_components as dbc
from dash import html


def create_pareto_modal():
    """Modal for Pareto Front Tab (Solutions)"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add to Interest Panel")),
        dbc.ModalBody([
            html.Div(id='pareto-front-tab-modal-item-info', className='mb-3'),
            dbc.Label("Add a comment or note:", className="fw-bold"),
            dbc.Textarea(
                id='pareto-front-tab-comment-input',
                placeholder="e.g., 'Promising solution', 'High accuracy set'...",
                style={'height': '100px'},
                className='mb-2'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="pareto-front-tab-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Add to Panel", id="pareto-front-tab-confirm-btn", color="primary")
        ])
    ], id="pareto-front-tab-interest-modal", is_open=False)


def create_genes_modal():
    """Modal for Genes Tab (Gene Groups/Individual Genes)"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Add Genes to Interest Panel")),
        dbc.ModalBody([
            html.Div(id='genes-tab-modal-item-info', className='mb-3'),
            dbc.Label("Add a comment or note:", className="fw-bold"),
            dbc.Textarea(
                id='genes-tab-comment-input',
                placeholder="e.g., 'Key genes for analysis', 'High frequency gene group'...",
                style={'height': '100px'},
                className='mb-2'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="genes-tab-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Add to Panel", id="genes-tab-confirm-btn", color="primary")
        ])
    ], id="genes-tab-interest-modal", is_open=False)


def create_gene_groups_modal():
    """Modal for Gene Groups Analysis Tab"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Create Combined Gene Group")),
        dbc.ModalBody([
            html.Div(id='gene-groups-analysis-tab-modal-info', className='mb-3'),
            dbc.Label("Group Name:", className="fw-bold"),
            dbc.Input(
                id='gene-groups-analysis-tab-name-input',
                placeholder="e.g., 'High-confidence genes from solutions 1-3'",
                type="text",
                className='mb-3'
            ),
            dbc.Label("Group Description/Comment:", className="fw-bold"),
            dbc.Textarea(
                id='gene-groups-analysis-tab-comment-input',
                placeholder="Describe the purpose or findings of this gene group...",
                style={'height': '100px'},
                className='mb-2'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="gene-groups-analysis-tab-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Create Group", id="gene-groups-analysis-tab-confirm-btn", color="success")
        ])
    ], id="gene-groups-analysis-tab-modal", is_open=False)


def create_consolidate_modal():
    """Modal for Consolidate Confirmation"""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Confirm Consolidation")),
        dbc.ModalBody([
            html.P(id='consolidate-modal-info', className='mb-3'),
            dbc.Label("New Front Name:", className="fw-bold"),
            dbc.Input(
                id='consolidate-front-name-input',
                placeholder="e.g., 'Consolidated Front 1'",
                type="text",
                className='mb-3'
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="consolidate-cancel-btn", color="secondary", className="me-2"),
            dbc.Button("Consolidate", id="consolidate-confirm-btn", color="success")
        ])
    ], id="consolidate-modal", is_open=False)
