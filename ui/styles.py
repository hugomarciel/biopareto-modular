"""
UI Styles - CSS and inline styles for the application
"""

# Header gradient style
HEADER_GRADIENT = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"

# Interest panel style
INTEREST_PANEL_STYLE = {
    'position': 'fixed',
    'right': '20px',
    'top': '120px',
    'width': '400px',
    'maxHeight': 'calc(100vh - 140px)',
    'overflowY': 'auto',
    'zIndex': '1000'
}

# Upload area style
UPLOAD_AREA_STYLE = {
    'width': '100%',
    'height': '60px',
    'lineHeight': '60px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '5px',
    'textAlign': 'center',
    'margin': '10px'
}

# Badge colors by item type
BADGE_COLORS = {
    'solution': 'primary',
    'solution_set': 'info',
    'gene_set': 'success',
    'individual_gene': 'warning',
    'combined_gene_group': 'success'
}

# Icons by item type
ITEM_ICONS = {
    'solution': '🔵',
    'solution_set': '📦',
    'gene_set': '🧬',
    'individual_gene': '🔬',
    'combined_gene_group': '🎯'
}
