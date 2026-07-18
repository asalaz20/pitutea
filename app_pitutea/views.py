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
from django.urls import reverse
from django.conf import settings

from .models import Pituto, Postulacion, Perfil
from .forms import RegistroForm, PerfilForm, PitutoForm, ReporteForm, normalizar_rut

# FASE 2: MATCHING Y PERFIL

# Páginas Legales y Estáticas
def terminos_condiciones(request):
    return render(request, 'terminos_condiciones.html')

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
            verification_link = request.build_absolute_uri(
                reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token})
            )
            
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
        
        rol_seleccionado = request.POST.get('rol', 'CUIDADOR')
        
        # Intentar buscar el nombre de usuario asociado al RUT ingresado y rol seleccionado
        username_to_auth = username
        rut_norm = normalizar_rut(username)
        if rut_norm:
            try:
                perfil = Perfil.objects.get(rut=rut_norm, rol=rol_seleccionado)
                username_to_auth = perfil.usuario.username
            except (Perfil.DoesNotExist, Perfil.MultipleObjectsReturned):
                pass
                
        user = authenticate(request, username=username_to_auth, password=password)
        if user is not None:
            # Validar que el rol del perfil coincida con el seleccionado
            if hasattr(user, 'perfil') and user.perfil.rol != rol_seleccionado and not user.is_staff:
                error_message = f"Esta cuenta no está registrada como {rol_seleccionado.lower()}."
            elif hasattr(user, 'perfil') and user.perfil.estado_verificacion == 'BLOQUEADO':
                error_message = "Esta cuenta ha sido bloqueada por mal uso de la plataforma y se le ha denegado el acceso."
            elif not user.is_active:
                error_message = "Esta cuenta no está activa. Por favor, verifica tu correo electrónico."
            else:
                auth_login(request, user)
                if next_url:
                    return redirect(next_url)
                if hasattr(user, 'perfil') and user.perfil.rol == 'OFERENTE':
                    return redirect('panel_oferente')
                else:
                    return redirect('listar_ofertas')
        else:
            error_message = "Usuario o contraseña incorrectos."
            
    return render(request, 'login.html', {'error_message': error_message, 'next': next_url})

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
    # Base QuerySet: solo pitutos activos en estado ACTIVO
    ofertas = Pituto.objects.filter(activo=True, estado='ACTIVO')
    
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

@login_required
def bitacora_cuidador(request):
    if request.user.perfil.rol != 'CUIDADOR':
        return redirect('listar_ofertas')

    postulaciones = Postulacion.objects.filter(usuario=request.user).select_related('pituto').order_by('-fecha_postulacion')
    # Pitutos donde el cuidador fue seleccionado (para mostrar calificación pendiente)
    pitutos_asignados = Pituto.objects.filter(
        cuidador_seleccionado=request.user
    ).select_related('creador').order_by('-fecha_finalizacion')

    return render(request, 'bitacora_cuidador.html', {
        'postulaciones': postulaciones,
        'pitutos_asignados': pitutos_asignados,
    })



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

@login_required
def editar_pituto(request, pituto_id):
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')
        
    pituto = get_object_or_404(Pituto, id=pituto_id, creador=request.user)
    
    if pituto.postulaciones.exists():
        messages.error(request, "No puedes editar este pituto porque ya tiene postulantes.")
        return redirect('panel_oferente')

    if request.method == 'POST':
        # Almacenar pago antiguo antes de enlazar el form
        old_pago = pituto.pago
        form = PitutoForm(request.POST, instance=pituto)
        
        if form.is_valid():
            nuevo_pituto = form.save(commit=False)
            if nuevo_pituto.pago != old_pago:
                nuevo_pituto.pago_anterior = old_pago
            nuevo_pituto.save()
            messages.success(request, "Pituto actualizado correctamente.")
            return redirect('panel_oferente')
    else:
        form = PitutoForm(instance=pituto)
        
    return render(request, 'editar_pituto.html', {'form': form, 'pituto': pituto})

@login_required
def archivar_pituto(request, pituto_id):
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')
        
    pituto = get_object_or_404(Pituto, id=pituto_id, creador=request.user)
    
    if pituto.postulaciones.exists():
        messages.error(request, "No puedes archivar este pituto porque ya tiene postulantes.")
    else:
        pituto.activo = False
        pituto.save()
        messages.success(request, "Pituto archivado correctamente.")
        
    return redirect('panel_oferente')


