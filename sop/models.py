from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractUser, Group, Permission

# ✅ Custom user model
class CustomUser(AbstractUser):
    company_name = models.CharField(max_length=255, blank=True, null=True)
    is_admin = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name="customuser_groups")  # ✅ Fix conflicts
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions")  # ✅ Fix conflicts

    def __str__(self):
        return self.username

# ✅ Upload SOP documents
class SOPDocument(models.Model):
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to="sops/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# ✅ Self-learning model for SOP interactions
class SOPInteraction(models.Model):
    user_query = models.TextField()
    sop_used = models.ForeignKey(SOPDocument, on_delete=models.SET_NULL, null=True, blank=True)
    ai_response = models.TextField()
    feedback = models.IntegerField(null=True, blank=True)  # 1-5 rating
    timestamp = models.DateTimeField(auto_now_add=True)

# ✅ Monitors reference count for SOPs
class SOP(models.Model):
    title = models.CharField(max_length=255)
    document = models.FileField(upload_to="sop_docs/")
    reference_count = models.IntegerField(default=0)  # Track SOP usage

# ✅ SOP Analytics - FIXED
class SOPAnalytics(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Use CustomUser
    query = models.TextField()
    response_time = models.FloatField(help_text="Response time in seconds")
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.user} - {self.query[:50]} - {self.response_time}s"


