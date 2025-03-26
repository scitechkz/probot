from django import forms
from .models import SOPDocument
#create a user friendly page for sop upload
class SOPUploadForm(forms.ModelForm):
    class Meta:
        model = SOPDocument
        fields = ["title", "document"]
