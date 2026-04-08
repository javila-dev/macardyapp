from django import template
from decimal import Decimal
from mcd_site.utils import numbers_names

register = template.Library()

@register.filter
def format_number(number,type="int"):
    if number == "" or number is None:
        return 0
    try:
        if type == 'int': number = int(number)
        elif type == 'float': number = float(number)
        elif type == 'decimal': number = Decimal(number)
        formated_value = f'{number:,}'
    except ValueError:
        formated_value = f'{number:,}'
    except:
        formated_value = number
    
    return formated_value

@register.filter
def numbers_to_letters(number):
    return numbers_names(number)

@register.filter
def decima_to_float(number):
    return float(number)

@register.filter
def to_int_list(start, end):
    return range(start, end + 1)

@register.filter
def rango(value, arg):
    """Uso: {{ 1|rango:12 }} → genera range(1, 13)"""
    return range(int(value), int(arg) + 1)

@register.filter
def has_perm(user_profile, perm):
    return user_profile.has_permission(perm)

@register.filter
def comma_to_point(value):
    print(type(value))
    try:
        return str(value).replace(',', '.')
    except:
        return ''