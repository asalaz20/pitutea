from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.db.models import Q
from .models import Pituto, Postulacion, Perfil
from .forms import RegistroForm, PerfilForm, PitutoForm

# FASE 2: MATCHING Y PERFIL
def registro_usuario(request):
    if request.user.is_authenticated:
        return redirect('listar_ofertas')
        
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Forzamos que configuren su perfil inicialmente
            return redirect('editar_perfil')
    else:
        form = RegistroForm()
        
    return render(request, 'registro.html', {'form': form})

@login_required
def editar_perfil(request):
    perfil = request.user.perfil
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
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
