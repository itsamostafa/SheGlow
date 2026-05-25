import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, Customer, EGYPTIAN_GOVERNORATES

INPUT_CLASS = 'w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-300 text-sm'


def validate_phone(phone):
    digits = re.sub(r'\D', '', phone)
    if len(digits) != 11 or not digits.startswith('01'):
        raise ValidationError('Enter a valid Egyptian mobile number (11 digits starting with 01).')
    return digits


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'First name',
    }))
    last_name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'Last name',
    }))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={
        'class': INPUT_CLASS, 'placeholder': '01XXXXXXXXX',
        'inputmode': 'tel',
    }))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'your@email.com (optional)',
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'Password',
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'Confirm password',
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email', 'password1', 'password2']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        digits = validate_phone(phone)
        if User.objects.filter(phone=digits).exists():
            raise ValidationError('An account with this phone number already exists.')
        return digits

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip()
        if email and User.objects.filter(email=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email or None


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': INPUT_CLASS,
        'placeholder': '01XXXXXXXXX',
        'inputmode': 'tel',
        'autofocus': True,
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'Password',
    }))


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    last_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': INPUT_CLASS}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={
        'class': INPUT_CLASS, 'placeholder': 'your@email.com (optional)',
    }))

    class Meta:
        model = Customer
        fields = ['address', 'city', 'governorate']
        widgets = {
            'address': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}),
            'city': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'governorate': forms.Select(attrs={'class': INPUT_CLASS}),
        }
