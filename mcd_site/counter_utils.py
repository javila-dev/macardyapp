import re

from django.db.models import Max

from sales.contract_utils import normalize_counter_prefix

PREFIX_PATTERN = re.compile(r'^[A-Z]{1,3}$')


def counter_uses_prefix(counter):
    return bool(normalize_counter_prefix(counter.prefix))


def storage_prefix_for_mode(use_prefix, prefix):
    if use_prefix:
        return normalize_counter_prefix(prefix)
    return 'CTR'


def contract_preview(use_prefix, prefix, value):
    normalized = normalize_counter_prefix(prefix) if use_prefix else ''
    if normalized:
        return f'{normalized}-{int(value):03d}'
    return str(int(value))


def validate_prefix_value(prefix):
    normalized = normalize_counter_prefix(prefix)
    if not normalized:
        return None, 'El prefijo es obligatorio cuando se usa numeración con prefijo.'
    if not PREFIX_PATTERN.match(normalized):
        return None, 'El prefijo debe tener entre 1 y 3 letras (A-Z).'
    return normalized, None


def max_contract_number(project, contract_prefix=''):
    from sales.models import Sales

    result = Sales.objects.filter(
        project=project,
        contract_prefix=contract_prefix or '',
    ).aggregate(max_number=Max('contract_number'))
    return result['max_number'] or 0


def is_last_contract(sale):
    """True if this sale holds the highest contract_number for its project+prefix."""
    max_used = max_contract_number(sale.project, sale.contract_prefix or '')
    return bool(max_used) and sale.contract_number == max_used


def rollback_contract_counter(sale):
    """
    Set the contratos counter next value back to sale.contract_number so that
    number can be reused. Only updates when the counter's active prefix matches
    the sale's prefix. Call inside transaction.atomic(); the sale row may already
    be deleted — only in-memory fields project / contract_prefix / contract_number
    are read.
    """
    from mcd_site.models import Counters

    project = sale.project
    counter = Counters.objects.select_for_update().get(
        name='contratos',
        project=project,
    )
    active_prefix = normalize_counter_prefix(counter.prefix)
    sale_prefix = sale.contract_prefix or ''
    if active_prefix != sale_prefix:
        return False
    counter.value = sale.contract_number
    counter.save(update_fields=['value'])
    return True


def max_receipt_number(project):
    from finance.models import Incomes

    max_num = 0
    for receipt in Incomes.objects.filter(project=project).values_list('receipt', flat=True):
        text = str(receipt or '').strip()
        if text.isdigit():
            max_num = max(max_num, int(text))
    return max_num


def prefix_is_locked(project):
    from sales.models import Sales

    return Sales.objects.filter(project=project).exclude(contract_prefix='').exists()


def get_or_create_contract_counter(project):
    from mcd_site.models import Counters

    counter, _ = Counters.objects.get_or_create(
        name='contratos',
        project=project,
        defaults={'prefix': 'CTR', 'value': 1},
    )
    return counter


def get_or_create_receipt_counter(project):
    from mcd_site.models import Counters

    counter, _ = Counters.objects.get_or_create(
        name='recibos',
        project=project,
        defaults={'prefix': '', 'value': 1},
    )
    return counter


def contract_rules_for_prefix(project, use_prefix, prefix=''):
    active_prefix = normalize_counter_prefix(prefix) if use_prefix else ''
    max_used = max_contract_number(project, active_prefix)
    min_value = max_used + 1
    can_restart_at_one = bool(use_prefix and active_prefix and max_used == 0)

    if can_restart_at_one:
        hint = (
            f'El prefijo {active_prefix} no tiene contratos registrados. '
            'Puedes reiniciar la numeración desde 1.'
        )
    elif use_prefix and active_prefix:
        if max_used:
            hint = (
                f'Último contrato {active_prefix}-{max_used:03d}. '
                f'El próximo debe ser al menos {min_value}.'
            )
        else:
            hint = 'Define el prefijo para ver la numeración disponible.'
    else:
        if max_used:
            hint = f'Último contrato clásico: {max_used}. El próximo debe ser al menos {min_value}.'
        else:
            hint = 'No hay contratos clásicos. Puedes iniciar desde 1.'

    return {
        'use_prefix': use_prefix,
        'prefix': active_prefix,
        'max_used': max_used,
        'min_value': min_value,
        'can_restart_at_one': can_restart_at_one,
        'hint': hint,
        'preview': contract_preview(use_prefix, active_prefix, min_value if can_restart_at_one else max(min_value, 1)),
    }


def snapshot_contract_counter(counter):
    return {
        'use_prefix': counter_uses_prefix(counter),
        'prefix': normalize_counter_prefix(counter.prefix),
        'storage_prefix': (counter.prefix or '').strip(),
        'next_value': counter.value,
    }


def snapshot_receipt_counter(counter):
    return {
        'next_value': counter.value,
    }