# --- Ciclo de vida del Pituto ---

@login_required
def seleccionar_cuidador(request, pituto_id, postulacion_id):
    """Oferente selecciona un cuidador → Pituto pasa a estado OTORGADO."""
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')
    if request.method != 'POST':
        return redirect('ver_postulantes', pituto_id=pituto_id)

    pituto = get_object_or_404(Pituto, id=pituto_id, creador=request.user)
    postulacion = get_object_or_404(Postulacion, id=postulacion_id, pituto=pituto)

    if pituto.estado != 'ACTIVO':
        messages.error(request, "Este pituto ya no está activo y no puedes cambiar el cuidador.")
        return redirect('ver_postulantes', pituto_id=pituto_id)

    pituto.cuidador_seleccionado = postulacion.usuario
    pituto.estado = 'OTORGADO'
    pituto.activo = False   # Ya no aparece en el listado público
    pituto.save()
    messages.success(
        request,
        f"¡Cuidador seleccionado! {postulacion.usuario.get_full_name() or postulacion.usuario.username} "
        f"realizará el pituto '{pituto.titulo}'."
    )
    return redirect('panel_oferente')


@login_required
def finalizar_pituto(request, pituto_id):
    """Oferente marca el pituto como finalizado y califica al cuidador."""
    if request.user.perfil.rol != 'OFERENTE':
        return redirect('listar_ofertas')

    pituto = get_object_or_404(Pituto, id=pituto_id, creador=request.user, estado='OTORGADO')

    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        comentario = request.POST.get('comentario', '').strip()

        if not calificacion or not calificacion.isdigit() or not (1 <= int(calificacion) <= 5):
            messages.error(request, "Debes seleccionar una calificación entre 1 y 5 estrellas.")
            return render(request, 'finalizar_pituto.html', {'pituto': pituto})

        from django.utils import timezone
        pituto.calificacion_a_cuidador = int(calificacion)
        pituto.comentario_a_cuidador = comentario if comentario else None
        pituto.estado = 'FINALIZADO'
        pituto.fecha_finalizacion = timezone.now()
        pituto.save()
        messages.success(request, f"Pituto '{pituto.titulo}' finalizado. ¡Gracias por tu calificación!")
        return redirect('panel_oferente')

    return render(request, 'finalizar_pituto.html', {'pituto': pituto})


@login_required
def calificar_oferente(request, pituto_id):
    """Cuidador califica al oferente tras la finalización del pituto."""
    if request.user.perfil.rol != 'CUIDADOR':
        return redirect('listar_ofertas')

    pituto = get_object_or_404(
        Pituto,
        id=pituto_id,
        cuidador_seleccionado=request.user,
        estado='FINALIZADO'
    )

    # Solo puede calificar si aún no lo ha hecho
    if pituto.calificacion_a_oferente is not None:
        messages.info(request, "Ya calificaste al oferente de este pituto.")
        return redirect('bitacora_cuidador')

    if request.method == 'POST':
        calificacion = request.POST.get('calificacion')
        comentario = request.POST.get('comentario', '').strip()

        if not calificacion or not calificacion.isdigit() or not (1 <= int(calificacion) <= 5):
            messages.error(request, "Debes seleccionar una calificación entre 1 y 5 estrellas.")
            return render(request, 'calificar_oferente.html', {'pituto': pituto})

        pituto.calificacion_a_oferente = int(calificacion)
        pituto.comentario_a_oferente = comentario if comentario else None
        pituto.save()
        messages.success(request, "¡Gracias por tu calificación! Ayuda a mejorar la comunidad Pitutea.")
        return redirect('bitacora_cuidador')

    return render(request, 'calificar_oferente.html', {'pituto': pituto})

