import requests
import logging
import re
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from ..models import SavedTranslation

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-2.5-flash",      
]         



def _get_gemini_url(model, api_key):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"


def is_429_error(exception):
    return isinstance(exception, requests.exceptions.HTTPError) and \
           exception.response.status_code == 429



def _call_gemini_api(url, payload):
    response = requests.post(
        url, 
        headers={'Content-Type': 'application/json'}, 
        json=payload, 
        timeout=60
    )
    response.raise_for_status()
    return response.json()


def process_song_translation(track_name, artist_name):
    logger.info(f"Starting translation for: {track_name} by {artist_name}")

    
    cached = SavedTranslation.objects.filter(
        track_name__iexact=track_name,
        artist_name__iexact=artist_name
    ).first()

    if cached:
        logger.info(f"Cache Hit for: {track_name}")
        return {'original': cached.original_lyrics, 'translated': cached.translated_lyrics, 'status': 'success'}

    
    lyrics = None
    try:
        lrclib_url = "https://lrclib.net/api/search"
        params = {'track_name': track_name, 'artist_name': artist_name}
        headers = {'User-Agent': 'WhatDoesTheSongSay/1.0 (Educational Project)'}
        response = requests.get(lrclib_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()

        if results:
            for hit in results:
                if hit.get('plainLyrics'):
                    lyrics = hit['plainLyrics']
                    break
                elif hit.get('syncedLyrics'):
                    lyrics = re.sub(r'\[.*?\]', '', hit['syncedLyrics']).strip()
                    break
    except Exception as e:
        logger.error(f"LRCLIB API Error: {str(e)}")
        return {
            'original': "Connection Error",
            'translated': "We're having trouble reaching the lyrics source. Try again!",
            'status': 'error'
        }

    if not lyrics:
        logger.warning(f"Lyrics not found on LRCLIB for: {track_name}")
        return {
            'original': "No Lyrics Found",
            'translated': "I couldn't find these lyrics. Try a more popular track?",
            'status': 'error'
        }

    
    logger.info("Sending to Gemini...")
    api_key = settings.GEMINI_API_KEY

    prompt = (
        f"You are a multilingual music expert. Translate the song '{track_name}' by '{artist_name}' into English.\n\n"
        f"STRICT RULES:\n"
        f"1. For FOREIGN languages (French, Spanish, Yoruba, Swahili, Benin/Edo, etc.): Provide a clear English translation.\n"
        f"2. For NIGERIAN PIDGIN: DO NOT translate it. Keep it exactly as written.\n"
        f"3. For STANDARD ENGLISH: Keep it exactly as written.\n"
        f"4. If the lyrics are already entirely English/Pidgin, return them unchanged.\n"
        f"5. Maintain the original line-by-line song structure.\n\n"
        f"Lyrics:\n{lyrics}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    translated_text = None
    last_error = None

    for model in GEMINI_MODELS:
        try:
            url = _get_gemini_url(model, api_key)
            data = _call_gemini_api(url, payload)
            translated_text = data['candidates'][0]['content']['parts'][0]['text']
            logger.info(f"Translated using {model}")
            break
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 429:
                logger.warning(f"{model} rate limited, trying next model...")
            elif status == 404:
                logger.warning(f"{model} not found (deprecated?), trying next model...")
            else:
                logger.error(f"Gemini HTTP error on {model}: {str(e)}")
            last_error = e
            continue  
        except Exception as e:
            logger.error(f"Unexpected error on {model}: {str(e)}")
            last_error = e
            continue  

    if translated_text is None:
        if isinstance(last_error, requests.exceptions.HTTPError):
            status = last_error.response.status_code
            if status == 429:
                sentry_message = "Gemini rate limit exhausted across all models (429)"
                user_message = "Our AI is currently experiencing a traffic spike. Please wait a minute and try again."
            elif status == 404:
                sentry_message = "All Gemini models returned 404 - check model names"
                user_message = "Our AI is currently experiencing a traffic spike. Please wait a minute and try again."
            elif status == 403:
                sentry_message = "Gemini API key lacks permission for all models (403)"
                user_message = "Our AI is currently experiencing a traffic spike. Please wait a minute and try again."
            else:
                sentry_message = f"Gemini HTTP error across all models: {status}"
                user_message = "Our AI is currently experiencing a traffic spike. Please wait a minute and try again."
        else:
            sentry_message = f"Gemini non-HTTP failure: {type(last_error).__name__}: {str(last_error)}"
            user_message = "Our AI is currently experiencing a traffic spike. Please wait a minute and try again."

        logger.error(f"All Gemini models failed — {sentry_message}")
        return {
            'original': lyrics,
            'translated': user_message,
            'status': 'error',
            'error_type': sentry_message,  
        }

    
    SavedTranslation.objects.update_or_create(
        track_name=track_name, artist_name=artist_name,
        defaults={'original_lyrics': lyrics, 'translated_lyrics': translated_text}
    )

    return {'original': lyrics, 'translated': translated_text, 'status': 'success'}
