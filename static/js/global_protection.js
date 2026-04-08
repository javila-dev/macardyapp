(function() {
    'use strict';
    
    let processingForms = new WeakSet();
    let transactionToken = null;
    
    // Obtener token de la sesión
    function getToken() {
        if (!transactionToken) {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta && meta.dataset.token) {
                transactionToken = meta.dataset.token;
            }
        }
        return transactionToken;
    }
    
    // Auto-proteger todos los formularios
    function protectForm(form) {
        if (form.dataset.protected) return;
        form.dataset.protected = 'true';
        
        form.addEventListener('submit', function(e) {
            if (processingForms.has(form)) {
                e.preventDefault();
                showToast('Procesando, por favor espere...', 'warning');
                return false;
            }
            
            processingForms.add(form);
            
            // Añadir token al formulario
            const token = getToken();
            if (token && !form.querySelector('input[name="transaction_token"]')) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'transaction_token';
                input.value = token;
                form.appendChild(input);
            }
            
            // Deshabilitar botones
            const buttons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
            buttons.forEach(btn => {
                btn.disabled = true;
                btn.classList.add('loading', 'disabled');
            });
            
            // Restaurar después de timeout
            setTimeout(() => {
                processingForms.delete(form);
                buttons.forEach(btn => {
                    btn.disabled = false;
                    btn.classList.remove('loading', 'disabled');
                });
            }, 5000);
        });
    }
    
    // Proteger AJAX global
    function protectAjax() {
        if (typeof $ !== 'undefined' && $.ajaxSetup) {
            $.ajaxSetup({
                beforeSend: function(xhr, settings) {
                    if (settings.type === 'POST') {
                        const token = getToken();
                        if (token) {
                            xhr.setRequestHeader('X-Transaction-Token', token);
                        }
                    }
                },
                complete: function(xhr) {
                    // Actualizar token si viene en response
                    const newToken = xhr.getResponseHeader('X-Transaction-Token');
                    if (newToken) {
                        transactionToken = newToken;
                        const meta = document.querySelector('meta[name="csrf-token"]');
                        if (meta) meta.dataset.token = newToken;
                    }
                },
                error: function(xhr) {
                    if (xhr.status === 409 || (xhr.responseJSON && xhr.responseJSON.type === 'warning')) {
                        const response = xhr.responseJSON || {};
                        showToast(response.msj || 'Operación ya procesada', 'warning');
                    }
                }
            });
        }
    }
    
    // Prevenir recarga durante procesamiento
    function preventReload() {
        window.addEventListener('beforeunload', function(e) {
            if (processingForms.size > 0) {
                const msg = 'Hay operaciones en proceso. ¿Desea salir?';
                e.returnValue = msg;
                return msg;
            }
        });
        
        document.addEventListener('keydown', function(e) {
            if (processingForms.size > 0 && (e.key === 'F5' || (e.ctrlKey && e.key === 'r'))) {
                e.preventDefault();
                showToast('Operación en proceso, no recargue la página', 'warning');
            }
        });
    }
    
    // Toast helper
    window.showToast = window.showToast || function(message, type) {
        if (typeof $().toast === 'function') {
            $('body').toast({ class: type || 'info', message: message });
        } else if (console && console.warn) {
            console.warn('Toast:', message);
        }
    };
    
    // Inicializar cuando DOM esté listo
    document.addEventListener('DOMContentLoaded', function() {
        // Proteger formularios existentes
        document.querySelectorAll('form').forEach(protectForm);
        
        // Observer para formularios dinámicos
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        if (node.tagName === 'FORM') protectForm(node);
                        node.querySelectorAll && node.querySelectorAll('form').forEach(protectForm);
                    }
                });
            });
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
        
        protectAjax();
        preventReload();
    });
})();