"""
UI Module - User Interface Components
"""

from .components.navbar import create_navbar
from .components.interest_panel import create_interest_panel
from .components.modals import *
from .layouts.upload_tab import create_upload_tab
from .layouts.pareto_tab import create_pareto_tab
from .layouts.genes_tab import create_genes_tab
from .layouts.gene_groups_tab import create_gene_groups_tab
from .layouts.enrichment_tab import create_enrichment_tab_modified
from .layouts.export_tab import create_export_tab

__all__ = [
    'create_navbar',
    'create_interest_panel',
    'create_upload_tab',
    'create_pareto_tab',
    'create_genes_tab',
    'create_gene_groups_tab',
    'create_enrichment_tab_modified',
    'create_export_tab'
]
