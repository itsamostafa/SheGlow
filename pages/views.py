from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactMessage


def privacy_policy(request):
    return render(request, 'pages/privacy_policy.html')


def refund_policy(request):
    return render(request, 'pages/refund_policy.html')


def terms(request):
    return render(request, 'pages/terms.html')


def shipping_policy(request):
    return render(request, 'pages/shipping_policy.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()
        errors = {}
        if not name:
            errors['name'] = 'Please enter your name.'
        if not email:
            errors['email'] = 'Please enter your email.'
        if not subject:
            errors['subject'] = 'Please enter a subject.'
        if not message_text:
            errors['message'] = 'Please enter your message.'
        if errors:
            return render(request, 'pages/contact.html', {
                'errors': errors,
                'post': request.POST,
            })
        ContactMessage.objects.create(name=name, email=email, subject=subject, message=message_text)
        messages.success(request, "Thanks for reaching out! We'll get back to you within 24 hours.")
        return redirect('pages:contact')
    return render(request, 'pages/contact.html', {'errors': {}, 'post': {}})
