import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pitutea_core.settings')
django.setup()

from django.contrib.auth.models import User
from app_pitutea.models import Pituto, Perfil

print("Iniciando configuración de la base de datos...")

# 1. Crear Superusuario (Oferente por defecto)
admin_user, created = User.objects.get_or_create(username='admin', defaults={'email':'admin@pitutea.cl'})
if created:
    admin_user.set_password('admin123')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()
    Perfil.objects.get_or_create(usuario=admin_user, defaults={'rol':'OFERENTE'})
    print("- Superusuario (Oferente) creado (Usuario: admin / Contraseña: admin123)")

# 2. Crear Cuidador de prueba
cuidador_user, created = User.objects.get_or_create(username='cuidador_test', defaults={'email':'cuidador@pitutea.cl'})
if created:
    cuidador_user.set_password('cuidador123')
    cuidador_user.save()
    Perfil.objects.get_or_create(usuario=cuidador_user, defaults={'rol':'CUIDADOR', 'habilidades':'Tipeo rápido.'})
    print("- Usuario Cuidador de prueba creado (Usuario: cuidador_test / Contraseña: cuidador123)")

# 3. Cargar Mock Data
if not Pituto.objects.exists():
    Pituto.objects.create(
        creador=admin_user,
        titulo='Ingreso de datos a Planilla',
        descripcion='Traspasar facturas a Excel. Ideal noche.',
        pago='$15.000',
        tipo_pago='tarea',
        flexibilidad='Remoto / Noche'
    )
    Pituto.objects.create(
        creador=admin_user,
        titulo='Planchado de camisas',
        descripcion='Planchar 10 camisas. Retiro domicilio.',
        pago='$20.000',
        tipo_pago='semana',
        flexibilidad='Horario libre'
    )
    Pituto.objects.create(
        creador=admin_user,
        titulo='Moderación Redes Sociales',
        descripcion='Borrar spam en Instagram. Guion listo.',
        pago='$120.000',
        tipo_pago='mes',
        flexibilidad='Remoto'
    )
    print("- Pitutos de prueba creados exitosamente.")

print("¡Configuración finalizada!")
