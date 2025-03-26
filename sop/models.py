from django.db import models

#creates an upload SOP documents - pdf , docxs 
class SOPDocument(models.Model):
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to="sops/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    
