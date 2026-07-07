from django import forms
from django.contrib.auth.models import User
from .models import Perfil, Pituto

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control rounded-3', 'placeholder': '••••••••'}), label='Contraseña')
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control rounded-3', 'placeholder': '••••••••'}), label='Confirmar Contraseña')
    rol = forms.ChoiceField(choices=Perfil.ROL_CHOICES, widget=forms.Select(attrs={'class': 'form-select rounded-3 py-2'}), label='¿Qué vienes a hacer?')

    class Meta:
        model = User
        fields = ['username', 'email']
        labels = {
            'username': 'Nombre de Usuario',
            'email': 'Correo Electrónico',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: juan_perez'}),
            'email': forms.EmailInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'juan@email.com'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            Perfil.objects.create(
                usuario=user,
                rol=self.cleaned_data['rol']
            )
        return user

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['telefono', 'comuna', 'categoria_interes', 'habilidades']
        widgets = {
            'telefono': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': '+56 9 1234 5678'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: Providencia (Déjalo en blanco si prefieres remoto)'}),
            'categoria_interes': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'habilidades': forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Cuéntanos qué sabes hacer, qué herramientas manejas...'}),
        }

class PitutoForm(forms.ModelForm):
    class Meta:
        model = Pituto
        fields = ['titulo', 'descripcion', 'categoria', 'comuna', 'pago', 'tipo_pago', 'flexibilidad']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: Ingreso de datos a Excel'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3}),
            'categoria': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Opcional. Ej: Santiago Centro'}),
            'pago': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: $15.000'}),
            'tipo_pago': forms.Select(attrs={'class': 'form-select rounded-3','placeholder': 'Seleccione ...'}),
            'flexibilidad': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: Noche / Fines de semana'}),
        }
