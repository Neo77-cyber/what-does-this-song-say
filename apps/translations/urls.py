from django.urls import path
from . import views

app_name = 'translations'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('translate/', views.translate_song, name='translate'),
]
