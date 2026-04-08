
import numpy_financial as npf
from dateutil.relativedelta import relativedelta
import datetime

def simulate_abono_capital(sale, monto):
    cuotas = sale.credit_info_set.filter().order_by('pay_date')
    pendiente = monto
    tasa = float(sale.sale_plan.rate) / 100
    hoy = datetime.date.today()

    # Paso 1: simular pago de cuotas vencidas
    for cuota in cuotas:
        if cuota.pay_date > hoy:
            break
        pendiente_cuota = cuota.quota_pending()['total_pending']
        if pendiente >= pendiente_cuota:
            pendiente -= pendiente_cuota
        else:
            pendiente = 0
            break

    if pendiente <= 0:
        return {'capital_disponible': 0, 'opciones': {}}

    # Paso 2: calcular capital restante del crédito
    cuotas_futuras = cuotas.filter(pay_date__gt=hoy, saldo_capital__gt=0)
    saldo_restante = sum(q.saldo_capital for q in cuotas_futuras)

    if saldo_restante == 0:
        return {'capital_disponible': pendiente, 'opciones': {}}

    n_cuotas = cuotas_futuras.count()
    valor_cuota = cuotas_futuras.first().total_payment() if n_cuotas > 0 else 0
    fecha_inicio = cuotas_futuras.first().pay_date if n_cuotas > 0 else hoy

    # Opción 1: disminuir número de cuotas, mantener valor
    nuevas_cuotas = npf.nper(tasa, valor_cuota, -(saldo_restante - pendiente))
    nuevas_cuotas = int(round(nuevas_cuotas)) if nuevas_cuotas > 0 else 1

    # Opción 2: mantener número de cuotas, reducir valor
    nueva_cuota = npf.pmt(tasa, n_cuotas, -(saldo_restante - pendiente))
    nueva_cuota = int(round(nueva_cuota)) if nueva_cuota > 0 else valor_cuota

    # Opción 3: cubrir cuotas futuras completas
    restante = pendiente
    cuotas_cubiertas = 0
    for q in cuotas_futuras:
        cuota_total = q.total_payment()
        if restante >= cuota_total:
            restante -= cuota_total
            cuotas_cubiertas += 1
        else:
            break

    return {
        'capital_disponible': pendiente,
        'opciones': {
            '1': {
                'nuevas_cuotas': nuevas_cuotas,
                'valor_cuota_aprox': valor_cuota
            },
            '2': {
                'mismas_cuotas': n_cuotas,
                'nueva_cuota': nueva_cuota
            },
            '3': {
                'cuotas_cubiertas': cuotas_cubiertas,
                'restante': restante
            }
        }
    }

