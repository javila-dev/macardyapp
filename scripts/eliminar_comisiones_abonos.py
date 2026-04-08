#!/usr/bin/env python
"""
Script para eliminar/revertir pagos de comisión de abonos a capital

Este script permite:
1. Ver abonos con comisión pagada
2. Eliminar el pago de comisión de uno o varios abonos
3. Registrar la reversión en el historial

Uso:
    python manage.py shell < scripts/eliminar_comisiones_abonos.py

    O interactivamente:
    python manage.py shell
    >>> exec(open('scripts/eliminar_comisiones_abonos.py').read())
    >>> eliminar_comision_abono(abono_id=4, motivo="Corrección de pago duplicado")
"""

from finance.models import AbonoCapital
from sales.models import Sales_history
from mcd_site.models import Timeline
from django.contrib.auth.models import User
from django.db import transaction
from datetime import datetime


def listar_abonos_con_comision():
    """
    Lista todos los abonos que tienen comisión pagada
    """
    print("="*80)
    print("ABONOS CON COMISIÓN PAGADA")
    print("="*80)
    print()

    abonos = AbonoCapital.objects.filter(
        comision_pagado_a__isnull=False
    ).select_related('sale', 'income', 'comision_pagado_a', 'comision_pagado_por').order_by('-comision_pagado_el')

    if not abonos.exists():
        print("✓ No hay abonos con comisión pagada")
        return []

    print(f"Total de abonos con comisión: {abonos.count()}")
    print()

    for abono in abonos:
        print(f"ID: {abono.id}")
        print(f"  Contrato: CTR{abono.sale.contract_number}")
        print(f"  Cliente: {abono.sale.first_owner.full_name()}")
        print(f"  Recibo: {abono.income.receipt}")
        print(f"  Fecha abono: {abono.fecha.strftime('%d/%m/%Y')}")
        print(f"  Capital aplicado: ${abono.capital_aplicado:,.0f}")
        print(f"  Tipo: {abono.get_tipo_display()}")
        print()
        print(f"  💰 Comisión:")
        print(f"     Valor: ${abono.valor_comision:,.2f}")
        print(f"     Porcentaje: {abono.porcentaje_comision}%")
        print(f"     Pagado a: {abono.comision_pagado_a.get_full_name()}")
        print(f"     Pagado el: {abono.comision_pagado_el.strftime('%d/%m/%Y %H:%M')}")
        if abono.comision_pagado_por:
            print(f"     Pagado por: {abono.comision_pagado_por.get_full_name()}")
        print()
        print("-"*80)
        print()

    return list(abonos)


def eliminar_comision_abono(abono_id, motivo, usuario_id=None):
    """
    Elimina/revierte el pago de comisión de un abono a capital

    Args:
        abono_id: ID del abono
        motivo: Razón de la eliminación (obligatorio)
        usuario_id: ID del usuario que ejecuta la acción (opcional)

    Returns:
        dict con status y mensaje
    """
    if not motivo or len(motivo.strip()) < 10:
        return {
            'status': 'error',
            'message': 'El motivo debe tener al menos 10 caracteres'
        }

    try:
        abono = AbonoCapital.objects.get(id=abono_id)
    except AbonoCapital.DoesNotExist:
        return {
            'status': 'error',
            'message': f'No existe abono con ID {abono_id}'
        }

    # Verificar que tenga comisión
    if not abono.comision_pagado_a and not abono.valor_comision:
        return {
            'status': 'error',
            'message': 'Este abono no tiene comisión pagada'
        }

    # Guardar info para el log
    info_comision = {
        'valor': float(abono.valor_comision) if abono.valor_comision else 0,
        'porcentaje': float(abono.porcentaje_comision) if abono.porcentaje_comision else 0,
        'pagado_a': abono.comision_pagado_a.get_full_name() if abono.comision_pagado_a else 'N/A',
        'pagado_el': abono.comision_pagado_el.strftime('%d/%m/%Y %H:%M') if abono.comision_pagado_el else 'N/A',
        'pagado_por': abono.comision_pagado_por.get_full_name() if abono.comision_pagado_por else 'N/A'
    }

    # Eliminar comisión
    with transaction.atomic():
        abono.valor_comision = None
        abono.porcentaje_comision = None
        abono.comision_pagado_a = None
        abono.comision_pagado_el = None
        abono.comision_pagado_por = None
        abono.save()

        # Registrar en historial
        usuario = None
        if usuario_id:
            try:
                usuario = User.objects.get(id=usuario_id)
            except User.DoesNotExist:
                pass

        mensaje_historial = (
            f"Eliminó pago de comisión de abono a capital: "
            f"${info_comision['valor']:,.2f} ({info_comision['porcentaje']}%) "
            f"que fue pagada a {info_comision['pagado_a']} el {info_comision['pagado_el']}. "
            f"Motivo: {motivo}"
        )

        Sales_history.objects.create(
            sale=abono.sale,
            action=mensaje_historial,
            user=usuario
        )

        if usuario:
            Timeline.objects.create(
                user=usuario,
                action=f"Eliminó comisión de abono en CTR{abono.sale.contract_number}. Motivo: {motivo}",
                project=abono.sale.project,
                aplication='finance'
            )

    return {
        'status': 'ok',
        'message': f'Comisión eliminada correctamente',
        'info': info_comision
    }


