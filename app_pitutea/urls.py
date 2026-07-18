from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Cuidadores / Ofertas
    path('', views.listar_ofertas, name='listar_ofertas'),
    path('postular/<int:oferta_id>/', views.postular_pituto, name='postular_pituto'),
    path('bitacora/', views.bitacora_cuidador, name='bitacora_cuidador'),
    
    # Autenticación y Perfil
    path('registro/', views.registro_usuario, name='registro'),
    path('verificar-correo/<str:uidb64>/<str:token>/', views.verificar_correo, name='verificar_correo'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='listar_ofertas'), name='logout'),
    path('perfil/', views.editar_perfil, name='editar_perfil'),
    
    # Panel Oferente
    path('panel/', views.panel_oferente, name='panel_oferente'),
    path('panel/crear/', views.crear_pituto, name='crear_pituto'),
    path('panel/pituto/<int:pituto_id>/editar/', views.editar_pituto, name='editar_pituto'),
    path('panel/pituto/<int:pituto_id>/archivar/', views.archivar_pituto, name='archivar_pituto'),
    path('panel/pituto/<int:pituto_id>/postulantes/', views.ver_postulantes, name='ver_postulantes'),
    path('panel/pituto/<int:pituto_id>/seleccionar/<int:postulacion_id>/', views.seleccionar_cuidador, name='seleccionar_cuidador'),
    path('panel/pituto/<int:pituto_id>/finalizar/', views.finalizar_pituto, name='finalizar_pituto'),

    # Cuidador califica al oferente (desde su bitácora)
    path('bitacora/pituto/<int:pituto_id>/calificar/', views.calificar_oferente, name='calificar_oferente'),
    path('reportar/', views.reportar, name='reportar'),
    path('api/visitas/', views.incrementar_visitas, name='incrementar_visitas'),
    path('api/regiones-comunas/', views.obtener_regiones_comunas, name='obtener_regiones_comunas'),
    
    # Páginas Legales
    path('terminos-y-condiciones/', views.terminos_condiciones, name='terminos_condiciones'),
]

