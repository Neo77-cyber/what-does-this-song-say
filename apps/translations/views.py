from django.shortcuts import render, redirect
from apps.users.services.spotify_service import get_user_library
from .services.translation_service import process_song_translation
import logging
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from .models import DailyUsage, SavedTranslation
from django.utils import timezone
from django.contrib.auth.decorators import login_required


logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    
    # 1. Get the token from the session
    token_info = request.session.get('spotify_token')
    
    # 2. If no token, they shouldn't be here! Redirect to login
    if not token_info:
        return redirect('users:login')
    
    force_refresh = request.GET.get('refresh') == 'true'
        
    # 3. Use the service to get real songs
    try:
        liked_songs = get_user_library(token_info, refresh=force_refresh)
    except Exception as e:
        # If the token expired or something went wrong, clear session and login again
        print(f"Error fetching Spotify data: {e}")
        return redirect('users:login')
    
    # 4. Send the data to the template
    return render(request, 'translations/dashboard.html', {
        'liked_songs': liked_songs
    })


@login_required
@ratelimit(key='user_or_ip', rate='10/m', method='POST', block=False)
def translate_song(request):
    if request.method == "POST":
        user = request.user
        track = request.POST.get('track_name')
        artist = request.POST.get('artist_name')

        # 1. BURST LIMIT CHECK (Anti-spam)
        if getattr(request, 'limited', False):
            logger.warning(f"🚫 Burst limit hit by user: {user.username}")
            messages.warning(request, "One song at a time. Rate limit has been exceeded")
            return redirect('translations:dashboard')

        # 2. DATABASE CHECK (The "Free Pass")
        existing = SavedTranslation.objects.filter(
            track_name__iexact=track, 
            artist_name__iexact=artist
        ).first()

        if existing:
            logger.info(f"♻️ Cache Hit: {track} served from database.")
            return render(request, 'translations/result.html', {
                'track_name': existing.track_name,
                'artist_name': existing.artist_name,
                'original': existing.original_lyrics,
                'translated': existing.translated_lyrics,
            })

        # 3. DAILY QUOTA CHECK 
        usage, _ = DailyUsage.objects.get_or_create(user=user, date=timezone.now().date())
        if usage.count >= 10:
            logger.info(f"🛑 Quota reached for: {user.username}")
            # Corrected message to match the '90' limit
            messages.info(request, "You've hit your 10 daily limit! Please, come back tomorrow.")
            return redirect('translations:dashboard')

        # 4. RUN THE SERVICE (Gemini API Call)
        result = process_song_translation(track, artist)

        if result.get('status') == 'error':
            messages.warning(request, result['translated'])
            return redirect('translations:dashboard')

        usage.count += 1
        usage.save()
        
        logger.info(f"✅ New translation saved for {user.username}: {track}")
        
        result['track_name'] = track
        result['artist_name'] = artist
        return render(request, 'translations/result.html', result)

    return redirect('translations:dashboard')
