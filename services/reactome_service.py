# services/reactome_service.py (CÓDIGO COMPLETO CON DEBUGGING DE ORGANISMO)

"""
Reactome Pathway Enrichment Analysis Service
Añadidos logs de DEBUG para verificar el organismo utilizado por la API.
"""

import logging
import json 
import requests 
import reactome2py.analysis as analysis 

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
        """
        # FALLBACK EXTENDIDO FINAL CON 5 ESPECIES MODELO
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
        Añadido logging para verificar el organismo.
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
            # --- LOG DE ENTRADA AL SERVICIO ---
            logger.info(f"SERVICE INPUT DEBUG: Running enrichment with species parameter: {organism_name} for {len(gene_list)} genes.")
            
            # --- 1. LLAMADA ESTABLE Y FUNCIONAL CON reactome2py ---
            report_data = analysis.identifiers( 
                ids=ids_string,              
                species=organism_name, 
                projection=False,            
                page_size='999999',          
                p_value='1.0'                
            )
            
            # --- 2. Extracción de metadatos ---
            analysis_token = report_data.get('token', 'N/A')
            if analysis_token == 'N/A' and 'summary' in report_data and report_data['summary']:
                analysis_token = report_data['summary'].get('token', 'N/A')
            
            if analysis_token == 'N/A':
                 analysis_token = 'REF_' + str(hash(ids_string))[:8] 
            
            # Extraer el organismo que la API USÓ REALMENTE
            if 'resourceSummary' in report_data and report_data['resourceSummary']:
                organism_used_api = report_data['resourceSummary'][0].get('speciesName', organism_name)

            # --- LOG DE SALIDA DEL SERVICIO ---
            logger.info(f"SERVICE OUTPUT DEBUG: API reported using organism: {organism_used_api}. Final Token: {analysis_token}")
            
            # --- 3. Mapeo a resultados ---
            pathways = report_data.get('pathways', [])
            mapped_results = []
            for p in pathways:
                entities = p.get('entities', {})
                
                mapped_results.append({
                    'source': 'Reactome', 'term_name': p.get('name', 'N/A'), 'description': p.get('stId', 'N/A'), 
                    'p_value': entities.get('pValue', 1.0), 'entities_found': entities.get('found', 0), 
                    'entities_total': entities.get('total', 0), 'fdr_value': entities.get('fdr', 1.0)
                })
            
            # RETORNA EL DICCIONARIO COMPLETO con metadatos
            return {
                'results': mapped_results,
                'token': analysis_token,
                'organism_used_api': organism_used_api, # El valor verificado
                'organism_selected': organism_name,
                'gene_list': gene_list,
                'genes_analyzed': len(gene_list)
            }

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment (Stable Identifiers Flow): {str(e)}")
            return None

    @staticmethod
    def get_diagram_url(pathway_st_id, analysis_token, file_format="png", quality="7"):
        # ... (Función se mantiene igual) ...
        if not pathway_st_id or not analysis_token or analysis_token.startswith('REF_'):
            logger.error("Missing valid pathway ID or analysis token to generate diagram URL.")
            return "/assets/reactome_placeholder.png" 

        # URL base + ID de la vía + formato + parámetros de consulta
        url = (
            f"{ReactomeService.DIAGRAM_EXPORTER_BASE_URL}"
            f"{pathway_st_id}.{file_format}?"
            f"token={analysis_token}"
        )
        
        if file_format in ["png", "jpg"] and quality:
             url += f"&quality={quality}"
             
        logger.info(f"Generated Diagram URL for {pathway_st_id} with token.")
        return url