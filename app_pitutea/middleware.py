from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect

class BlockUserMiddleware:
    """
    Middleware que deniega el acceso al sistema a cualquier usuario
    (cuidador u oferente) cuyo perfil tenga el estado 'BLOQUEADO'.
    En cada petición HTTP, si el usuario autenticado está bloqueado,
    se cierra su sesión de inmediato y se le redirige al login.
    Los superusuarios administradores (is_superuser) están exentos.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            try:
                perfil = request.user.perfil
                if perfil.estado_verificacion == 'BLOQUEADO':
                    logout(request)
                    messages.error(
                        request,
                        "Tu cuenta ha sido bloqueada por mal uso de la plataforma. "
                        "Contacta al administrador si crees que esto es un error."
                    )
                    return redirect('login')
            except Exception:
                # El usuario no tiene perfil asociado, dejamos pasar
                pass

        response = self.get_response(request)
        return response
