from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PatientProfile, MedicalNote

class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, label="Full name")
    class Meta(UserCreationForm.Meta): model = User; fields = ("username", "first_name", "email")
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError("An account with this email already exists.")
        return email

class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label="Full name")
    email = forms.EmailField()
    class Meta: model = PatientProfile; fields = ("age", "gender", "phone", "health_information")
    def __init__(self, *args, user, **kwargs):
        self.user = user; super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = user.first_name; self.fields["email"].initial = user.email
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists(): raise forms.ValidationError("That email belongs to another account.")
        return email
    def save(self, commit=True):
        profile = super().save(commit)
        self.user.first_name = self.cleaned_data["first_name"]; self.user.email = self.cleaned_data["email"]
        if commit: self.user.save()
        return profile

class MedicalNoteForm(forms.ModelForm):
    class Meta: model = MedicalNote; fields = ("title", "body")

class ChatForm(forms.Form):
    message = forms.CharField(max_length=2000, strip=True)
