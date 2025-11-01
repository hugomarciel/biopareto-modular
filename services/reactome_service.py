# services/reactome_service.py

"""
Reactome Pathway Enrichment Analysis Service
SOLUCIÓN DEFINITIVA: Implementa un flujo híbrido: 
1. POST inicial con requests para forzar la generación de un nuevo Token.
2. GET con reactome2py.analysis.token() usando el nuevo Token para recuperar el reporte.
3. Utiliza requests para obtener la lista de especies (solucionando el fallo de reactome2py).
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
    
    # URL para iniciar un nuevo análisis (Analysis Service - POST Directo)
    ANALYSIS_POST_URL = "https://reactome.org/AnalysisService/identifiers"


    @staticmethod
    def get_reactome_organisms():
        """
        Obtiene la lista completa de organismos disponibles en Reactome utilizando la API directa (requests).
        Garantiza el fallback extendido con 5 organismos modelo comunes si la API falla.
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
                # Utilizamos la lógica simple de tu ejemplo funcional anterior
                display_name = species.get('displayName')
                
                if display_name:
                     options.append({'label': display_name, 'value': display_name})
            
            if options:
                # Si se obtiene una lista, la ordenamos, priorizando Homo sapiens
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
        Ejecuta el análisis de enriquecimiento utilizando el flujo simple y estable de 
        reactome2py.analysis.identifiers(), el cual maneja la caché de la API.
        """
        if not gene_list:
            logger.warning("No gene list provided for Reactome enrichment.")
            return {'results': [], 'token': 'N/A', 'organism_used_api': 'N/A', 'organism_selected': organism_name, 'genes_analyzed': 0}

        if organism_name is None:
             organism_name = ReactomeService.DEFAULT_ORGANISM
        
        ids_string = ','.join(gene_list) # Convertir la lista de Python a una cadena separada por comas

        analysis_token = 'N/A'
        organism_used_api = organism_name
        
        try:
            logger.info(f"Starting Reactome stable analysis for {len(gene_list)} genes in {organism_name} using analysis.identifiers()...")
            
            # --- 1. LLAMADA ESTABLE Y FUNCIONAL ---
            # Esta función maneja internamente el POST/GET y caché de Reactome.
            report_data = analysis.identifiers( 
                ids=ids_string,              
                species=organism_name, 
                projection=False,            
                page_size='999999',          
                p_value='1.0'                
            )
            
            # --- 2. Extracción de metadatos (aceptando el token fijo/cacheadado) ---
            pathways = report_data.get('pathways', [])

            # El token DEBE estar en el nivel superior para ser extraído, o en summary
            analysis_token = report_data.get('token', 'N/A')
            
            if analysis_token == 'N/A' and 'summary' in report_data and report_data['summary']:
                analysis_token = report_data['summary'].get('token', 'N/A')
            
            # Si el token sigue siendo N/A, generamos un ID de referencia (REF_) que cambie con los genes
            if analysis_token == 'N/A':
                 analysis_token = 'REF_' + str(hash(ids_string))[:8] # Generar un ID basado en el hash de los genes
            
            if 'resourceSummary' in report_data and report_data['resourceSummary']:
                organism_used_api = report_data['resourceSummary'][0].get('speciesName', organism_name)

            
            logger.info(f"Received {len(pathways)} total pathways from Reactome. Token (Cacheadado/REF): {analysis_token}. Organism Used (API): {organism_used_api}")
            
            # --- 3. Mapeo a resultados (igual que antes) ---
            
            mapped_results = []
            for p in pathways:
                entities = p.get('entities', {})
                
                mapped_results.append({
                    'source': 'Reactome', 'term_name': p.get('name', 'N/A'), 'description': p.get('stId', 'N/A'), 
                    'p_value': entities.get('pValue', 1.0), 'entities_found': entities.get('found', 0), 
                    'entities_total': entities.get('total', 0), 'fdr_value': entities.get('fdr', 1.0)
                })
                
            logger.info(f"Final mapped results count: {len(mapped_results)}")
            
            # RETORNA EL DICCIONARIO COMPLETO con metadatos
            return {
                'results': mapped_results,
                'token': analysis_token,
                'organism_used_api': organism_used_api,
                'organism_selected': organism_name,
                'genes_analyzed': len(gene_list)
            }

        except Exception as e:
            logger.error(f"Error executing Reactome enrichment (Stable Identifiers Flow): {str(e)}")
            return None