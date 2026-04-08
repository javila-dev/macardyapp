#!/usr/bin/env python
"""
Script para corregir los códigos de cuotas ABCAP que usan sale.pk en lugar de sale.contract_number

Este script:
1. Identifica todas las cuotas ABCAP con códigos basados en sale.pk
2. Recalcula el código correcto usando sale.contract_number
3. Actualiza los códigos en la base de datos
4. Genera un reporte de los cambios realizados

Uso:
    python manage.py shell < scripts/fix_abcap_codes.py

O desde Django shell:
    exec(open('scripts/fix_abcap_codes.py').read())
"""

from sales.models import Payment_plans
from django.db import transaction
import re

def fix_abcap_codes(dry_run=False):
    """
    Corrige los códigos de cuotas ABCAP

    Args:
        dry_run: Si es True, solo muestra los cambios sin aplicarlos
    """
    print("=" * 80)
    print("CORRECCIÓN DE CÓDIGOS DE CUOTAS ABCAP")
    print("=" * 80)
    print()

    # Buscar todas las cuotas ABCAP
    cuotas_abcap = Payment_plans.objects.filter(
        quota_type='ABCAP'
    ).select_related('sale', 'sale__project').order_by('sale_id', 'id_quota')

    print(f"Total de cuotas ABCAP encontradas: {cuotas_abcap.count()}")
    print()

    # Agrupar por venta para recalcular números secuenciales
    ventas_cuotas = {}
    for cuota in cuotas_abcap:
        sale_id = cuota.sale_id
        if sale_id not in ventas_cuotas:
            ventas_cuotas[sale_id] = []
        ventas_cuotas[sale_id].append(cuota)

    # Procesar correcciones
    correcciones = []
    sin_cambios = []

    for sale_id, cuotas in ventas_cuotas.items():
        sale = cuotas[0].sale

        # Verificar si necesita corrección
        necesita_correccion = sale.pk != sale.contract_number

        if not necesita_correccion:
            for cuota in cuotas:
                sin_cambios.append({
                    'cuota': cuota,
                    'motivo': 'Sale PK coincide con contract_number'
                })
            continue

        # Recalcular códigos secuencialmente
        for idx, cuota in enumerate(cuotas, start=1):
            codigo_antiguo = cuota.id_quota

            # Extraer el número de secuencia del código antiguo
            match = re.match(r'ABCAP(\d+)CTR(\d+)', codigo_antiguo)
            if match:
                numero_secuencia = int(match.group(1))
                # Usar el número de secuencia original para mantener consistencia
                codigo_nuevo = f"ABCAP{numero_secuencia}CTR{sale.contract_number}"
            else:
                # Si no coincide con el patrón, usar el índice
                codigo_nuevo = f"ABCAP{idx}CTR{sale.contract_number}"

            if codigo_antiguo != codigo_nuevo:
                correcciones.append({
                    'cuota': cuota,
                    'codigo_antiguo': codigo_antiguo,
                    'codigo_nuevo': codigo_nuevo,
                    'sale_pk': sale.pk,
                    'contract_number': sale.contract_number,
                    'proyecto': sale.project.name
                })

    # Mostrar resumen
    print(f"Cuotas que necesitan corrección: {len(correcciones)}")
    print(f"Cuotas sin cambios: {len(sin_cambios)}")
    print()

    if correcciones:
        print("=" * 80)
        print("CAMBIOS A REALIZAR:")
        print("=" * 80)
        print()

        for corr in correcciones:
            print(f"Proyecto: {corr['proyecto']}")
            print(f"  Sale PK: {corr['sale_pk']} -> Contract Number: {corr['contract_number']}")
            print(f"  Código antiguo: {corr['codigo_antiguo']}")
            print(f"  Código nuevo:   {corr['codigo_nuevo']}")
            print()

        if dry_run:
            print("=" * 80)
            print("MODO DRY-RUN: No se aplicaron cambios")
            print("Para aplicar los cambios, ejecute: fix_abcap_codes(dry_run=False)")
            print("=" * 80)
        else:
            # Aplicar cambios
            print("=" * 80)
            print("APLICANDO CAMBIOS...")
            print("=" * 80)
            print()

            try:
                with transaction.atomic():
                    actualizados = 0
                    for corr in correcciones:
                        cuota = corr['cuota']
                        cuota.id_quota = corr['codigo_nuevo']
                        cuota.save(update_fields=['id_quota'])
                        actualizados += 1
                        print(f"✓ Actualizado: {corr['codigo_antiguo']} -> {corr['codigo_nuevo']}")

                    print()
                    print("=" * 80)
                    print(f"✅ CORRECCIÓN COMPLETADA EXITOSAMENTE")
                    print(f"   Total de cuotas actualizadas: {actualizados}")
                    print("=" * 80)

            except Exception as e:
                print()
                print("=" * 80)
                print(f"❌ ERROR AL APLICAR CAMBIOS: {str(e)}")
                print("   Los cambios fueron revertidos (rollback)")
                print("=" * 80)
                raise
    else:
        print("✅ No hay cuotas que necesiten corrección")

    return {
        'total': len(correcciones) + len(sin_cambios),
        'correcciones': len(correcciones),
        'sin_cambios': len(sin_cambios)
    }


# Ejecutar en modo dry-run por defecto
if __name__ == '__main__':
    print()
    print("EJECUTANDO EN MODO DRY-RUN (solo visualización)")
    print()
    resultado = fix_abcap_codes(dry_run=True)
    print()
    print("Para aplicar los cambios realmente, ejecute:")
    print(">>> fix_abcap_codes(dry_run=False)")
