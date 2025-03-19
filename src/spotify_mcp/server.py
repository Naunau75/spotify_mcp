import sys
import json
import traceback
from typing import Optional, Any

import mcp.types as types
from mcp.server import Server  # , stdio_server
import mcp.server.stdio
from pydantic import BaseModel, Field
from spotipy import SpotifyException

from spotify_mcp import spotify_api


def setup_logger():
    class Logger:
        def __init__(self):
            # Créer un fichier de log avec le chemin complet
            import os

            log_dir = os.path.dirname(os.path.abspath(__file__))
            self.log_file = open(
                os.path.join(log_dir, "spotify_mcp.log"), "a", encoding="utf-8"
            )

        def info(self, message):
            log_message = f"[INFO] {message}"
            print(log_message, file=self.log_file)
            self.log_file.flush()
            print(log_message)  # Affiche aussi dans le terminal

        def error(self, message):
            log_message = f"[ERROR] {message}"
            print(log_message, file=self.log_file)
            self.log_file.flush()
            print(log_message)

        def debug(self, message):
            log_message = f"[DEBUG] {message}"
            print(log_message, file=self.log_file)
            self.log_file.flush()
            print(log_message)

        def trace(self, message, obj=None):
            log_message = f"[TRACE] {message}"
            print(log_message, file=self.log_file)
            if obj:
                print(f"[TRACE] Object: {repr(obj)}", file=self.log_file)
            self.log_file.flush()
            print(log_message)
            if obj:
                print(f"[TRACE] Object: {repr(obj)}")

        def exception(self, message):
            log_message = f"[EXCEPTION] {message}\n{traceback.format_exc()}"
            print(log_message, file=self.log_file)
            self.log_file.flush()
            print(log_message)

        def __del__(self):
            # Fermer le fichier de log quand l'objet est détruit
            if hasattr(self, "log_file"):
                self.log_file.close()

    return Logger()


def debug_object(obj: Any, name: str = "Object") -> str:
    """Helper function to debug print objects"""
    if obj is None:
        return f"{name}: None"
    try:
        return f"{name} ({type(obj).__name__}): {repr(obj)}"
    except Exception as e:
        return f"{name}: <Error getting representation: {str(e)}>"


server = Server("spotify-mcp")
options = server.create_initialization_options()
global_logger = setup_logger()

# Debug log startup information
global_logger.debug(
    f"Server initialized with options: {debug_object(options, 'options')}"
)
global_logger.debug(f"Python version: {sys.version}")
global_logger.debug(f"Arguments: {debug_object(sys.argv, 'sys.argv')}")

try:
    global_logger.debug("Initializing Spotify client")
    spotify_client = spotify_api.Client(global_logger)
    global_logger.debug("Spotify client initialized successfully")
except Exception as e:
    global_logger.exception(f"Failed to initialize Spotify client: {str(e)}")
    raise


class ToolModel(BaseModel):
    @classmethod
    def as_tool(cls):
        return types.Tool(
            name="Spotify" + cls.__name__,
            description=cls.__doc__,
            inputSchema=cls.model_json_schema(),
        )


class Play(ToolModel):

    action: str = Field(
        description="Action to perform: 'get', 'start', 'pause' or 'skip'."
    )
    spotify_uri: Optional[str] = Field(
        default=None,
        description="Spotify uri of item to play for 'start' action. "
        + "If omitted, resumes current playback.",
    )
    num_skips: Optional[int] = Field(
        default=1, description="Number of tracks to skip for `skip` action."
    )


class Queue(ToolModel):
    """Manage the playback queue - get the queue or add tracks."""

    action: str = Field(description="Action to perform: 'add' or 'get'.")
    track_id: Optional[str] = Field(
        default=None, description="Track ID to add to queue (required for add action)"
    )


class Info(ToolModel):
    """Get information about an item (track, album, artist, or playlist)."""

    item_uri: str = Field(
        description="URI of the item to get information about. "
        + "If 'playlist' or 'album', returns its tracks. "
        + "If 'artist', returns albums and top tracks."
    )
    # qtype: str = Field(default="track", description="Type of item: 'track', 'album', 'artist', or 'playlist'. "
    #                                                 )


