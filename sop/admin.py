from django.contrib import admin

# Create admin panel for SOP
from .models import SOPDocument

admin.site.register(SOPDocument)

#keeps SOP interaction in admin.py
from .models import SOPInteraction
admin.site.register(SOPInteraction)
