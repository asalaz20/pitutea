from django.db import models
from django.contrib.auth.models import User

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
    comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna de residencia")
    categoria_interes = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES, blank=True, null=True, verbose_name="Categoría de mayor interés")
    habilidades = models.TextField(blank=True, null=True, verbose_name="Habilidades o experiencia")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de contacto")

    def __str__(self):
        return f"{self.usuario.username} - {self.get_rol_display()}"

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"

class Pituto(models.Model):
    TIPO_PAGO_CHOICES = [
        ('tarea', 'Por Tarea'),
        ('hora', 'Por Hora'),
        ('dia', 'Por Día'),
        ('semana', 'Por Semana'),
        ('mes', 'Por Mes'),
    ]

    creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pitutos_creados', verbose_name="Oferente creador")
    titulo = models.CharField(max_length=200, verbose_name="Título del Pituto")
    descripcion = models.TextField(verbose_name="Descripción detallada")
    
    # Nuevos campos para Matching
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES, default='otro', verbose_name="Categoría del trabajo")
    comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name="Comuna (Dejar en blanco si es Remoto)")
    
    pago = models.CharField(max_length=50, verbose_name="Monto a pagar (Ej: $15.000)")
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