class Search(ToolModel):
    """Search for tracks, albums, artists, or playlists on Spotify."""

    query: str = Field(description="query term")
    qtype: Optional[str] = Field(
        default="track",
        description="Type of items to search for (track, album, artist, playlist, "
        + "or comma-separated combination)",
    )
    limit: Optional[int] = Field(
        default=10, description="Maximum number of items to return"
    )


# Nouvelle classe pour l'historique des artistes les plus écoutés
class TopItems(ToolModel):
    """Get the user's top artists or tracks based on calculated affinity."""

    item_type: str = Field(
        description="Type of items to retrieve ('artists' or 'tracks')"
    )
    time_range: Optional[str] = Field(
        default="long_term",
        description="Time period over which to retrieve top items: 'long_term' (~ 1 year), 'medium_term' (~ 6 months), or 'short_term' (~ 4 weeks)",
    )
    limit: Optional[int] = Field(
        default=10, description="Number of items to retrieve (max 50)"
    )


class PlaylistCreator(ToolModel):
    """Création et gestion des playlists Spotify"""

    action: str = Field(description="Action : 'create', 'search_and_add'")  # Simplifié
    playlist_details: Optional[dict] = Field(
        description={
            "name": "Nom de la playlist",
            "description": "Description de la playlist",
            "public": "Visibilité (true/false)",
            "collaborative": "Playlist collaborative (true/false)",
        }
    )
    playlist_id: Optional[str] = Field(
        description="ID de la playlist (requis pour search_and_add)"
    )
    search_query: Optional[str] = Field(description="Recherche de titres à ajouter")
    limit: Optional[int] = Field(
        default=10, description="Nombre maximum de résultats de recherche"
    )


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return []


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return []


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    global_logger.info("Listing available tools")
    global_logger.debug("handle_list_tools called")
    # await server.request_context.session.send_notification("are you recieving this notification?")
    tools = [
        Play.as_tool(),
        Search.as_tool(),
        Queue.as_tool(),
        Info.as_tool(),
        TopItems.as_tool(),
        PlaylistCreator.as_tool(),
    ]
    global_logger.info(f"Available tools: {[tool.name for tool in tools]}")
    global_logger.debug(f"Returning {len(tools)} tools")
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    global_logger.info(f"Tool called: {name} with arguments: {arguments}")
    assert name[:7] == "Spotify", f"Unknown tool: {name}"
    try:
        match name[7:]:
            case "Play":
                action = arguments.get("action")
                match action:
                    case "get":
                        global_logger.info("Attempting to get current track")
                        curr_track = spotify_client.get_current_track()
                        if curr_track:
                            global_logger.info(
                                f"Current track retrieved: {curr_track.get('name', 'Unknown')}"
                            )
                            return [
                                types.TextContent(
                                    type="text", text=json.dumps(curr_track, indent=2)
                                )
                            ]
                        global_logger.info("No track currently playing")
                        return [
                            types.TextContent(type="text", text="No track playing.")
                        ]
                    case "start":
                        global_logger.info(
                            f"Starting playback with arguments: {arguments}"
                        )
                        spotify_client.start_playback(
                            spotify_uri=arguments.get("spotify_uri")
                        )
                        global_logger.info("Playback started successfully")
                        return [
                            types.TextContent(type="text", text="Playback starting.")
                        ]
                    case "pause":
                        global_logger.info("Attempting to pause playback")
                        spotify_client.pause_playback()
                        global_logger.info("Playback paused successfully")
                        return [types.TextContent(type="text", text="Playback paused.")]
                    case "skip":
                        num_skips = int(arguments.get("num_skips", 1))
                        global_logger.info(f"Skipping {num_skips} tracks.")
                        spotify_client.skip_track(n=num_skips)
                        return [
                            types.TextContent(
                                type="text", text="Skipped to next track."
                            )
                        ]

            case "Search":
                global_logger.info(f"Performing search with arguments: {arguments}")
                search_results = spotify_client.search(
                    query=arguments.get("query", ""),
                    qtype=arguments.get("qtype", "track"),
                    limit=arguments.get("limit", 10),
                )
                global_logger.info("Search completed successfully.")
                return [
                    types.TextContent(
                        type="text", text=json.dumps(search_results, indent=2)
                    )
                ]

            case "Queue":
                global_logger.info(f"Queue operation with arguments: {arguments}")
                action = arguments.get("action")

                match action:
                    case "add":
                        track_id = arguments.get("track_id")
                        if not track_id:
                            global_logger.error(
                                "track_id is required for add to queue."
                            )
                            return [
                                types.TextContent(
                                    type="text",
                                    text="track_id is required for add action",
                                )
                            ]
                        spotify_client.add_to_queue(track_id)
                        return [
                            types.TextContent(
                                type="text", text=f"Track added to queue."
                            )
                        ]

                    case "get":
                        queue = spotify_client.get_queue()
                        return [
                            types.TextContent(
                                type="text", text=json.dumps(queue, indent=2)
                            )
                        ]

                    case _:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Unknown queue action: {action}. Supported actions are: add, remove, and get.",
                            )
                        ]

            case "Info":
                global_logger.info(f"Getting item info with arguments: {arguments}")
                item_info = spotify_client.get_info(item_uri=arguments.get("item_uri"))
                return [
                    types.TextContent(type="text", text=json.dumps(item_info, indent=2))
                ]

            case "TopItems":
                global_logger.info(f"Getting top items with arguments: {arguments}")
                item_type = arguments.get("item_type", "artists")
                time_range = arguments.get("time_range", "long_term")
                limit = arguments.get("limit", 10)

                top_items = spotify_client.get_top_items(
                    item_type=item_type, time_range=time_range, limit=limit
                )

                return [
                    types.TextContent(type="text", text=json.dumps(top_items, indent=2))
                ]

            case "PlaylistCreator":
                global_logger.info(
                    f"Handling playlist operation with arguments: {arguments}"
                )
                action = arguments.get("action")

                match action:
                    case "create":
                        global_logger.info("Creating a new playlist")
                        details = arguments.get("playlist_details", {})

                        # Si details est une chaîne JSON, la convertir en dictionnaire
                        if isinstance(details, str):
                            try:
                                details = json.loads(details)
                            except json.JSONDecodeError as e:
                                raise ValueError(
                                    f"Format invalide pour playlist_details: {e}"
                                )

                        if "name" not in details:
                            raise ValueError("Le nom de la playlist est requis")

                        # Récupérer l'ID de l'utilisateur courant
                        user_id = spotify_client.sp.current_user()["id"]

                        # Créer la playlist en utilisant la méthode correcte de spotipy
                        new_playlist = spotify_client.sp.user_playlist_create(
                            user=user_id,
                            name=details.get("name"),
                            public=details.get("public", True),
                            collaborative=details.get("collaborative", False),
                            description=details.get("description", ""),
                        )

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Playlist créée avec succès! ID: {new_playlist['id']}",
                            )
                        ]

                    case "search_and_add":
                        global_logger.info("Searching tracks and adding to playlist")
                        playlist_id = arguments.get("playlist_id")
                        search_query = arguments.get("search_query")
                        limit = arguments.get("limit", 10)

                        global_logger.info(
                            f"Arguments reçus: {json.dumps(arguments, indent=2)}"
                        )

                        # Vérifier si l'ID de playlist est un nom plutôt qu'un ID
                        try:
                            # Rechercher d'abord la playlist par son nom si ce n'est pas un ID valide
                            if (
                                not playlist_id.startswith("spotify:playlist:")
                                and not len(playlist_id) == 22
                            ):
                                playlists = spotify_client.sp.current_user_playlists()
                                for playlist in playlists["items"]:
                                    if playlist["name"] == playlist_id:
                                        playlist_id = playlist["id"]
                                        global_logger.info(
                                            f"Playlist trouvée par nom, ID: {playlist_id}"
                                        )
                                        break
                                else:
                                    raise ValueError(
                                        f"Playlist non trouvée : {playlist_id}"
                                    )

                            # Recherche du titre
                            global_logger.info(f"Recherche du titre : {search_query}")
                            sp_results = spotify_client.sp.search(
                                q=search_query,
                                type="track",
                                limit=1,
                                market="FR",  # Ajout du marché pour de meilleurs résultats
                            )

                            global_logger.info(
                                f"Résultats de recherche reçus: {bool(sp_results)}"
                            )
                            global_logger.debug(
                                f"Résultats détaillés: {json.dumps(sp_results, indent=2)}"
                            )

                            if not sp_results or not sp_results.get("tracks", {}).get(
                                "items"
                            ):
                                raise ValueError(
                                    f"Aucun titre trouvé pour : {search_query}"
                                )

                            track = sp_results["tracks"]["items"][0]
                            track_uri = track["uri"]
                            global_logger.info(
                                f"Titre trouvé : {track['name']} ({track_uri})"
                            )

                            # Ajouter le titre à la playlist
                            add_result = spotify_client.sp.playlist_add_items(
                                playlist_id=playlist_id, items=[track_uri]
                            )
                            global_logger.info(f"Résultat de l'ajout : {add_result}")

                            return [
                                types.TextContent(
                                    type="text",
                                    text=json.dumps(
                                        {
                                            "message": "Titre ajouté avec succès !",
                                            "track": {
                                                "name": track["name"],
                                                "artist": track["artists"][0]["name"],
                                                "uri": track_uri,
                                            },
                                        },
                                        indent=2,
                                    ),
                                )
                            ]

                        except Exception as e:
                            error_details = (
                                f"Erreur détaillée : {str(e)}\n{traceback.format_exc()}"
                            )
                            global_logger.error(error_details)
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Erreur lors de l'opération : {str(e)}",
                                )
                            ]

                    case _:
                        error_msg = f"Action inconnue: {action}. Actions supportées: create, search_and_add"
                        global_logger.error(error_msg)
                        return [types.TextContent(type="text", text=error_msg)]

            case _:
                error_msg = f"Unknown tool: {name}"
                global_logger.error(error_msg)
                raise ValueError(error_msg)

    except SpotifyException as se:
        error_msg = f"Spotify Client error occurred: {str(se)}"
        global_logger.error(error_msg)
        return [
            types.TextContent(
                type="text",
                text=f"An error occurred with the Spotify Client: {str(se)}",
            )
        ]
    except Exception as e:
        error_msg = f"Unexpected error occurred: {str(e)}"
        global_logger.error(error_msg)
        raise


async def main():
    global_logger.debug("====== main() function started ======")
    try:
        global_logger.debug("Initializing stdio server")
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            global_logger.debug(
                f"stdio server initialized: read_stream={debug_object(read_stream, 'read_stream')}, write_stream={debug_object(write_stream, 'write_stream')}"
            )
            try:
                global_logger.debug("About to call server.run()")
                await server.run(read_stream, write_stream, options)
                global_logger.debug("server.run() completed normally")
            except Exception as e:
                global_logger.exception(f"Error in server.run(): {str(e)}")
                raise
        global_logger.debug("stdio server context exited")
    except Exception as e:
        global_logger.exception(f"Error in main(): {str(e)}")
        raise
    finally:
        global_logger.debug("====== main() function exiting ======")


if __name__ == "__main__":
    global_logger.debug("Module executed directly")
    import asyncio

    global_logger.debug("Starting asyncio.run(main())")
    try:
        asyncio.run(main())
        global_logger.debug("asyncio.run(main()) completed successfully")
    except Exception as e:
        global_logger.exception(f"Uncaught exception in asyncio.run(main()): {str(e)}")
        sys.exit(1)
    global_logger.debug("Script exiting")
