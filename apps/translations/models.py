from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class SavedTranslation(models.Model):
    # Unique together means we never store "Blinding Lights - The Weeknd" twice
    track_name = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    
    original_lyrics = models.TextField()
    translated_lyrics = models.TextField()
    
    # Track when it was first translated
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['track_name', 'artist_name'], 
                name='unique_song_translation'
            )
        ]

    def __str__(self):
        return f"{self.track_name} by {self.artist_name}"


class DailyUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date') 

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.count}"