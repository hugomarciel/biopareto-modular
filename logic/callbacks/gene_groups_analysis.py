# logic/callbacks/gene_groups_analysis.py

import dash
from dash import Output, Input, State, dcc, html, dash_table, ALL, MATCH # <--- IMPORTANTE: Se agregó MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from collections import defaultdict
import plotly.express as px
from datetime import datetime
import numpy as np
import io 

# Imports para Venn (si están disponibles)
try:
    from matplotlib_venn import venn2, venn3
    import matplotlib.pyplot as plt
    import base64
except ImportError:
    pass


def register_gene_groups_callbacks(app):

    # --- NUEVO: CLIENTSIDE CALLBACK PARA FEEDBACK INSTANTÁNEO ---
    # Este callback se ejecuta en el navegador (JS) inmediatamente al hacer clic,
    # sin esperar al servidor Python. Elimina el "lag" visual.
    app.clientside_callback(
        """
        function(selected_value) {
            // selected_value es una lista. Si tiene elementos, está seleccionado.
            const is_selected = selected_value && selected_value.length > 0;
            
            if (is_selected) {
                return [
                    {
                        'transition': 'all 0.2s ease-in-out',
                        'border': '2px solid #0d6efd',       // Borde Azul Fuerte
                        'backgroundColor': '#f0f8ff',        // Fondo Azul Pálido
                        'transform': 'scale(1.02)',          // Efecto Pop sutil
                        'cursor': 'pointer'
                    },
                    "h-100 shadow" // Clase con sombra más fuerte
                ];
            } else {
                return [
                    {
                        'transition': 'all 0.2s ease-in-out',
                        'border': '1px solid rgba(0,0,0,0.125)', // Borde default
                        'backgroundColor': 'white',
                        'transform': 'scale(1)',
                        'cursor': 'pointer'
                    },
                    "h-100 shadow-sm hover-shadow" // Clase normal
                ];
            }
        }
        """,
        [Output({'type': 'gene-group-card-wrapper', 'index': MATCH}, 'style'),
         Output({'type': 'gene-group-card-wrapper', 'index': MATCH}, 'className')],
        Input({'type': 'gene-group-card-checkbox', 'index': MATCH}, 'value'),
        prevent_initial_call=True
    )
    # -----------------------------------------------------------

    # 1. Callback para renderizar el selector visual de Gene Groups
    @app.callback(
        Output('gene-groups-visual-selector', 'children'),
        [Input('interest-panel-store', 'data'),
         Input('selected-gene-group-indices-store', 'data')], 
        State('data-store', 'data')
    )
    def render_visual_gene_groups_selector(items, selected_indices_list, data_store):
        """Render visual card-based selector for gene groups analysis, maintaining selection."""
        if not items:
            return html.P("No items available. Add items to your Interest Panel first.",
                         className="text-muted text-center py-4")

        all_solutions_dict = {}
        if data_store:
            for front in data_store.get("fronts", []):
                for sol in front["data"]:
                    all_solutions_dict[sol['solution_id']] = sol
        
        if selected_indices_list is None:
            selected_indices_list = []

        cards = []
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', '')
            item_comment = item.get('comment', '')

            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            # Crear badge e ícono
            if item_type == 'solution':
                badge_color = "primary"
                badge_text = "Solution"
                icon = "🔵"
                sol_data = item.get('data', {})
                sol_id = sol_data.get('id', 'Unknown')
                genes = sol_data.get('selected_genes', [])
                if not genes and sol_id in all_solutions_dict:
                    genes = all_solutions_dict[sol_id].get('selected_genes', [])
                gene_count = len(genes)
                front_name = sol_data.get('front_name', 'Unknown')
                description = f"{gene_count} genes | {front_name}"

            elif item_type == 'solution_set':
                badge_color = "info"
                badge_text = "Solution Set"
                icon = "📦"
                solutions = item.get('data', {}).get('solutions', [])
                unique_genes = set()
                for sol in solutions:
                    sol_id = sol.get('id', '')
                    genes = sol.get('selected_genes', [])
                    if not genes and sol_id in all_solutions_dict:
                        genes = all_solutions_dict[sol_id].get('selected_genes', [])
                    unique_genes.update(genes)
                gene_count = len(unique_genes)
                description = f"{len(solutions)} solutions | {gene_count} unique genes"

            elif item_type == 'gene_set':
                badge_color = "success"
                badge_text = "Gene Group"
                icon = "🧬"
                genes = item.get('data', {}).get('genes', [])
                frequency = item.get('data', {}).get('frequency', 'N/A')
                description = f"{len(genes)} genes | Freq: {frequency}%"

            elif item_type == 'individual_gene':
                badge_color = "warning"
                badge_text = "Gene"
                icon = "🔬"
                gene = item.get('data', {}).get('gene', 'Unknown')
                description = f"Gene: {gene}"

            elif item_type == 'combined_gene_group':
                badge_color = "success"
                badge_text = "Combined Group"
                icon = "🎯"
                gene_count = item.get('data', {}).get('gene_count', 0)
                source_count = len(item.get('data', {}).get('source_items', []))
                description = f"{gene_count} genes | {source_count} sources"
            else:
                continue

            # Estado inicial (para renderizado desde servidor)
            is_selected_bool = idx in selected_indices_list
            is_selected_value = [idx] if is_selected_bool else []
            
            # Definimos estilos base para que coincidan con el clientside callback
            if is_selected_bool:
                card_style = {'transition': 'all 0.2s ease-in-out', 'border': '2px solid #0d6efd', 'backgroundColor': '#f0f8ff', 'transform': 'scale(1.02)', 'cursor': 'pointer'}
                card_class_name = "h-100 shadow"
            else:
                card_style = {'transition': 'all 0.2s ease-in-out', 'border': '1px solid rgba(0,0,0,0.125)', 'backgroundColor': 'white', 'transform': 'scale(1)', 'cursor': 'pointer'}
                card_class_name = "h-100 shadow-sm hover-shadow"

            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                value=is_selected_value,
                                # El ID del checkbox que dispara el clientside callback
                                id={'type': 'gene-group-card-checkbox', 'index': idx},
                                switch=True,
                                style={'transform': 'scale(1.3)'}
                            )
                        ], style={
                            'position': 'absolute',
                            'top': '10px',
                            'right': '10px',
                            'zIndex': '10'
                        }),
                        html.Div([
                            html.Div([
                                html.Span(icon, style={'fontSize': '1.2rem', 'marginRight': '8px'}),
                                dbc.Badge(badge_text, color=badge_color, className="ms-1", style={'fontSize': '0.7rem'})
                            ], className="d-flex align-items-center mb-1"),
                            html.Strong(item_name, className="d-block mb-1", style={'fontSize': '0.9rem'}),
                            html.P(description, className="text-muted small mb-1", style={'fontSize': '0.75rem'}),
                            html.P(item_comment, className="text-muted small fst-italic mb-0", style={'fontSize': '0.7rem'}) if item_comment else None
                        ], style={'paddingRight': '40px'})
                    ], className="p-2", style={'minHeight': '120px', 'position': 'relative'})
                ], 
                # ID necesario para que el clientside callback sepa qué tarjeta modificar
                id={'type': 'gene-group-card-wrapper', 'index': idx}, 
                className=card_class_name, 
                style=card_style)
            ], width=12, md=6, lg=3, className="mb-3")

            cards.append(card)

        if not cards:
            return html.P("No compatible items found in Interest Panel.",
                         className="text-muted text-center py-4")

        return dbc.Row(cards, className="g-3")

    # 2. Callback principal para analizar la selección visual
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
        """Automatically analyze and display combined genes when visual selection changes."""
        
        selected_indices = []
        for values in checkbox_values:
            if values and len(values) > 0:
                selected_indices.extend(values) 

        if not selected_indices or not items:
            return html.Div("Select items to analyze.", className="alert alert-info mt-4"), None, [], []

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
        
        summary_stats = dbc.Card([
            dbc.CardHeader(html.H5("Summary Statistics", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H3(len(unique_genes), className="text-primary mb-0"),
                        html.P("Unique Genes", className="text-muted small")
                    ], width=4),
                    dbc.Col([
                        html.H3(num_items, className="text-info mb-0"),
                        html.P("Items Compared", className="text-muted small")
                    ], width=4),
                    dbc.Col([
                        html.H3(sum(len(v) for v in gene_sources.values()), className="text-success mb-0"),
                        html.P("Total Gene Instances", className="text-muted small")
                    ], width=4)
                ])
            ])
        ], className="mb-4")

        visual_section = None
        intersection_data_list = []
        
        # CASO A: Diagrama de Venn (2-3 items)
        if 2 <= num_items <= 3:
            try:
                sets_list = list(item_gene_sets.values())
                labels_list = list(item_gene_sets.keys())
                VENN_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c'] 
                
                COLOR_INTERSECTION_ALL = '#6f42c1' 
                COLOR_INTERSECTION_SECONDARY = '#0dcaf0' 

                fig, ax = plt.subplots(figsize=(6, 6))
                sets_list_for_drawing = [s.copy() or {'__TEMP__'} for s in sets_list]
                set_colors = VENN_COLORS[:len(sets_list)]
                
                if len(sets_list) == 2:
                    v = venn2(sets_list_for_drawing, set_labels=['', ''], ax=ax, set_colors=set_colors, alpha=0.5)
                elif len(sets_list) == 3:
                    v = venn3(sets_list_for_drawing, set_labels=['', '', ''], ax=ax, set_colors=set_colors, alpha=0.5)
                
                plt.title("Gene Overlap", fontsize=12, fontweight='bold')
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)

                legend_items = []
                for i, label in enumerate(labels_list):
                    display_label = label if len(label) < 30 else label[:27] + '...' 
                    legend_items.append(html.Div([
                        html.Div(style={'backgroundColor': VENN_COLORS[i], 'width': '12px', 'height': '12px', 'borderRadius': '50%', 'marginRight': '5px'}),
                        html.Span(display_label, title=label, style={'fontSize': '0.85rem'})
                    ], className="d-flex align-items-center me-3 mb-2"))

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

                int_cards = []
                for idx, d in enumerate(intersection_data_list):
                    int_cards.append(dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span(f"{d['count']}", className="badge me-2", style={'backgroundColor': d['color'], 'fontSize': '0.9rem'}),
                                html.Strong(d['name'], style={'fontSize':'0.9rem'})
                            ], className="d-flex align-items-center mb-2"),
                            html.Div(', '.join(d['genes'][:15]) + ('...' if d['count']>15 else ''), className="text-muted small mb-2"),
                            dbc.Button("Add to Panel", id={'type': 'add-intersection-btn', 'index': idx}, size="sm", outline=True, color="primary")
                        ], className="p-2")
                    ], className="mb-2"))

                visual_section = dbc.Row([
                    dbc.Col([
                        html.H5("Venn Diagram", className="mb-3"),
                        html.Div(legend_items, className="d-flex flex-wrap mb-2"),
                        html.Img(src=f"data:image/png;base64,{img_base64}", style={'maxWidth': '100%', 'height': 'auto'})
                    ], width=12, lg=6),
                    dbc.Col([
                        html.H5("Intersections", className="mb-3"),
                        html.Div(int_cards, style={'maxHeight': '450px', 'overflowY': 'auto'})
                    ], width=12, lg=6)
                ])

            except Exception as e:
                visual_section = html.Div(f"Error generating Venn: {e}", className="text-danger")

        # CASO B: Matrix Cards (4+ items)
        elif num_items >= 4:
            
            intersection_map = defaultdict(list)
            for gene, sources in gene_sources.items():
                signature = tuple(sorted(sources))
                intersection_map[signature].append(gene)
            
            sorted_intersections = sorted(
                intersection_map.items(), 
                key=lambda x: (len(x[0]), len(x[1])),
                reverse=True
            )

            matrix_cards = []
            matrix_header = dbc.Row([
                dbc.Col(html.Strong("Count", className="small text-muted"), width=2),
                dbc.Col(html.Strong("Source Matrix", className="small text-muted"), width=8),
                dbc.Col(html.Strong("Action", className="small text-muted"), width=2),
            ], className="mb-2 border-bottom pb-1 mx-1 g-0")
            matrix_cards.append(matrix_header)
            
            count_idx = 0
            for signature, genes in sorted_intersections:
                count = len(genes)
                intersection_data_list.append({
                    'name': f"Intersection: {len(signature)} sources",
                    'genes': sorted(genes),
                    'count': count,
                    'source_sets': [] 
                })
                
                dots_row = []
                for source in ordered_source_names:
                    is_present = source in signature
                    tooltip_id = f"tooltip-src-{count_idx}-{ordered_source_names.index(source)}"
                    dot = html.Div([
                        html.Span("●" if is_present else "○", id=tooltip_id,
                                  style={'color': '#28a745' if is_present else '#dee2e6', 'fontSize': '1.4rem', 'cursor': 'help', 'marginRight': '6px', 'lineHeight': '1'}),
                        dbc.Tooltip(source, target=tooltip_id, placement="top")
                    ], className="d-inline-block")
                    dots_row.append(dot)

                badge_type = dbc.Badge("ALL", color="success", className="me-2") if len(signature) == num_items else \
                             (dbc.Badge("UNIQUE", color="primary", className="me-2") if len(signature) == 1 else \
                              dbc.Badge("MIX", color="warning", text_color="dark", className="me-2"))

                preview_text = f"Preview: {', '.join(genes[:20])}{'...' if len(genes)>20 else ''}"

                card = dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H4(count, className="mb-0 text-dark fw-bold"),
                                html.Small("genes", className="text-muted"),
                                html.Div(badge_type, className="mt-1")
                            ], width=2, className="d-flex flex-column align-items-center justify-content-center border-end"),
                            
                            dbc.Col([
                                html.Div(dots_row, className="d-flex flex-wrap align-items-center mb-1"),
                                html.Div(
                                    html.Small(preview_text, className="text-muted fst-italic"),
                                    style={'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis', 'width': '100%', 'display': 'block'}
                                )
                            ], width=8, className="d-flex flex-column justify-content-center ps-3"),
                            
                            dbc.Col([
                                dbc.Button("Add Group", id={'type': 'add-intersection-btn', 'index': count_idx}, color="outline-dark", size="sm", className="w-100")
                            ], width=2, className="d-flex align-items-center pe-3")
                        ], className="g-0 align-items-center")
                    ], className="p-2")
                ], className="mb-2 shadow-sm")
                matrix_cards.append(card)
                count_idx += 1

            visual_section = html.Div([
                html.Div([html.H5(f"Detailed Intersection Analysis", className="mb-0"), html.P("Visual matrix showing gene overlap patterns (Sorted by Complexity).", className="text-muted small")], className="mb-3"),
                html.Div([html.Span("● Present", className="text-success fw-bold me-3"), html.Span("○ Absent", className="text-muted fw-bold")], className="mb-3 small border p-2 rounded bg-light d-inline-block"),
                html.Div(matrix_cards, style={'maxHeight': '600px', 'overflowY': 'auto'})
            ])

        gene_frequency = []
        for gene, sources in gene_sources.items():
            gene_frequency.append({'Gene': gene, 'Frequency': len(sources), 'Sources': ', '.join(sources[:3]) + ('...' if len(sources) > 3 else '')})
        
        gene_freq_df = pd.DataFrame(gene_frequency).sort_values('Frequency', ascending=False)
        gene_freq_df.insert(0, 'N°', range(1, len(gene_freq_df) + 1))

        default_items_to_show = 50
        fig_bar = px.bar(gene_freq_df, x='Gene', y='Frequency', title=f'Gene Frequency (Top {default_items_to_show} shown)', labels={'Frequency': 'Number of Sources'}, color='Frequency', color_continuous_scale='Blues')
        max_range = min(default_items_to_show, len(gene_freq_df))
        fig_bar.update_layout(xaxis_tickangle=-45, height=400, xaxis_range=[-0.5, max_range - 0.5], xaxis_rangeslider=dict(visible=True, thickness=0.1))

        table = dash_table.DataTable(
            data=gene_freq_df.to_dict('records'),
            columns=[{"name": i, "id": i} for i in gene_freq_df.columns],
            page_size=100,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'fontFamily': 'sans-serif'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )

        buttons_row = dbc.Row([
            dbc.Col([
                dbc.Button("Save Combined Group (Union)", id="save-combined-group-btn-top", color="success", className="me-2"),
                dbc.Button("Clear Selection", id="clear-gene-groups-selection-btn", color="secondary", outline=True)
            ], className="mb-3")
        ])

        final_layout = [buttons_row]
        if num_items == 1:
            final_layout.append(html.H5("Gene Frequency Table", className="mt-4 mb-3"))
            final_layout.append(table)
        elif num_items >= 2:
            final_layout.append(summary_stats)
            if visual_section: final_layout.append(visual_section)
            final_layout.append(html.H5("Gene Frequency Chart", className="mt-4 mb-3"))
            final_layout.append(dcc.Graph(figure=fig_bar))
            final_layout.append(html.Div([html.H5("Complete Gene List (Paginated)", className="mt-4 mb-3"), table]))

        store_data = {'genes': list(unique_genes), 'sources': list(item_gene_sets.keys())}
        
        return html.Div(final_layout), store_data, intersection_data_list, selected_indices

    # 3. Callback para limpiar (Sin cambios)
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

    # 4. Callback Modal Union (Sin cambios)
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
            modal_info = html.Div([html.P([html.Strong("Adding Combined Selection: ")]), html.P([html.Strong("Total Unique Genes: "), html.Span(f"{gene_count}")])])
            return True, modal_info, f"Combined Group - {gene_count} Genes", f"Combined from {len(sources)} sources.", genes_store_data
        raise PreventUpdate

    # 5. Callback Modal Intersección (Sin cambios)
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