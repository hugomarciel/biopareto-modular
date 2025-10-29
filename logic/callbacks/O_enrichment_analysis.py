# logic/callbacks/O_enrichment_analysis.py

import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from collections import defaultdict
from services.gprofiler_service import GProfilerService 


def register_O_enrichment_callbacks(app): # <-- FUNCIÓN RENOMBRADA

    # 1. Callback de Renderizado (Final y Estructuralmente Válido)
    @app.callback(
        [Output('O_enrichment-visual-selector', 'children'), # 🔑 CORRECCIÓN: Eliminamos allow_duplicate=True
         Output('enrichment-selected-item-ids-store', 'data', allow_duplicate=True)],
        [Input('interest-panel-store', 'data'),
         Input('enrichment-selected-indices-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=True 
    )
    def render_O_visual_enrichment_selector(items, selected_indices_list, active_tab): # <-- FUNCIÓN RENOMBRADA
        """
        Render visual card-based selector for enrichment analysis.
        """
        
        # Condición CRÍTICA: La ejecución solo ocurre si la pestaña está activa.
        if active_tab != 'enrichment-tab':
             raise PreventUpdate

        if not items:
            return html.P("No items available. Add solutions, genes, or gene groups to your Interest Panel first.",
                         className="text-muted text-center py-4"), []

        cards = []
        selected_item_ids = []
        
        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', '')
            
            # Solo items que contienen genes
            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            # Determinar detalles
            gene_count = len(item.get('data', {}).get('selected_genes', item.get('data', {}).get('genes', [])))
            if item_type == 'solution_set':
                solutions = item.get('data', {}).get('solutions', [])
                unique_genes = set()
                for sol in solutions:
                    unique_genes.update(sol.get('selected_genes', []))
                gene_count = len(unique_genes)
            elif item_type == 'individual_gene':
                gene_count = 1
            
            description = f"{gene_count} genes"
            badge_color = "primary" if item_type in ['solution', 'solution_set'] else "success"
            
            is_selected = [idx] if idx in selected_indices_list else []
            item_id = item.get('id', str(idx))

            if idx in selected_indices_list:
                selected_item_ids.append(item_id)
            
            card = dbc.Col([
                html.Div([
                    dbc.Checklist(
                        options=[{"label": "", "value": idx}],
                        value=is_selected,
                        id={'type': 'O_enrichment-card-checkbox', 'index': idx}, # <-- ID RENOMBRADO
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
                    dbc.Badge(item_type.replace('_', ' ').title(), color=badge_color, className="mb-1", style={'fontSize': '0.7rem'}),
                    html.Strong(item_name, className="d-block mb-1", style={'fontSize': '0.9rem'}),
                    html.P(description, className="text-muted small mb-1", style={'fontSize': '0.75rem'}),
                ], style={'paddingRight': '40px'})
            ], className="p-2", style={'minHeight': '100px', 'position': 'relative', 'border': '1px solid #ccc', 'borderRadius': '4px', 'backgroundColor': '#f8f9fa'})

            cards.append(card)

        if not cards:
            return html.P("No compatible items found.", className="text-muted text-center py-4"), []

        return dbc.Row([dbc.Col(c, width=12, md=6, lg=3, className="mb-3") for c in cards], className="g-3"), selected_item_ids


    # 2. Callback para manejar la selección de los checkboxes y actualizar el panel de resumen
    # ... (El resto de callbacks se mantiene igual)
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data'),
         Output('enrichment-selection-panel', 'children')],
        Input({'type': 'O_enrichment-card-checkbox', 'index': ALL}, 'value'), # <-- ID RENOMBRADO
        State('interest-panel-store', 'data')
    )
    def update_O_enrichment_selection(checkbox_values, items): # <-- FUNCIÓN RENOMBRADA
        """Processes selection checkboxes and updates the summary panel."""
        if not checkbox_values:
            return [], ""

        selected_indices = []
        for i, values in enumerate(checkbox_values):
            if values and len(values) > 0:
                selected_indices.append(values[0])

        if not selected_indices:
            return [], dbc.Alert("No items selected for analysis.", color="warning")

        # Lógica de agregación de genes
        combined_genes = set()
        selected_names = []
        
        for idx in selected_indices:
            item = items[idx]
            item_type = item.get('type', '')
            
            if item_type == 'solution':
                combined_genes.update(item.get('data', {}).get('selected_genes', []))
            elif item_type == 'solution_set':
                solutions = item.get('data', {}).get('solutions', [])
                for sol in solutions:
                    combined_genes.update(sol.get('selected_genes', []))
            elif item_type in ['gene_set', 'combined_gene_group']:
                combined_genes.update(item.get('data', {}).get('genes', []))
            elif item_type == 'individual_gene':
                combined_genes.add(item.get('data', {}).get('gene', ''))
            
            selected_names.append(item.get('name'))


        # Almacenar la lista de genes combinados para el análisis
        combined_genes_list = sorted(list(combined_genes))

        # Renderizar el panel de resumen de la selección
        summary_panel = dbc.Card([
            dbc.CardHeader("Combined Genes for Enrichment"),
            dbc.CardBody([
                html.P(f"Total Unique Genes: {len(combined_genes_list)}", className="mb-1"),
                html.P(f"Sources: {len(selected_indices)} item(s)"),
                html.Details([
                    html.Summary("View Sources"),
                    dbc.ListGroup([
                        dbc.ListGroupItem(name, className="small py-1") for name in selected_names
                    ], flush=True, className="mt-2")
                ])
            ])
        ])

        return selected_indices, summary_panel


    # 3. Callback para habilitar el botón de enriquecimiento
    @app.callback(
        Output('O_run-enrichment-btn', 'disabled'), # <-- ID RENOMBRADO
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_O_enrichment_button(selected_indices): # <-- FUNCIÓN RENOMBRADA
        """Habilitar/deshabilitar botón de enriquecimiento si hay genes seleccionados."""
        if not selected_indices:
            return True
        return False


    # 4. Callback para ejecutar el análisis de enriquecimiento biológico
    @app.callback(
        [Output('enrichment-data-store', 'data'),
         Output('O_enrichment-results', 'children')], # <-- ID RENOMBRADO
        Input('O_run-enrichment-btn', 'n_clicks'), # <-- ID RENOMBRADO
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('O_organism-dropdown', 'value')], # <-- ID RENOMBRADO
        prevent_initial_call=True
    )
    def run_O_enrichment_analysis(n_clicks, selected_indices, items, organism): # <-- FUNCIÓN RENOMBRADA
        """Executes g:Profiler enrichment analysis and stores results."""
        if not n_clicks or not selected_indices:
            raise PreventUpdate

        # 1. Recolectar lista final de genes
        combined_genes = set()
        for idx in selected_indices:
            item = items[idx]
            item_type = item.get('type', '')
            
            if item_type == 'solution':
                combined_genes.update(item.get('data', {}).get('selected_genes', []))
            elif item_type == 'solution_set':
                solutions = item.get('data', {}).get('solutions', [])
                for sol in solutions:
                    combined_genes.update(sol.get('selected_genes', []))
            elif item_type in ['gene_set', 'combined_gene_group']:
                combined_genes.update(item.get('data', {}).get('genes', []))
            elif item_type == 'individual_gene':
                combined_genes.add(item.get('data', {}).get('gene', ''))
        
        gene_list = [g for g in combined_genes if g and isinstance(g, str)]

        if not gene_list:
            return None, dbc.Alert("No genes found in the selected items to run enrichment.", color="warning")

        # 2. Ejecutar servicio de g:Profiler
        results = GProfilerService.get_enrichment(gene_list, organism)

        if results is None:
            return None, dbc.Alert("Error connecting to g:Profiler API or receiving response.", color="danger")
        
        if not results:
             return results, dbc.Alert(f"g:Profiler found no significant enrichment results for {len(gene_list)} genes in {organism}.", color="info")


        # 3. Procesar y Renderizar Resultados
        
        # Filtro inicial: p_value < 0.05
        filtered_results = [res for res in results if res.get('p_value', 1.0) < 0.05]
        
        if not filtered_results:
             return results, dbc.Alert(f"No significant (P < 0.05) enrichment results found for {len(gene_list)} genes.", color="info")

        # Convertir a DataFrame para fácil manejo y visualización
        df = pd.DataFrame(filtered_results)
        
        # Columnas de interés y formato
        df = df[['source', 'term_name', 'p_value', 'term_size', 'query_size', 'intersection']]
        df['p_value'] = df['p_value'].apply(lambda x: f"{x:.4e}")
        df['intersection_size'] = df['intersection'].apply(lambda x: len(x))
        df.rename(columns={
            'source': 'Source',
            'term_name': 'Term',
            'p_value': 'P-Value',
            'term_size': 'Term Size',
            'query_size': 'Query Size',
            'intersection': 'Genes',
            'intersection_size': 'Genes Matched'
        }, inplace=True)
        
        df.sort_values(by='P-Value', inplace=True)
        
        
        # Resumen
        summary = html.Div([
            html.P(f"Analysis successful for {len(gene_list)} genes against {organism}.", className="mb-1"),
            html.P(f"Found {len(df)} significant terms (P < 0.05).", className="mb-3")
        ])

        # Tabla de resultados
        table = dash_table.DataTable(
            id='enrichment-results-table',
            columns=[
                {"name": i, "id": i} for i in df.columns if i != 'Genes'
            ] + [
                {"name": "Genes", "id": "Genes"} # Genes se incluye para hover/tooltip
            ],
            data=df.to_dict('records'),
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_current=0,
            page_size=10,
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'maxWidth': '150px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            # Configurar Tooltip para mostrar la lista completa de Genes
            tooltip_data=[
                {
                    'Genes': {'value': ', '.join(row['Genes']), 'type': 'text'}
                } for row in df.to_dict('records')
            ],
            tooltip_duration=None,
            
        )


        return df.to_dict('records'), html.Div([summary, table])