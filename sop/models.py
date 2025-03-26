from django.db import models

#creates an upload SOP documents - pdf , docxs 
class SOPDocument(models.Model):
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to="sops/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    
#creates a user model
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class CustomUser(AbstractUser):
    company_name = models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name="customuser_groups")  # ✅ Fix conflicts
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions")  # ✅ Fix conflicts

    def __str__(self):
        return self.username
