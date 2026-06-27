from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Cuidadores / Ofertas
    path('', views.listar_ofertas, name='listar_ofertas'),
    path('postular/<int:oferta_id>/', views.postular_pituto, name='postular_pituto'),
    
    # Autenticación y Perfil
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='listar_ofertas'), name='logout'),
    path('perfil/', views.editar_perfil, name='editar_perfil'),
    
    # Panel Oferente
    path('panel/', views.panel_oferente, name='panel_oferente'),
    path('panel/crear/', views.crear_pituto, name='crear_pituto'),
    path('panel/pituto/<int:pituto_id>/postulantes/', views.ver_postulantes, name='ver_postulantes'),
]
