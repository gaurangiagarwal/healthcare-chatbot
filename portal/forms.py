from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PatientProfile, MedicalNote, EmergencyContact, HospitalEnquiry, Referral, Hospital, HospitalService

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

class EmergencyContactForm(forms.ModelForm):
    class Meta: model = EmergencyContact; fields = ("name", "phone", "relationship")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

class HospitalEnquiryForm(forms.ModelForm):
    class Meta:
        model = HospitalEnquiry
        fields = ("hospital", "message")
        labels = {"hospital": "Facility", "message": "Your enquiry"}
        help_texts = {
            "message": "Keep this general and concise. Do not include emergency requests or unnecessary sensitive details. This is saved locally and is not sent to the facility.",
        }
        widgets = {"message": forms.Textarea(attrs={"rows": 4, "maxlength": 1000})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hospital"].queryset = Hospital.objects.order_by("city", "name")
        self.fields["hospital"].widget.attrs.setdefault("class", "form-select")
        self.fields["message"].widget.attrs.setdefault("class", "form-control")

class ReferralForm(forms.ModelForm):
    class Meta:
        model = Referral
        fields = ("hospital", "summary")
        labels = {"hospital": "Requested facility", "summary": "Reason for referral"}
        help_texts = {
            "summary": "Briefly explain the care you are requesting. Share only information needed to understand the request; up to 1,000 characters.",
        }
        widgets = {"summary": forms.Textarea(attrs={"rows": 4, "maxlength": 1000})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["hospital"].queryset = Hospital.objects.order_by("city", "name")
        self.fields["hospital"].widget.attrs.setdefault("class", "form-select")
        self.fields["summary"].widget.attrs.setdefault("class", "form-control")

class HospitalProfileForm(forms.ModelForm):
    class Meta: model = Hospital; fields = ("name", "city", "address", "latitude", "longitude", "phone", "website")

    def clean_latitude(self):
        value = self.cleaned_data.get("latitude")
        if value is not None and not -90 <= value <= 90:
            raise forms.ValidationError("Latitude must be between -90 and 90 degrees.")
        return value

    def clean_longitude(self):
        value = self.cleaned_data.get("longitude")
        if value is not None and not -180 <= value <= 180:
            raise forms.ValidationError("Longitude must be between -180 and 180 degrees.")
        return value

class HospitalServiceForm(forms.ModelForm):
    class Meta: model = HospitalService; fields = ("service_type", "specialty_name", "status", "details", "source", "expires_at")
