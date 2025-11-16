# services/gprofiler_service.py

"""
Módulo de Servicio para la API de g:Profiler

Este archivo encapsula toda la lógica de comunicación con 
los endpoints de la API de g:Profiler.
"""

# Se importa 'requests' para realizar solicitudes HTTP a la API.
import requests
# Se importa 'logging' para registrar eventos, errores y mensajes de depuración.
import logging

# Se configura una instancia de 'logger' específica para este módulo.
# '__name__' asegura que el logger tenga el nombre del archivo (services.gprofiler_service).
logger = logging.getLogger(__name__)


class GProfilerService:
    """
    Clase estática que agrupa los métodos para interactuar con g:Profiler.
    No se necesita instanciar esta clase, se usan sus métodos directamente.
    """

    # URL base para el endpoint de análisis de enriquecimiento funcional (g:GOSt).
    BASE_URL = "https://biit.cs.ut.ee/gprofiler/api/gost/profile/"
    # URL para el endpoint que lista los organismos disponibles.
    ORGANISMS_URL = "https://biit.cs.ut.ee/gprofiler/api/util/organisms_list"

    @staticmethod
    def get_enrichment(gene_list, organism='hsapiens', sources=None):
        """
        Obtiene los resultados de enriquecimiento biológico para una lista de genes dada.
        
        Args:
            gene_list (list): La lista de IDs de genes a analizar.
            organism (str): El ID del organismo (ej. 'hsapiens').
            sources (list): Lista de fuentes de datos (ej. ['GO:BP', 'KEGG']).

        Returns:
            dict: El objeto JSON completo de la respuesta de la API (incluyendo 'result' y 'meta').
                  Retorna None si la solicitud falla.
        """
        try:
            # Si no se especifican fuentes, se utiliza una lista por defecto.
            if not sources:
                sources = ["GO:BP", "GO:MF", "GO:CC", "KEGG", "REAC"]

            # Registro de depuración (reemplaza a print) con información de la solicitud.
            logger.debug(f"Solicitando enriquecimiento a g:Profiler para {len(gene_list)} genes.")
            logger.debug(f"Organismo: {organism}, Fuentes: {sources}") 
            
            # Se construye el 'payload' (cuerpo de la solicitud) en formato JSON.
            payload = {
                "organism": organism,
                "query": gene_list,    # Esta es la lista "sucia" (con todos los genes).
                "sources": sources,     
                "all_results": True     # Se piden todos los resultados (significativos o no).
            }

            # Se realiza la solicitud POST a la API, con un tiempo de espera (timeout) de 420s.
            response = requests.post(GProfilerService.BASE_URL, json=payload, timeout=420)

            # Se verifica si la solicitud fue exitosa (código de estado 200).
            if response.status_code == 200:
                # Se convierte la respuesta JSON en un diccionario de Python.
                data = response.json()
                logger.debug("Respuesta de g:Profiler recibida exitosamente.")
                # Se retorna la respuesta completa. Esto es crucial, ya que
                # necesitamos tanto 'result' (los términos) como 'meta' (la validación).
                return data
            else:
                # Si la API devuelve un error (ej. 404, 500), se registra y retorna None.
                logger.error(f"Error en la API de g:Profiler: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            # Si ocurre un error de red o de timeout, se captura, registra y retorna None.
            logger.error(f"Error de conexión con g:Profiler: {str(e)}")
            return None

    # La función 'validate_genes' se eliminó, ya que este
    # análisis ahora se realiza implícitamente en 'get_enrichment'
    # y se maneja en el callback usando los metadatos.


def get_organisms_from_api():
    """
    Obtiene la lista de organismos disponibles desde la API de g:Profiler.
    Esto se usa para poblar el menú desplegable en la UI.
    """
    try:
        # Se realiza una solicitud GET simple para obtener la lista.
        response = requests.get(GProfilerService.ORGANISMS_URL, timeout=10)
        
        # Si la solicitud es exitosa:
        if response.status_code == 200:
            organisms_data = response.json()
            options = []
            # Se itera sobre la lista de organismos...
            for org in organisms_data:
                # ...y se formatea cada uno en el formato que espera dcc.Dropdown (label y value).
                display_name = f"{org.get('display_name', org['id'])} ({org['id']})"
                options.append({'label': display_name, 'value': org['id']})
            # Se retorna la lista de opciones ordenada alfabéticamente.
            return sorted(options, key=lambda x: x['label'])
        else:
            # Si la API falla, se retorna una lista de 'fallback' (emergencia).
            return _get_fallback_organisms()
    except Exception as e:
        # Si hay un error de conexión, se registra y se usa la lista de fallback.
        logger.error(f"Error obteniendo lista de organismos: {e}")
        return _get_fallback_organisms()


def _get_fallback_organisms():
    """
    Retorna una lista estática de organismos comunes.
    Se usa solo si la API de g:Profiler falla, para que la app siga funcionando.
    """
    return [
        {'label': 'Homo sapiens (hsapiens)', 'value': 'hsapiens'},
        {'label': 'Mus musculus (mmusculus)', 'value': 'mmusculus'},
        {'label': 'Rattus norvegicus (rnorvegicus)', 'value': 'rnorvegicus'},
        {'label': 'Danio rerio (drerio)', 'value': 'drerio'},
        {'label': 'Drosophila melanogaster (dmelanogaster)', 'value': 'dmelanogaster'},
        {'label': 'Caenorhabditis elegans (celegans)', 'value': 'celegans'}
    ]