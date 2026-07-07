from django import forms
from django.contrib.auth.models import User
from .models import Perfil, Pituto

def normalizar_rut(rut_str):
    if not rut_str:
        return ""
    return rut_str.replace(".", "").replace("-", "").strip().upper()

class RegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control rounded-3', 'placeholder': '••••••••'}), label='Contraseña')
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control rounded-3', 'placeholder': '••••••••'}), label='Confirmar Contraseña')
    rol = forms.ChoiceField(choices=Perfil.ROL_CHOICES, widget=forms.Select(attrs={'class': 'form-select rounded-3 py-2'}), label='¿Qué vienes a hacer?')
    
    # Campos adicionales para cuidadores
    nombres = forms.CharField(max_length=150, required=False, label='Nombres', widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: Juan Andrés'}))
    apellidos = forms.CharField(max_length=150, required=False, label='Apellidos', widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: Pérez Gómez'}))
    rut = forms.CharField(max_length=20, required=False, label='RUT', widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: 12.345.678-9'}))
    telefono = forms.CharField(max_length=20, required=False, label='Teléfono Celular', widget=forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: +56 9 1234 5678'}))
    habilidades = forms.CharField(required=False, label='Habilidades o Competencias', widget=forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Cuéntanos qué sabes hacer, qué herramientas manejas...'}))
    carnet_cuidador = forms.FileField(required=False, label='Carnet de Cuidador', widget=forms.ClearableFileInput(attrs={'class': 'form-control rounded-3'}))

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
            self.add_error("password_confirm", "Las contraseñas no coinciden.")

        rol = cleaned_data.get("rol")
        if rol == 'CUIDADOR':
            nombres = cleaned_data.get("nombres")
            apellidos = cleaned_data.get("apellidos")
            rut = cleaned_data.get("rut")
            telefono = cleaned_data.get("telefono")
            habilidades = cleaned_data.get("habilidades")
            carnet_cuidador = cleaned_data.get("carnet_cuidador")

            if not nombres:
                self.add_error("nombres", "Los nombres son requeridos para cuidadores.")
            if not apellidos:
                self.add_error("apellidos", "Los apellidos son requeridos para cuidadores.")
            if not rut:
                self.add_error("rut", "El RUT es requerido para cuidadores.")
            elif rut:
                if not self.validar_rut(rut):
                    self.add_error("rut", "El RUT ingresado no es válido.")
                else:
                    # Validar RUT único para cuidadores
                    rut_norm = normalizar_rut(rut)
                    if Perfil.objects.filter(rut=rut_norm, rol='CUIDADOR').exists():
                        self.add_error("rut", "Este RUT ya está registrado por otro cuidador.")
            if not telefono:
                self.add_error("telefono", "El teléfono celular es requerido para cuidadores.")
            if not habilidades:
                self.add_error("habilidades", "Las habilidades o competencias son requeridas para cuidadores.")
            if not carnet_cuidador:
                self.add_error("carnet_cuidador", "El carnet de cuidador es requerido para registrarse como cuidador.")

        return cleaned_data

    def validar_rut(self, rut_str):
        rut_str = normalizar_rut(rut_str)
        if not rut_str or len(rut_str) < 2:
            return False
        cuerpo = rut_str[:-1]
        dv = rut_str[-1]
        if not cuerpo.isdigit():
            return False
        
        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = 2 if multiplo == 7 else multiplo + 1
        
        dvr = 11 - (suma % 11)
        if dvr == 11:
            dvr_str = '0'
        elif dvr == 10:
            dvr_str = 'K'
        else:
            dvr_str = str(dvr)
            
        return dv == dvr_str

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_active = False
        
        rol = self.cleaned_data['rol']
        if rol == 'CUIDADOR':
            user.first_name = self.cleaned_data.get('nombres', '')
            user.last_name = self.cleaned_data.get('apellidos', '')
            
        if commit:
            user.save()
            perfil = Perfil.objects.create(
                usuario=user,
                rol=rol
            )
            if rol == 'CUIDADOR':
                perfil.rut = normalizar_rut(self.cleaned_data.get('rut'))
                perfil.telefono = self.cleaned_data.get('telefono')
                perfil.habilidades = self.cleaned_data.get('habilidades')
                perfil.carnet_cuidador = self.cleaned_data.get('carnet_cuidador')
                perfil.save()
        return user

class PerfilForm(forms.ModelForm):
    nombres = forms.CharField(max_length=150, required=False, label='Nombres', widget=forms.TextInput(attrs={'class': 'form-control rounded-3'}))
    apellidos = forms.CharField(max_length=150, required=False, label='Apellidos', widget=forms.TextInput(attrs={'class': 'form-control rounded-3'}))

    class Meta:
        model = Perfil
        fields = ['rut', 'carnet_cuidador', 'telefono', 'comuna', 'categoria_interes', 'habilidades']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: 12.345.678-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': '+56 9 1234 5678'}),
            'comuna': forms.TextInput(attrs={'class': 'form-control rounded-3', 'placeholder': 'Ej: Providencia (Déjalo en blanco si prefieres remoto)'}),
            'categoria_interes': forms.Select(attrs={'class': 'form-select rounded-3'}),
            'habilidades': forms.Textarea(attrs={'class': 'form-control rounded-3', 'rows': 3, 'placeholder': 'Cuéntanos qué sabes hacer, qué herramientas manejas...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.rol == 'OFERENTE':
            self.fields.pop('nombres', None)
            self.fields.pop('apellidos', None)
            self.fields.pop('rut', None)
            self.fields.pop('carnet_cuidador', None)
        else:
            if self.instance and self.instance.usuario:
                self.initial['nombres'] = self.instance.usuario.first_name
                self.initial['apellidos'] = self.instance.usuario.last_name
                self.initial['rut'] = self.instance.rut_formateado
                
            if 'nombres' in self.fields:
                self.fields['nombres'].required = True
            if 'apellidos' in self.fields:
                self.fields['apellidos'].required = True
            if 'rut' in self.fields:
                self.fields['rut'].required = True

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if self.instance and self.instance.rol == 'CUIDADOR':
            if not rut:
                raise forms.ValidationError("El RUT es requerido para cuidadores.")
            if not self.validar_rut_check(rut):
                raise forms.ValidationError("El RUT ingresado no es válido.")
            
            # Validar RUT único para cuidadores
            rut_norm = normalizar_rut(rut)
            if Perfil.objects.filter(rut=rut_norm, rol='CUIDADOR').exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Este RUT ya está registrado por otro cuidador.")
            return rut_norm
        return rut

    def validar_rut_check(self, rut_str):
        rut_str = normalizar_rut(rut_str)
        if not rut_str or len(rut_str) < 2:
            return False
        cuerpo = rut_str[:-1]
        dv = rut_str[-1]
        if not cuerpo.isdigit():
            return False
        suma = 0
        multiplo = 2
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = 2 if multiplo == 7 else multiplo + 1
        dvr = 11 - (suma % 11)
        if dvr == 11:
            dvr_str = '0'
        elif dvr == 10:
            dvr_str = 'K'
        else:
            dvr_str = str(dvr)
        return dv == dvr_str

    def save(self, commit=True):
        perfil = super().save(commit=False)
        if perfil.rol == 'CUIDADOR':
            perfil.usuario.first_name = self.cleaned_data.get('nombres', '')
            perfil.usuario.last_name = self.cleaned_data.get('apellidos', '')
            perfil.usuario.save()
        if commit:
            perfil.save()
        return perfil

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
