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

    # URL correcta para iniciar el análisis (POST), incluyendo 'projection'
    ANALYSIS_SERVICE_URL = "https://reactome.org/AnalysisService/identifiers/projection" 
    
    # Organismo por defecto (Human)
    DEFAULT_ORGANISM = "Homo sapiens"

    # Diccionario para mapear nombres de organismos largos a códigos Reactome
    ORGANISM_CODE_MAP = {
        "Homo sapiens": "HSA",
        "Mus musculus": "MMU",
        "Rattus norvegicus": "RNO",
        # Añadir más organismos si la app los soporta
    }

    @staticmethod
    def _get_reactome_species_code(organism_name):
        """Convierte el nombre del organismo a su código corto, si está disponible."""
        return ReactomeService.ORGANISM_CODE_MAP.get(organism_name, organism_name)


    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Executes Reactome pathway enrichment analysis.
        """
        if not gene_list:
            return []
        
        species_code = ReactomeService._get_reactome_species_code(organism_name)
        
        try:
            # 1. Enviar lista de genes para iniciar el análisis
            post_data = "\n".join(gene_list)
            
            logger.info(f"Submitting {len(gene_list)} genes to Reactome for {organism_name}.")

            response = requests.post(
                ReactomeService.ANALYSIS_SERVICE_URL, 
                data=post_data, 
                params={'species': species_code}, 
                headers={'Content-Type': 'text/plain'}, 
                timeout=45
            )

            if response.status_code != 200:
                logger.error(f"Reactome POST error: {response.status_code} - {response.text}")
                return None
            
            # 2. Obtener el token de análisis del encabezado o del cuerpo JSON
            analysis_token = response.headers.get('X-Analysisservice-Token')
            
            if not analysis_token:
                try:
                    response_json = response.json()
                    analysis_token = response_json.get('summary', {}).get('token')
                except json.JSONDecodeError:
                    logger.error("Reactome did not return a token and response body is not valid JSON.")
                    return None
                
            if not analysis_token:
                 logger.error(f"Reactome did not return an analysis token. Response body: {response.text[:200]}...")
                 return None
            
            logger.info(f"Reactome analysis started. Token: {analysis_token}")

            # 3. Obtener el reporte de enriquecimiento con el token
            report_url = f"https://reactome.org/AnalysisService/download/{analysis_token}/result.json"
            report_response = requests.get(report_url, timeout=30)
            
            if report_response.status_code != 200:
                logger.error(f"Reactome GET Report error: {report_response.status_code} - {report_response.text}")
                return None
                
            report_data = report_response.json()
            
            # Reactome devuelve una lista de objetos de 'pathways' en el campo 'pathways'
            pathways = report_data.get('pathways', [])
            
            logger.info(f"Received {len(pathways)} total pathways from Reactome before filtering.")
            
            # --- CORRECCIÓN CLAVE: Desactivar filtro para mostrar todos los resultados ---
            # Si el filtro estaba activo (e.g., FDR < 0.05), estaba eliminando todos los caminos.
            # significant_pathways = [p for p in pathways if p.get('entities', {}).get('fdr', 1.0) < 0.05]
            significant_pathways = pathways # Muestra todos los resultados
            
            logger.info(f"Displaying {len(significant_pathways)} pathways (FDR filter temporarily disabled).")

            # Mapeo a un formato de resultados simplificado y usable
            mapped_results = []
            for p in significant_pathways:
                # Nos aseguramos de acceder a los datos de entidades de forma segura
                entities = p.get('entities', {})
                
                mapped_results.append({
                    'source': 'Reactome',
                    'term_name': p.get('name', 'N/A'),
                    'description': p.get('stId', 'N/A'), 
                    'p_value': entities.get('pValue', 1.0),
                    'entities_found': entities.get('found', 0), 
                    'entities_total': entities.get('total', 0), 
                    'fdr_value': entities.get('fdr', 1.0)
                })
                
            logger.info(f"Final mapped results count: {len(mapped_results)}")
            return mapped_results

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment: {str(e)}")
            return None