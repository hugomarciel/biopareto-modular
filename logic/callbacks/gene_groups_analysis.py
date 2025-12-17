# logic/callbacks/gene_groups_analysis.py

import dash
from dash import Output, Input, State, dcc, html, dash_table, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import numpy as np
import io 
from collections import defaultdict

# Imports for Venn (if available)
try:
    from matplotlib_venn import venn2, venn3
    from matplotlib_venn.layout.venn3 import DefaultLayoutAlgorithm
    from matplotlib_venn.layout.venn2 import DefaultLayoutAlgorithm as DefaultLayoutAlgorithm2
    import matplotlib.pyplot as plt
    import base64
except ImportError:
    pass


def register_gene_groups_callbacks(app):

    @app.callback(
        Output('gene-groups-items-lite-store', 'data'),
        Input('interest-panel-store', 'data')
    )
    def build_gene_groups_items_lite(items):
        if not items:
            return []

        lite_items = []
        for item in items:
            item_type = item.get('type', '')
            data = item.get('data', {}) or {}
            lite_data = {}

            if item_type == 'solution':
                genes = data.get('selected_genes', [])
                lite_data = {
                    'selected_genes_count': len(genes),
                    'front_name': data.get('front_name', '?')
                }
            elif item_type == 'solution_set':
                n_genes = data.get('unique_genes_count', 0)
                if n_genes == 0 and 'solutions' in data:
                    unique_g = set()
                    for s in data.get('solutions', []):
                        unique_g.update(s.get('selected_genes', []))
                    n_genes = len(unique_g)
                lite_data = {
                    'unique_genes_count': n_genes,
                    'solutions_count': len(data.get('solutions', []))
                }
            elif item_type == 'gene_set':
                genes = data.get('genes', [])
                lite_data = {
                    'genes_count': len(genes),
                    'frequency': data.get('frequency')
                }
            elif item_type == 'individual_gene':
                lite_data = {
                    'gene': data.get('gene'),
                    'source': data.get('source')
                }
            elif item_type == 'combined_gene_group':
                lite_data = {
                    'gene_count': data.get('gene_count', len(data.get('genes', []))),
                    'source_items_count': len(data.get('source_items', []))
                }

            lite_items.append({
                'type': item_type,
                'name': item.get('name', 'Unknown'),
                'comment': item.get('comment', ''),
                'tool_origin': item.get('tool_origin', 'Manual Selection'),
                'data': lite_data
            })

        return lite_items

    # --- SERVER-SIDE CALLBACK (Visual Feedback) ---
    @app.callback(
        [Output({'type': 'gene-group-card-wrapper', 'index': MATCH}, 'style'),
         Output({'type': 'gene-group-card-wrapper', 'index': MATCH}, 'className')],
        Input({'type': 'gene-group-card-checkbox', 'index': MATCH}, 'value'),
        prevent_initial_call=True
    )
    def update_card_visual_feedback(selected_value):
        is_selected = selected_value and len(selected_value) > 0
        if is_selected:
            return (
                {'transition': 'all 0.2s ease-in-out', 'border': '2px solid #0d6efd', 'backgroundColor': '#f0f8ff', 'transform': 'scale(1.02)', 'cursor': 'pointer'},
                "h-100 shadow"
            )
        else:
            return (
                {'transition': 'all 0.2s ease-in-out', 'border': '1px solid rgba(0,0,0,0.125)', 'backgroundColor': 'white', 'transform': 'scale(1)', 'cursor': 'pointer'},
                "h-100 shadow-sm hover-shadow"
            )

    # 1. Render Visual Selector (Standardized)
    @app.callback(
        Output('gene-groups-visual-selector', 'children'),
        [Input('gene-groups-items-lite-store', 'data'),
         Input('selected-gene-group-indices-store', 'data')], 
        State('data-store', 'data')
    )
    def render_visual_gene_groups_selector(items, selected_indices_list, data_store):
        if not items:
            return dbc.Alert([
                html.I(className="bi bi-exclamation-circle me-2"),
                "No items available. Add items to your Interest Panel first."
            ], color="warning", className="d-flex align-items-center")

        if selected_indices_list is None:
            selected_indices_list = []

        cards = []
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', 'Unknown')
            item_comment = item.get('comment', '')
            item_origin = item.get('tool_origin', 'Manual Selection')
            data = item.get('data', {})

            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            # Standardized Styles & Icons
            if item_type == 'solution':
                badge_color, icon, badge_text = "primary", "🔵", "Solution"
            elif item_type == 'solution_set':
                badge_color, icon, badge_text = "info", "📦", "Set"
            elif item_type == 'gene_set':
                badge_color, icon, badge_text = "success", "🧬", "Gene Group"
            elif item_type == 'individual_gene':
                badge_color, icon, badge_text = "warning", "🔬", "Gene"
            elif item_type == 'combined_gene_group':
                badge_color, icon, badge_text = "success", "🎯", "Combined"
            else:
                badge_color, icon, badge_text = "secondary", "❓", "Unknown"

            # Stats Text Logic
            stats_text_left = ""
            stats_text_right = ""

            if item_type == 'solution':
                stats_text_left = f"Genes/Probes: {data.get('selected_genes_count', 0)}"
                stats_text_right = f"Src: {data.get('front_name', '?')}"
            elif item_type == 'solution_set':
                stats_text_left = f"Genes/Probes: {data.get('unique_genes_count', 0)}"
                stats_text_right = f"Sols: {data.get('solutions_count', 0)}"
            elif item_type == 'gene_set':
                stats_text_left = f"Genes/Probes: {data.get('genes_count', 0)}"
                freq = data.get('frequency')
                stats_text_right = f"Freq: {freq}%" if freq else "Table"
            elif item_type == 'individual_gene':
                stats_text_left = f"ID: {data.get('gene')}"
                stats_text_right = f"Src: {data.get('source')}"
            elif item_type == 'combined_gene_group':
                stats_text_left = f"Genes/Probes: {data.get('gene_count', 0)}"
                stats_text_right = f"Srcs: {data.get('source_items_count', 0)}"

            is_selected = idx in selected_indices_list
            
            # Card Styles
            card_style = {'transition': 'all 0.2s ease-in-out', 'border': '2px solid #0d6efd', 'backgroundColor': '#f0f8ff', 'transform': 'scale(1.02)', 'cursor': 'pointer'} if is_selected else \
                         {'transition': 'all 0.2s ease-in-out', 'border': '1px solid rgba(0,0,0,0.125)', 'backgroundColor': 'white', 'transform': 'scale(1)', 'cursor': 'pointer'}
            card_class = "h-100 shadow" if is_selected else "h-100 shadow-sm hover-shadow"

            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                value=[idx] if is_selected else [],
                                id={'type': 'gene-group-card-checkbox', 'index': idx},
                                switch=True,
                                style={'transform': 'scale(1.3)'}
                            )
                        ], style={'position': 'absolute', 'top': '10px', 'right': '10px', 'zIndex': '10'}),

                        html.Div([
                            html.Div([
                                html.Span(icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
                                dbc.Badge(badge_text, color=badge_color, style={'fontSize': '0.75rem'}),
                            ], className="d-flex align-items-center mb-2"),
                            
                            html.H6(item_name, className="fw-bold mb-2 text-truncate", title=item_name, style={'maxWidth': '90%'}),
                            html.Hr(className="my-2"),
                            html.Div([
                                html.Span(stats_text_left, className="fw-bold text-primary"),
                                html.Span(" | ", className="text-muted mx-1"),
                                # CAMBIO: Se eliminó el parámetro 'style' con maxWidth
                                html.Span(stats_text_right, className="text-muted text-truncate") 
                            ], className="small mb-2"),
                            html.P(item_comment, className="text-muted small fst-italic mb-0 text-truncate", title=item_comment) if item_comment else None,
                            html.Div([html.Small(f"Via: {item_origin}", className="text-muted", style={'fontSize': '0.65rem'})], className="mt-2 pt-1 border-top")
                        ], style={'paddingRight': '25px'}) 
                    ], className="p-3")
                ], id={'type': 'gene-group-card-wrapper', 'index': idx}, className=card_class, style=card_style)
            ], width=12, md=6, lg=4, xl=3, className="mb-3")

            cards.append(card)

        return dbc.Row(cards, className="g-3")

    # 2. Analyze Selection (Main Callback)
    @app.callback(
        [Output('combined-genes-analysis-results', 'children'),
         Output('gene-groups-analysis-tab-temp-store', 'data'),
         Output('intersection-data-temp-store', 'data', allow_duplicate=True),
         Output('selected-gene-group-indices-store', 'data')],
        Input({'type': 'gene-group-card-checkbox', 'index': ALL}, 'value'),
        State('interest-panel-store', 'data'),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def analyze_combined_genes_auto_visual(checkbox_values, items, data_store):
        selected_indices = []
        for values in checkbox_values:
            if values and len(values) > 0:
                selected_indices.extend(values) 

        if not selected_indices or not items:
            return html.Div([
                dbc.Alert([
                    html.I(className="bi bi-arrow-up-circle me-2"),
                    "Please select at least one item from the selection panel above to start the analysis."
                ], color="info", className="d-flex align-items-center border-0 shadow-sm")
            ], className="mt-3"), None, [], []

        # Data processing logic
        all_solutions_dict = {}
        if data_store:
            for front in data_store.get("fronts", []):
                for sol in front["data"]:
                    all_solutions_dict[sol['solution_id']] = sol

        gene_sources = {}
        item_gene_sets = {} 
        ordered_source_names = [] 

        for idx in selected_indices:
            if idx < len(items):
                item = items[idx]
                item_name_base = item.get('name', f'Item {idx}')
                item_type = item.get('type', '')
                current_genes_set = set()
                current_display_key = ""

                # Extracción de genes según tipo...
                if item_type == 'solution':
                    sol_data = item.get('data', {})
                    sol_id = sol_data.get('solution_id', 'Unknown')
                    front_name = sol_data.get('front_name', 'Unknown Front')
                    genes = sol_data.get('selected_genes', [])
                    if not genes and sol_id in all_solutions_dict:
                        genes = all_solutions_dict[sol_id].get('selected_genes', [])
                    current_genes_set = set(genes)
                    current_display_key = f"{sol_id} ({front_name})"
                elif item_type == 'solution_set':
                    solutions = item.get('data', {}).get('solutions', [])
                    genes_in_set = set()
                    for sol in solutions:
                        sol_id = sol.get('id', '')
                        genes = sol.get('selected_genes', [])
                        if not genes and sol_id in all_solutions_dict:
                            genes = all_solutions_dict[sol_id].get('selected_genes', [])
                        genes_in_set.update(genes)
                    current_genes_set = genes_in_set
                    current_display_key = item_name_base
                elif item_type in ['gene_set', 'combined_gene_group']:
                    genes_list = item.get('data', {}).get('genes', [])
                    current_genes_set = set(genes_list)
                    current_display_key = item_name_base
                elif item_type == 'individual_gene':
                    gene = item.get('data', {}).get('gene', '')
                    current_genes_set = {gene} if gene else set()
                    current_display_key = f"Gene: {gene}"
                
                if current_genes_set:
                    unique_key = current_display_key
                    key_counter = 1
                    while unique_key in item_gene_sets:
                        unique_key = f"{current_display_key} ({key_counter})"
                        key_counter += 1
                    item_gene_sets[unique_key] = current_genes_set
                    ordered_source_names.append(unique_key)
                    for gene in current_genes_set:
                        gene_sources.setdefault(gene, []).append(unique_key)

        unique_genes = set(gene_sources.keys())
        num_items = len(item_gene_sets)
        
        # --- LAYOUT DE RESULTADOS ---
        
        buttons_row = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Button([html.I(className="bi bi-layers-fill me-2"), "Save Combined Group (Union)"], 
                                   id="save-combined-group-btn-top", color="success", className="me-2 shadow-sm fw-bold"),
                        dbc.Button([html.I(className="bi bi-trash3 me-2"), "Clear Selection"], 
                                   id="clear-gene-groups-selection-btn", color="secondary", outline=True, className="shadow-sm")
                    ], width=12)
                ])
            ], className="p-3")
        ], className="mb-4 shadow-sm border-0")

        summary_stats = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    html.Div(html.I(className="bi bi-dna fs-3 text-primary"), className="me-3"),
                    html.Div([html.H3(len(unique_genes), className="mb-0 text-primary fw-bold"), html.Small("Total Unique Genes/Probes", className="text-muted fw-bold text-uppercase")])
                ], className="d-flex align-items-center")
            ]), className="h-100 shadow-sm border-start border-primary border-5"), width=12, md=4, className="mb-3"),
            
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    html.Div(html.I(className="bi bi-collection fs-3 text-info"), className="me-3"),
                    html.Div([html.H3(num_items, className="mb-0 text-info fw-bold"), html.Small("Items Compared", className="text-muted fw-bold text-uppercase")])
                ], className="d-flex align-items-center")
            ]), className="h-100 shadow-sm border-start border-info border-5"), width=12, md=4, className="mb-3"),
            
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div([
                    html.Div(html.I(className="bi bi-asterisk fs-3 text-success"), className="me-3"),
                    html.Div([html.H3(sum(len(v) for v in gene_sources.values()), className="mb-0 text-success fw-bold"), html.Small("Total Occurrences", className="text-muted fw-bold text-uppercase")])
                ], className="d-flex align-items-center")
            ]), className="h-100 shadow-sm border-start border-success border-5"), width=12, md=4, className="mb-3"),
        ])

        visual_section = None
        intersection_data_list = []
        
        intersections_help_popover = dbc.Popover([
            dbc.PopoverHeader("Intersection Logic"),
            dbc.PopoverBody([
                html.Div([html.Span("■", style={'color': '#6f42c1', 'fontSize': '1.2rem'}), " Purple: Core genes shared by ALL sources (Highest Priority)."], className="mb-2 small"),
                html.Div([html.Span("■", style={'color': '#0dcaf0', 'fontSize': '1.2rem'}), " Cyan: Genes/Probes shared by a subset of sources."], className="mb-2 small"),
                html.Div([html.Span("■", style={'color': 'gray', 'fontSize': '1.2rem'}), " Gray: Genes/Probes unique to a single source."], className="mb-2 small"),
                html.Hr(className="my-2"),
                html.Div([html.I(className="bi bi-plus-circle me-1"), "Click 'Add' to save any specific intersection subset to your panel."], className="small text-primary fw-bold")
            ])
        ], target="intersection-help-icon", trigger="legacy", placement="left")

        # --- CASO A: VENN (2-3 items) ---
        if 2 <= num_items <= 3:
            try:
                # (Lógica Venn igual a la anterior...)
                sets_list = list(item_gene_sets.values())
                labels_list = list(item_gene_sets.keys())
                VENN_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c'] 
                COLOR_INTERSECTION_ALL = '#6f42c1' 
                COLOR_INTERSECTION_SECONDARY = '#0dcaf0' 

                fig, ax = plt.subplots(figsize=(6, 6))
                sets_list_for_drawing = [s.copy() or {'__TEMP__'} for s in sets_list]
                set_colors = VENN_COLORS[:len(sets_list)]
                
                if len(sets_list) == 2:
                    layout_algorithm2 = DefaultLayoutAlgorithm2(fixed_subset_sizes=(1, 1, 1))
                    v = venn2(sets_list_for_drawing, set_labels=['', ''], ax=ax, set_colors=set_colors, alpha=0.5, layout_algorithm=layout_algorithm2)
                elif len(sets_list) == 3:
                    layout_algorithm = DefaultLayoutAlgorithm(fixed_subset_sizes=(1, 1, 1, 1, 1, 1, 1))
                    v = venn3(sets_list_for_drawing, set_labels=['', '', ''], ax=ax, set_colors=set_colors, alpha=0.5, layout_algorithm=layout_algorithm)

                centers = getattr(v, 'centers', None)
                if getattr(v, 'subset_labels', None):
                    for t in v.subset_labels:
                        if t:
                            t.set_fontsize(14)
                            t.set_fontweight('bold')
                if centers and getattr(v, 'set_labels', None):
                    center_points = []
                    radii = []
                    for center in centers:
                        x = getattr(center, 'x', center[0] if hasattr(center, '__iter__') else 0)
                        y = getattr(center, 'y', center[1] if hasattr(center, '__iter__') else 0)
                        center_points.append((x, y))
                    for circle in getattr(v, 'circles', []) or []:
                        radii.append(getattr(circle, 'radius', 0))
                    mean_x = sum(p[0] for p in center_points) / len(center_points)
                    mean_y = sum(p[1] for p in center_points) / len(center_points)

                    for i, t in enumerate(v.set_labels):
                        if i >= len(labels_list):
                            break
                        label = labels_list[i]
                        x, y = center_points[i]
                        vec_x = x - mean_x
                        vec_y = y - mean_y
                        norm = (vec_x ** 2 + vec_y ** 2) ** 0.5 or 1.0
                        radius = radii[i] if i < len(radii) else 0.6
                        offset = radius * 1.2 + 0.05
                        out_x = x + (vec_x / norm) * offset
                        out_y = y + (vec_y / norm) * offset
                        t.set_text(label)
                        t.set_position((out_x, out_y))
                        t.set_ha('left' if vec_x >= 0 else 'right')
                        t.set_va('center')
                        t.set_fontsize(14)
                        t.set_fontweight('bold')
                
                plt.title("Gene Overlap", fontsize=12, fontweight='bold')
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', pad_inches=0.3)
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)

                # Legend...
                legend_items = []
                for i, label in enumerate(labels_list):
                    display_label = label if len(label) < 30 else label[:27] + '...' 
                    legend_items.append(html.Div([
                        html.Div(style={'backgroundColor': VENN_COLORS[i], 'width': '12px', 'height': '12px', 'borderRadius': '50%', 'marginRight': '5px'}),
                        html.Span(display_label, title=label, style={'fontSize': '0.85rem'})
                    ], className="d-flex align-items-center me-3 mb-2"))

                # Intersection Data Logic...
                def create_intersection_entry(name, genes, color_hex, sources):
                    return {'name': name, 'genes': sorted(list(genes)), 'count': len(genes), 'color': color_hex, 'source_sets': sources}

                if len(sets_list) == 2:
                    int_all = sets_list[0] & sets_list[1]
                    if int_all: intersection_data_list.append(create_intersection_entry("Intersection (Both)", int_all, COLOR_INTERSECTION_ALL, [0, 1]))
                    int_a = sets_list[0] - sets_list[1]
                    if int_a: intersection_data_list.append(create_intersection_entry(f"Unique to {labels_list[0]}", int_a, VENN_COLORS[0], [0]))
                    int_b = sets_list[1] - sets_list[0]
                    if int_b: intersection_data_list.append(create_intersection_entry(f"Unique to {labels_list[1]}", int_b, VENN_COLORS[1], [1]))

                elif len(sets_list) == 3:
                    int_all = sets_list[0] & sets_list[1] & sets_list[2]
                    if int_all: intersection_data_list.append(create_intersection_entry("Intersection (All 3)", int_all, COLOR_INTERSECTION_ALL, [0,1,2]))
                    int_01 = (sets_list[0] & sets_list[1]) - sets_list[2]
                    if int_01: intersection_data_list.append(create_intersection_entry(f"{labels_list[0]} & {labels_list[1]} only", int_01, COLOR_INTERSECTION_SECONDARY, [0,1]))
                    int_02 = (sets_list[0] & sets_list[2]) - sets_list[1]
                    if int_02: intersection_data_list.append(create_intersection_entry(f"{labels_list[0]} & {labels_list[2]} only", int_02, COLOR_INTERSECTION_SECONDARY, [0,2]))
                    int_12 = (sets_list[1] & sets_list[2]) - sets_list[0]
                    if int_12: intersection_data_list.append(create_intersection_entry(f"{labels_list[1]} & {labels_list[2]} only", int_12, COLOR_INTERSECTION_SECONDARY, [1,2]))
                    int_0 = sets_list[0] - (sets_list[1] | sets_list[2])
                    if int_0: intersection_data_list.append(create_intersection_entry(f"Unique to {labels_list[0]}", int_0, VENN_COLORS[0], [0]))
                    int_1 = sets_list[1] - (sets_list[0] | sets_list[2])
                    if int_1: intersection_data_list.append(create_intersection_entry(f"Unique to {labels_list[1]}", int_1, VENN_COLORS[1], [1]))
                    int_2 = sets_list[2] - (sets_list[0] | sets_list[1])
                    if int_2: intersection_data_list.append(create_intersection_entry(f"Unique to {labels_list[2]}", int_2, VENN_COLORS[2], [2]))

                # Cards...
                int_cards = []
                for idx, d in enumerate(intersection_data_list):
                    int_cards.append(dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span(f"{d['count']}", className="badge me-2 rounded-pill", style={'backgroundColor': d['color'], 'fontSize': '0.9rem'}),
                                html.Strong(d['name'], style={'fontSize':'0.9rem'})
                            ], className="d-flex align-items-center mb-2"),
                            html.Div(', '.join(d['genes'][:15]) + ('...' if d['count']>15 else ''), className="text-muted small mb-2 fst-italic"),
                            dbc.Button([html.I(className="bi bi-plus-lg me-1"), "Add"], id={'type': 'add-intersection-btn', 'index': idx}, size="sm", outline=True, color="primary", className="w-100")
                        ], className="p-2")
                    ], className="mb-2 border-light bg-light"))

                visual_section = dbc.Card([
                    dbc.CardHeader([
                        html.Div([
                            html.I(className="bi bi-intersect me-2"),
                            html.H6("Overlap Analysis (Venn)", className="d-inline-block m-0 fw-bold"),
                            html.I(id="intersection-help-icon", className="bi bi-question-circle-fill text-muted ms-2", style={'cursor': 'pointer'})
                        ], className="d-flex align-items-center text-primary")
                    ], className="bg-white border-bottom"),
                    dbc.CardBody([
                        intersections_help_popover,
                        dbc.Row([
                            dbc.Col([
                                html.Div(legend_items, className="d-flex flex-wrap mb-3 justify-content-center"),
                                html.Div(html.Img(src=f"data:image/png;base64,{img_base64}", style={'maxWidth': '100%', 'height': 'auto'}), className="text-center")
                            ], width=12, lg=7, className="border-end"),
                            dbc.Col([
                                html.H6("Ranked Intersections", className="text-muted small fw-bold text-uppercase mb-3"),
                                html.Div(int_cards, style={'maxHeight': '400px', 'overflowY': 'auto', 'paddingRight': '5px'})
                            ], width=12, lg=5)
                        ])
                    ])
                ], className="shadow-sm border-0 mb-4")

            except Exception as e:
                visual_section = dbc.Alert(f"Error generating Venn: {e}", color="danger")

        # --- CASO B: MATRIX (4+ items) ---
        elif num_items >= 4:
            # (Lógica Matrix igual a la anterior...)
            intersection_map = defaultdict(list)
            for gene, sources in gene_sources.items():
                signature = tuple(sorted(sources))
                intersection_map[signature].append(gene)
            sorted_intersections = sorted(intersection_map.items(), key=lambda x: (len(x[0]), len(x[1])), reverse=True)

            matrix_cards = []
            count_idx = 0
            for signature, genes in sorted_intersections:
                count = len(genes)
                intersection_data_list.append({'name': f"Intersection: {len(signature)} sources", 'genes': sorted(genes), 'count': count, 'source_sets': []})
                
                dots_row = []
                for source in ordered_source_names:
                    is_present = source in signature
                    dot_color = '#198754' if is_present else '#e9ecef' # Green vs Gray
                    dot = html.Div([
                        html.Div(style={'width': '12px', 'height': '12px', 'borderRadius': '50%', 'backgroundColor': dot_color, 'marginRight': '4px', 'display': 'inline-block'}),
                    ], title=source, className="d-inline-block")
                    dots_row.append(dot)

                badge_type = dbc.Badge("ALL", color="purple", className="me-2") if len(signature) == num_items else \
                             (dbc.Badge("UNIQUE", color="secondary", className="me-2") if len(signature) == 1 else \
                              dbc.Badge("MIX", color="info", text_color="dark", className="me-2"))

                # --- 💡 MODIFICACIÓN: Borde más visible (border border-secondary) ---
                card = dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H4(count, className="mb-0 text-dark fw-bold"),
                                html.Small("genes", className="text-muted"),
                            ], width=2, className="d-flex flex-column align-items-center justify-content-center border-end"),
                            
                            dbc.Col([
                                html.Div(badge_type, className="mb-1"),
                                html.Div(dots_row, className="mb-1"),
                                html.Small(f"{', '.join(genes[:10])}...", className="text-muted fst-italic")
                            ], width=8, className="ps-3"),
                            
                            dbc.Col([
                                dbc.Button([html.I(className="bi bi-plus-lg")], id={'type': 'add-intersection-btn', 'index': count_idx}, color="outline-primary", size="sm")
                            ], width=2, className="d-flex align-items-center justify-content-end pe-3")
                        ], className="g-0 align-items-center")
                    ], className="p-2")
                ], className="mb-2 shadow-sm border border-secondary border-2") # <-- CAMBIO APLICADO AQUÍ
                
                matrix_cards.append(card)
                count_idx += 1

            visual_section = dbc.Card([
                 dbc.CardHeader([
                    html.Div([
                        html.I(className="bi bi-grid-3x3-gap me-2"),
                        html.H6("Overlap Analysis (Matrix)", className="d-inline-block m-0 fw-bold"),
                        html.I(id="intersection-help-icon", className="bi bi-question-circle-fill text-muted ms-2", style={'cursor': 'pointer'})
                    ], className="d-flex align-items-center text-primary")
                ], className="bg-white border-bottom"),
                dbc.CardBody([
                    intersections_help_popover,
                    html.P("Ordered by complexity. Top cards show genes present in the most sources.", className="text-muted small mb-3"),
                    html.Div(matrix_cards, style={'maxHeight': '500px', 'overflowY': 'auto'})
                ])
            ], className="shadow-sm border-0 mb-4")

        # --- FREQUENCY CHART ---
        gene_frequency = []
        for gene, sources in gene_sources.items():
            # CORRECCIÓN: Restauro la columna 'Sources' (comma separated)
            gene_frequency.append({
                'Gene': gene, 
                'Frequency': len(sources),
                'Sources': ", ".join(sources) # <--- AÑADIDO
            })
        gene_freq_df = pd.DataFrame(gene_frequency).sort_values('Frequency', ascending=False)
        gene_freq_df.insert(0, 'N°', range(1, len(gene_freq_df) + 1))

        fig_bar = px.bar(gene_freq_df, x='Gene', y='Frequency', 
                         title=f'Gene Frequency (All {len(gene_freq_df)} genes)', 
                         labels={'Frequency': 'Source Count'}, 
                         color='Frequency', 
                         color_continuous_scale='Blues')
        
        fig_bar.update_layout(
            xaxis_tickangle=-45, 
            height=400, 
            margin=dict(l=40, r=20, t=40, b=80), 
            #plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                range=[-0.5, 49.5], 
                rangeslider=dict(visible=True)
            )
        )

        chart_help_popover = dbc.Popover([
            dbc.PopoverHeader("Chart Navigation"),
            dbc.PopoverBody([
                html.Div("Shows gene frequency across selected sources."),
                html.Div([html.Strong("Navigation:"), " Use the slider bar below the X-axis to scroll through all genes."]),
                html.Div("Taller bars and brighter colors indicate higher consensus (present in more sources).", className="small text-muted mt-2")
            ])
        ], target="chart-help-icon", trigger="legacy", placement="left")

        chart_section = dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="bi bi-bar-chart-fill me-2"),
                    html.H6("Gene Frequency Chart", className="d-inline-block m-0 fw-bold"),
                    html.I(id="chart-help-icon", className="bi bi-question-circle-fill text-muted ms-2", style={'cursor': 'pointer'})
                ], className="d-flex align-items-center text-primary")
            ], className="bg-white border-bottom"),
            dbc.CardBody([
                chart_help_popover,
                dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
            ])
        ], className="shadow-sm border-0 mb-4")

        # --- DATA TABLE (Modified with Filters and Help) ---
        
        # 1. Popover de Ayuda de Tabla (Copiado de genes_analysis.py)
        table_help_popover = dbc.Popover(
            [
                dbc.PopoverHeader("Table Filtering & Sorting Help"),
                dbc.PopoverBody([
                    html.Div([
                        html.Strong("To Sort:"),
                        html.Span(" Click the arrows (▲/▼) in the column header to sort ascending or descending.", className="small text-muted")
                    ], className="mb-2"),

                    html.Div([
                        html.Strong("Text Filters:"),
                        html.Span(" Type a value (e.g., ", className="small text-muted"),
                        html.Code("TP53", className="small"),
                        html.Span(") for exact match. Use ", className="small text-muted"),
                        html.Code("contains TP", className="small"),
                        html.Span(" or ", className="small text-muted"),
                        html.Code("!= val", className="small"),
                        html.Span(" to exclude.", className="small text-muted")
                    ], className="mb-2"),

                    html.Div([
                        html.Strong("Numeric Filters:"),
                        html.Span(" Use operators like ", className="small text-muted"),
                        html.Code("> 0.8", className="small"),
                        html.Span(", ", className="small text-muted"),
                        html.Code("<= 10", className="small"),
                        html.Span(" or ranges.", className="small text-muted")
                    ], className="mb-2"),

                    html.Div([
                        html.Strong("Tips:"),
                        html.Span(" Combine filters across columns. Use the 'Clear All Filters' button to reset.", className="small text-muted")
                    ], className="mb-0"),
                ])
            ],
            id="gga-table-filter-help-popover",
            target="gga-table-filter-help-icon",
            trigger="legacy",
            placement="bottom-start",
        )

        # 2. Controls Row (Detailed Data + Icon + Clear Button)
        table_controls = html.Div([
            html.Div([
                html.H6("Detailed Data", className="fw-bold m-0"),
                html.I(id="gga-table-filter-help-icon", className="bi bi-question-circle-fill text-muted ms-2", style={'cursor': 'pointer'}),
            ], className="d-flex align-items-center"),
            dbc.Button("Clear Filters", id='gga-table-clear-filters-btn', size="sm", color="secondary", outline=True)
        ], className="d-flex justify-content-between align-items-center mb-2 mt-2")

        table_section = dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="bi bi-table me-2"),
                    html.H6("Complete Gene List", className="d-inline-block m-0 fw-bold")
                ], className="d-flex align-items-center text-primary")
            ], className="bg-white border-bottom"),
            dbc.CardBody([
                table_help_popover,
                table_controls,
                dash_table.DataTable(
                    id='gga-genes-table', # Added ID
                    data=gene_freq_df.to_dict('records'),
                    columns=[{"name": i, "id": i} for i in gene_freq_df.columns],
                    page_size=20,
                    style_table={'overflowX': 'auto'},
                    style_header={'backgroundColor': '#f8f9fa', 'color': '#333', 'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                    style_filter={'backgroundColor': 'rgb(220, 235, 255)', 'border': '1px solid rgb(180, 200, 220)', 'fontWeight': 'bold', 'color': '#333'},
                    style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'sans-serif', 'fontSize': '0.9rem'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
                    # CORRECCIÓN: Ajuste de anchos de columna según imagen
                    style_cell_conditional=[
                        {'if': {'column_id': 'N°'}, 'width': '100px'},
                        {'if': {'column_id': 'Frequency'}, 'width': '100px'},
                        {'if': {'column_id': 'Gene'}, 'width': '300px'}, # El resto del espacio
                        {'if': {'column_id': 'Sources'}, 'width': 'auto'}
                    ],
                    filter_action="native",
                    sort_action="native"
                )
            ])
        ], className="shadow-sm border-0 mb-4")

        final_layout = [buttons_row]
        if num_items >= 2:
            final_layout.append(summary_stats)
            if visual_section: final_layout.append(visual_section)
            final_layout.append(chart_section)
        
        final_layout.append(table_section)

        store_data = {'genes': list(unique_genes), 'sources': list(item_gene_sets.keys())}
        
        return html.Div(final_layout), store_data, intersection_data_list, selected_indices

    # 3. Callback Clear (Sin Cambios)
    @app.callback(
        [Output({'type': 'gene-group-card-checkbox', 'index': ALL}, 'value'),
         Output('selected-gene-group-indices-store', 'data', allow_duplicate=True)],
        Input('clear-gene-groups-selection-btn', 'n_clicks'),
        State({'type': 'gene-group-card-checkbox', 'index': ALL}, 'value'),
        prevent_initial_call=True
    )
    def clear_gene_groups_checkboxes(n_clicks, current_values):
        if not n_clicks: raise PreventUpdate
        return [[] for _ in current_values], []

    # 4. Callback Union Modal (Sin Cambios)
    @app.callback(
        [Output('gene-groups-analysis-tab-modal', 'is_open', allow_duplicate=True),
         Output('gene-groups-analysis-tab-modal-info', 'children', allow_duplicate=True),
         Output('gene-groups-analysis-tab-name-input', 'value', allow_duplicate=True),
         Output('gene-groups-analysis-tab-comment-input', 'value', allow_duplicate=True),
         Output('gene-groups-analysis-tab-temp-store', 'data', allow_duplicate=True)],
        [Input('save-combined-group-btn-top', 'n_clicks')],
        State('gene-groups-analysis-tab-temp-store', 'data'),
        prevent_initial_call=True
    )
    def open_combined_group_modal_for_selection(n_clicks, genes_store_data):
        if not n_clicks: raise PreventUpdate
        if genes_store_data and genes_store_data.get('genes'):
            sources = genes_store_data.get('sources', [])
            gene_count = len(genes_store_data.get('genes', []))
            genes_store_data['meta_type'] = 'combined_selection'
            modal_info = html.Div([html.P([html.Strong("Adding Combined Selection: ")]), html.P([html.Strong("Total Unique Genes/Probes: "), html.Span(f"{gene_count}")])])
            return True, modal_info, f"Combined Group - {gene_count} Genes/Probes", f"Combined from {len(sources)} sources.", genes_store_data
        raise PreventUpdate

    # 5. Callback Intersection Modal (Sin Cambios)
    @app.callback(
        [Output('gene-groups-analysis-tab-modal', 'is_open', allow_duplicate=True),
         Output('gene-groups-analysis-tab-modal-info', 'children', allow_duplicate=True),
         Output('gene-groups-analysis-tab-name-input', 'value', allow_duplicate=True),
         Output('gene-groups-analysis-tab-comment-input', 'value', allow_duplicate=True),
         Output('gene-groups-analysis-tab-temp-store', 'data', allow_duplicate=True)],
        [Input({'type': 'add-intersection-btn', 'index': ALL}, 'n_clicks')],
        [State('intersection-data-temp-store', 'data'),
         State({'type': 'add-intersection-btn', 'index': ALL}, 'id')],
        prevent_initial_call=True
    )
    def open_intersection_modal(single_n_clicks, intersection_data, single_btn_ids):
        ctx = dash.callback_context
        if not intersection_data or not any(c is not None and c > 0 for c in single_n_clicks):
            raise PreventUpdate
            
        triggered_dict = ctx.triggered_id 
        if triggered_dict and triggered_dict.get('type') == 'add-intersection-btn':
             index = triggered_dict['index']
             if 0 <= index < len(intersection_data):
                intersection = intersection_data[index]
                modal_info = html.Div([
                    html.P([html.Strong("Adding Intersection: "), html.Span(intersection['name'])]),
                    html.P([html.Strong("Gene Count: "), html.Span(f"{intersection['count']}")])
                ])
                group_data = {'genes': intersection['genes'], 'sources': [intersection['name']], 'meta_type': 'single_intersection', 'name': intersection['name']}
                return True, modal_info, intersection['name'], f"Intersection group with {intersection['count']} genes.", group_data

        raise PreventUpdate

    # 6. Callback for Clearing Table Filters
    @app.callback(
        Output('gga-genes-table', 'filter_query'),
        Input('gga-table-clear-filters-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def clear_gga_table_filters(n_clicks):
        if n_clicks:
            return ""
        raise PreventUpdate
