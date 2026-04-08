from ast import Sub
from faulthandler import disable
from random import choices
import unicodedata

from crispy_forms.bootstrap import (AppendedText, InlineRadios,
                                    PrependedAppendedText, PrependedText,
                                    StrictButton)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django import forms
from django.contrib.auth.models import User
from django.utils.regex_helper import Choice
from django.db.models.query_utils import Q
from finance.models import Collection_feed, CommentType
from mcd_site.crispycustomfields import (dateField, dropdownField, iconField,
                                         inlineField,checkbox)
from mcd_site.models import Bank_entities, Perfil, Projects
from terceros.models import Clients

from sales.models import Comission_position, Properties, Sales, Sales_plans, SalesFiles


class newsaleForm(forms.Form):
    id_first_owner = forms.ModelChoiceField(Clients.objects.exclude(client_document="").order_by('first_name'),
                                            label='Primer titular', required=True)
    id_second_owner = forms.ModelChoiceField(Clients.objects.exclude(client_document="").order_by('first_name'),
                                             label='Segundo titular', required=False)
    id_third_owner = forms.ModelChoiceField(Clients.objects.exclude(client_document="").order_by('first_name'),
                                            label='Tercer titular', required=False)
    id_fourth_owner = forms.ModelChoiceField(Clients.objects.exclude(client_document="").order_by('first_name'),
                                             label='Cuarto titular', required=False)
    id_property = forms.CharField(max_length=255,label='Inmueble')
    sale_value = forms.CharField(max_length=255,label='Valor')
    sale_plan = forms.ModelChoiceField(Sales_plans.objects.filter(status=True),label='Plan')
    type_of_payment = forms.ChoiceField(choices=(
        ('Normal','Normal'),
        ('Extraordinario','Extraordinario')
    ),label='Tipo')
    initial_value = forms.CharField(max_length=255,label='Cuota inicial')
    initial_rate = forms.DecimalField(max_digits=3,label='%',min_value=0)
    to_finance = forms.CharField(max_length=255,label='Saldo')
    rate = forms.FloatField(label='Tasa mv',initial=0)
    to_finance_rate = forms.DecimalField(max_digits=3,label='%',min_value=0)
    quanty_to_finance_quota = forms.IntegerField(label='Cuotas',min_value=1)
    initial_date_to_finance_quota = forms.DateField(label='A partir de')
    value_to_finance_quota = forms.CharField(max_length=255,label='Valor')
    quanty_extra_quota = forms.IntegerField(label='Cantidad',required=False,min_value=1)
    initial_date_extra_quota = forms.DateField(label='Fecha',required=False)
    periodicity_extra_quota = forms.ChoiceField(choices=(
        ('','Selecciona...'),
        (1,'Mensual'),
        (3,'Trimestral'),
        (6,'Semestral'),
        (12,'Anual')
    ),label='Periodo',required=False)
    value_extra_quota = forms.CharField(max_length=255,label='Valor',required=False)
    observations = forms.CharField(widget=forms.Textarea({'rows':2}),
                                   label=False,required=False,max_length=255)
    club = forms.BooleanField(label='Incluye Club Mediterraneo', required = False)
    
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-sale'
        self.helper.form_class = 'ui form'
        self.helper.layout = Layout(
            Div(
                HTML(
                    '''
                    <h4 class="ui horizontal dividing header">
                        <i class="user icon"></i>
                            Propietarios
                    </h4>
                    '''
                ),
                Div(
                    dropdownField('id_first_owner',data_owner='1',css_class='search'),
                    dropdownField('id_second_owner',data_owner='2',css_class='search'),
                    css_class='equal width fields'
                ),   
                Div(
                    dropdownField('id_third_owner',data_owner='3',css_class='search'),
                    dropdownField('id_fourth_owner',data_owner='4',css_class='search'),
                    css_class='equal width fields'
                ),            
                Div(
                    Div(
                        HTML(
                            '''
                            <h4 class="ui dividing header">
                                <i class="mountain icon"></i>
                                <div class="content">
                                    Inmueble
                                </div>
                            </h4>
                            '''
                        ),
                        Div(
                            Field('id_property',css_class='text-center',readonly=True),
                            PrependedText('sale_value','$',css_class='text-center money'),
                            css_class='equal width fields'
                        ),  
                        Div(
                            dropdownField('sale_plan'),
                            dropdownField('type_of_payment'),
                            css_class='equal width fields'
                        ),  
                        css_class='eight wide column'
                    ),
                    Div(
                        HTML(
                            '''
                            <h4 class="ui dividing header">
                                <i class="dollar sign icon"></i>
                                <div class="content">
                                    Forma de pago
                                </div>
                            </h4>
                            '''
                        ),
                        Div(
                            Div(
                                AppendedText('initial_rate','%',css_class='text-center',
                                             min=0,max=100,step=0.1,readonly=True),
                                css_class='six wide field'
                            ),
                            Div(
                                Field('initial_value',css_class='text-center money',readonly=True),
                                css_class='ten wide field'
                            ),
                            css_class='fields'
                        ),  
                        Div(
                            Div(
                                AppendedText('to_finance_rate','%',css_class='text-center',
                                             min=0,max=100,step=0.1,readonly=True),
                                css_class='five wide field'
                            ),
                            Div(
                                AppendedText('rate','%',css_class='text-center',readonly=True),
                                css_class='five wide field'
                            ),
                            Div(
                                Field('to_finance',css_class='text-center money',readonly=True),
                                css_class='six wide field'
                            ),
                            css_class='fields'
                        ),
                        css_class='eight wide column'
                    ),
                    css_class='ui grid'
                ),
                HTML(
                    '''
                    <h4 class="ui dividing header">
                        <i class="hand holding usd icon"></i>
                            Detalle de pagos
                    </h4>
                    '''
                ),
                Div(
                    Div(
                        HTML(
                            '''
                            <h4 class="ui dividing header">
                                <div class="content">
                                    Cuota inicial
                                </div>
                            </h4>
                            '''
                        ),
                        HTML('''
                            <table id="tableCI" class="ui small selected single line table">
                                <thead>
                                    <th class="four wide">Cantidad</th>
                                    <th class="seven wide">Fecha</th>
                                    <th class="five wide">Valor</th>
                                </thead>
                                <tbody></tbody>
                                <tfoot>
                                    <th>
                                        <div class="ui buttons">
                                            <button type="button" id="button-remove-ci" class="ui red icon button">
                                                <i class="minus icon"></i>
                                            </button>
                                            <div class="or" data-text="O"></div>
                                            <button type="button" id="button-add-ci" class="ui positive icon button">
                                                <i class="plus icon"></i>
                                            </button>
                                        </div>
                                    </th>
                                    <th class="right aligned">Total:</th>
                                    <th class="center aligned">$0</th>
                                </tfoot>
                            </table>
                        '''),
                        css_class='eight wide column'
                    ),
                    Div(
                        HTML(
                            '''
                            <h4 class="ui dividing header">
                                <div class="content">
                                    Saldo
                                </div>
                            </h4>
                            '''
                        ),
                        Div(
                            Div(
                                Field('quanty_to_finance_quota',css_class='text-center',disabled=True),
                                css_class='five wide field'
                            ),
                            Div(
                                dateField('initial_date_to_finance_quota',onkeydown="return false;",disabled=True),
                                css_class='five wide field'
                            ),
                            Div(
                                PrependedText('value_to_finance_quota','$',css_class='text-center money',
                                              disabled=True,readonly=True),
                                css_class='six wide field'
                            ),
                            css_class='fields',id='div_regular_quotas'
                        ),
                        HTML(
                            '''
                            <h4 class="ui dividing header">
                                <div class="content">
                                    Extraordinarias
                                </div>
                            </h4>
                            '''
                        ),
                        Div(
                            Div(
                                dropdownField('periodicity_extra_quota',readonly=True,disabled=True),
                                css_class='eight wide field'
                            ),
                            Div(
                                Field('quanty_extra_quota',css_class='text-center',disabled=True),
                                css_class='eight wide field'
                            ),
                            css_class='fields'
                        ),
                        Div(
                            Div(
                                dateField('initial_date_extra_quota',css_class='text-center',disabled=True),
                                css_class='eight wide field'
                            ),
                            Div(
                                PrependedText('value_extra_quota','$',css_class='text-center money',readonly=True,disabled=True),
                                css_class='eight wide field'
                            ),
                            css_class='fields'
                        ),
                        css_class='eight wide column',id='div_saldo'
                    ),
                    css_class='ui grid'
                ),
                HTML(
                    '''
                    <h4 class="ui dividing header">
                        <i class="eye outline icon"></i>
                        <div class="content">
                            Observaciones
                        </div>
                    </h4>
                    '''
                ),
                Field('observations'),
                Div(
                    StrictButton('Crear',type='submit',css_class='ui green circular button'),
                css_class="ui basic center aligned segment"),
            css_class='mt-3'
            )
        )
        

