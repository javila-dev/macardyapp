import uuid
import time
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect

class DoubleSubmitProtectionMiddleware(MiddlewareMixin):
    def process_request(self, request):
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
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'type': 'warning', 
                            'title': 'Operación duplicada',
                            'msj': 'Esta operación ya fue procesada'
                        })
                    else:
                        return redirect(request.path)
                
                # Marcar token como usado
                cache.set(cache_key, time.time(), 300)  # 5 minutos
        
        return None

    def process_response(self, request, response):
        # Añadir token al response para AJAX
        if hasattr(request, 'session') and 'transaction_token' in request.session:
            response['X-Transaction-Token'] = request.session['transaction_token']
        return response