from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        label=_('Email'),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_("Этот email уже используется."))
        return email


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    username = forms.CharField(
        label=_('Username'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise ValidationError(_("Этот email уже используется."))
        return email


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control-file'})
        }
        labels = {
            'image': _('Изображение профиля')
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 2 * 1024 * 1024:  # 2MB limit
                raise ValidationError(_("Размер изображения не должен превышать 2MB."))
        return image