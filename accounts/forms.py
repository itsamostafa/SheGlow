import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
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


class PhonePasswordResetForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        label='Phone Number',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': '01XXXXXXXXX',
            'inputmode': 'tel',
            'autofocus': True,
        }),
    )

    def clean_phone(self):
        raw = self.cleaned_data.get('phone', '').strip()
        digits = re.sub(r'\D', '', raw)
        try:
            self._user = User.objects.get(phone=digits, is_active=True)
        except User.DoesNotExist:
            raise ValidationError('No account found with this phone number.')
        if not self._user.email:
            raise ValidationError(
                'No email address is linked to this account. '
                'Please contact us on WhatsApp to reset your password.'
            )
        return digits

    def save(self, domain_override=None, subject_template_name=None,
             email_template_name=None, use_https=False,
             token_generator=default_token_generator,
             from_email=None, request=None, **kwargs):
        user = self._user
        domain = domain_override or (request.get_host() if request else 'example.com')
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        context = {
            'email': user.email,
            'domain': domain,
            'site_name': 'SheGlow',
            'uid': uid,
            'token': token,
            'protocol': 'https' if use_https else 'http',
            'user': user,
        }
        subject = render_to_string(
            subject_template_name or 'accounts/emails/password_reset_subject.txt',
            context,
        ).strip()
        body = render_to_string(
            email_template_name or 'accounts/emails/password_reset_email.txt',
            context,
        )
        send_mail(subject, body, from_email, [user.email])


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
