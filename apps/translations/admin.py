from django.contrib import admin
from .models import SavedTranslation, DailyUsage

# Register your models here.
admin.site.register(SavedTranslation)
admin.site.register(DailyUsage)
