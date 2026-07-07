import random
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, authenticate
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.contrib import messages
from django.conf import settings

from .models import Pituto, Postulacion, Perfil
from .forms import RegistroForm, PerfilForm, PitutoForm

# FASE 2: MATCHING Y PERFIL

def registro_usuario(request):
    if request.user.is_authenticated:
        return redirect('listar_ofertas')
        
    if request.method == 'POST':
        form = RegistroForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Generar token de activación seguro
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            domain = get_current_site(request).domain
            verification_link = f"http://{domain}/verificar-correo/{uid}/{token}/"
            
            # Enviar correo de activación
            subject = "Verifica tu correo electrónico - Pitutea"
            message = f"Hola {user.username},\n\nPara activar tu cuenta en Pitutea y poder iniciar sesión, por favor haz clic en el siguiente enlace:\n{verification_link}\n\n¡Gracias por registrarte!"
            send_mail(
                subject,
                message,
                'no-reply@pitutea.cl',
                [user.email],
                fail_silently=False,
            )
            
            # Mostrar pantalla de verificación pendiente
            return render(request, 'registro_pendiente.html', {
                'email': user.email,
                'debug_activation_link': verification_link if settings.DEBUG else None
            })
    else:
        form = RegistroForm()
        
    return render(request, 'registro.html', {'form': form})

def verificar_correo(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "¡Tu cuenta ha sido activada con éxito! Ahora puedes iniciar sesión.")
        return redirect('login')
    else:
        return render(request, 'registro_error_verificacion.html')

def login_usuario(request):
    if request.user.is_authenticated:
        return redirect('listar_ofertas')
        
    error_message = None
    next_url = request.GET.get('next', '') or request.POST.get('next', '')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_active:
                error_message = "Esta cuenta no está activa. Por favor, verifica tu correo electrónico."
            else:
                # Generar código OTP de 6 dígitos para doble autenticación
                otp = f"{random.randint(100000, 999999)}"
                expiry = time.time() + 300 # Vence en 5 minutos
                
                # Guardar datos en sesión
                request.session['pre_2fa_user_id'] = user.id
                request.session['2fa_otp'] = otp
                request.session['2fa_expiry'] = expiry
                request.session['next_url'] = next_url
                if settings.DEBUG:
                    request.session['2fa_debug_otp'] = otp
                
                # Enviar OTP por correo
                subject = "Código de doble autenticación (2FA) - Pitutea"
                message = f"Hola {user.username},\n\nTu código de verificación de inicio de sesión de un solo uso (OTP) es:\n\n{otp}\n\nEste código vencerá en 5 minutos."
                send_mail(
                    subject,
                    message,
                    'no-reply@pitutea.cl',
                    [user.email],
                    fail_silently=False,
                )
                
                # Redirigir a verificación OTP
                return redirect('login_2fa')
        else:
            error_message = "Usuario o contraseña incorrectos."
            
    return render(request, 'login.html', {'error_message': error_message, 'next': next_url})

def login_2fa(request):
    if request.user.is_authenticated:
        return redirect('listar_ofertas')
        
    user_id = request.session.get('pre_2fa_user_id')
    otp_expected = request.session.get('2fa_otp')
    expiry = request.session.get('2fa_expiry')
    next_url = request.session.get('next_url', '')
    
    if not user_id or not otp_expected or not expiry:
        return redirect('login')
        
    error_message = None
    
    if request.method == 'POST':
        otp_entered = request.POST.get('otp', '').strip()
        
        # Verificar expiración
        if time.time() > expiry:
            error_message = "El código OTP ha expirado. Por favor, inicia sesión de nuevo."
            # Limpiar datos
            request.session.pop('pre_2fa_user_id', None)
            request.session.pop('2fa_otp', None)
            request.session.pop('2fa_expiry', None)
            request.session.pop('next_url', None)
            return render(request, 'login_2fa.html', {'error_message': error_message})
            
        if otp_entered == otp_expected:
            try:
                user = User.objects.get(pk=user_id)
                auth_login(request, user)
                
                # Limpiar datos de sesión 2FA
                request.session.pop('pre_2fa_user_id', None)
                request.session.pop('2fa_otp', None)
                request.session.pop('2fa_expiry', None)
                request.session.pop('next_url', None)
                
                if next_url:
                    return redirect(next_url)
                if user.perfil.rol == 'OFERENTE':
                    return redirect('panel_oferente')
                else:
                    return redirect('listar_ofertas')
            except User.DoesNotExist:
                return redirect('login')
        else:
            error_message = "Código OTP incorrecto. Inténtalo nuevamente."

    debug_otp = request.session.get('2fa_debug_otp') if settings.DEBUG else None
    return render(request, 'login_2fa.html', {'error_message': error_message, 'debug_otp': debug_otp})