def eliminar_todas_comisiones(motivo, usuario_id=None, dry_run=True):
    """
    Elimina todas las comisiones de abonos a capital (usar con precaución)

    Args:
        motivo: Razón de la eliminación masiva
        usuario_id: ID del usuario
        dry_run: Si es True, solo muestra lo que haría sin ejecutar

    Returns:
        dict con resultados
    """
    if not motivo or len(motivo.strip()) < 20:
        return {
            'status': 'error',
            'message': 'Para eliminación masiva, el motivo debe tener al menos 20 caracteres'
        }

    abonos = AbonoCapital.objects.filter(comision_pagado_a__isnull=False)

    if not abonos.exists():
        return {
            'status': 'info',
            'message': 'No hay abonos con comisión para eliminar'
        }

    print()
    print("="*80)
    print("ELIMINACIÓN MASIVA DE COMISIONES")
    print("="*80)
    print()
    print(f"Total de abonos a procesar: {abonos.count()}")
    print(f"Modo: {'DRY-RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")
    print()

    resultados = {
        'total': abonos.count(),
        'exitosos': 0,
        'errores': 0,
        'detalles': []
    }

    for abono in abonos:
        info = f"Abono {abono.id} - CTR{abono.sale.contract_number} - ${abono.valor_comision:,.2f}"
        print(f"Procesando: {info}")

        if not dry_run:
            resultado = eliminar_comision_abono(abono.id, motivo, usuario_id)
            if resultado['status'] == 'ok':
                resultados['exitosos'] += 1
                print(f"  ✓ Eliminado")
            else:
                resultados['errores'] += 1
                print(f"  ✗ Error: {resultado['message']}")
            resultados['detalles'].append({
                'abono_id': abono.id,
                'info': info,
                'resultado': resultado
            })
        else:
            print(f"  (simulado)")
            resultados['detalles'].append({
                'abono_id': abono.id,
                'info': info,
                'simulado': True
            })

    print()
    print("="*80)
    print("RESUMEN")
    print("="*80)
    print(f"Total procesados: {resultados['total']}")
    if not dry_run:
        print(f"Exitosos: {resultados['exitosos']}")
        print(f"Errores: {resultados['errores']}")
    else:
        print("Modo DRY-RUN - ningún cambio fue aplicado")
        print("Para ejecutar realmente, use: dry_run=False")
    print()

    return resultados


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================

if __name__ == '__main__':
    print()
    print("="*80)
    print("SCRIPT DE ELIMINACIÓN DE COMISIONES DE ABONOS")
    print("="*80)
    print()

    # Listar abonos con comisión
    abonos = listar_abonos_con_comision()

    if abonos:
        print()
        print("EJEMPLOS DE USO:")
        print()
        print("# Eliminar comisión de un abono específico:")
        print(f">>> eliminar_comision_abono(")
        print(f"...     abono_id={abonos[0].id},")
        print(f"...     motivo='Error en el cálculo de comisión',")
        print(f"...     usuario_id=1  # opcional")
        print(f"... )")
        print()
        print("# Eliminar todas las comisiones (simulación):")
        print(">>> eliminar_todas_comisiones(")
        print("...     motivo='Reversión masiva por recálculo de comisiones',")
        print("...     dry_run=True  # cambiar a False para ejecutar")
        print("... )")
        print()
    else:
        print("No hay comisiones para eliminar")
        print()

    print("="*80)
