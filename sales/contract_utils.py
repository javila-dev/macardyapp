import re

LEGACY_COUNTER_PREFIXES = frozenset({'', 'CTR'})


def normalize_counter_prefix(prefix):
    value = (prefix or '').strip().upper()
    if value in LEGACY_COUNTER_PREFIXES:
        return ''
    return value


def formatted_contract_number(sale):
    prefix = (sale.contract_prefix or '').strip()
    if prefix:
        return f'{prefix}-{sale.contract_number:03d}'
    return str(sale.contract_number)


def formatted_contract_label(sale):
    prefix = (sale.contract_prefix or '').strip()
    if prefix:
        return formatted_contract_number(sale)
    return f'CTR{sale.contract_number}'


def quota_contract_suffix(sale):
    prefix = (sale.contract_prefix or '').strip()
    if prefix:
        return f'{prefix}{sale.contract_number:03d}'
    return str(sale.contract_number)


def build_id_quota(quota_type, sequence, sale):
    return f'{quota_type}{sequence}CTR{quota_contract_suffix(sale)}'


def parse_contract_identifier(value):
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    prefixed = re.match(r'^([A-Za-z]+)-(\d+)$', text)
    if prefixed:
        return prefixed.group(1).upper(), int(prefixed.group(2))

    if text.isdigit():
        return '', int(text)

    return None


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


def resolve_sale(project, identifier, *, project_field='name'):
    from sales.models import Sales

    if identifier is None or str(identifier).strip() == '':
        raise Sales.DoesNotExist

    text = str(identifier).strip()
    lookup = {f'project__{project_field}': project}

    if text.isdigit():
        pk = int(text)
        try:
            return Sales.objects.get(pk=pk, **lookup)
        except Sales.DoesNotExist:
            pass

    parsed = parse_contract_identifier(text)
    if parsed is not None:
        prefix, number = parsed
        return Sales.objects.get(
            contract_prefix=prefix,
            contract_number=number,
            **lookup,
        )

    raise Sales.DoesNotExist