@login_required
def reportar(request):
    pituto_id = request.GET.get('pituto_id') or request.POST.get('pituto_id')
    cuidador_id = request.GET.get('cuidador_id') or request.POST.get('cuidador_id')
    
    pituto = None
    cuidador = None
    tipo_reporte = 'pituto'
    
    if pituto_id:
        pituto = get_object_or_404(Pituto, id=pituto_id)
        
    if cuidador_id:
        cuidador = get_object_or_404(User, id=cuidador_id)
        tipo_reporte = 'cuidador'
        
    user_rol = getattr(request.user.perfil, 'rol', None)
    if user_rol == 'CUIDADOR' and tipo_reporte == 'cuidador':
        messages.error(request, "Acción no permitida.")
        return redirect('listar_ofertas')
    if user_rol == 'OFERENTE' and tipo_reporte == 'pituto':
        messages.error(request, "Acción no permitida.")
        return redirect('panel_oferente')

    if request.method == 'POST':
        form = ReporteForm(request.POST, tipo_reporte=tipo_reporte)
        if form.is_valid():
            motivo = form.cleaned_data['motivo']
            detalles = form.cleaned_data['detalles']
            motivo_display = dict(form.fields['motivo'].choices).get(motivo, motivo)
            
            reporter = request.user
            reporter_perfil = getattr(reporter, 'perfil', None)
            reporter_telefono = reporter_perfil.telefono if reporter_perfil else 'No registrado'
            
            subject = f"[REPORTE PITUTEA] - {motivo_display}"
            
            body = f"SE HA REGISTRADO UN REPORTE EN LA PLATAFORMA PITUTEA\n"
            body += f"==================================================\n\n"
            body += f"TIPO DE REPORTE: Reporte de {tipo_reporte.capitalize()}\n\n"
            
            body += f"DATOS DEL REPORTANTE:\n"
            body += f"---------------------\n"
            body += f"- Usuario: {reporter.username}\n"
            body += f"- Nombre completo: {reporter.get_full_name()}\n"
            body += f"- Correo: {reporter.email}\n"
            body += f"- Teléfono: {reporter_telefono}\n"
            body += f"- Rol: {user_rol}\n\n"
            
            body += f"DATOS DE LA DENUNCIA:\n"
            body += f"---------------------\n"
            if tipo_reporte == 'pituto' and pituto:
                body += f"- Pituto ID: {pituto.id}\n"
                body += f"- Título del Pituto: {pituto.titulo}\n"
                body += f"- Creador del Pituto (Oferente): {pituto.creador.username} ({pituto.creador.get_full_name()})\n\n"
            elif tipo_reporte == 'cuidador' and cuidador:
                body += f"- Cuidador ID: {cuidador.id}\n"
                body += f"- Cuidador (Usuario): {cuidador.username}\n"
                body += f"- Nombre del Cuidador: {cuidador.get_full_name()}\n"
                if pituto:
                    body += f"- Asociado al Pituto ID: {pituto.id}\n"
                    body += f"- Título del Pituto: {pituto.titulo}\n\n"
                else:
                    body += f"\n"
                    
            body += f"MOTIVO DEL REPORTE:\n"
            body += f"--------------------\n"
            body += f"{motivo_display}\n\n"
            
            body += f"DETALLES / COMENTARIOS DEL REPORTANTE:\n"
            body += f"--------------------------------------\n"
            body += f"{detalles}\n\n"
            
            body += f"==================================================\n"
            body += f"Mensaje generado automáticamente por el sistema de reportes de Pitutea.\n"
            
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL or 'no-reply@pitutea.cl',
                    recipient_list=['contactopitutea@gmail.com'],
                    fail_silently=False
                )
                messages.success(request, "Reporte enviado con éxito. Gracias por ayudarnos a mantener segura la comunidad.")
            except Exception as e:
                messages.error(request, "Hubo un error al enviar el reporte. Por favor, inténtalo de nuevo más tarde.")
                
            if user_rol == 'CUIDADOR':
                return redirect('bitacora_cuidador')
            else:
                return redirect('panel_oferente')
    else:
        form = ReporteForm(tipo_reporte=tipo_reporte)
        
    context = {
        'form': form,
        'tipo_reporte': tipo_reporte,
        'pituto': pituto,
        'cuidador': cuidador
    }
    return render(request, 'reportar.html', context)

def incrementar_visitas(request):
    from django.http import JsonResponse
    import os
    from django.conf import settings
    
    file_path = os.path.join(settings.BASE_DIR, 'visitas.txt')
    count = 0
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                count = int(f.read().strip())
        except ValueError:
            pass
            
    session_key = 'visita_registrada'
    if not request.session.get(session_key):
        request.session[session_key] = True
        count += 1
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(str(count))
        except Exception:
            pass
            
    return JsonResponse({'visitas': count})

def obtener_regiones_comunas(request):
    import json
    import os
    from django.http import JsonResponse
    from django.conf import settings
    
    json_path = os.path.join(settings.BASE_DIR, 'app_pitutea', 'static', 'assets', 'territoriochile.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
