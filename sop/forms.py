from django import forms
from .models import SOPDocument
#create a user friendly page for sop upload
class SOPUploadForm(forms.ModelForm):
    class Meta:
        model = SOPDocument
        fields = ["title", "document"]

#ensures sign up and login form exist

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class SignupForm(UserCreationForm):
    company_name = forms.CharField(max_length=255, required=True)

    class Meta:
        model = CustomUser
        fields = ["username", "email", "company_name", "password1", "password2"]

class LoginForm(AuthenticationForm):
    pass
