from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.contrib.auth.models import User
from app_pitutea.models import Perfil, Pituto, Postulacion

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
            'password': 'testpassword123',
            'rol': 'OFERENTE'
        })
        # Debe redirigir al flujo 2FA tras validar credenciales con éxito
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

    def test_login_with_rut_unformatted(self):
        # Intentar iniciar sesión usando el RUT sin formatear
        response = self.client.post(reverse('login'), {
            'username': '123456785',
            'password': 'testpassword123',
            'rol': 'OFERENTE'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

    def test_login_with_username_fallback(self):
        # Intentar iniciar sesión usando el nombre de usuario (como para el admin)
        response = self.client.post(reverse('login'), {
            'username': 'admin',
            'password': 'adminpassword123',
            'rol': 'OFERENTE'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

    def test_login_invalid_credentials(self):
        # Intentar iniciar sesión con contraseña incorrecta
        response = self.client.post(reverse('login'), {
            'username': '12.345.678-5',
            'password': 'wrongpassword',
            'rol': 'OFERENTE'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], "Usuario o contraseña incorrectos.")

    def test_login_multiple_profiles_same_rut(self):
        # Crear un segundo usuario (cuidador) con el mismo RUT
        cuidador_user = User.objects.create_user(
            username='maria_perez',
            email='maria@example.com',
            password='cuidadorpassword123'
        )
        Perfil.objects.create(
            usuario=cuidador_user,
            rol='CUIDADOR',
            rut='123456785',
            telefono='+56998765432'
        )

        # 1. Iniciar sesión como CUIDADOR: debe ingresar con la cuenta de maria_perez
        response = self.client.post(reverse('login'), {
            'username': '12.345.678-5',
            'password': 'cuidadorpassword123',
            'rol': 'CUIDADOR'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

        # 2. Iniciar sesión como OFERENTE: debe ingresar con la cuenta de juan_perez
        response = self.client.post(reverse('login'), {
            'username': '12.345.678-5',
            'password': 'testpassword123',
            'rol': 'OFERENTE'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login_2fa')))

        # 3. Intentar ingresar con rol OFERENTE usando la contraseña de CUIDADOR: debe fallar (credenciales incorrectas)
        response = self.client.post(reverse('login'), {
            'username': '12.345.678-5',
            'password': 'cuidadorpassword123',
            'rol': 'OFERENTE'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['error_message'], "Usuario o contraseña incorrectos.")

        # 4. Intentar ingresar con contraseña correcta pero rol incorrecto (ej: loguear a maria_perez como OFERENTE)
        # Esto debería fallar porque maria_perez tiene rol CUIDADOR, no OFERENTE.
        # Al buscar por rut y rol=OFERENTE, obtendrá el usuario de juan_perez, pero la contraseña no coincidirá con la de juan_perez
        # de modo que authenticate fallará.
        # Y si se usa username directamente:
        response = self.client.post(reverse('login'), {
            'username': 'maria_perez',
            'password': 'cuidadorpassword123',
            'rol': 'OFERENTE'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['error_message'], "Esta cuenta no está registrada como oferente.")

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

class VerPostulantesPrivacyTests(TestCase):
    def setUp(self):
        # Crear oferente
        self.oferente_user = User.objects.create_user(
            username='oferente1',
            email='oferente1@example.com',
            password='password123',
            first_name='Juan',
            last_name='Perez'
        )
        self.oferente_perfil = Perfil.objects.create(
            usuario=self.oferente_user,
            rol='OFERENTE',
            rut='11111111-1'
        )
        
        # Crear cuidador/postulante
        self.cuidador_user = User.objects.create_user(
            username='cuidador1',
            email='cuidador1@example.com',
            password='password123',
            first_name='Gisela',
            last_name='Moreno'
        )
        self.cuidador_perfil = Perfil.objects.create(
            usuario=self.cuidador_user,
            rol='CUIDADOR',
            rut='18674168-4',
            telefono='941145250',
            comuna='Santiago',
            habilidades='Planchar'
        )
        
        # Crear pituto
        self.pituto = Pituto.objects.create(
            creador=self.oferente_user,
            titulo='Aseo hogar',
            descripcion='Description',
            pago='15000',
            tipo_pago='Transferencia',
            flexibilidad='Finde',
            estado='ACTIVO'
        )
        
        # Crear postulacion
        self.postulacion = Postulacion.objects.create(
            pituto=self.pituto,
            usuario=self.cuidador_user
        )

    def test_ver_postulantes_hides_sensitive_information(self):
        # Loguear como oferente
        self.client.login(username='oferente1', password='password123')
        
        response = self.client.get(reverse('ver_postulantes', kwargs={'pituto_id': self.pituto.id}))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Debe mostrar los campos autorizados
        self.assertIn('cuidador1', html) # Username
        self.assertIn('941145250', html) # Teléfono
        self.assertIn('Planchar', html) # Habilidades
        
        # No debe mostrar la información sensible
        self.assertNotIn('Gisela', html) # Nombre de pila
        self.assertNotIn('Moreno', html) # Apellido
        self.assertNotIn('cuidador1@example.com', html) # Correo
        self.assertNotIn('18674168-4', html) # RUT
        self.assertNotIn('Ver Documento', html) # Enlace a carnet


class ReportesFormAndMailTests(TestCase):
    def setUp(self):
        # Crear cuidador
        self.cuidador_user = User.objects.create_user(
            username='cuidador_reporter',
            email='cuidador_reporter@example.com',
            password='password123',
            first_name='Maria',
            last_name='Gonzalez'
        )
        self.cuidador_perfil = Perfil.objects.create(
            usuario=self.cuidador_user,
            rol='CUIDADOR',
            rut='12345678-5',
            telefono='999999999'
        )
        
        # Crear oferente y pituto
        self.oferente_user = User.objects.create_user(
            username='oferente_reported',
            email='oferente_reported@example.com',
            password='password123'
        )
        self.oferente_perfil = Perfil.objects.create(
            usuario=self.oferente_user,
            rol='OFERENTE',
            rut='22222222-2'
        )
        self.pituto = Pituto.objects.create(
            creador=self.oferente_user,
            titulo='Pituto Irregular',
            descripcion='Description',
            pago='20000',
            tipo_pago='Transferencia',
            flexibilidad='Finde',
            estado='ACTIVO'
        )

    def test_reportar_pituto_sends_email_to_admin(self):
        # Loguear cuidador
        self.client.login(username='cuidador_reporter', password='password123')
        
        # Enviar reporte
        response = self.client.post(reverse('reportar'), {
            'pituto_id': self.pituto.id,
            'motivo': 'CONTACTO',
            'detalles': 'El oferente nunca me contactó después de postular.'
        })
        
        # Debe redirigir a bitacora
        self.assertRedirects(response, reverse('bitacora_cuidador'))
        
        # Verificar que el correo fue enviado
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Verificar destinatario
        self.assertEqual(email.to, ['contactopitutea@gmail.com'])
        
        # Verificar asunto y cuerpo
        self.assertIn("[REPORTE PITUTEA]", email.subject)
        self.assertIn("El oferente nunca me contactó", email.subject)
        self.assertIn("cuidador_reporter", email.body)
        self.assertIn("Pituto Irregular", email.body)
        self.assertIn("El oferente nunca me contactó después de postular.", email.body)

class VisitaCounterTests(TestCase):
    def setUp(self):
        import os
        from django.conf import settings
        self.file_path = os.path.join(settings.BASE_DIR, 'visitas.txt')
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass

    def tearDown(self):
        import os
        if os.path.exists(self.file_path):
            try:
                os.remove(self.file_path)
            except Exception:
                pass

    def test_incrementar_visitas_api(self):
        response = self.client.get(reverse('incrementar_visitas'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['visitas'], 1)

        response = self.client.get(reverse('incrementar_visitas'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['visitas'], 1)

        self.client.cookies.clear()
        response = self.client.get(reverse('incrementar_visitas'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['visitas'], 2)

    def test_obtener_regiones_comunas_api(self):
        response = self.client.get(reverse('obtener_regiones_comunas'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertGreater(len(data), 0)
        first_region = data[0]
        self.assertIn('nombre', first_region)
        self.assertIn('provincias', first_region)
