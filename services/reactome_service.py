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
    # NUEVA URL para obtener la lista de especies
    SPECIES_URL = "https://reactome.org/ContentService/data/species/all"
    
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
    def get_reactome_organisms():
        """Fetch available organisms from Reactome API and return Dash options format."""
        try:
            response = requests.get(ReactomeService.SPECIES_URL, timeout=10)
            if response.status_code == 200:
                species_data = response.json()
                options = []
                for sp in species_data:
                    # Reactome devuelve 'displayName' como nombre completo (e.g., 'Homo sapiens')
                    display_name = sp.get('displayName') 
                    # Usamos el nombre completo para el 'value', ya que es lo que el servicio de análisis espera/usa.
                    if display_name:
                         options.append({'label': display_name, 'value': display_name})
                
                # Ordenar alfabéticamente
                return sorted(options, key=lambda x: x['label'])
            else:
                logger.error(f"Error fetching Reactome species: {response.status_code} - {response.text}")
                return ReactomeService._get_fallback_organisms()
        except Exception as e:
            logger.error(f"Error fetching Reactome species: {e}")
            return ReactomeService._get_fallback_organisms()

    @staticmethod
    def _get_fallback_organisms():
        """Fallback organism list for Reactome."""
        return [
            {'label': 'Homo sapiens', 'value': 'Homo sapiens'},
            {'label': 'Mus musculus', 'value': 'Mus musculus'},
            {'label': 'Rattus norvegicus', 'value': 'Rattus norvegicus'},
        ]

    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Executes Reactome pathway enrichment analysis.
        """
        if not gene_list:
            return []
        
        # El servicio de Reactome usa el nombre completo de la especie (ej: "Homo sapiens") para 'species',
        # por lo que no es necesario el código corto en esta función de enriquecimiento, pero lo mantengo por si acaso.
        species_code = ReactomeService._get_reactome_species_code(organism_name) 
        
        try:
            # 1. Enviar lista de genes para iniciar el análisis
            post_data = "\n".join(gene_list)
            
            logger.info(f"Submitting {len(gene_list)} genes to Reactome for {organism_name}.")

            # Utilizamos el nombre completo del organismo para el parámetro 'species'
            response = requests.post(
                ReactomeService.ANALYSIS_SERVICE_URL, 
                data=post_data, 
                params={'species': organism_name}, 
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
            
            pathways = report_data.get('pathways', [])
            
            logger.info(f"Received {len(pathways)} total pathways from Reactome before filtering.")
            
            # Muestra todos los resultados
            significant_pathways = pathways 
            
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