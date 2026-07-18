from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth.models import User
from app_pitutea.models import Perfil, Pituto

class RegistroUsuarioTests(TestCase):
    def test_registro_usuario_sends_email_with_correct_link(self):
        # Realizar el registro de un nuevo usuario con rol OFERENTE
        response = self.client.post(reverse('registro'), {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'password_confirm': 'testpassword123',
            'rol': 'OFERENTE',
            'acepta_terminos': True,
            'nombres': 'Juan Andres',
            'apellidos': 'Perez Gomez',
            'rut': '12345678-5',
            'telefono': '+56912345678',
            'region': 'Arica y Parinacota',
            'ciudad': 'Arica'
        })
        
        # Verificar la respuesta
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registro_pendiente.html')
        
        # Verificar que el perfil se creó con la región y ciudad correctas
        user = User.objects.get(username='testuser')
        self.assertEqual(user.perfil.region, 'Arica y Parinacota')
        self.assertEqual(user.perfil.ciudad, 'Arica')
        self.assertEqual(user.perfil.comuna, 'Arica') # Comuna sincronizada con ciudad
        
        # Verificar que el correo fue enviado
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Comprobar asunto y cuerpo del correo
        self.assertEqual(email.subject, "Verifica tu correo electrónico - Pitutea")
        self.assertIn("testuser", email.body)
        
        # El enlace de verificación debe contener el host de prueba (testserver) y no example.com
        self.assertNotIn("example.com", email.body)
        self.assertIn("http://testserver/verificar-correo/", email.body)

class LoginUsuarioTests(TestCase):
    def setUp(self):
        # Crear un usuario de prueba
        self.user = User.objects.create_user(
            username='juan_perez',
            email='juan@example.com',
            password='testpassword123'
        )
        # Crear perfil con un RUT normalizado (el guardar normaliza el RUT en el formulario o en la lógica de creación)
        self.perfil = Perfil.objects.create(
            usuario=self.user,
            rol='OFERENTE',
            rut='123456785',
            telefono='+56912345678'
        )
        
        # Crear un administrador o usuario sin Perfil para probar el fallback
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword123'
        )

    def test_login_with_rut_formatted(self):
        # Intentar iniciar sesión usando el RUT formateado (con puntos y guión)
        response = self.client.post(reverse('login'), {
            'username': '12.345.678-5',
            'password': 'testpassword123'
        })
        # Debe redirigir al flujo 2FA tras validar credenciales con éxito
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

    def test_login_with_rut_unformatted(self):
        # Intentar iniciar sesión usando el RUT sin formatear
        response = self.client.post(reverse('login'), {
            'username': '123456785',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

    def test_login_with_username_fallback(self):
        # Intentar iniciar sesión usando el nombre de usuario (como para el admin)
        response = self.client.post(reverse('login'), {
            'username': 'admin',
            'password': 'adminpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

    def test_login_invalid_credentials(self):
        # Intentar iniciar sesión con contraseña incorrecta
        response = self.client.post(reverse('login'), {
            'username': '12.345.678-5',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Usuario o contraseña incorrectos.")

class PitutoFormattingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='oferente_test',
            email='oferente@example.com',
            password='password123'
        )

    def test_pago_formateado_numeric(self):
        pituto = Pituto.objects.create(
            creador=self.user,
            titulo='Test Pituto 1',
            descripcion='Description',
            pago='15000',
            tipo_pago='Transferencia',
            flexibilidad='Finde'
        )
        self.assertEqual(pituto.pago_formateado, '$ 15.000 CLP')

    def test_pago_formateado_already_contains_symbols(self):
        pituto = Pituto.objects.create(
            creador=self.user,
            titulo='Test Pituto 2',
            descripcion='Description',
            pago='$15.000 CLP',
            tipo_pago='Transferencia',
            flexibilidad='Finde'
        )
        self.assertEqual(pituto.pago_formateado, '$ 15.000 CLP')

    def test_pago_formateado_text(self):
        pituto = Pituto.objects.create(
            creador=self.user,
            titulo='Test Pituto 3',
            descripcion='Description',
            pago='A convenir',
            tipo_pago='Transferencia',
            flexibilidad='Finde'
        )
        self.assertEqual(pituto.pago_formateado, 'A convenir')
