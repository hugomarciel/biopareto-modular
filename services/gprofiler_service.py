# services/gprofiler_service.py (CÓDIGO COMPLETO CON CORRECCIÓN DE ORGANISMOS)

"""
gProfiler API Service
"""

import requests
import logging

logger = logging.getLogger(__name__)


class GProfilerService:
    """Service to connect with g:Profiler API"""

    BASE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    ORGANISMS_URL = "https://biit.cs.ut.ee/gprofiler/api/util/organisms_list"

    @staticmethod
    def get_enrichment(gene_list, organism='hsapiens'):
        """
        Get biological enrichment for a gene list
        """
        try:
            payload = {
                "organism": organism,
                "query": gene_list,
                "sources": ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]
            }

            # Añadir logging de la llamada
            logger.info(f"g:Profiler: Calling API for organism '{organism}' with {len(gene_list)} genes.")
            
            response = requests.post(GProfilerService.BASE_URL, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                if 'result' in data and data['result']:
                    return data['result']
                else:
                    return []
            else:
                logger.error(f"Error in g:Profiler API: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error connecting with g:Profiler: {str(e)}")
            return None

    @staticmethod
    def _get_fallback_organisms():
        """Fallback organism list"""
        return [
            {'label': 'Homo sapiens (hsapiens)', 'value': 'hsapiens'},
            {'label': 'Mus musculus (mmusculus)', 'value': 'mmusculus'},
            {'label': 'Rattus norvegicus (rnorvegicus)', 'value': 'rnorvegicus'},
            {'label': 'Danio rerio (drerio)', 'value': 'drerio'},
            {'label': 'Drosophila melanogaster (dmelanogaster)', 'value': 'dmelanogaster'},
            {'label': 'Caenorhabditis elegans (celegans)', 'value': 'celegans'}
        ]

    @staticmethod
    def get_organisms_from_api():
        """Fetch available organisms from gProfiler API"""
        try:
            logger.info("g:Profiler: Attempting to fetch full organism list.")
            response = requests.get(GProfilerService.ORGANISMS_URL, timeout=10)
            response.raise_for_status()  # Lanza excepción para códigos 4xx/5xx

            organisms_data = response.json()
            options = []
            for org in organisms_data:
                # Asegurarse de que el ID del organismo (código corto) se usa como valor
                display_name = f"{org.get('display_name', org['id'])} ({org['id']})"
                options.append({'label': display_name, 'value': org['id']})
            
            logger.info(f"g:Profiler: Successfully fetched {len(options)} organisms.")
            return sorted(options, key=lambda x: x['label'])
        
        except Exception as e:
            logger.error(f"g:Profiler: Failed to fetch organisms. Falling back. Error: {e}")
            return GProfilerService._get_fallback_organisms()
        
# Mantenemos esta función para compatibilidad con la importación en app.py, pero solo llama a la clase
def get_organisms_from_api():
    return GProfilerService.get_organisms_from_api()