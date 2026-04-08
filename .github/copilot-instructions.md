# Instrucciones para agentes AI en este proyecto

## Arquitectura y estructura
- Proyecto Django modular: apps principales en `finance/`, `sales/`, `mcd_site/`, `terceros/`, cada una con modelos, vistas, forms y templates propios.
- Configuración global en `mcd_project/` (`settings.py`, `urls.py`).
- Datos y archivos estáticos en `data/`, `static/`, `static_files/`, `static_media/`.
- SQL y dumps de datos en `auxiliares/`.

## Flujos de desarrollo
- Usa `docker compose` para levantar servicios y base de datos local.
- Ejecuta tests con `pytest` (ver `pytest.ini`).
- Comandos de gestión: `python manage.py <comando>`.
- Los cambios en modelos requieren migraciones (`python manage.py makemigrations && python manage.py migrate`).

## Patrones y convenciones
- Vistas usan decoradores de permisos: `@project_permission`, `@user_permission('permiso')`, y `@login_required`.
- Filtros de datos por rol: gestor solo ve sus datos, líder ve todos (ver ejemplo en `comisiones_cartera`).
- AJAX: vistas que retornan `JsonResponse` o HTML parcial, detectan `request.is_ajax()`.
- Templates: estructura en `templates/` y subcarpetas por app.
- No usar variables globales; pasa todo por parámetros o contexto.
- Código eficiente y legible, sin comentarios innecesarios ni funciones redundantes.
- Nombres de variables cortos pero claros.

## Integraciones y dependencias
- Usa PostgreSQL (ver `data/db/` y configuración en `docker-compose.yml`).
- Dependencias Python en `requirements.txt`.
- Algunas vistas generan y manipulan archivos Excel (`openpyxl`).

## Ejemplos clave
- Filtro de datos por rol:
  ```python
  es_gestor = any('gestor' in r.descripcion and 'cartera' in r.descripcion for r in user.user_profile.rol.all())
  es_lider = any('lider' in r.descripcion and 'cartera' in r.descripcion for r in user.user_profile.rol.all())
  if es_gestor and not es_lider:
      queryset = queryset.filter(usuario=user)
  ```
- AJAX en vistas:
  ```python
  if request.is_ajax():
      return JsonResponse({'data': ...})
  ```
- Decoradores de permisos:
  ```python
  @login_required
  @project_permission
  @user_permission('permiso')
  ```

## Directorios y archivos clave
- `finance/views.py`: lógica de negocio y ejemplos de patrones de permisos y filtrado.
- `mcd_project/settings.py`: configuración global.
- `requirements.txt`: dependencias.
- `docker-compose.yml`: servicios y base de datos.

---
Actualiza este archivo si cambian los patrones globales, flujos de permisos o estructura de apps.