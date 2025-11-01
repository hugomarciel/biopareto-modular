# services/reactome_service.py (CÓDIGO FINAL ESTABLE Y ROBUSTO CON 5 ESPECIES)

"""
Reactome Pathway Enrichment Analysis Service
FALLBACK EXTENDIDO FINAL: Incluye Homo sapiens, Mus musculus, Rattus norvegicus, 
Danio rerio, y Saccharomyces cerevisiae.
"""

import logging
import json 
import reactome2py.analysis as analysis
import reactome2py.content as content

logger = logging.getLogger(__name__)

class ReactomeService:
    """Service to connect with the Reactome Content and Analysis Service API via reactome2py."""
    
    DEFAULT_ORGANISM = "Homo sapiens"

    @staticmethod
    def get_reactome_organisms():
        """
        Intenta obtener la lista completa de organismos. Si falla o está vacía, 
        aplica el fallback extendido con 5 organismos modelo comunes.
        """
        # 🔑 FALLBACK EXTENDIDO FINAL CON 5 ESPECIES MODELO 🔑
        EXTENDED_FALLBACK = [
            {'label': 'Homo sapiens (Human)', 'value': 'Homo sapiens'},
            {'label': 'Mus musculus (Mouse)', 'value': 'Mus musculus'},
            {'label': 'Rattus norvegicus (Rat)', 'value': 'Rattus norvegicus'},
            {'label': 'Danio rerio (Zebrafish)', 'value': 'Danio rerio'},
            {'label': 'Saccharomyces cerevisiae (Yeast)', 'value': 'Saccharomyces cerevisiae'}
        ]
        
        try:
            logger.info("Fetching Reactome species list using reactome2py.content.species().")
            
            species_data = content.species()
            options = []
            
            for species in species_data:
                if species.get('pathwayCounts', 0) > 0:
                     display_name = species['displayName']
                     # Usamos el nombre del organismo si no hay un nombre común fácil de obtener.
                     options.append({'label': display_name, 'value': display_name})
            
            if options:
                options.sort(key=lambda x: (x['value'] != 'Homo sapiens', x['value']))
                logger.info(f"Fetched {len(options)} Reactome species with pathways. (Success)")
                return options
            else:
                logger.warning("Fetched 0 species with pathways. Applying final extended fallback.")
                return EXTENDED_FALLBACK

        except Exception as e:
            logger.error(f"Error fetching Reactome species with reactome2py: {str(e)}")
            logger.warning("Error fetching species. Applying final extended fallback.")
            return EXTENDED_FALLBACK


    @staticmethod
    def get_enrichment(gene_list, organism_name=DEFAULT_ORGANISM):
        """
        Ejecuta el análisis de enriquecimiento utilizando la función probada y funcional
        de reactome2py.analysis.identifiers().
        """
        if not gene_list:
            logger.warning("No gene list provided for Reactome enrichment.")
            return []

        if organism_name is None:
             organism_name = ReactomeService.DEFAULT_ORGANISM
        
        try:
            logger.info(f"Starting Reactome enrichment for {len(gene_list)} genes in {organism_name} using analysis.identifiers().")
            
            ids_string = ','.join(gene_list)
            
            report_data = analysis.identifiers( 
                ids=ids_string,              
                species=organism_name, 
                projection=False,            
                page_size='999999',          
                p_value='1.0'                
            )
            
            pathways = report_data.get('pathways', [])
            
            logger.info(f"Received {len(pathways)} total pathways from Reactome.")
            
            # Mapeo a un formato de resultados simplificado y usable
            mapped_results = []
            for p in pathways:
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
            logger.error(f"Error executing Reactome enrichment with reactome2py: {str(e)}")
            return None