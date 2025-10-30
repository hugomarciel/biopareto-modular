# services/reactome_service.py

"""
Reactome Pathway Enrichment Analysis Service
Uses the Reactome Content Service API (Analysis tab)
"""

import requests
import logging
import json

logger = logging.getLogger(__name__)

class ReactomeService:
    """Service to connect with the Reactome Content Service API for pathway enrichment."""

    # URL para el análisis de la lista de genes (POST)
    ANALYSIS_SERVICE_URL = "https://reactome.org/AnalysisService/identifiers/?page=1&pageSize=20&sortBy=ENTITIES_PVALUE&order=ASC"
    # URL base para obtener los resultados detallados
    BASE_REPORT_URL = "https://reactome.org/AnalysisService/report/"
    
    # Organismo por defecto (Human)
    DEFAULT_ORGANISM = "Homo sapiens"

    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Executes Reactome pathway enrichment analysis.
        
        Note: Reactome's enrichment process is asynchronous. 
        We need to send the list (POST) and then fetch the results (GET).
        """
        if not gene_list:
            return []
        
        try:
            # 1. Enviar lista de genes para iniciar el análisis
            post_payload = {
                "identifiers": gene_list,
                "species": organism_name # Ej: "Homo sapiens"
            }
            
            # Reactome usa 'species' como nombre (ej: "Homo sapiens"), no ID corto (ej: "hsapiens")
            
            logger.info(f"Submitting {len(gene_list)} genes to Reactome for {organism_name}.")

            response = requests.post(
                ReactomeService.ANALYSIS_SERVICE_URL, 
                json=post_payload, 
                headers={'Content-Type': 'application/json'},
                timeout=45
            )

            if response.status_code != 200:
                logger.error(f"Reactome POST error: {response.status_code} - {response.text}")
                return None
            
            # 2. Obtener el token de análisis del encabezado de la respuesta
            analysis_token = response.headers.get('X-Analysisservice-Token')
            if not analysis_token:
                 logger.error("Reactome did not return an analysis token.")
                 return None
            
            logger.info(f"Reactome analysis started. Token: {analysis_token}")

            # 3. Obtener el reporte de enriquecimiento con el token
            report_url = f"{ReactomeService.BASE_REPORT_URL}{analysis_token}/pathways/low?page=1&pageSize=100"
            
            report_response = requests.get(report_url, timeout=30)
            
            if report_response.status_code != 200:
                logger.error(f"Reactome GET Report error: {report_response.status_code} - {report_response.text}")
                return None
                
            report_data = report_response.json()
            
            # Reactome devuelve una lista de objetos de 'pathways' en el campo 'pathways'
            pathways = report_data.get('pathways', [])
            
            # Filtrar por términos significativos (pValue < 0.05)
            significant_pathways = [
                p for p in pathways if p.get('entities', {}).get('pValue', 1.0) < 0.05
            ]
            
            # Mapeo a un formato de resultados simplificado y usable
            mapped_results = []
            for p in significant_pathways:
                mapped_results.append({
                    'source': 'Reactome',
                    'term_name': p.get('name', 'N/A'),
                    'description': p.get('stId', 'N/A'), # Usamos el Stable ID como descripción corta
                    'p_value': p.get('entities', {}).get('pValue', 1.0),
                    'entities_found': p.get('entities', {}).get('found', 0), # Genes intersectados
                    'entities_total': p.get('entities', {}).get('total', 0), # Tamaño del término
                    'fdr_value': p.get('entities', {}).get('fdr', 1.0) # Valor de corrección FDR
                })
                
            return mapped_results

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment: {str(e)}")
            return None