@login_required
def editar_perfil(request):
    perfil = request.user.perfil
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            if perfil.rol == 'OFERENTE':
                return redirect('panel_oferente')
            else:
                return redirect('listar_ofertas')
    else:
        form = PerfilForm(instance=perfil)
    
    return render(request, 'editar_perfil.html', {'form': form})

def listar_ofertas(request):
    # Base QuerySet
    ofertas = Pituto.objects.filter(activo=True)
    
    # Filtros
    q = request.GET.get('q', '')
    if q:
        ofertas = ofertas.filter(Q(titulo__icontains=q) | Q(descripcion__icontains=q))
        
    tipo = request.GET.get('tipo', '')
    if tipo:
        ofertas = ofertas.filter(tipo_pago=tipo)

    categoria = request.GET.get('categoria', '')
    if categoria:
        ofertas = ofertas.filter(categoria=categoria)

    comuna = request.GET.get('comuna', '')
    if comuna:
        ofertas = ofertas.filter(comuna__icontains=comuna)

    # ALGORITMO DE MATCHING SUAVE (Para Cuidadores logueados)
    if request.user.is_authenticated and hasattr(request.user, 'perfil') and request.user.perfil.rol == 'CUIDADOR':
        perfil = request.user.perfil
        ofertas_list = list(ofertas)
        
        for oferta in ofertas_list:
            oferta.es_recomendado = False
            # Si coincide la categoria o la comuna es un match
            if perfil.categoria_interes and oferta.categoria == perfil.categoria_interes:
                oferta.es_recomendado = True
            elif perfil.comuna and oferta.comuna and perfil.comuna.lower() in oferta.comuna.lower():
                oferta.es_recomendado = True

        # Ordenar (Recomendados primero) y luego por id/fecha (python mantiene el orden estable)
        ofertas_list.sort(key=lambda x: x.es_recomendado, reverse=True)
        ofertas = ofertas_list

    context = {
        'ofertas': ofertas,
        'q': q, 'tipo': tipo, 'categoria': categoria, 'comuna': comuna,
    }

    if request.headers.get('HX-Request') == 'true':
        return render(request, 'parcial_grilla_ofertas.html', context)

    return render(request, 'ofertas.html', context)

@login_required
def postular_pituto(request, oferta_id):
    if request.method == 'POST':
        if request.user.perfil.rol != 'CUIDADOR':
            return HttpResponse('<div class="alert alert-danger w-100 p-2 text-center mb-0">Solo Cuidadores</div>')

        pituto = get_object_or_404(Pituto, id=oferta_id)
        
        if Postulacion.objects.filter(pituto=pituto, usuario=request.user).exists():
             return HttpResponse('<button class="btn btn-secondary w-100 fw-bold py-2 rounded-3 disabled" disabled>Ya postulaste</button>')

        Postulacion.objects.create(pituto=pituto, usuario=request.user)
        return render(request, 'boton_postulado.html')
    
    return HttpResponse("Método no permitido", status=405)


# FASE 3: PANEL OFERENTE
@login_required
def panel_oferente(request):
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')
        
    pitutos = Pituto.objects.filter(creador=request.user).order_by('-fecha_creacion')
    return render(request, 'panel_oferente.html', {'pitutos': pitutos})

@login_required
def crear_pituto(request):
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')

    if request.method == 'POST':
        form = PitutoForm(request.POST)
        if form.is_valid():
            pituto = form.save(commit=False)
            pituto.creador = request.user
            pituto.save()
            return redirect('panel_oferente')
    else:
        form = PitutoForm()
        
    return render(request, 'crear_pituto.html', {'form': form})

@login_required
def ver_postulantes(request, pituto_id):
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')
        
    pituto = get_object_or_404(Pituto, id=pituto_id, creador=request.user)
    postulaciones = pituto.postulaciones.all().order_by('-fecha_postulacion')
    return render(request, 'ver_postulantes.html', {'pituto': pituto, 'postulaciones': postulaciones})
