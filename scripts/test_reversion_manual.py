#!/usr/bin/env python
"""
Script para probar manualmente la función de reversión de abonos a capital
y detectar errores potenciales

Uso:
    python manage.py shell < scripts/test_reversion_manual.py
"""

from finance.models import AbonoCapital, Incomes, Incomes_detail
from sales.models import Sales, Payment_plans, backup_payment_plans
from django.db.models import Count, Q
from datetime import datetime, timedelta

print("="*80)
print("ANÁLISIS DE POSIBLES ERRORES EN REVERSIÓN DE ABONOS")
print("="*80)
print()

# ============================================================================
# ERROR 1: COMISIÓN PAGADA
# ============================================================================
print("1. Verificando abonos con comisión pagada...")
abonos_con_comision = AbonoCapital.objects.filter(
    Q(comision_pagado_a__isnull=False) | Q(valor_comision__isnull=False)
).select_related('sale', 'income', 'comision_pagado_a')

if abonos_con_comision.exists():
    print(f"   ⚠️  ADVERTENCIA: Hay {abonos_con_comision.count()} abono(s) con comisión pagada")
    print("   Estos NO deberían poder revertirse sin revertir primero la comisión")
    print()
    for abono in abonos_con_comision[:5]:
        print(f"   - Abono {abono.id}: CTR{abono.sale.contract_number}")
        print(f"     Recibo: {abono.income.receipt}")
        print(f"     Comisión: ${abono.valor_comision} pagada a {abono.comision_pagado_a.get_full_name() if abono.comision_pagado_a else 'N/A'}")
        print()
else:
    print("   ✓ No hay abonos con comisión pagada")
print()

# ============================================================================
# ERROR 2: ORDEN DE RE-APLICACIÓN
# ============================================================================
print("2. Verificando orden de abonos y recibos...")

# Buscar ventas con múltiples abonos
ventas_multiples_abonos = AbonoCapital.objects.values('sale_id').annotate(
    count=Count('id')
).filter(count__gt=1)

if ventas_multiples_abonos.exists():
    print(f"   Hay {ventas_multiples_abonos.count()} venta(s) con múltiples abonos")
    print("   Verificando si hay recibos intercalados...")

    problemas_orden = []
    for venta_info in ventas_multiples_abonos[:10]:
        sale = Sales.objects.get(id_sale=venta_info['sale_id'])
        abonos = AbonoCapital.objects.filter(sale=sale).order_by('fecha')

        if abonos.count() >= 2:
            # Verificar si hay recibos entre abonos
            primer_abono = abonos.first()
            ultimo_abono = abonos.last()

            recibos_entre = Incomes.objects.filter(
                sale=sale,
                payment_date__gt=primer_abono.fecha,
                payment_date__lt=ultimo_abono.fecha
            ).exclude(
                id__in=abonos.values_list('income_id', flat=True)
            )

            if recibos_entre.exists():
                problemas_orden.append({
                    'sale': sale,
                    'abonos': abonos.count(),
                    'recibos_entre': recibos_entre.count()
                })

    if problemas_orden:
        print(f"   ⚠️  ADVERTENCIA: {len(problemas_orden)} venta(s) con recibos intercalados entre abonos")
        for prob in problemas_orden[:3]:
            print(f"   - CTR{prob['sale'].contract_number}: {prob['abonos']} abonos, {prob['recibos_entre']} recibos intercalados")
        print("   Esto puede causar problemas de orden en la re-aplicación")
    else:
        print("   ✓ No se detectaron problemas de orden")
else:
    print("   ✓ No hay ventas con múltiples abonos")
print()

# ============================================================================
# ERROR 3: CÓDIGOS ABCAP INCORRECTOS
# ============================================================================
print("3. Verificando códigos ABCAP en backups...")

# Buscar backups con cuotas ABCAP
backups_con_abcap = backup_payment_plans.objects.filter(
    quota_type='ABCAP'
).select_related('sale')

