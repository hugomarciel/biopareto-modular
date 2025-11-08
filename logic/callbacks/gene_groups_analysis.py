# logic/callbacks/gene_groups_analysis.py

import dash
from dash import Output, Input, State, dcc, html, ALL
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

    # 1. Callback para renderizar el selector visual de Gene Groups
    @app.callback(
        Output('gene-groups-visual-selector', 'children'),
        [Input('interest-panel-store', 'data'),
         Input('selected-gene-group-indices-store', 'data')], # Mantiene la selección
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

            is_selected = [idx] if idx in selected_indices_list else []
            
            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            dbc.Checklist(
                                options=[{"label": "", "value": idx}],
                                value=is_selected,
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
                ], className="h-100 shadow-sm hover-shadow", style={'transition': 'all 0.2s'})
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
         Output('selected-gene-group-indices-store', 'data')], # Guarda la selección
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
            # Si no hay selección, devolver el contenedor de resultados vacío, sin fallo.
            return html.Div("Select items to analyze.", className="alert alert-info mt-4"), None, [], []

        all_solutions_dict = {}
        if data_store:
            for front in data_store.get("fronts", []):
                for sol in front["data"]:
                    all_solutions_dict[sol['solution_id']] = sol

        # Collect all genes and their sources
        gene_sources = {}
        item_gene_sets = {}  # Clave: Nombre Único/Etiqueta, Valor: Set de genes

        for idx in selected_indices:
            if idx < len(items):
                item = items[idx]
                item_name_base = item.get('name', f'Item {idx}')
                item_type = item.get('type', '')
                
                if item_type == 'solution':
                    sol_data = item.get('data', {})
                    sol_id = sol_data.get('solution_id', 'Unknown')
                    front_name = sol_data.get('front_name', 'Unknown Front')
                    genes = sol_data.get('selected_genes', set())
                    if not genes and sol_id in all_solutions_dict:
                        genes = all_solutions_dict[sol_id].get('selected_genes', set())
                    
                    if genes:
                        # 🔑 CORRECCIÓN DE KEY: Usar nombre amigable para una solución individual
                        unique_key = f"{sol_id} (from {front_name})" 
                        item_gene_sets[unique_key] = set(genes)
                        for gene in genes:
                            gene_sources.setdefault(gene, []).append(unique_key)

                elif item_type == 'solution_set':
                    solutions = item.get('data', {}).get('solutions', [])
                    
                    # Desempaquetar el set de soluciones
                    for sol in solutions:
                        sol_id = sol.get('solution_id', sol.get('id', 'Unknown'))
                        front_name = sol.get('front_name', 'Unknown Front')
                        
                        # Fallback robusto para asegurar los genes
                        genes = sol.get('selected_genes', set())
                        if not genes and sol_id in all_solutions_dict:
                            genes = all_solutions_dict[sol_id].get('selected_genes', set())
                        
                        if genes:
                            # 🔑 CORRECCIÓN DE KEY: Usar nombre amigable para cada solución del set
                            display_key = f"{sol_id} (from {front_name})"
                            unique_key = display_key # Usar display_key como base
                            
                            # Manejo de duplicados: Añadir contador si el nombre ya existe
                            key_counter = 1
                            while unique_key in item_gene_sets:
                                unique_key = f"{display_key} ({key_counter})"
                                key_counter += 1
                                
                            item_gene_sets[unique_key] = set(genes)
                            for gene in genes:
                                gene_sources.setdefault(gene, []).append(unique_key)
                    
                elif item_type in ['gene_set', 'combined_gene_group']:
                    genes_list = item.get('data', {}).get('genes', [])
                    
                    if genes_list:
                        # 🔑 CORRECCIÓN DE KEY: Usar el nombre del ítem del panel directamente
                        display_key = item_name_base 
                        unique_key = display_key # Usar display_key como base
                        
                        # Manejo de duplicados: Añadir contador si el nombre ya existe
                        key_counter = 1
                        while unique_key in item_gene_sets:
                            unique_key = f"{display_key} ({key_counter})"
                            key_counter += 1
                            
                        item_gene_sets[unique_key] = set(genes_list)
                        for gene in genes_list:
                            gene_sources.setdefault(gene, []).append(unique_key)

                elif item_type == 'individual_gene':
                    gene = item.get('data', {}).get('gene', '')
                    if gene:
                        # 🔑 CORRECCIÓN DE KEY: Usar el nombre del gen
                        display_key = f"Gene: {gene}"
                        unique_key = display_key # Usar display_key como base
                        
                        # Manejo de duplicados: Añadir contador si el nombre ya existe
                        key_counter = 1
                        while unique_key in item_gene_sets:
                            unique_key = f"{display_key} ({key_counter})"
                            key_counter += 1
                            
                        item_gene_sets[unique_key] = {gene}
                        gene_sources.setdefault(gene, []).append(unique_key)


        unique_genes = set(gene_sources.keys())
        
        # --- Generar Componentes de Resultados ---
        
        # A. Summary Stats (No modificado, utiliza unique_genes y item_gene_sets)
        summary_stats = dbc.Card([
            dbc.CardHeader(html.H5("Summary Statistics", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H3(len(unique_genes), className="text-primary mb-0"),
                        html.P("Unique Genes", className="text-muted small")
                    ], width=4),
                    dbc.Col([
                        html.H3(len(item_gene_sets), className="text-info mb-0"),
                        html.P("Items Compared", className="text-muted small")
                    ], width=4),
                    dbc.Col([
                        html.H3(sum(len(v) for v in gene_sources.values()), className="text-success mb-0"),
                        html.P("Total Gene Instances", className="text-muted small")
                    ], width=4)
                ])
            ])
        ], className="mb-4")

        # B. Venn Diagram and Intersections
        venn_section = None
        intersection_data_list = []
        VENN_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c'] 
        
        if 2 <= len(item_gene_sets) <= 3:
            try:
                sets_list = list(item_gene_sets.values())
                # 🔑 Claves de etiqueta ahora usan las claves amigables (unique_key)
                labels_list = list(item_gene_sets.keys()) 
                
                fig, ax = plt.subplots(figsize=(6, 6))

                # Forzar un elemento ficticio para que el círculo se dibuje si el set está vacío
                sets_list_for_drawing = [s.copy() or {'__TEMP_GENE_FOR_VENN__'} for s in sets_list]
                set_colors = VENN_COLORS[:len(sets_list)]

                if len(sets_list) == 2:
                    v = venn2(sets_list_for_drawing, set_labels=['', ''], ax=ax, set_colors=set_colors, alpha=0.5)
                elif len(sets_list) == 3:
                    v = venn3(sets_list_for_drawing, set_labels=['', '', ''], ax=ax, set_colors=set_colors, alpha=0.5)
                
                # ... (Lógica de estilo y corrección de labels) ...
                
                plt.title("Gene Overlap Between Selected Items", fontsize=12, fontweight='bold')

                # Convert plot to base64 image
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
                buf.seek(0)
                img_base64 = base64.b64encode(buf.read()).decode('utf-8')
                plt.close(fig)

                # --- RENDER VENN LEGEND (Usando las claves internas para identificar) ---
                legend_items = []
                for i, label in enumerate(labels_list):
                    # Acortar la etiqueta solo para la visualización de la leyenda
                    display_label = label if len(label) < 30 else label[:27] + '...' 
                    color_style = {'backgroundColor': VENN_COLORS[i], 
                                   'width': '15px', 'height': '15px', 
                                   'borderRadius': '3px', 'display': 'inline-block', 'marginRight': '8px'}
                    legend_items.append(
                        html.Div([
                            html.Div(style=color_style),
                            html.Span(f"{display_label}", title=label)
                        ], className="d-flex align-items-center me-4")
                    )
                
                legend_card = dbc.Card([
                    dbc.CardBody(
                        html.Div(legend_items, className="d-flex flex-row flex-wrap justify-content-center"),
                        className="small py-2"
                    )
                ], className="mb-3")
                
                # --- CALCULATE INTERSECTIONS AND POPULATE LIST ---
                def create_intersection_entry(name, genes, color, source_sets=None):
                    return {
                        'name': name,
                        'genes': sorted(list(genes)),
                        'count': len(genes),
                        'color': color,
                        'source_sets': source_sets or []
                    }
                
                # CÁLCULOS REALES USANDO sets_list
                if len(sets_list) == 2:
                    int_all = sets_list[0] & sets_list[1]
                    if int_all:
                        intersection_data_list.append(create_intersection_entry(
                            f"Intersection: {labels_list[0]} ∩ {labels_list[1]}", int_all, 'success', [0, 1]))
                    int_a_only = sets_list[0] - sets_list[1]
                    if int_a_only:
                        intersection_data_list.append(create_intersection_entry(
                            f"Unique to {labels_list[0]}", int_a_only, 'primary', [0]))
                    int_b_only = sets_list[1] - sets_list[0]
                    if int_b_only:
                        intersection_data_list.append(create_intersection_entry(
                            f"Unique to {labels_list[1]}", int_b_only, 'info', [1]))

                elif len(sets_list) == 3:
                    int_all = sets_list[0] & sets_list[1] & sets_list[2]
                    if int_all:
                        intersection_data_list.append(create_intersection_entry(
                            f"All three: {labels_list[0]} ∩ {labels_list[1]} ∩ {labels_list[2]}", int_all, 'success', [0, 1, 2]))
                    int_01 = (sets_list[0] & sets_list[1]) - sets_list[2]
                    if int_01:
                        intersection_data_list.append(create_intersection_entry(
                            f"{labels_list[0]} ∩ {labels_list[1]} only", int_01, 'warning', [0, 1]))
                    int_02 = (sets_list[0] & sets_list[2]) - sets_list[1]
                    if int_02:
                        intersection_data_list.append(create_intersection_entry(
                            f"{labels_list[0]} ∩ {labels_list[2]} only", int_02, 'warning', [0, 2]))
                    int_12 = (sets_list[1] & sets_list[2]) - sets_list[0]
                    if int_12:
                        intersection_data_list.append(create_intersection_entry(
                            f"{labels_list[1]} ∩ {labels_list[2]} only", int_12, 'warning', [1, 2]))
                    
                    int_a_only = sets_list[0] - (sets_list[1] | sets_list[2])
                    if int_a_only:
                        intersection_data_list.append(create_intersection_entry(
                            f"Unique to {labels_list[0]}", int_a_only, 'primary', [0]))
                    int_b_only = sets_list[1] - (sets_list[0] | sets_list[2])
                    if int_b_only:
                        intersection_data_list.append(create_intersection_entry(
                            f"Unique to {labels_list[1]}", int_b_only, 'info', [1]))
                    int_c_only = sets_list[2] - (sets_list[0] | sets_list[1])
                    if int_c_only:
                        intersection_data_list.append(create_intersection_entry(
                            f"Unique to {labels_list[2]}", int_c_only, 'danger', [2]))


                
                # Render intersection cards 
                intersection_cards = []
                for idx, int_data in enumerate(intersection_data_list):
                    genes_display = ', '.join(int_data['genes'])
                    
                    source_sets = int_data['source_sets']
                    
                    # Heurística para asignar color al badge
                    card_color_hex = '#6c757d'
                    if len(source_sets) == len(sets_list):
                        card_color_hex = '#28a745'
                    elif len(source_sets) == 1:
                        card_color_hex = VENN_COLORS[source_sets[0]]
                    elif len(source_sets) > 1:
                         card_color_hex = '#ffc107'

                    card = dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.Span(f" {int_data['count']} genes", 
                                          className="me-2 badge",
                                          style={'backgroundColor': card_color_hex, 
                                                 'color': 'white', 
                                                 'fontSize': '0.8rem',
                                                 'fontWeight': 'bold'}),
                                html.Strong(int_data['name'])
                            ], className="mb-2"),
                            html.Div(genes_display, className="small text-muted mb-2",
                                  style={'fontSize': '0.85rem', 'maxHeight': '150px', 'overflowY': 'auto'}),
                            
                            dbc.Button(
                                "Add to Panel",
                                id={'type': 'add-intersection-btn', 'index': idx}, 
                                color='secondary',
                                size="sm",
                                outline=True
                            )
                        ])
                    ], className="mb-2")
                    intersection_cards.append(card)


                venn_section = dbc.Row([
                    dbc.Col([
                        html.H5("Venn Diagram", className="mb-3"),
                        legend_card,
                        html.Img(src=f"data:image/png;base64,{img_base64}",
                                style={'maxWidth': '100%', 'height': 'auto'})
                    ], width=6),
                    dbc.Col([
                        html.Div([
                            html.H5("Gene Intersections", className="mb-0 d-inline-block"),
                            # Botón Add All Intersections
                            dbc.Button(
                                "Add All Intersections 📌",
                                id="add-all-intersections-btn",
                                color="success",
                                size="sm",
                                className="ms-3",
                                style={'fontSize': '0.8rem'},
                                disabled=not intersection_data_list
                            )
                        ], className="d-flex align-items-center mb-3"),
                        html.Div(intersection_cards, style={'maxHeight': '450px', 'overflowY': 'auto'})
                    ], width=6)
                ], className="mb-4")

            except Exception as e:
                # Fallback si matplotlib_venn falla
                venn_section = html.Div([
                    html.H5("Venn Diagram", className="mt-4 mb-3 text-danger"),
                    html.P(f"Could not generate Venn diagram. Error: {e}", className="text-muted")
                ])
        elif len(item_gene_sets) > 3:
            venn_section = html.Div([
                html.H5("Venn Diagram", className="mt-4 mb-3"),
                html.P("Venn diagrams are only available for 2-3 items. Please select fewer items.",
                      className="text-muted fst-italic")
            ])
        
        # C. Gene Frequency Table/Chart (No modificado)
        gene_frequency = []
        for gene, sources in gene_sources.items():
            gene_frequency.append({
                'Gene': gene,
                'Frequency': len(sources),
                'Sources': ', '.join(sources[:3]) + ('...' if len(sources) > 3 else '')
            })

        gene_freq_df = pd.DataFrame(gene_frequency).sort_values('Frequency', ascending=False)
        gene_freq_df.insert(0, 'N°', range(1, 1 + len(gene_freq_df)))
        
        fig_bar = px.bar(
            gene_freq_df.head(20),
            x='Gene',
            y='Frequency',
            title='Top 20 Genes by Frequency Across Selected Items',
            labels={'Frequency': 'Number of Sources'},
            color='Frequency',
            color_continuous_scale='Blues'
        )
        fig_bar.update_layout(xaxis_tickangle=-45, height=400)
        
        table = dbc.Table.from_dataframe(
            gene_freq_df,
            striped=True,
            bordered=True,
            hover=True,
            responsive=True,
            size='sm',
            style={'fontSize': '0.85rem'} 
        )
        
        buttons_row = dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Save selected items as Combined Group",
                    id="save-combined-group-btn-top",
                    color="success",
                    className="me-2"
                ),
                dbc.Button(
                    "Clear Selection",
                    id="clear-gene-groups-selection-btn",
                    color="secondary",
                    outline=True
                )
            ], className="mb-3")
        ])


        # Store data for genes and sources (Asegurando que las claves sean las nuevas)
        store_data = {'genes': list(unique_genes), 'sources': list(item_gene_sets.keys())}
        
        return html.Div([
            buttons_row,
            summary_stats,
            venn_section if venn_section else None,
            html.H5("Gene Frequency Chart", className="mt-4 mb-3"),
            dcc.Graph(figure=fig_bar),
            html.H5("Gene Frequency Table", className="mt-4 mb-3"),
            table
        ]), store_data, intersection_data_list, selected_indices

    # 3. Callback para limpiar la selección de Gene Groups (Checkboxes)
    @app.callback(
        [Output({'type': 'gene-group-card-checkbox', 'index': ALL}, 'value'),
         Output('selected-gene-group-indices-store', 'data', allow_duplicate=True)],
        Input('clear-gene-groups-selection-btn', 'n_clicks'),
        State({'type': 'gene-group-card-checkbox', 'index': ALL}, 'value'),
        prevent_initial_call=True
    )
    def clear_gene_groups_checkboxes(n_clicks, current_values):
        """Clear all selected checkboxes in gene groups analysis"""
        if not n_clicks:
            raise PreventUpdate

        return [[] for _ in current_values], []

    # 4. Callback para abrir el modal de guardar grupo combinado (selección visual)
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
        """Open modal to save combined gene group (from visual selection)"""
        if not n_clicks:
            raise PreventUpdate

        if genes_store_data and genes_store_data.get('genes'):
            sources = genes_store_data.get('sources', [])
            gene_count = len(genes_store_data.get('genes', []))

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tentative_name = f"Combined Group - {gene_count} Genes"
            tentative_comment = f"Combined {gene_count} genes from {len(sources)} initial sources."
            
            genes_store_data['meta_type'] = 'combined_selection'
            
            modal_info = html.Div([
                html.P([html.Strong("Adding Combined Selection: ")]),
                html.P([html.Strong("Total Unique Genes: "), html.Span(f"{gene_count}")])
            ])

            return True, modal_info, tentative_name, tentative_comment, genes_store_data

        raise PreventUpdate

    # 5. Callback para abrir el modal de intersección (individual o Add All)
    @app.callback(
        [Output('gene-groups-analysis-tab-modal', 'is_open', allow_duplicate=True),
         Output('gene-groups-analysis-tab-modal-info', 'children', allow_duplicate=True),
         Output('gene-groups-analysis-tab-name-input', 'value', allow_duplicate=True),
         Output('gene-groups-analysis-tab-comment-input', 'value', allow_duplicate=True),
         Output('gene-groups-analysis-tab-temp-store', 'data', allow_duplicate=True)],
        [Input({'type': 'add-intersection-btn', 'index': ALL}, 'n_clicks'),
         Input('add-all-intersections-btn', 'n_clicks')],
        [State('intersection-data-temp-store', 'data'),
         State({'type': 'add-intersection-btn', 'index': ALL}, 'id')],
        prevent_initial_call=True
    )
    def open_intersection_modal_or_add_all(single_n_clicks, all_n_clicks, intersection_data, single_btn_ids):
        """Open modal to save an individual intersection or setup for 'Add All'."""
        ctx = dash.callback_context
        if not intersection_data:
            raise PreventUpdate

        triggered_input = ctx.triggered[0]['prop_id']
        trigger_id = triggered_input.split('.')[0]
        
        # 1. Manejo de la lógica 'Add All' (Botón Fijo)
        if trigger_id == 'add-all-intersections-btn' and all_n_clicks and all_n_clicks > 0:
            
            all_genes = set()
            for intersection in intersection_data:
                all_genes.update(intersection['genes'])
                
            group_data = {
                'genes': list(all_genes),
                'sources': [item['name'] for item in intersection_data],
                'meta_type': 'all_intersections_set',
                'name': f"Combined Intersections Set ({len(intersection_data)})"
            }
            
            modal_info = html.Div([
                html.P([html.Strong("Adding Gene Group (Combined Intersections): ")]),
                html.P([html.Strong("Total Unique Genes: "), html.Span(f"{len(all_genes)}")]),
                html.P([html.Strong("Sources: "), html.Span(f"{len(intersection_data)} Intersections")])
            ])
            
            tentative_name = f"All Intersections Set - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            tentative_comment = f"Union of {len(intersection_data)} Venn diagram intersections. Total unique genes: {len(all_genes)}."

            return True, modal_info, tentative_name, tentative_comment, group_data

        # 2. Manejo de la lógica de intersección individual (Botones Dinámicos)
        if 'add-intersection-btn' in trigger_id and any(c is not None and c > 0 for c in single_n_clicks):
            
            triggered_dict = ctx.triggered_id 
            
            if triggered_dict and triggered_dict.get('type') == 'add-intersection-btn':
                 index = triggered_dict['index']
                 
                 if 0 <= index < len(intersection_data):
                    intersection = intersection_data[index]
                    
                    modal_info = html.Div([
                        html.P([html.Strong("Adding Intersection Group: "), html.Code(intersection['name'], className="text-primary")]),
                        html.P([html.Strong("Gene Count: "), html.Span(f"{intersection['count']}")])
                    ])
                    
                    group_data = {
                        'genes': intersection['genes'],
                        'sources': [intersection['name']],
                        'meta_type': 'single_intersection',
                        'name': intersection['name']
                    }
                    
                    tentative_name = intersection['name']
                    tentative_comment = f"Genes found in the intersection '{intersection['name']}'."
                    
                    return True, modal_info, tentative_name, tentative_comment, group_data

        raise PreventUpdate
    