from django.contrib import admin
from .models import Pituto, Postulacion, Perfil

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'habilidades')
    list_filter = ('rol',)

@admin.register(Pituto)
class PitutoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'creador', 'pago', 'tipo_pago', 'flexibilidad', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'tipo_pago')
    search_fields = ('titulo', 'descripcion')

@admin.register(Postulacion)
class PostulacionAdmin(admin.ModelAdmin):
    list_display = ('pituto', 'usuario', 'fecha_postulacion')
    list_filter = ('fecha_postulacion',)
