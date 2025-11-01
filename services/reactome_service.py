# services/reactome_service.py (CÓDIGO CORREGIDO PARA USAR SPECIES ID)

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

    # URL para iniciar el análisis (POST), incluyendo 'projection'
    ANALYSIS_SERVICE_URL = "https://reactome.org/AnalysisService/identifiers/projection" 
    # URL para obtener el reporte
    REPORT_SERVICE_URL = "https://reactome.org/AnalysisService/report"
    # URL para obtener la lista de especies
    SPECIES_URL = "https://reactome.org/ContentService/data/species/all"
    
    # Organismo por defecto (Human ID)
    DEFAULT_ORGANISM_ID = 9606

    # 1. Función de fallback (corregida para usar IDs)
    @staticmethod
    def _get_fallback_organisms():
        """Fallback organism list using Species IDs."""
        return [
            {'label': 'Homo sapiens', 'value': 9606},
            {'label': 'Mus musculus', 'value': 10090},
            {'label': 'Rattus norvegicus', 'value': 10116},
            {'label': 'Danio rerio', 'value': 7955},
        ]
    
    # 2. Función para obtener la lista de organismos con ID
    @staticmethod
    def get_reactome_organisms():
        """Fetch available organisms from Reactome API and use dbId as value."""
        try:
            response = requests.get(ReactomeService.SPECIES_URL, timeout=10)
            if response.status_code == 200:
                species_data = response.json()
                options = []
                for sp in species_data:
                    # Usar dbId (Species ID) como el valor, que la API necesita
                    options.append({'label': sp.get('displayName', 'Unknown'), 'value': sp.get('dbId', sp['displayName'])})
                # Ordenar options alfabéticamente por nombre
                return sorted(options, key=lambda x: x['label'])
            else:
                return ReactomeService._get_fallback_organisms()
        except Exception as e:
            logger.error(f"Error fetching Reactome organisms: {e}")
            return ReactomeService._get_fallback_organisms()
        
    # 3. Función de enriquecimiento (CORREGIDA para usar Species ID)
    @staticmethod
    def get_enrichment(gene_list, organism_id):
        """
        Executes Reactome pathway enrichment analysis.
        organism_id is now the species dbId (e.g., 9606 for human).
        """
        try:
            # --- Paso 1: Iniciar el Análisis (Obtener el token) ---
            analysis_payload = {
                "identifiers": gene_list,
                # La clave 'species' debe ser el dbId.
                "species": str(organism_id) # Reactome prefiere el ID como string aquí.
            }

            analysis_response = requests.post(
                ReactomeService.ANALYSIS_SERVICE_URL, 
                data=json.dumps(analysis_payload), 
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if analysis_response.status_code != 200:
                logger.error(f"Error in Reactome Analysis Service (Step 1): {analysis_response.status_code} - {analysis_response.text}")
                return None

            analysis_data = analysis_response.json()
            token = analysis_data.get('summary', {}).get('token')

            if not token:
                logger.error("Reactome analysis token not found in response.")
                return []

            # --- Paso 2: Obtener el Reporte (Usar el token y el species ID) ---
            # La URL para el reporte requiere el token y el species ID
            report_url = f"{ReactomeService.REPORT_SERVICE_URL}/{token}/species/{organism_id}"
            report_response = requests.get(report_url, timeout=30)
            
            if report_response.status_code != 200:
                logger.error(f"Error in Reactome Analysis Service (Step 2): {report_response.status_code} - {report_response.text}")
                # Intentamos limpiar el token
                requests.delete(f"{ReactomeService.REPORT_SERVICE_URL}/{token}")
                return None

            report_data = report_response.json()
            
            # Limpiamos el token después de obtener el reporte
            requests.delete(f"{ReactomeService.REPORT_SERVICE_URL}/{token}")

            pathways = report_data.get('pathways', [])
            
            logger.info(f"Received {len(pathways)} total pathways from Reactome before filtering.")
            
            # Muestra todos los resultados (como se definió anteriormente)
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