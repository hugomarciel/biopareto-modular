# services/reactome_service.py (CÓDIGO COMPLETO CON LA NUEVA FUNCIÓN DE DESCARGA)

"""
Reactome Pathway Enrichment Analysis Service
Añadidos logs de DEBUG para verificar el organismo utilizado por la API.
"""

import logging
import json 
import requests 
import reactome2py.analysis as analysis 
import base64 # 🔑 AÑADIDA ESTA IMPORTACIÓN

logger = logging.getLogger(__name__)

class ReactomeService:
    """Service to connect with the Reactome Content and Analysis Service API."""
    
    DEFAULT_ORGANISM = "Homo sapiens"
    
    # URL para obtener la lista de especies (Content Service - API Directa)
    SPECIES_URL = "https://reactome.org/ContentService/data/species/all"
    
    # URL Base para el Diagram Exporter (para generar la imagen coloreada)
    DIAGRAM_EXPORTER_BASE_URL = "https://reactome.org/ContentService/exporter/diagram/"


    @staticmethod
    def get_reactome_organisms():
        """
        Obtiene la lista completa de organismos disponibles en Reactome.
        (Esta función se mantiene sin cambios)
        """
        EXTENDED_FALLBACK = [
            {'label': 'Homo sapiens (Human)', 'value': 'Homo sapiens'},
            {'label': 'Mus musculus (Mouse)', 'value': 'Mus musculus'},
            {'label': 'Rattus norvegicus (Rat)', 'value': 'Rattus norvegicus'},
            {'label': 'Danio rerio (Zebrafish)', 'value': 'Danio rerio'},
            {'label': 'Saccharomyces cerevisiae (Yeast)', 'value': 'Saccharomyces cerevisiae'}
        ]
        
        try:
            logger.info(f"Fetching Reactome species list from direct API: {ReactomeService.SPECIES_URL}")
            
            response = requests.get(ReactomeService.SPECIES_URL, timeout=10)
            response.raise_for_status() 
            
            species_data = response.json()
            options = []
            
            for species in species_data:
                display_name = species.get('displayName')
                
                if display_name:
                     options.append({'label': display_name, 'value': display_name})
            
            if options:
                options.sort(key=lambda x: (x['value'] != 'Homo sapiens', x['value']))
                logger.info(f"Fetched {len(options)} Reactome species. (Success)")
                return options
            else:
                logger.warning("Fetched 0 species via direct API. Applying extended fallback.")
                return EXTENDED_FALLBACK

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Reactome API for species list: {str(e)}")
            logger.warning("Connection error fetching species. Applying extended fallback.")
            return EXTENDED_FALLBACK
        except Exception as e:
            logger.error(f"Unexpected error processing Reactome species list: {str(e)}")
            logger.warning("Processing error fetching species. Applying extended fallback.")
            return EXTENDED_FALLBACK


    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Ejecuta el análisis de enriquecimiento y extrae el token para la visualización.
        (Esta función se mantiene sin cambios)
        """
        if not gene_list:
            logger.warning("No gene list provided for Reactome enrichment.")
            return {'results': [], 'token': 'N/A', 'organism_used_api': 'N/A', 'organism_selected': organism_name, 'genes_analyzed': 0}

        if organism_name is None:
             organism_name = ReactomeService.DEFAULT_ORGANISM
        
        ids_string = ','.join(gene_list)

        analysis_token = 'N/A'
        organism_used_api = organism_name
        
        try:
            logger.info(f"SERVICE INPUT DEBUG: Running enrichment with species parameter: {organism_name} for {len(gene_list)} genes.")
            
            report_data = analysis.identifiers( 
                ids=ids_string,              
                species=organism_name, 
                projection=False,            
                page_size='999999',          
                p_value='1.0'                
            )
            
            analysis_token = report_data.get('token', 'N/A')
            if analysis_token == 'N/A' and 'summary' in report_data and report_data['summary']:
                analysis_token = report_data['summary'].get('token', 'N/A')
            
            if analysis_token == 'N/A':
                 analysis_token = 'REF_' + str(hash(ids_string))[:8] 
            
            if 'resourceSummary' in report_data and report_data['resourceSummary']:
                organism_used_api = report_data['resourceSummary'][0].get('speciesName', organism_name)

            logger.info(f"SERVICE OUTPUT DEBUG: API reported using organism: {organism_used_api}. Final Token: {analysis_token}")
            
            pathways = report_data.get('pathways', [])
            mapped_results = []
            for p in pathways:
                entities = p.get('entities', {})
                
                mapped_results.append({
                    'source': 'Reactome', 'term_name': p.get('name', 'N/A'), 'description': p.get('stId', 'N/A'), 
                    'p_value': entities.get('pValue', 1.0), 'entities_found': entities.get('found', 0), 
                    'entities_total': entities.get('total', 0), 'fdr_value': entities.get('fdr', 1.0)
                })
            
            return {
                'results': mapped_results,
                'token': analysis_token,
                'organism_used_api': organism_used_api, 
                'organism_selected': organism_name,
                'gene_list': gene_list,
                'genes_analyzed': len(gene_list)
            }

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment (Stable Identifiers Flow): {str(e)}")
            return None

    @staticmethod
    def get_diagram_url(pathway_st_id, analysis_token, file_format="png", quality="7"):
        """
        Construye la URL para la imagen del diagrama (esto es rápido).
        (Esta función se mantiene sin cambios)
        """
        if not pathway_st_id or not analysis_token or analysis_token.startswith('REF_'):
            logger.error("Missing valid pathway ID or analysis token to generate diagram URL.")
            return "/assets/reactome_placeholder.png" 

        url = (
            f"{ReactomeService.DIAGRAM_EXPORTER_BASE_URL}"
            f"{pathway_st_id}.{file_format}?"
            f"token={analysis_token}"
        )
        
        if file_format in ["png", "jpg"] and quality:
             url += f"&quality={quality}"
             
        logger.info(f"Generated Diagram URL for {pathway_st_id} with token.")
        return url

    # 🔑 --- INICIO DE LA NUEVA FUNCIÓN AÑADIDA --- 🔑
    @staticmethod
    def get_diagram_image_base64(pathway_st_id, analysis_token, file_format="png", quality=8):
        """
        Descarga la imagen del diagrama y la devuelve como una cadena base64.
        Esta es una operación SÍNCRONA (lenta) que bloquea el callback.
        """
        
        # 1. Construir la URL (usando la función que ya teníamos)
        #    Nota: pasamos 'quality' como string, ya que get_diagram_url lo espera así.
        diagram_url = ReactomeService.get_diagram_url(
            pathway_st_id, 
            analysis_token, 
            file_format, 
            str(quality)
        )
        
        logger.info(f"Downloading Reactome diagram from: {diagram_url}")
        
        try:
            # 2. Descargar la imagen (AQUÍ ES DONDE TARDA)
            response = requests.get(diagram_url, timeout=20) # 20 segundos de timeout
            
            if response.status_code == 200:
                # 3. Codificar la imagen a base64
                content_type = response.headers.get('Content-Type', 'image/png')
                image_bytes = response.content
                encoded_string = base64.b64encode(image_bytes).decode('utf-8')
                
                # 4. Retornar la cadena de datos que html.Img puede leer
                return f"data:{content_type};base64,{encoded_string}"
            else:
                logger.error(f"Failed to download diagram. Status: {response.status_code}, URL: {diagram_url}")
                return None
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading Reactome diagram: {e}")
            return None
    # 🔑 --- FIN DE LA NUEVA FUNCIÓN AÑADIDA --- 🔑