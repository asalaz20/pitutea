import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pitutea_core.settings')
django.setup()

from django.contrib.auth.models import User
from app_pitutea.models import Pituto, Perfil

print("Iniciando configuración de la base de datos...")
print()
print("3 perfiles del sistema: ADMINISTRADOR (solo /admin/), OFERENTE, CUIDADOR")
print("-" * 60)

# ─────────────────────────────────────────────
# 1. Administrador del Sistema (solo Django Admin)
#    NO tiene Perfil de plataforma. Solo accede a /admin/.
# ─────────────────────────────────────────────
admin_user, created = User.objects.get_or_create(username='admin', defaults={'email': 'admin@pitutea.cl'})
if created:
    admin_user.set_password('admin123')
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.is_active = True
    admin_user.save()
    print("✅ Administrador creado  | Usuario: admin       | Contraseña: admin123")
    print("   ℹ️  Acceso: http://localhost:8000/admin/  (NO tiene rol en la plataforma)")
else:
    # Asegurar que no tenga perfil
    try:
        admin_user.perfil.delete()
        print("✅ Perfil de plataforma eliminado del admin (correcto: admin solo usa /admin/)")
    except Perfil.DoesNotExist:
        print("ℹ️  Admin ya existía sin perfil de plataforma.")

# ─────────────────────────────────────────────
# 2. Oferente de prueba (publica y gestiona Pitutos)
# ─────────────────────────────────────────────
oferente_user, created = User.objects.get_or_create(
    username='oferente_test',
    defaults={
        'email': 'oferente@pitutea.cl',
        'first_name': 'Sofía',
        'last_name': 'Rodríguez',
        'is_active': True,
    }
)
if created:
    oferente_user.set_password('oferente123')
    oferente_user.save()
    print("✅ Oferente creado       | Usuario: oferente_test | Contraseña: oferente123")
else:
    print("ℹ️  Oferente ya existía.")

Perfil.objects.get_or_create(usuario=oferente_user, defaults={'rol': 'OFERENTE'})

# ─────────────────────────────────────────────
# 3. Cuidador de prueba (postula a Pitutos)
# ─────────────────────────────────────────────
cuidador_user, created = User.objects.get_or_create(
    username='cuidador_test',
    defaults={
        'email': 'cuidador@pitutea.cl',
        'first_name': 'Carlos',
        'last_name': 'González',
        'is_active': True,
    }
)
if created:
    cuidador_user.set_password('cuidador123')
    cuidador_user.save()
    print("✅ Cuidador creado       | Usuario: cuidador_test | Contraseña: cuidador123")
else:
    print("ℹ️  Cuidador ya existía.")

Perfil.objects.get_or_create(
    usuario=cuidador_user,
    defaults={'rol': 'CUIDADOR', 'habilidades': 'Cuidado de adultos mayores, cocina básica.'}
)

# ─────────────────────────────────────────────
# 4. Mock Data: Pitutos de prueba
# ─────────────────────────────────────────────
if not Pituto.objects.exists():
    Pituto.objects.create(
        creador=oferente_user,
        titulo='Ingreso de datos a Planilla',
        descripcion='Traspasar facturas a Excel. Ideal noche.',
        pago='$15.000',
        tipo_pago='Transferencia',
        flexibilidad='Remoto / Noche'
    )
    Pituto.objects.create(
        creador=oferente_user,
        titulo='Planchado de camisas',
        descripcion='Planchar 10 camisas. Retiro domicilio.',
        pago='$20.000',
        tipo_pago='Efectivo',
        flexibilidad='Horario libre'
    )
    Pituto.objects.create(
        creador=oferente_user,
        titulo='Moderación Redes Sociales',
        descripcion='Borrar spam en Instagram. Guion listo.',
        pago='$120.000',
        tipo_pago='Transferencia',
        flexibilidad='Remoto'
    )
    print("✅ Pitutos de prueba creados.")
else:
    print("ℹ️  Pitutos ya existen, no se crearon nuevos.")

print()
print("=" * 60)
print("CREDENCIALES DE ACCESO")
print("=" * 60)
print(f"  🔑 Administrador  → http://localhost:8000/admin/")
print(f"     Usuario: admin         Contraseña: admin123")
print()
print(f"  🏢 Oferente       → http://localhost:8000/login/")
print(f"     Usuario: oferente_test  Contraseña: oferente123")
print()
print(f"  👤 Cuidador       → http://localhost:8000/login/")
print(f"     Usuario: cuidador_test  Contraseña: cuidador123")
print("=" * 60)
print("¡Configuración finalizada!")
