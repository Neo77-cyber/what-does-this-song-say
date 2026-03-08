import logging
import requests
from langdetect import detect_langs, DetectorFactory
from lyricsgenius import Genius
from django.conf import settings
from ..models import SavedTranslation
from sentry_sdk import capture_message, capture_exception

logger = logging.getLogger(__name__) # Use the module's name for the logger
DetectorFactory.seed = 0

def process_song_translation(track_name, artist_name):
    logger.info(f" Starting translation for: {track_name} by {artist_name}")

    # STEP 0: Cache Check
    cached = SavedTranslation.objects.filter(
        track_name__iexact=track_name, 
        artist_name__iexact=artist_name
    ).first()

    if cached:
        
        logger.info(f" Cache Hit for: {track_name}")
        return {'original': cached.original_lyrics, 'translated': cached.translated_lyrics, 'status': 'success'}

    # STEP 1: Genius Fetch with specific error handling
    # STEP 1: Genius Fetch (The fixed API-Safe version)
    # STEP 1: LRCLIB Fetch (Replacement for Genius)
    lyrics = None
    try:
        # Search for the track on LRCLIB
        lrclib_url = "https://lrclib.net/api/search"
        params = {'track_name': track_name, 'artist_name': artist_name}
        
        # Adding a timeout and a generic User-Agent is good practice
        headers = {'User-Agent': 'WhatDoesTheSongSay/1.0 (Educational Project)'}
        response = requests.get(lrclib_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        
        if results:
            # We look for 'plainLyrics'. If it's missing, we check 'syncedLyrics'
            # and strip the timestamps, but usually plainLyrics is what we want.
            # We take the first result that actually has text.
            for hit in results:
                if hit.get('plainLyrics'):
                    lyrics = hit['plainLyrics']
                    break
                elif hit.get('syncedLyrics'):
                    # Basic fallback: keep the text, ignore the [00:12.34] tags
                    import re
                    lyrics = re.sub(r'\[.*?\]', '', hit['syncedLyrics']).strip()
                    break

    except Exception as e:
        capture_exception(e)
        logger.error(f" LRCLIB API Error: {str(e)}") 
        return {

            'original': "Connection Error",

            'translated': "We're having trouble reaching the lyrics source. Try again in a moment!",

            'status': 'error'

            } 
        # We don't return error yet; maybe it's just a temporary blip
    
    if not lyrics:
        logger.warning(f" Lyrics not found on LRCLIB for: {track_name}")
        return {
            'original': "No Lyrics Found",
            'translated': "I searched everywhere I couldn't find these lyrics. Try a more popular track?",
            'status': 'error'
        }

    # STEP 2: Language Detection
    try:
        results = detect_langs(lyrics)
        if results[0].lang == 'en' and results[0].prob > 0.85:
            return {
                'original': lyrics,
                'translated': " This song is already in English! No translation needed.",
                'status': 'success'
            }
    except Exception as e:
        logger.warning(f" Language detection failed: {e}")

    # STEP 3: Gemini Translation
    logger.info(" Sending to Gemini...")
    api_key = settings.GEMINI_API_KEY
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    prompt = f"Translate the song '{track_name}' by '{artist_name}' to English. Lyrics: {lyrics}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload, timeout=30)
        response.raise_for_status()
        translated_text = response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"❌ Gemini Failure: {str(e)}") 
        return {
            'original': "AI Busy",
            'translated': "Our AI translator is currently over-caffeinated. Give it a minute to cool down and try again!",
            'status': 'error'
        }

    # STEP 4: Save & Return
    SavedTranslation.objects.update_or_create(
        track_name=track_name, artist_name=artist_name,
        defaults={'original_lyrics': lyrics, 'translated_lyrics': translated_text}
    )
    
    return {'original': lyrics, 'translated': translated_text, 'status': 'success'}