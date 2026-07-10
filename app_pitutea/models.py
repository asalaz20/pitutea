from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image
import os
from io import BytesIO

def validar_tamano_imagen(file):
    max_size_mb = 5
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"La imagen no debe superar los {max_size_mb}MB.")

# Categorías predefinidas comunes para facilitar el filtrado y matching
CATEGORIAS_CHOICES = [
    ('admin', 'Administrativo / Oficina'),
    ('hogar', 'Hogar / Limpieza'),
    ('cuidado', 'Cuidado de Personas'),
    ('digital', 'Digital / Redes Sociales'),
    ('logistica', 'Logística / Reparto'),
    ('otro', 'Otro'),
]

class Perfil(models.Model):
    ROL_CHOICES = [
        ('OFERENTE', 'Oferente (Publica trabajos)'),
        ('CUIDADOR', 'Cuidador (Busca trabajos)'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    
    # Nuevos campos para Perfil Avanzado y Matching
    rut = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUT")
    direccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Dirección")
    carnet_cuidador = models.ImageField(upload_to='carnets/', blank=True, null=True, verbose_name="Carnet de Cuidador", validators=[validar_tamano_imagen])
    comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna de residencia")
    categoria_interes = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES, blank=True, null=True, verbose_name="Categoría de mayor interés")
    habilidades = models.TextField(blank=True, null=True, verbose_name="Habilidades o experiencia")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de contacto")

    @property
    def rut_formateado(self):
        if not self.rut:
            return ""
        cleaned = self.rut.replace(".", "").replace("-", "").strip().upper()
        if len(cleaned) <= 1:
            return cleaned
        cuerpo = cleaned[:-1]
        dv = cleaned[-1]
        cuerpo_formateado = ""
        while len(cuerpo) > 3:
            cuerpo_formateado = "." + cuerpo[-3:] + cuerpo_formateado
            cuerpo = cuerpo[:-3]
        cuerpo_formateado = cuerpo + cuerpo_formateado
        return f"{cuerpo_formateado}-{dv}"

    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()}"
        
    def save(self, *args, **kwargs):
        # Optimizar imagen del carnet al guardar
        if self.carnet_cuidador and not getattr(self, '_carnet_optimizado', False):
            try:
                # Abrir imagen con Pillow
                img = Image.open(self.carnet_cuidador)
                
                # Convertir a RGB si es necesario
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    
                # Redimensionar la imagen para no ocupar espacio innecesario
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                
                # Guardar en memoria optimizada (WEBP)
                output = BytesIO()
                img.save(output, format='WEBP', quality=85)
                output.seek(0)
                
                # Generar nuevo nombre y asignar el contenido optimizado
                filename = os.path.splitext(os.path.basename(self.carnet_cuidador.name))[0] + '.webp'
                self.carnet_cuidador = ContentFile(output.read(), name=filename)
                
                # Marcar para evitar bucles si se vuelve a llamar save en el ciclo de vida del objeto
                self._carnet_optimizado = True
            except Exception:
                pass # Si hay cualquier problema con la imagen (por ej., no era imagen o estaba corrupta), se guarda original
                
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

class Pituto(models.Model):
    TIPO_PAGO_CHOICES = [

        ('Transferencia', 'Transferencia'),
        ('Efectivo', 'Efectivo'),
    ]

    creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pitutos_creados', verbose_name="Oferente creador")
    titulo = models.CharField(max_length=200, verbose_name="Título del Pituto")
    descripcion = models.TextField(verbose_name="Descripción detallada")
    
    # Nuevos campos para Matching
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES, default='otro', verbose_name="Categoría del trabajo")
    comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna (Dejar en blanco si es Remoto)")
    
    pago = models.CharField(max_length=50, verbose_name="Monto a pagar (Ej: $15.000)")
    pago_anterior = models.CharField(max_length=50, blank=True, null=True, verbose_name="Monto anterior (tachado)")
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO_CHOICES, default='tarea', verbose_name="Modalidad de pago")
    flexibilidad = models.CharField(max_length=100, verbose_name="Etiqueta de Flexibilidad (Ej: Remoto / Noche)")
    activo = models.BooleanField(default=True, verbose_name="¿Está activo?")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} - {self.pago}"

    class Meta:
        verbose_name = "Pituto"
        verbose_name_plural = "Pitutos"
        ordering = ['-fecha_creacion']

class Postulacion(models.Model):
    pituto = models.ForeignKey(Pituto, on_delete=models.CASCADE, related_name='postulaciones', verbose_name="Pituto")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='postulaciones', verbose_name="Cuidador postulante")
    fecha_postulacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Postulación")

    def __str__(self):
        return f"{self.usuario.username} -> {self.pituto.titulo}"

    class Meta:
        verbose_name = "Postulación"
        verbose_name_plural = "Postulaciones"
