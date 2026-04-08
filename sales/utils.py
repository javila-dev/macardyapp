from datetime import datetime
import decimal
from django.db.models import Sum
from .models import Payment_plans, backup_payment_plans, Sales

def backup_plan_pagos(sale):
    """Crea backup del plan de pagos actual"""
    payment_plan = Payment_plans.objects.filter(sale=sale)
    backup_datetime = datetime.now()
    
    for cuota in payment_plan:
        backup_payment_plans.objects.create(
            id_payment=cuota.pk,
            id_quota=cuota.id_quota,
            quota_type=cuota.quota_type,
            sale=sale,
            pay_date=cuota.pay_date,
            capital=cuota.capital,
            interest=cuota.interest,
            others=cuota.others,
            project=sale.project,
            backup_date=backup_datetime
        )
    return True

def recalcular_plan_pagos(sale_id, cuota_modificada_id=None, nuevos_valores=None):
    """
    Recalcula el plan de pagos después de modificar una cuota.
    
    Args:
        sale_id: ID de la venta
        cuota_modificada_id: ID de la cuota modificada (None si es recálculo completo)
        nuevos_valores: Diccionario con los nuevos valores {capital, interest, others, pay_date}
    
    Returns:
        True si se completó correctamente
    """
    sale = Sales.objects.get(pk=sale_id)
    
    # Si hay una cuota modificada, aplicamos los cambios primero
    if cuota_modificada_id and nuevos_valores:
        cuota = Payment_plans.objects.get(pk=cuota_modificada_id)
        
        # Guardamos los valores previos para calcular la diferencia
        saldo_anterior = cuota.capital + cuota.interest + cuota.others - cuota.paid()
        
        # Actualizamos la cuota con los nuevos valores
        if 'capital' in nuevos_valores:
            cuota.capital = decimal.Decimal(nuevos_valores['capital'])
        if 'interest' in nuevos_valores:
            cuota.interest = decimal.Decimal(nuevos_valores['interest'])
        if 'others' in nuevos_valores:
            cuota.others = decimal.Decimal(nuevos_valores['others'])
        if 'pay_date' in nuevos_valores:
            cuota.pay_date = nuevos_valores['pay_date']
        
        cuota.save()
        
        # Calculamos el nuevo saldo y la diferencia
        nuevo_saldo = cuota.capital + cuota.interest + cuota.others - cuota.paid()
        diferencia_saldo = saldo_anterior - nuevo_saldo
    else:
        diferencia_saldo = 0
    
    # Obtenemos cuotas posteriores para redistribuir la diferencia
    cuotas_posteriores = None
    if cuota_modificada_id:
        cuota_modificada = Payment_plans.objects.get(pk=cuota_modificada_id)
        # Solo las cuotas del mismo tipo y con fechas posteriores
        cuotas_posteriores = Payment_plans.objects.filter(
            sale=sale,
            quota_type=cuota_modificada.quota_type,
            pay_date__gt=cuota_modificada.pay_date,
        ).order_by('pay_date')
    
    # Si hay diferencia de saldo y cuotas posteriores, redistribuimos
    if diferencia_saldo != 0 and cuotas_posteriores and cuotas_posteriores.count() > 0:
        tasa = float(sale.sale_plan.rate) / 100 if cuota_modificada.quota_type != 'CI' else 0
        saldo_restante = -diferencia_saldo  # Si diferencia es positiva, debemos reducir las cuotas posteriores
        
        # Primera pasada: recalculamos montos manteniendo la cuota total igual
        for cuota in cuotas_posteriores:
            # Si la cuota ya está pagada, no la modificamos
            if cuota.paid() >= cuota.total_payment():
                continue
                
            saldo_pendiente = cuota.saldo_pendiente()
            # Evitar modificar cuotas con saldo muy pequeño
            if abs(saldo_pendiente) < 0.01:
                continue
                
            # Si es cuota inicial, solo ajustamos capital
            if cuota.quota_type == 'CI':
                nuevo_capital = cuota.capital + saldo_restante
                # Si el nuevo capital es negativo o demasiado pequeño, lo ajustamos
                if nuevo_capital <= 0:
                    saldo_restante -= (cuota.capital - 1)  # Dejamos 1 peso y movemos el resto
                    cuota.capital = 1
                else:
                    cuota.capital = nuevo_capital
                    saldo_restante = 0
            else:
                # Para cuotas con interés, recalculamos proporcionalmente
                # manteniendo el valor total de la cuota
                total_cuota = cuota.total_payment()
                saldo_acumulado = abs(saldo_restante)
                interes = saldo_acumulado * tasa
                capital = total_cuota - interes - cuota.others
                
                if capital <= 0:
                    # Si el capital resulta negativo, ajustamos
                    capital = 1
                    interes = total_cuota - capital - cuota.others
                
                cuota.capital = capital
                cuota.interest = interes
            
            cuota.save()
            
            if abs(saldo_restante) < 0.01:
                break
    
    return True