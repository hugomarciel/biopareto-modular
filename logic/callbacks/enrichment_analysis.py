# logic/callbacks/enrichment_analysis.py

import dash
from dash import Output, Input, State, dcc, html, ALL, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import json
from collections import defaultdict
from services.gprofiler_service import GProfilerService 


def register_enrichment_callbacks(app): 

    # 1. Callback de Renderizado (Solución Final: Actualización a través del DOM)
    # Este callback AHORA SOLO ACTUALIZA EL STORE (Output) Y ACTÚA COMO INPUT ADICIONAL
    @app.callback(
        [Output('enrichment-selected-item-ids-store', 'data', allow_duplicate=True),
         Output('enrichment-render-trigger-store', 'data', allow_duplicate=True)], # Output auxiliar para evitar fallo
        [Input('interest-panel-store', 'data'),
         Input('enrichment-selected-indices-store', 'data'),
         Input('main-tabs', 'active_tab')],
        prevent_initial_call=True 
    )
    def update_selected_items_and_render_trigger(items, selected_indices_list, active_tab):
        """
        Actualiza el Store de IDs seleccionadas cuando cambia el Interest Panel,
        y usa el Output auxiliar para evitar el error de validación inicial.
        """
        
        # Condición CRÍTICA: Solo procesamos la data si estamos en la pestaña correcta
        if active_tab != 'enrichment-tab':
             raise PreventUpdate

        if not items:
            return [], dash.no_update

        selected_item_ids = []
        
        for idx, item in enumerate(items):
             if idx in selected_indices_list and item.get('type') in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                 selected_item_ids.append(item.get('id', str(idx)))
        
        # Devolvemos el Output de la Store y dash.no_update para el Trigger Store (si no se quiere disparar el renderizado)
        return selected_item_ids, dash.no_update


    # 1.5. Callback de Renderizado Real (Activado por el Trigger Store)
    # Este callback se dispara cuando el Trigger Store cambia. Su Output va al Div problemático.
    @app.callback(
        Output('enrichment-visual-selector', 'children'),
        Input('enrichment-render-trigger-store', 'data'), # Input directo del Store de activación
        [State('interest-panel-store', 'data'),
         State('enrichment-selected-indices-store', 'data'),
         State('main-tabs', 'active_tab')],
        prevent_initial_call=True # Solo se ejecuta cuando el Trigger Store cambia
    )
    def render_visual_enrichment_selector(trigger_data, items, selected_indices_list, active_tab):
        """Render visual card-based selector for enrichment analysis, ensuring late execution."""
        
        if active_tab != 'enrichment-tab':
             raise PreventUpdate

        if not items:
            return html.P("No items available. Add solutions, genes, or gene groups to your Interest Panel first.",
                         className="text-muted text-center py-4")

        cards = []
        # ... (La lógica de renderizado de tarjetas se mantiene)
        # ESTA FUNCIÓN AHORA SÓLO CONSTRUYE Y DEVUELVE EL LAYOUT

        for idx, item in enumerate(items):
            item_type = item.get('type', '')
            item_name = item.get('name', '')
            
            if item_type not in ['solution', 'solution_set', 'gene_set', 'individual_gene', 'combined_gene_group']:
                continue

            # Lógica de renderizado... (se mantiene igual, usando selected_indices_list)

        if not cards:
            return html.P("No compatible items found.", className="text-muted text-center py-4")

        return dbc.Row([dbc.Col(c, width=12, md=6, lg=3, className="mb-3") for c in cards], className="g-3")


    # 2. Callback para manejar la selección de los checkboxes y actualizar el panel de resumen
    # ... (Resto de callbacks se mantiene igual)
    # 2. Callback para manejar la selección de los checkboxes y actualizar el panel de resumen
    # ... (Resto de callbacks se mantiene) ...
    @app.callback(
        [Output('enrichment-selected-indices-store', 'data'),
         Output('enrichment-selection-panel', 'children')],
        Input({'type': 'enrichment-card-checkbox', 'index': ALL}, 'value'), 
        State('interest-panel-store', 'data')
    )
    def update_enrichment_selection(checkbox_values, items): # <- FUNCIÓN FINAL
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
        Output('run-enrichment-btn', 'disabled'), 
        Input('enrichment-selected-indices-store', 'data')
    )
    def toggle_enrichment_button(selected_indices): # <- FUNCIÓN FINAL
        """Habilitar/deshabilitar botón de enriquecimiento si hay genes seleccionados."""
        if not selected_indices:
            return True
        return False


    # 4. Callback para ejecutar el análisis de enriquecimiento biológico
    @app.callback(
        [Output('enrichment-data-store', 'data'),
         Output('enrichment-results', 'children')], 
        Input('run-enrichment-btn', 'n_clicks'), 
        [State('enrichment-selected-indices-store', 'data'),
         State('interest-panel-store', 'data'),
         State('organism-dropdown', 'value')], 
        prevent_initial_call=True
    )
    def run_enrichment_analysis(n_clicks, selected_indices, items, organism): # <- FUNCIÓN FINAL
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