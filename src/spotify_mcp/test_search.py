import sys
import json
from spotify_mcp.spotify_api import Client
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("test_search.log"),
    ],
)
logger = logging.getLogger(__name__)


def test_spotify_search():
    try:
        # Initialisation du client
        logger.info("Initialisation du client Spotify...")
        spotify_client = Client(logger)
        playlist_id = "3m5hb1nCyn5KnUFKPJa21U"

        # Test de recherche
        search_query = "Genesis Mama"
        logger.info(f"Test de recherche pour : {search_query}")

        # Effectuer la recherche
        results = spotify_client.sp.search(
            q=search_query, type="track", limit=1, market="FR"
        )

        track = results["tracks"]["items"][0]
        track_uri = track["uri"]
        logger.info(f"Titre trouvé : {track['name']} ({track_uri})")

        add_result = spotify_client.sp.playlist_add_items(
            playlist_id=playlist_id, items=[track_uri]
        )
        logger.info(f"Résultat de l'ajout : {add_result}")

    except Exception as e:
        logger.error(f"Une erreur s'est produite : {str(e)}")


if __name__ == "__main__":
    logger.info("Démarrage des tests de recherche Spotify")
    test_spotify_search()
    logger.info("Tests terminés")
