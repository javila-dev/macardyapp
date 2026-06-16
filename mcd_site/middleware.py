import uuid
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from mcd_site.models import ensure_user_profile

logger = logging.getLogger(__name__)

class EnsureUserProfileMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if getattr(request, "user", None) and request.user.is_authenticated:
            ensure_user_profile(request.user)
        return None


class DoubleSubmitProtectionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Password reset / auth flows must not be disrupted by accidental duplicate-submit tokens
        # (some clients/extensions may inject hidden fields / headers unexpectedly).
        path = request.path or ''
        # Auth pages are especially sensitive to accidental duplicate-submit handling.
        # Keep protection focused on app POSTs that explicitly include transaction_token.
        if path.startswith('/accounts/'):
            return None

        # Generar token para requests GET
        if request.method == 'GET':
            request.session['transaction_token'] = str(uuid.uuid4())
        
        # Validar token para requests POST
        elif request.method == 'POST':
            token = request.POST.get('transaction_token') or request.META.get('HTTP_X_TRANSACTION_TOKEN')
            
            if token:
                cache_key = f'submit_token_{token}'
                if cache.get(cache_key):  # LocMemCache maneja esto perfectamente
                    # Token ya usado - prevenir doble submit
                    logger.warning(
                        'Envío duplicado bloqueado en %s (token=%s)',
                        path,
                        token,
                    )
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'type': 'warning', 
                            'title': 'Operación duplicada',
                            'msj': 'Esta operación ya fue procesada. Recarga la página e intenta de nuevo.'
                        })
                    messages.warning(
                        request,
                        '<div class="header">Envío duplicado</div>'
                        'Esta solicitud ya fue procesada. '
                        'Recarga la página antes de volver a enviar el formulario.'
                    )
                    return redirect(request.path)
                
                # Marcar token como usado
                cache.set(cache_key, time.time(), 300)  # 5 minutos
        
        return None

    def process_response(self, request, response):
        # Añadir token al response para AJAX
        if hasattr(request, 'session') and 'transaction_token' in request.session:
            response['X-Transaction-Token'] = request.session['transaction_token']
        return response