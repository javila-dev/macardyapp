import re

LEGACY_COUNTER_PREFIXES = frozenset({'', 'CTR'})


def normalize_counter_prefix(prefix):
    value = (prefix or '').strip().upper()
    if value in LEGACY_COUNTER_PREFIXES:
        return ''
    return value


def parse_contract_identifier(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    prefixed = re.match(r'^([A-Za-z]+)-(\d+)$', text)
    if prefixed:
        return prefixed.group(1).upper(), int(prefixed.group(2))

    ctr_legacy = re.match(r'^CTR(\d+)$', text, re.IGNORECASE)
    if ctr_legacy:
        return '', int(ctr_legacy.group(1))

    if text.isdigit():
        return '', int(text)

    return None


def _contract_parts(value):
    if value is None:
        return None, None

    if isinstance(value, (str, int)):
        parsed = parse_contract_identifier(value)
        if parsed is None:
            return None, None
        return parsed

    prefix = (getattr(value, 'contract_prefix', '') or '').strip()
    number = getattr(value, 'contract_number', None)
    if number is None:
        return None, None
    return prefix, number


def formatted_contract_number(sale):
    prefix, number = _contract_parts(sale)
    if number is None:
        return '' if sale is None else str(sale).strip()
    if prefix:
        return f'{prefix}-{int(number):03d}'
    return str(int(number))


def formatted_contract_label(sale):
    prefix, number = _contract_parts(sale)
    if number is None:
        return '' if sale is None else str(sale).strip()
    if prefix:
        return formatted_contract_number(sale)
    return f'CTR{int(number)}'


def quota_contract_suffix(sale):
    prefix, number = _contract_parts(sale)
    if number is None:
        return '' if sale is None else str(sale).strip()
    if prefix:
        return f'{prefix}{int(number):03d}'
    return str(int(number))


def build_id_quota(quota_type, sequence, sale):
    return f'{quota_type}{sequence}CTR{quota_contract_suffix(sale)}'


def parse_quota_id(id_quota):
    match = re.match(r'^([A-Z]+)(\d+)CTR(.+)$', str(id_quota or '').strip())
    if not match:
        return None
    return {
        'prefix': match.group(1),
        'sequence': int(match.group(2)),
        'contract_suffix': f'CTR{match.group(3)}',
    }


def quota_display_sequence(id_quota):
    parsed = parse_quota_id(id_quota)
    if parsed:
        return str(parsed['sequence'])
    return str(id_quota or '')


def contract_filename_slug(sale):
    return formatted_contract_label(sale).replace('-', '_').replace('ñ', 'n')


def filter_sales_by_contract(qs, identifier, lookup_prefix=''):
    parsed = parse_contract_identifier(identifier)
    if parsed is None:
        return qs.none()
    contract_prefix, contract_number = parsed
    return qs.filter(**{
        f'{lookup_prefix}contract_prefix': contract_prefix,
        f'{lookup_prefix}contract_number': contract_number,
    })


def resolve_sale_by_pk(project, sale_id, *, project_field='name'):
    from sales.models import Sales

    lookup = {f'project__{project_field}': project}
    return Sales.objects.get(pk=int(sale_id), **lookup)


def resolve_sale(project, identifier, *, project_field='name'):
    """Resolve a sale from a contract label entered by users (350, CTR350, M-001)."""
    from sales.models import Sales

    if identifier is None or str(identifier).strip() == '':
        raise Sales.DoesNotExist

    text = str(identifier).strip()
    lookup = {f'project__{project_field}': project}

    parsed = parse_contract_identifier(text)
    if parsed is not None:
        prefix, number = parsed
        return Sales.objects.get(
            contract_prefix=prefix,
            contract_number=number,
            **lookup,
        )

    raise Sales.DoesNotExist
