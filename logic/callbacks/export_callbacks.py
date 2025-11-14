# logic/callbacks/export_callbacks.py (CÓDIGO COMPLETO CON NUEVO CALLBACK)

import dash
from dash import Output, Input, State, dcc
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import json
import pandas as pd
from datetime import datetime
from services.report_generator import (
    generate_pdf_report, 
    generate_txt_report, 
    export_pareto_data, 
    export_genes_list
)


def register_export_callbacks(app):

    # 1. Callback para generar PDF Report
    @app.callback(
        Output("pdf-report-download", "data"),
        Input("generate-pdf-report", "n_clicks"),
        [State('data-store', 'data'),
         State('enrichment-data-store', 'data')], # Datos de enriquecimiento
        prevent_initial_call=True
    )
    def download_pdf_report(n_clicks, data_store, enrichment_data):
        if not n_clicks or not data_store or not data_store.get('fronts'):
            raise PreventUpdate

        # Generar el buffer del PDF usando el servicio
        pdf_buffer = generate_pdf_report(data_store, enrichment_data)
        
        if pdf_buffer:
            return dcc.send_bytes(pdf_buffer.getvalue(), f"BioPareto_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        # En caso de fallo
        raise PreventUpdate


    # 2. Callback para generar TXT Report
    @app.callback(
        Output("txt-report-download", "data"),
        Input("generate-txt-report", "n_clicks"),
        [State('data-store', 'data'),
         State('enrichment-data-store', 'data')],
        prevent_initial_call=True
    )
    def download_txt_report(n_clicks, data_store, enrichment_data):
        if not n_clicks or not data_store or not data_store.get('fronts'):
            raise PreventUpdate

        # Generar el contenido del TXT
        txt_content = generate_txt_report(data_store, enrichment_data)
        
        if txt_content:
            return dcc.send_string(txt_content, f"BioPareto_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        raise PreventUpdate


    # 3. Exportar Pareto Data (CSV)
    @app.callback(
        Output("download-pareto-csv", "data"),
        Input("btn-export-pareto-csv", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_pareto_csv(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
            
        csv_data = export_pareto_data(data_store, 'csv')
        
        if csv_data:
            return dcc.send_string(csv_data, f"pareto_solutions_{datetime.now().strftime('%Y%m%d')}.csv")
            
        raise PreventUpdate


    # 4. Exportar Pareto Data (JSON)
    @app.callback(
        Output("download-pareto-json", "data"),
        Input("btn-export-pareto-json", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_pareto_json(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
            
        json_data = export_pareto_data(data_store, 'json')
        
        if json_data:
            return dcc.send_string(json_data, f"pareto_solutions_{datetime.now().strftime('%Y%m%d')}.json")
            
        raise PreventUpdate


    # 5. Exportar Lista de Genes (CSV)
    @app.callback(
        Output("download-genes-csv", "data"),
        Input("btn-export-genes-csv", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_genes_csv(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
            
        csv_data = export_genes_list(data_store, 'csv')
        
        if csv_data:
            return dcc.send_string(csv_data, f"unique_genes_{datetime.now().strftime('%Y%m%d')}.csv")
            
        raise PreventUpdate


    # 6. Exportar Lista de Genes (TXT)
    @app.callback(
        Output("download-genes-txt", "data"),
        Input("btn-export-genes-txt", "n_clicks"),
        State('data-store', 'data'),
        prevent_initial_call=True
    )
    def export_genes_txt(n_clicks, data_store):
        if not n_clicks or not data_store:
            raise PreventUpdate
            
        txt_data = export_genes_list(data_store, 'txt')
        
        if txt_data:
            return dcc.send_string(txt_data, f"unique_genes_{datetime.now().strftime('%Y%m%d')}.txt")
            
        raise PreventUpdate


    # 7. Resumen de la Sesión
    @app.callback(
        Output('session-summary', 'children'),
        Input('data-store', 'data'),
        State('interest-panel-store', 'data')
    )
    def update_session_summary(data_store, interest_items):
        if not data_store:
            return dbc.Alert("No data loaded.", color="warning")

        fronts = data_store.get('fronts', [])
        all_solutions = [s for f in fronts for s in f['data'] if f.get('visible', True)]
        
        unique_genes = set(g for sol in all_solutions for g in sol.get('selected_genes', []))

        return dbc.ListGroup([
            dbc.ListGroupItem(f"Loaded Fronts: {len(fronts)}"),
            dbc.ListGroupItem(f"Total Solutions: {len(all_solutions)}"),
            dbc.ListGroupItem(f"Unique Genes: {len(unique_genes)}"),
            dbc.ListGroupItem(f"Items in Interest Panel: {len(interest_items)}"),
        ])
        
        
    