if backups_con_abcap.exists():
    print(f"   Hay {backups_con_abcap.count()} cuota(s) ABCAP en backups")

    codigos_incorrectos = []
    for cuota_backup in backups_con_abcap[:20]:
        sale = cuota_backup.sale
        # Extraer número de contrato del código
        import re
        match = re.match(r'ABCAP\d+CTR(\d+)', cuota_backup.id_quota)
        if match:
            numero_en_codigo = int(match.group(1))
            if numero_en_codigo != sale.contract_number:
                codigos_incorrectos.append({
                    'cuota': cuota_backup,
                    'codigo': cuota_backup.id_quota,
                    'codigo_correcto': cuota_backup.id_quota.replace(f'CTR{numero_en_codigo}', f'CTR{sale.contract_number}'),
                    'sale_pk': sale.pk,
                    'contract_number': sale.contract_number
                })

    if codigos_incorrectos:
        print(f"   ⚠️  ADVERTENCIA: {len(codigos_incorrectos)} cuota(s) con código incorrecto en backups")
        for item in codigos_incorrectos[:3]:
            print(f"   - Código actual: {item['codigo']}")
            print(f"     Código correcto: {item['codigo_correcto']}")
            print(f"     (Sale PK={item['sale_pk']}, Contract={item['contract_number']})")
        print()
        print("   Al restaurar estos backups, se copiarían los códigos incorrectos")
    else:
        print("   ✓ Todos los códigos ABCAP en backups son correctos")
else:
    print("   ℹ️  No hay cuotas ABCAP en backups")
print()

# ============================================================================
# ERROR 4: BACKUPS FALTANTES
# ============================================================================
print("4. Verificando existencia de backups para cada abono...")

abonos_sin_backup = []
for abono in AbonoCapital.objects.all()[:50]:
    backup_anterior = backup_payment_plans.objects.filter(
        sale=abono.sale,
        backup_date__lt=abono.fecha
    ).values('backup_date').distinct().order_by('-backup_date').first()

    if not backup_anterior:
        abonos_sin_backup.append(abono)

if abonos_sin_backup:
    print(f"   ⚠️  ADVERTENCIA: {len(abonos_sin_backup)} abono(s) sin backup anterior")
    for abono in abonos_sin_backup[:3]:
        print(f"   - Abono {abono.id}: CTR{abono.sale.contract_number}, Fecha: {abono.fecha}")
    print("   Estos abonos NO podrán revertirse")
else:
    print("   ✓ Todos los abonos tienen backup anterior")
print()

# ============================================================================
# ERROR 5: MÚLTIPLES ABONOS EN EL MISMO DÍA
# ============================================================================
print("5. Verificando abonos en la misma fecha...")

abonos_mismo_dia = AbonoCapital.objects.values('sale_id', 'fecha').annotate(
    count=Count('id')
).filter(count__gt=1)

if abonos_mismo_dia.exists():
    print(f"   ⚠️  ADVERTENCIA: {abonos_mismo_dia.count()} caso(s) de múltiples abonos en la misma fecha")
    for caso in abonos_mismo_dia[:3]:
        sale = Sales.objects.get(id_sale=caso['sale_id'])
        print(f"   - CTR{sale.contract_number}: {caso['count']} abonos el {caso['fecha']}")
    print("   Al revertir uno, los demás del mismo día se re-aplicarán")
else:
    print("   ✓ No hay múltiples abonos en la misma fecha")
print()

# ============================================================================
# RESUMEN DE RIESGOS
# ============================================================================
print("="*80)
print("RESUMEN DE RIESGOS DETECTADOS")
print("="*80)

riesgos = []

if abonos_con_comision.exists():
    riesgos.append(f"🔴 CRÍTICO: {abonos_con_comision.count()} abono(s) con comisión pagada que podrían revertirse incorrectamente")

if problemas_orden:
    riesgos.append(f"🔴 CRÍTICO: {len(problemas_orden)} venta(s) con posibles problemas de orden en re-aplicación")

if codigos_incorrectos:
    riesgos.append(f"🟡 ALTO: {len(codigos_incorrectos)} código(s) ABCAP incorrectos en backups")

if abonos_sin_backup:
    riesgos.append(f"🟠 MEDIO: {len(abonos_sin_backup)} abono(s) sin backup (no revertibles)")

if abonos_mismo_dia.exists():
    riesgos.append(f"🟢 BAJO: {abonos_mismo_dia.count()} caso(s) de múltiples abonos mismo día")

if riesgos:
    print("\nRiesgos encontrados:")
    for i, riesgo in enumerate(riesgos, 1):
        print(f"{i}. {riesgo}")

    print()
    print("RECOMENDACIÓN: Aplicar correcciones antes de usar la reversión en producción")
else:
    print("\n✅ No se detectaron riesgos significativos")
    print("La funcionalidad de reversión puede usarse con precaución")

print()
print("="*80)
print("FIN DEL ANÁLISIS")
print("="*80)