def build_contract_counter_state(project):
    counter = get_or_create_contract_counter(project)
    use_prefix = counter_uses_prefix(counter)
    active_prefix = normalize_counter_prefix(counter.prefix)
    rules = contract_rules_for_prefix(project, use_prefix, active_prefix)
    legacy_max = max_contract_number(project, '')
    locked = prefix_is_locked(project)

    from sales.models import Sales

    last_sale = Sales.objects.filter(project=project).order_by('-add_date', '-id_sale').first()
    last_display = '—'
    if last_sale:
        if last_sale.contract_prefix:
            last_display = f'{last_sale.contract_prefix}-{last_sale.contract_number:03d}'
        else:
            last_display = str(last_sale.contract_number)

    return {
        'counter': counter,
        'use_prefix': use_prefix,
        'prefix': active_prefix,
        'next_value': counter.value,
        'min_value': rules['min_value'],
        'max_used': rules['max_used'],
        'legacy_max': legacy_max,
        'prefixed_count': Sales.objects.filter(project=project).exclude(contract_prefix='').count(),
        'prefix_locked': locked,
        'can_restart_at_one': rules['can_restart_at_one'],
        'rules_hint': rules['hint'],
        'last_display': last_display,
        'preview': contract_preview(use_prefix, active_prefix, counter.value),
    }


def build_receipt_counter_state(project):
    counter = get_or_create_receipt_counter(project)
    max_used = max_receipt_number(project)
    return {
        'counter': counter,
        'next_value': counter.value,
        'min_value': max_used + 1,
        'max_used': max_used,
        'preview': str(counter.value),
    }


def validate_contract_counter_update(project, *, use_prefix, prefix, next_value):
    counter = get_or_create_contract_counter(project)
    errors = []
    locked = prefix_is_locked(project)
    current_use_prefix = counter_uses_prefix(counter)
    current_prefix = normalize_counter_prefix(counter.prefix)

    try:
        next_value = int(next_value)
    except (TypeError, ValueError):
        return ['El consecutivo debe ser un número entero.']

    if next_value < 1:
        errors.append('El consecutivo debe ser mayor o igual a 1.')

    normalized_prefix = ''
    if use_prefix:
        normalized_prefix, prefix_error = validate_prefix_value(prefix)
        if prefix_error:
            errors.append(prefix_error)

    if locked:
        if use_prefix != current_use_prefix:
            errors.append(
                'No se puede cambiar el formato porque ya existen contratos con prefijo en este proyecto.'
            )
        if use_prefix and normalized_prefix != current_prefix:
            errors.append(
                'No se puede cambiar el prefijo porque ya existen contratos numerados con él.'
            )
        active_prefix = current_prefix if current_use_prefix else ''
    else:
        active_prefix = normalized_prefix if use_prefix else ''

    max_used = max_contract_number(project, active_prefix)
    if next_value <= max_used:
        if use_prefix and active_prefix:
            errors.append(
                f'El consecutivo debe ser mayor a {max_used} (último contrato {active_prefix}-{max_used:03d}).'
            )
        else:
            errors.append(
                f'El consecutivo debe ser mayor a {max_used} (último contrato clásico).'
            )

    if errors:
        return errors

    storage_prefix = storage_prefix_for_mode(use_prefix, normalized_prefix)
    rules = contract_rules_for_prefix(project, use_prefix, active_prefix)
    return {
        'counter': counter,
        'storage_prefix': storage_prefix,
        'next_value': next_value,
        'use_prefix': use_prefix,
        'active_prefix': active_prefix,
        'can_restart_at_one': rules['can_restart_at_one'] and next_value == 1,
        'max_used': max_used,
    }


def validate_receipt_counter_update(project, next_value):
    counter = get_or_create_receipt_counter(project)
    errors = []

    try:
        next_value = int(next_value)
    except (TypeError, ValueError):
        return ['El consecutivo debe ser un número entero.']

    if next_value < 1:
        errors.append('El consecutivo debe ser mayor o igual a 1.')

    max_used = max_receipt_number(project)
    if next_value <= max_used:
        errors.append(
            f'El consecutivo debe ser mayor a {max_used} (último recibo emitido).'
        )

    if errors:
        return errors

    return {
        'counter': counter,
        'next_value': next_value,
    }


def describe_contract_counter_change(project, previous, result):
    parts = []

    if not previous['use_prefix'] and result['use_prefix']:
        parts.append('activó prefijo')
    elif previous['use_prefix'] and not result['use_prefix']:
        parts.append('volvió a formato clásico')

    if result['use_prefix'] and previous['prefix'] != result['active_prefix']:
        if previous['prefix']:
            parts.append(f"prefijo {previous['prefix']}→{result['active_prefix']}")
        else:
            parts.append(f"prefijo {result['active_prefix']}")

    if result.get('can_restart_at_one'):
        parts.append('reinicio en 1')

    if previous['next_value'] != result['next_value']:
        parts.append(f"próximo {previous['next_value']}→{result['next_value']}")

    if not parts:
        parts.append('sin cambios')

    message = f"Consecutivos contratos {project.name_to_show}: {', '.join(parts)}."
    return message[:255]


def describe_receipt_counter_change(project, previous, result):
    message = (
        f"Consecutivos recibos {project.name_to_show}: "
        f"próximo {previous['next_value']}→{result['next_value']}."
    )
    return message[:255]
