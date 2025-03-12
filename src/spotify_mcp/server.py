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
        def info(self, message):
            print(f"[INFO] {message}", file=sys.stderr)

        def error(self, message):
            print(f"[ERROR] {message}", file=sys.stderr)

        def debug(self, message):
            print(f"[DEBUG] {message}", file=sys.stderr)

        def trace(self, message, obj=None):
            print(f"[TRACE] {message}", file=sys.stderr)
            if obj:
                print(f"[TRACE] Object: {repr(obj)}", file=sys.stderr)

        def exception(self, message):
            print(f"[EXCEPTION] {message}", file=sys.stderr)
            print(f"[EXCEPTION] {traceback.format_exc()}", file=sys.stderr)

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
logger = setup_logger()

# Debug log startup information
logger.debug(f"Server initialized with options: {debug_object(options, 'options')}")
logger.debug(f"Python version: {sys.version}")
logger.debug(f"Arguments: {debug_object(sys.argv, 'sys.argv')}")

try:
    logger.debug("Initializing Spotify client")
    spotify_client = spotify_api.Client(logger)
    logger.debug("Spotify client initialized successfully")
except Exception as e:
    logger.exception(f"Failed to initialize Spotify client: {str(e)}")
    raise


class ToolModel(BaseModel):
    @classmethod
    def as_tool(cls):
        return types.Tool(
            name="Spotify" + cls.__name__,
            description=cls.__doc__,
            inputSchema=cls.model_json_schema(),
        )


class Playback(ToolModel):
    """Manages the current playback with the following actions:
    - get: Get information about user's current track.
    - start: Starts playing new item or resumes current playback if called with no uri.
    - pause: Pauses current playback.
    - skip: Skips current track.
    """

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


class GetInfo(ToolModel):
    """Get detailed information about a Spotify item (track, album, artist, or playlist)."""

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


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    return []


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    return []


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    logger.info("Listing available tools")
    logger.debug("handle_list_tools called")
    # await server.request_context.session.send_notification("are you recieving this notification?")
    tools = [
        Playback.as_tool(),
        Search.as_tool(),
        Queue.as_tool(),
        GetInfo.as_tool(),
        TopItems.as_tool(),
    ]
    logger.info(f"Available tools: {[tool.name for tool in tools]}")
    logger.debug(f"Returning {len(tools)} tools")
    return tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    assert name[:7] == "Spotify", f"Unknown tool: {name}"
    try:
        match name[7:]:
            case "Playback":
                action = arguments.get("action")
                match action:
                    case "get":
                        logger.info("Attempting to get current track")
                        curr_track = spotify_client.get_current_track()
                        if curr_track:
                            logger.info(
                                f"Current track retrieved: {curr_track.get('name', 'Unknown')}"
                            )
                            return [
                                types.TextContent(
                                    type="text", text=json.dumps(curr_track, indent=2)
                                )
                            ]
                        logger.info("No track currently playing")
                        return [
                            types.TextContent(type="text", text="No track playing.")
                        ]
                    case "start":
                        logger.info(f"Starting playback with arguments: {arguments}")
                        spotify_client.start_playback(
                            spotify_uri=arguments.get("spotify_uri")
                        )
                        logger.info("Playback started successfully")
                        return [
                            types.TextContent(type="text", text="Playback starting.")
                        ]
                    case "pause":
                        logger.info("Attempting to pause playback")
                        spotify_client.pause_playback()
                        logger.info("Playback paused successfully")
                        return [types.TextContent(type="text", text="Playback paused.")]
                    case "skip":
                        num_skips = int(arguments.get("num_skips", 1))
                        logger.info(f"Skipping {num_skips} tracks.")
                        spotify_client.skip_track(n=num_skips)
                        return [
                            types.TextContent(
                                type="text", text="Skipped to next track."
                            )
                        ]

            case "Search":
                logger.info(f"Performing search with arguments: {arguments}")
                search_results = spotify_client.search(
                    query=arguments.get("query", ""),
                    qtype=arguments.get("qtype", "track"),
                    limit=arguments.get("limit", 10),
                )
                logger.info("Search completed successfully.")
                return [
                    types.TextContent(
                        type="text", text=json.dumps(search_results, indent=2)
                    )
                ]

            case "Queue":
                logger.info(f"Queue operation with arguments: {arguments}")
                action = arguments.get("action")

                match action:
                    case "add":
                        track_id = arguments.get("track_id")
                        if not track_id:
                            logger.error("track_id is required for add to queue.")
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

            case "GetInfo":
                logger.info(f"Getting item info with arguments: {arguments}")
                item_info = spotify_client.get_info(item_uri=arguments.get("item_uri"))
                return [
                    types.TextContent(type="text", text=json.dumps(item_info, indent=2))
                ]

            case "TopItems":
                logger.info(f"Getting top items with arguments: {arguments}")
                item_type = arguments.get("item_type", "artists")
                time_range = arguments.get("time_range", "long_term")
                limit = arguments.get("limit", 10)

                top_items = spotify_client.get_top_items(
                    item_type=item_type, time_range=time_range, limit=limit
                )

                return [
                    types.TextContent(type="text", text=json.dumps(top_items, indent=2))
                ]

            case _:
                error_msg = f"Unknown tool: {name}"
                logger.error(error_msg)
                raise ValueError(error_msg)

    except SpotifyException as se:
        error_msg = f"Spotify Client error occurred: {str(se)}"
        logger.error(error_msg)
        return [
            types.TextContent(
                type="text",
                text=f"An error occurred with the Spotify Client: {str(se)}",
            )
        ]
    except Exception as e:
        error_msg = f"Unexpected error occurred: {str(e)}"
        logger.error(error_msg)
        raise


async def main():
    logger.debug("====== main() function started ======")
    try:
        logger.debug("Initializing stdio server")
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            logger.debug(
                f"stdio server initialized: read_stream={debug_object(read_stream, 'read_stream')}, write_stream={debug_object(write_stream, 'write_stream')}"
            )
            try:
                logger.debug("About to call server.run()")
                await server.run(read_stream, write_stream, options)
                logger.debug("server.run() completed normally")
            except Exception as e:
                logger.exception(f"Error in server.run(): {str(e)}")
                raise
        logger.debug("stdio server context exited")
    except Exception as e:
        logger.exception(f"Error in main(): {str(e)}")
        raise
    finally:
        logger.debug("====== main() function exiting ======")


if __name__ == "__main__":
    logger.debug("Module executed directly")
    import asyncio

    logger.debug("Starting asyncio.run(main())")
    try:
        asyncio.run(main())
        logger.debug("asyncio.run(main()) completed successfully")
    except Exception as e:
        logger.exception(f"Uncaught exception in asyncio.run(main()): {str(e)}")
        sys.exit(1)
    logger.debug("Script exiting")
