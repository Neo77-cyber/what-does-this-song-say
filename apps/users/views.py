
from django.shortcuts import render, redirect
from .services.spotify_service import get_spotify_oauth
from django.contrib.auth import login
from django.contrib.auth.models import User
import spotipy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Waitlist

from maintenance_mode.decorators import force_maintenance_mode_off

from django.http import JsonResponse


def home_view(request):

    if request.user.is_authenticated:
      
        return redirect('translations:dashboard')

    return render(request, 'users/home.html')

def login_view(request):
    """Redirects the user to the Spotify Authorization page."""
    auth_manager = get_spotify_oauth(request)
    auth_url = auth_manager.get_authorize_url()
    return redirect(auth_url)


def callback_view(request):
    auth_manager = get_spotify_oauth(request)
    code = request.GET.get('code')
    
    if code:
        token_info = auth_manager.get_access_token(code)
        request.session['spotify_token'] = token_info
        
        
      
        
        sp = spotipy.Spotify(auth=token_info['access_token'])
        spotify_user = sp.current_user()
        
        
        user, created = User.objects.get_or_create(
            username=f"spotify_{spotify_user['id']}",
            defaults={'email': spotify_user.get('email', '')}
        )
        
        
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
       
        
        return redirect('translations:dashboard')
    
    return redirect('users:login')

from django.contrib.auth import logout as django_logout

def logout_view(request):
    django_logout(request)
    
    request.session.flush() 
    return redirect('users:home')



@csrf_exempt
@require_http_methods(["POST"])
@force_maintenance_mode_off 
def waitlist_signup(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email is required'}, status=400)
        
        obj, created = Waitlist.objects.get_or_create(email=email)
        
        if created:
            return JsonResponse({'status': 'success', 'message': 'Added to waitlist'})
        else:
            return JsonResponse({'status': 'success', 'message': 'Already on waitlist'})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



