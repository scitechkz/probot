from django.contrib import admin

# Create admin panel for SOP
from .models import SOPDocument

admin.site.register(SOPDocument)
