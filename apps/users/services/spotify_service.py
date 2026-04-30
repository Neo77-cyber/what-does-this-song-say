import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.conf import settings
from spotipy.cache_handler import DjangoSessionCacheHandler





def get_spotify_oauth(request):

    cache_handler = DjangoSessionCacheHandler(request)
    return SpotifyOAuth(
        client_id=settings.SPOTIPY_CLIENT_ID,
        client_secret=settings.SPOTIPY_CLIENT_SECRET,
        redirect_uri=settings.SPOTIPY_REDIRECT_URI,
        scope="user-library-read user-read-recently-played",
        cache_handler=cache_handler,
        show_dialog=True
    )

def get_user_library(token_info, refresh=False):
    """Fetches the user's 20 most recent 'Liked Songs'."""
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_saved_tracks(limit=20)
    
    tracks = []
    for item in results['items']:
        track = item['track']
        tracks.append({
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album_art': track['album']['images'][0]['url']
        })
    return tracks

def get_recently_played(token_info):
    """Fetches the 20 most recently played tracks."""
    sp = spotipy.Spotify(auth=token_info['access_token'])
    results = sp.current_user_recently_played(limit=20)
    
    tracks = []
    for item in results['items']:
        track = item['track']
        tracks.append({
            'id': track['id'],
            'name': track['name'],
            'artist': track['artists'][0]['name'],
            'album_art': track['album']['images'][0]['url']
        })
    return tracks