class ComissionPositionForm(forms.ModelForm):
    class Meta:
        model = Comission_position
        fields = [
            'name',
            'group',
            'rate',
            'default',
            'advance_bonus',
            'include_default',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.setdefault('placeholder', 'Nombre del cargo')
        self.fields['rate'].widget.attrs.setdefault('step', '0.01')
        self.fields['rate'].widget.attrs.setdefault('min', '0')
        self.fields['advance_bonus'].widget.attrs.setdefault('min', '0')

    def clean_name(self):
        name = self.cleaned_data.get('name', '')
        return name.strip()

    def clean_advance_bonus(self):
        bonus = self.cleaned_data.get('advance_bonus') or 0
        if bonus < 0:
            raise forms.ValidationError('El bono no puede ser negativo.')
        return bonus

    @staticmethod
    def _normalize_name(value: str) -> str:
        base = unicodedata.normalize('NFKD', value or '')
        base = ''.join(ch for ch in base if not unicodedata.combining(ch))
        base = ''.join(base.split())
        return base.lower()

    def clean(self):
        cleaned = super().clean()
        name = cleaned.get('name')
        project = self.project or self.instance.project
        if name and project:
            normalized = self._normalize_name(name)
            qs = Comission_position.objects.filter(project=project)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            for pos in qs:
                if self._normalize_name(pos.name) == normalized:
                    raise forms.ValidationError({'name': 'Ya existe un cargo con un nombre similar.'})
        return cleaned
class adjudicate_saleForm(forms.Form):
    comission_base = forms.CharField(max_length=255,label='Base de comision')
    collector_user = forms.ModelChoiceField(
        Perfil.objects.filter(rol__descripcion__icontains='gestor de cartera'),
    label='Gestor de cartera')
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-adjudicate'
        self.helper.form_class = 'ui form'
        self.helper.layout = Layout(
            Div(
                PrependedText('comission_base','$',css_class='money text-center'),
                dropdownField('collector_user'),
            ),
        )

class collectionfeed_Form(forms.Form):
    comment_type = forms.ModelChoiceField(
        queryset=CommentType.objects.filter(is_active=True),
        label='Tipo de seguimiento',
        empty_label='Selecciona...',
        to_field_name='id'  # Asegurar que use el ID
    )
    comment = forms.CharField(max_length=500,widget=forms.Textarea({'cols':4,'rows':2}),
                              label='Comentario')
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        # Refrescar queryset en cada instancia
        self.fields['comment_type'].queryset = CommentType.objects.filter(is_active=True)
        
        self.helper = FormHelper()
        self.helper.form_id = 'form-collect-feed'
        self.helper.form_class = 'ui form'
        self.helper.layout = Layout(
            dropdownField('comment_type'),
            Field('comment'),
            Div(
                Submit('registrar','Registrar',css_class='ui green button'),
                css_class='ui right aligned basic segment'
            )
        )

class change_property_Form(forms.Form):
    new_property = forms.ModelChoiceField(
        Properties.objects.filter(state='Libre'), label='Inmueble nuevo'
    )
    
    def __init__(self,*args,**kwargs):
        project = kwargs.pop('project','')
        super().__init__(*args,**kwargs)
        self.fields['new_property'].queryset = Properties.objects.filter(state='Libre',
                                                              project = project)
        self.helper = FormHelper()
        self.helper.form_class = 'ui form'
        self.helper.form_id = 'form-change-prop'
        self.helper.layout = Layout(
            dropdownField('new_property'),
            Submit('cambiar','Cambiar',css_class='fluid ui green button')
        )

class SalesFileForm(forms.ModelForm):
    class Meta:
        model = SalesFiles
        fields = ['description', 'file', 'file_type', 'observations']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'file_type': forms.TextInput(attrs={'class': 'form-control'}),
            'observations': forms.Textarea(attrs={'class': 'form-control'}),
        }

