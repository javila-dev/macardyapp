from unicodedata import name
from django import template
from decimal import Decimal
from mcd_site.utils import countries_data
from sales.contract_utils import formatted_contract_label, formatted_contract_number

register = template.Library()


@register.filter
def contract_display(sale):
    if sale is None:
        return ''
    return formatted_contract_number(sale)


@register.filter
def contract_label(sale):
    if sale is None:
        return ''
    return formatted_contract_label(sale)

@register.filter
def is_blank(value):
    if value == '':
        return True
    
    return False

@register.filter
def countries(code,type_of):
    if type_of == 'country':
        name = countries_data().country(code)
        
    elif type_of == 'state':
        name = countries_data().state(code)
        
        
    elif type_of == 'city':
        name = countries_data().city(code)
    
    else:
        name = None
    
    return name