# Architecture du Projet spotify-mcp

Ce document présente l'architecture du projet spotify-mcp, un serveur MCP (Model Context Protocol) permettant à Claude d'interagir avec l'API Spotify.

## Vue d'ensemble

spotify-mcp est un serveur MCP (Model Context Protocol) qui permet à Claude d'interagir avec Spotify. Il utilise la bibliothèque spotipy pour communiquer avec l'API Spotify et expose des fonctionnalités comme la lecture, la pause, la recherche de musique et la gestion de la file d'attente.

## Diagramme de composants

```mermaid
graph TD
    Claude[Claude Assistant] <-->|MCP Protocol| Server[Server MCP]
    Server <-->|API Calls| SpotifyAPI[Spotify API Client]
    SpotifyAPI <-->|HTTP Requests| SpotifyWeb[Spotify Web API]
    
    subgraph "spotify-mcp"
        Server
        SpotifyAPI
        Utils[Utilities]
    end
    
    Server --> Utils
    SpotifyAPI --> Utils
```

## Structure du projet

```mermaid
graph LR
    Root[spotify-mcp/] --> Src[src/]
    Root --> Config[pyproject.toml]
    Root --> Readme[README.md]
    Root --> Env[.env]
    
    Src --> Package[spotify_mcp/]
    
    Package --> Init[__init__.py]
    Package --> ServerPy[server.py]
    Package --> SpotifyApiPy[spotify_api.py]
    Package --> UtilsPy[utils.py]
```

## Flux de données

```mermaid
sequenceDiagram
    participant Claude as Claude
    participant Server as Server MCP
    participant SpotifyAPI as Spotify API Client
    participant SpotifyWeb as Spotify Web API
    
    Claude->>Server: Appel d'outil (ex: playback, search, queue)
    Server->>SpotifyAPI: Demande correspondante
    SpotifyAPI->>SpotifyWeb: Requête HTTP API
    SpotifyWeb-->>SpotifyAPI: Réponse JSON
    SpotifyAPI-->>Server: Données formatées
    Server-->>Claude: Réponse formatée pour l'assistant
```

## Classes principales

### Modèle de classe pour server.py

```mermaid
classDiagram
    class Server {
        +list_prompts()
        +list_resources()
        +list_tools()
        +call_tool(name, arguments)
    }
    
    class ToolModel {
        +as_tool()
    }
    
    class Playback {
        +action: str
        +spotify_uri: Optional[str]
        +num_skips: Optional[int]
    }
    
    class Queue {
        +action: str
        +track_id: Optional[str]
    }
    
    class GetInfo {
        +item_uri: str
    }
    
    class Search {
        +query: str
        +qtype: Optional[str]
        +limit: Optional[int]
    }
    
    class TopItems {
        +item_type: str
        +time_range: Optional[str]
        +limit: Optional[int]
    }
    
    ToolModel <|-- Playback
    ToolModel <|-- Queue
    ToolModel <|-- GetInfo
    ToolModel <|-- Search
    ToolModel <|-- TopItems
```

### Modèle de classe pour spotify_api.py

```mermaid
classDiagram
    class Client {
        -sp: Spotify
        -auth_manager: SpotifyOAuth
        -cache_handler: CacheFileHandler
        -username: str
        -logger: Logger
        +get_username()
        +search(query, qtype, limit, device)
        +get_top_items(item_type, time_range, limit)
        +get_info(item_uri)
        +get_current_track()
        +start_playback(spotify_uri, device)
        +pause_playback(device)
        +add_to_queue(track_id, device)
        +get_queue(device)
        +skip_track(n)
        +previous_track()
        +seek_to_position(position_ms)
        +set_volume(volume_percent)
    }
```

## Fonctionnalités principales

1. **Lecture et contrôle**
   - Démarrer, mettre en pause, passer à la chanson suivante
   - Obtenir des informations sur la piste en cours
   - Gérer la file d'attente Spotify

2. **Recherche et découverte**
   - Rechercher des pistes, albums, artistes, playlists
   - Obtenir des informations détaillées sur un élément Spotify
   - Obtenir les éléments préférés de l'utilisateur (artistes, pistes)

## Flux d'authentification

```mermaid
sequenceDiagram
    participant User as Utilisateur
    participant Server as Server MCP
    participant SpotifyOAuth as SpotifyOAuth
    participant SpotifyWeb as Spotify Web API
    
    User->>Server: Lance le serveur MCP
    Server->>SpotifyOAuth: Initialise l'authentification
    SpotifyOAuth->>User: Ouvre le navigateur pour l'autorisation
    User->>SpotifyWeb: Autorise l'application
    SpotifyWeb->>SpotifyOAuth: Redirige avec le code d'autorisation
    SpotifyOAuth->>SpotifyWeb: Échange le code contre un token
    SpotifyWeb-->>SpotifyOAuth: Renvoie le token d'accès
    SpotifyOAuth-->>Server: Stocke le token dans le cache
    Server-->>User: Prêt à recevoir des commandes
```

## Interface MCP

Le projet implémente le protocole MCP (Model Context Protocol) qui permet à Claude d'interagir avec des outils externes. Les outils exposés incluent:

1. **playback** - Contrôle de la lecture
2. **queue** - Gestion de la file d'attente
3. **get_info** - Obtention d'informations sur un élément Spotify
4. **search** - Recherche d'éléments sur Spotify
5. **top_items** - Obtention des éléments préférés de l'utilisateur

## Dépendances

Les principales dépendances du projet sont:
- mcp==1.3.0 - Bibliothèque pour implémenter le protocole MCP
- python-dotenv>=1.0.1 - Pour gérer les variables d'environnement
- spotipy==2.24.0 - SDK Python pour l'API Spotify 