class change_plan_Form(forms.Form):
    
    actual_value = forms.CharField(max_length=255,label='Valor actual')
    actual_capital = forms.CharField(max_length=255,label='Capital actual')
    actual_plan = forms.CharField(max_length=255,label='Plan actual')
    
    type_of_change= forms.ChoiceField(choices=(
        ('credit_value','Valor del credito'),
        ('payment_plan','Plan de pagos'),
        ('all_plan','Forma de pago completa'),
        ('initial','Solo cuota inicial'),
        ('finance','Solo financiacion'),
        #('to_capital_pay','Abono a capital'),
    ),widget=forms.RadioSelect,label=False)
    
    
    new_sale_value = forms.CharField(max_length=255,label='Nuevo valor de venta')
    new_payment_plan = forms.ModelChoiceField(
        Sales_plans.objects.filter(status=True),empty_label='Selecciona...',
        label='Plan de pagos'
    )
    new_capital = forms.CharField(max_length=255,label='Nuevo capital')
    
    ci_to_change = forms.CharField(max_length=255,label='')
    finance_to_change = forms.CharField(max_length=255,label='')
    #to_capital_pay = forms.CharField(max_length=255,label='')
    
    rate = forms.FloatField(label='Tasa mv',initial=0)
    type_of_payment = forms.ChoiceField(choices=(
        ('Normal','Normal'),
        ('Extraordinario','Extraordinario')
    ),label='Tipo')
    quanty_to_finance_quota = forms.IntegerField(label='Cuotas',min_value=0)
    initial_date_to_finance_quota = forms.DateField(label='A partir de')
    value_to_finance_quota = forms.CharField(max_length=255,label='Valor')
    quanty_extra_quota = forms.IntegerField(label='Cantidad',required=False)
    initial_date_extra_quota = forms.DateField(label='Fecha',required=False)
    periodicity_extra_quota = forms.ChoiceField(choices=(
        ('','Selecciona...'),
        (1,'Mensual'),
        (3,'Trimestral'),
        (6,'Semestral'),
        (12,'Anual')
    ),label='Periodo',required=False)
    value_extra_quota = forms.CharField(max_length=255,label='Valor',required=False)
    
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.helper = FormHelper()
        self.helper.form_id ='form-change-plan'
        self.helper.form_class = 'ui form'
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('actual_value',css_class='text-center',readonly=True),
                    Field('actual_capital',css_class='text-center',readonly=True),
                    Field('actual_plan',css_class='text-center',readonly=True),
                    HTML(
                        """
                        <h3 class="ui dividing header">
                            ¿Que deseas modificar?
                        </h3>
                        """
                    ),
                    Field('type_of_change',slider=True),
                    css_class='five wide column'
                ),
                Div(
                    
                    Div(
                        HTML(
                            """
                            <h4 class="ui dividing header">
                                Cambiar valor del credito
                            </h4>
                        """
                        ),
                        Div(
                            Field('new_sale_value',css_class='text-center money',disabled=True),
                            Field('new_capital',css_class='text-center money',readonly=True,disabled=True),
                            css_class='two fields'
                        ),
                        css_class='ui disabled segment',id='div-change-value'
                    ),
                    
                    Div(
                        HTML(
                            """
                            <h4 class="ui dividing header">
                                Cambiar plan de pagos
                            </h4>
                        """
                        ),
                        Div(
                            Div(
                                Div(
                                    dropdownField('new_payment_plan'),
                                    css_class='twelve wide field'
                                ),                              
                                css_class='fields'
                            ),
                        ),
                        css_class='ui disabled segment',id='div-change-payment-plan'
                    ),
                    Div(
                        HTML(
                            """
                            <h4 class="ui dividing header">
                                Cambiar cuota inicial
                            </h4>"""),
                        PrependedText('ci_to_change','Pendiente',
                                    css_class='text-center money',readonly=True),
                        HTML(
                            """<table id="tableCI" class="ui small selected single line table">
                                <thead>
                                    <th class="four wide">Cantidad</th>
                                    <th class="seven wide">Fecha</th>
                                    <th class="five wide">Valor</th>
                                </thead>
                                <tbody></tbody>
                                <tfoot>
                                    <th>
                                        <div class="ui buttons">
                                            <button type="button" id="button-remove-ci" class="ui red icon button">
                                                <i class="minus icon"></i>
                                            </button>
                                            <div class="or" data-text="O"></div>
                                            <button type="button" id="button-add-ci" class="ui positive icon button">
                                                <i class="plus icon"></i>
                                            </button>
                                        </div>
                                    </th>
                                    <th class="right aligned">Total:</th>
                                    <th class="center aligned">$0</th>
                                </tfoot>
                            </table>
                        """
                        ),
                        css_class='ui disabled segment',id='div-change-ci'
                    ),
                    
                    Div(
                        HTML(
                            """
                            <h4 class="ui dividing header">
                                Cambiar financiacion
                            </h4>
                        """
                        ),
                        PrependedText('finance_to_change','Capital por pagar',
                                          css_class='text-center money',readonly=True),
                        Div(
                            Div(
                                dropdownField('type_of_payment',disabled=True),
                                css_class='twelve wide field'
                            ),  
                            Div(
                                AppendedText('rate','%',css_class='text-center',readonly=True),
                                css_class='four wide field'
                            ),  
                            css_class='fields scr'
                        ),
                        Div(
                            Div(
                                Field('quanty_to_finance_quota',css_class='text-center',disabled=True),
                                css_class='three wide field'
                            ),
                            Div(
                                dateField('initial_date_to_finance_quota',onkeypress="return false;",
                                          disabled=True),
                                css_class='seven wide field'
                            ),
                            Div(
                                PrependedText('value_to_finance_quota','$',css_class='text-center money',
                                              readonly=True,disabled=True),
                                css_class='six wide field'
                            ),
                            css_class='fields scr values'
                        ),
                        HTML(
                            '''
                            <h4 class="ui dividing header">
                                <div class="content">
                                    Extraordinarias
                                </div>
                            </h4>
                            '''
                        ),
                        Div(
                            Div(
                                dropdownField('periodicity_extra_quota',readonly=True,disabled=True),
                                css_class='eight wide field'
                            ),
                            Div(
                                Field('quanty_extra_quota',css_class='text-center',disabled=True),
                                css_class='eight wide field'
                            ),
                            css_class='fields sce'
                        ),
                        Div(
                            Div(
                                dateField('initial_date_extra_quota',css_class='text-center',disabled=True),
                                css_class='eight wide field'
                            ),
                            Div(
                                PrependedText('value_extra_quota','$',css_class='text-center money',readonly=True,disabled=True),
                                css_class='eight wide field'
                            ),
                            css_class='fields sce'
                        ),
                        css_class='ui disabled segment',id='div-change-finance'
                    ),
                    Div(
                        Submit('btnchangeplan','Cambiar plan',css_class='ui green disabled button'),
                        css_class='ui basic right aligned segment'
                    ),
                    css_class='eleven wide column'
                ),
                css_class='ui grid'
            )
            
        )

class SalesPlanForm(forms.ModelForm):
    class Meta:
        model = Sales_plans
        fields = ['name', 'initial_payment', 'to_finance', 'rate', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'ui input'}),
            'initial_payment': forms.NumberInput(attrs={'class': 'ui input'}),
            'to_finance': forms.NumberInput(attrs={'class': 'ui input'}),
            'rate': forms.NumberInput(attrs={'class': 'ui input'}),
            'status': forms.CheckboxInput(attrs={'class': 'ui checkbox'}),
        }
