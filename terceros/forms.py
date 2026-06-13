from django import forms
from terceros.models import Clients, Sellers
from mcd_site.models import Bank_entities, Projects
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Field, HTML, Button
from crispy_forms.bootstrap import AppendedText, PrependedAppendedText, PrependedText, StrictButton
from mcd_site.crispycustomfields import checkbox, dropdownField, inlineField, dateField
from django.conf import settings
import json
from mcd_site.utils import countries_data, parse_semantic_date


class nuevo_cliente_form(forms.Form):
    IDENTIFICATION_TYPES = (
        ('CC', 'Cédula de Ciudadanía'),
        ('TI', 'Tarjeta de Identidad'),
        ('RC', 'Registro Civil de nacimiento'),
        ('CE', 'Cédula de Extranjería'),
        ('P', 'Pasaporte'),
    )

    # Campos básicos existentes
    identification_type = forms.ChoiceField(
        choices=IDENTIFICATION_TYPES, label='Tipo de Identificación', initial='CC'
    )
    client_document = forms.CharField(max_length=255, label='Documento de identificación')
    first_name = forms.CharField(max_length=255, label=False)
    last_name = forms.CharField(max_length=255, label=False)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15, label=False)
    phone_office = forms.CharField(max_length=255, label=False, required=False)
    phone_house = forms.CharField(max_length=255, label=False, required=False)
    address = forms.CharField(max_length=255, label=False)
    office_address = forms.CharField(max_length=255, label='Diireccion Oficina', required=False)
    birth_date = forms.DateField(label='Fecha de nacimiento')
    marital_status = forms.ChoiceField(choices=(
        ('', 'Selecciona...'),
        ('Soltero(a)', 'Soltero(a)'),
        ('Casado(a)', 'Casado(a)'),
        ('Union Libre', 'Union Libre')
    ), label='Estado Civil')
    city = forms.ChoiceField(choices=[], label='Ciudad', required=False)
    state = forms.ChoiceField(choices=[], label='Estado', required=False)
    country = forms.ChoiceField(choices=[], label='País', required=False)
    seller = forms.ModelChoiceField(Sellers.objects.filter(seller_state='Activo'), label='Captador por', required=False,
                                    empty_label='Selecciona...')

    # Nuevos campos de información laboral
    company_name = forms.CharField(max_length=255, label='Empresa donde labora', required=False)
    position = forms.CharField(max_length=255, label='Cargo', required=False)
    profession = forms.CharField(max_length=255, label='Profesión', required=False)
    occupation = forms.CharField(max_length=255, label='Ocupación', required=False)
    monthly_salary = forms.DecimalField(max_digits=15, decimal_places=2, label='Salario/Ingresos Mensuales', required=False)
    years_experience = forms.IntegerField(label='Antigüedad (años)', required=False, min_value=0)
    company_city = forms.CharField(max_length=255, label='Ciudad empresa', required=False)
    company_address = forms.CharField(max_length=500, label='Dirección empresa', required=False)
    company_phone = forms.CharField(max_length=20, label='Teléfono empresa', required=False)
    social_organizations = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), 
                                         label='Entidades sociales, Deportivas, Culturales o Agremiaciones', 
                                         required=False)

    # Referencias familiares
    ref_familiar_1_name = forms.CharField(max_length=255, label='Nombre', required=True)
    ref_familiar_1_occupation = forms.CharField(max_length=255, label='Ocupación', required=True)
    ref_familiar_1_phone = forms.CharField(max_length=20, label='Teléfono', required=True)
    
    ref_familiar_2_name = forms.CharField(max_length=255, label='Nombre', required=True)
    ref_familiar_2_occupation = forms.CharField(max_length=255, label='Ocupación', required=True)
    ref_familiar_2_phone = forms.CharField(max_length=20, label='Teléfono', required=True)

    # Referencias personales
    ref_personal_1_name = forms.CharField(max_length=255, label='Nombre', required=True)
    ref_personal_1_occupation = forms.CharField(max_length=255, label='Ocupación', required=True)
    ref_personal_1_phone = forms.CharField(max_length=20, label='Teléfono', required=True)
    
    ref_personal_2_name = forms.CharField(max_length=255, label='Nombre', required=True)
    ref_personal_2_occupation = forms.CharField(max_length=255, label='Ocupación', required=True)
    ref_personal_2_phone = forms.CharField(max_length=20, label='Teléfono', required=True)

    # Nuevos campos solicitados
    neighborhood = forms.CharField(max_length=255, label=False, required=False)
    birth_place = forms.CharField(max_length=255, label='Lugar de nacimiento', required=False)
    lives_in_own_house = forms.BooleanField(label='Vive en casa propia', required=False)

    def __init__(self, *args, **kwargs):
        valid_countries = kwargs.pop('valid_countries', [])
        valid_states = kwargs.pop('valid_states', [])
        valid_cities = kwargs.pop('valid_cities', [])

        super().__init__(*args, **kwargs)

        self.fields['country'].choices = [('', 'Selecciona...')] + valid_countries
        self.fields['state'].choices = [('', 'Selecciona...')] + valid_states
        self.fields['city'].choices = [('', 'Selecciona...')] + valid_cities

        self.helper = FormHelper()
        self.helper.form_id = 'public-client-form'
        self.helper.form_class = 'ui form'
        self.helper.layout = Layout(
            Div(
                # Información básica
                Div(
                    Div(
                        dropdownField('identification_type', css_class='search clearable selection'),
                        Field('client_document'),
                        dropdownField('seller', css_class='search clearable selection'),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    HTML('<label>Nombre</label>'),
                    Div(
                        Field('first_name', placeholder='Nombre(s)'),
                        Field('last_name', placeholder='Apellidos'),
                        css_class='two fields'
                    ),
                    css_class='required field'
                ),
                Div(
                    Div(
                        Div(
                            HTML('<label>Teléfono(s)</label>'),
                            Div(
                                Field('phone', placeholder='Celular'),
                                Field('phone_office', placeholder='Teléfono casa'),
                                Field('phone_house', placeholder='Teléfono oficina'),
                                css_class='three fields'
                            ),
                            css_class='required field'
                        ),
                        Field('email'),
                        dropdownField('marital_status'),
                        css_class='one field'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        Field('birth_place', placeholder='Ciudad/País de nacimiento'),
                        dateField('birth_date', onkeypress="return false;"),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                
                Div(
                    Div(
                        dropdownField('country', css_class='search'),
                        dropdownField('state', css_class='search'),
                        dropdownField('city', css_class='search'),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    HTML('<label>Dirección</label>'),
                    Div(
                        Field('address', placeholder='Residencia'),                        
                        Field('neighborhood', placeholder='Barrio de residencia'),
                        css_class='two fields'
                    ),
                    css_class='required field'
                ),
                Div(
                    checkbox('lives_in_own_house', slider=True),
                    Field('office_address', placeholder='Oficina'),
                    css_class='two fields'
                ),
                
                
                # Información laboral
                HTML('<h4 class="ui dividing header"><i class="briefcase icon"></i>Información Laboral del Solicitante</h4>'),
                Div(
                    Div(
                        Field('company_name', placeholder='Nombre de la empresa'),
                        Field('position', placeholder='Cargo que desempeña'),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        Field('profession', placeholder='Profesión'),
                        Field('occupation', placeholder='Ocupación'),
                        PrependedText('monthly_salary', '$', placeholder='0.00'),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        Field('years_experience', placeholder='Años'),
                        Field('company_city', placeholder='Ciudad'),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        Field('company_address', placeholder='Dirección de la empresa'),
                        Field('company_phone', placeholder='Teléfono de la empresa'),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Field('social_organizations', placeholder='Mencione las entidades sociales, Deportivas, Culturales o Agremiaciones a las que pertenece'),
                
                # Referencias familiares
                HTML('<h4 class="ui dividing header"><i class="users icon"></i>Referencias Familiares</h4>'),
                HTML('<div class="ui info message"><p><strong>Referencia 1:</strong></p></div>'),
                Div(
                    Div(
                        Field('ref_familiar_1_name', placeholder='Nombre completo'),
                        Field('ref_familiar_1_occupation', placeholder='Ocupación'),
                        Field('ref_familiar_1_phone', placeholder='Teléfono'),
                        css_class='three fields'
                    ),
                    css_class='required field'  # Añadido required field
                ),
                HTML('<div class="ui info message"><p><strong>Referencia 2:</strong></p></div>'),
                Div(
                    Div(
                        Field('ref_familiar_2_name', placeholder='Nombre completo'),
                        Field('ref_familiar_2_occupation', placeholder='Ocupación'),
                        Field('ref_familiar_2_phone', placeholder='Teléfono'),
                        css_class='three fields'
                    ),
                    css_class='required field'  # Añadido required field
                ),
                
                # Referencias personales
                HTML('<h4 class="ui dividing header"><i class="user friends icon"></i>Referencias Personales</h4>'),
                HTML('<div class="ui info message"><p><strong>Referencia 1:</strong></p></div>'),
                Div(
                    Div(
                        Field('ref_personal_1_name', placeholder='Nombre completo'),
                        Field('ref_personal_1_occupation', placeholder='Ocupación'),
                        Field('ref_personal_1_phone', placeholder='Teléfono'),
                        css_class='three fields'
                    ),
                    css_class='required field'  # Añadido required field
                ),
                HTML('<div class="ui info message"><p><strong>Referencia 2:</strong></p></div>'),
                Div(
                    Div(
                        Field('ref_personal_2_name', placeholder='Nombre completo'),
                        Field('ref_personal_2_occupation', placeholder='Ocupación'),
                        Field('ref_personal_2_phone', placeholder='Teléfono'),
                        css_class='three fields'
                    ),
                    css_class='required field'  # Añadido required field
                ),
                
                Div(
                    Submit('sbmt', 'Registrar Cliente', css_class='ui right green large button'),
                    css_class='ui right aligned container fluid'
                ),
                css_class='ui form'
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['country'] = self.data.get('country')
        cleaned_data['state'] = self.data.get('state')
        cleaned_data['city'] = self.data.get('city')
        return cleaned_data

class gestores_form(forms.Form):
    seller_document = forms.CharField(max_length=255,label='Documento de identificación')
    seller_first_name = forms.CharField(max_length=255,label=False)
    seller_last_name = forms.CharField(max_length=255,label=False)
    seller_email = forms.EmailField(label='Email')
    seller_phone = forms.CharField(max_length=15,label='Telefono')
    seller_address = forms.CharField(max_length=255,label='Direccion')
    seller_birth_date = forms.DateField(label='Fecha de nacimiento')
    seller_marital_status = forms.ChoiceField(choices = (
        ('','Selecciona...'),
        ('Soltero(a)','Soltero(a)'),
        ('Casado(a)','Casado(a)'),
        ('Union Libre','Union Libre')
    ), label='Estado Civil')
    seller_city = forms.ChoiceField(choices=(
        ('','Selecciona...'),),label='Ciudad')
    seller_state = forms.ChoiceField(choices=( ('','Selecciona...'),),label='Estado')
    seller_country = forms.ChoiceField(choices=( ('','Selecciona...'),),label='Pais')
    cv_support = forms.FileField(label = 'Hoja de vida',help_text='Carga un archivo PDF de maximo 10 MB')
    rut_support = forms.FileField(label = 'RUT',help_text='Carga un archivo PDF de maximo 10 MB')
    bank_certificate = forms.FileField(label = 'Certificado Bancario',help_text='Carga un archivo PDF de maximo 10 MB')
    bank_entity = forms.ModelChoiceField(Bank_entities.objects.all(),label='Banco')
    account_type = forms.ChoiceField(choices=(
        ('S', 'Ahorros'), ('D', 'Corriente')
        ),label = 'Tipo de cuenta')
    bank_account_number = forms.IntegerField(label='Numero de cuenta')
    retencion = forms.FloatField(initial=10)
    projects = forms.ModelChoiceField(Projects.objects.all(),label='Proyecto(s)',required=True)
    pay_pmt = forms.BooleanField(label='Aplica PMT',required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-registro-gestor'
        self.helper.layout = Layout(
            Div(
               Div(
                   Div(
                        inlineField('seller_document'),
                    ),
                    css_class='field'
                ),
                Div(
                    HTML('<label>Nombre</label>'),
                    Div(
                        Field('seller_first_name',placeholder='Nombre'),
                        Field('seller_last_name',placeholder='Apellidos'),
                        css_class='two fields'
                    ),
                    css_class='required field'
                ),
                Div(
                    Div(
                        Field('seller_phone'),
                        Field('seller_email'),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        dropdownField('seller_marital_status'),
                        dateField('seller_birth_date',onkeypress="return false;"),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        dropdownField('seller_country',css_class='search'),
                        dropdownField('seller_state',css_class='search'),
                        dropdownField('seller_city',css_class='search'),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Field('seller_address'),
                Div(
                    Div(
                        dropdownField('bank_entity',css_class='search'),
                        dropdownField('account_type',css_class=''),
                        Field('bank_account_number',css_class=''),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        Field('cv_support',css_class='',accept="application/pdf"),
                        Field('rut_support',css_class='',accept="application/pdf"),
                        Field('bank_certificate',css_class='',accept="application/pdf"),
                        css_class='three fields'
                    ),
                    css_class='ui segment'
                ),
               Div(
                    dropdownField('projects',multiple=""),
                    Field('retencion',css_class='text-center'),
                    checkbox('pay_pmt',slider=True),
                    css_class='fields'
                ),
                Div(
                    Submit('sbmt','Registrar',css_class='ui right button'),
                css_class='ui right aligned container fluid'),
                css_class='ui form'
            )
            
        )
    
class collaborators_form(forms.Form):
    col_document = forms.CharField(
        max_length=255, label='Documento de identificación', required=True)
    col_first_name = forms.CharField(max_length=255, label=False, required=True)
    col_last_name = forms.CharField(max_length=255, label=False, required=True)
    col_email = forms.EmailField(label='Email', required=False)
    col_phone = forms.CharField(max_length=15, label='Telefono', required=False)
    col_address = forms.CharField(max_length=255, label='Direccion', required=False)
    col_birth_date = forms.CharField(label='Fecha de nacimiento', required=True)
    city = forms.ChoiceField(
        choices=(('', 'Selecciona...'),), label='Ciudad', required=False)
    state = forms.ChoiceField(
        choices=(('', 'Selecciona...'),), label='Estado', required=False)
    country = forms.ChoiceField(
        choices=(('', 'Selecciona...'),), label='Pais', required=False)
    scholarity = forms.ChoiceField(label='Escolaridad', required=True, choices=(
        ('Sin estudios', 'Sin estudios'),  ('Primaria', 'Primaria'),
        ('Bachillerato', 'Bachillerato'),  ('Tecnico', 'Tecnico'),
         ('Tecnologo', 'Tecnologo'), ('Pregrado', 'Pregrado'),
        ('Postgrado', 'Postgrado'), ('Maestria', 'Maestria')
    ))
    cv_support = forms.FileField(
        label='Hoja de vida',
        help_text='Carga un archivo PDF de maximo 10 MB',
        required=True,
    )
    contract_support = forms.FileField(
        label='Contrato',
        help_text='Carga un archivo PDF de maximo 10 MB',
        required=True,
    )
    bank_certificate = forms.FileField(
        label='Certificado Bancario',
        help_text='Carga un archivo PDF de maximo 10 MB',
        required=True,
    )
    bank_entity = forms.ModelChoiceField(
        Bank_entities.objects.all(), label='Banco', required=True)
    account_type = forms.ChoiceField(choices=(
        ('S', 'Ahorros'), ('D', 'Corriente')
        ), label='Tipo de cuenta', required=True)
    bank_account_number = forms.CharField(
        max_length=255, label='Numero de cuenta', required=False)
    type_of_contract = forms.ChoiceField(label='Tipo de contrato', required=True, choices=(
        ('Fijo','Fijo'),
        ('Obra labor','Obra labor'),
        ('Indefinido','Indefinido'),
        ('Prestación de servicios','Prestación de servicios'),
    ))
    initial_date = forms.CharField(label='Fecha de inicio', required=True)
    duration = forms.IntegerField(
        label='Duración (en meses)', required=False, min_value=1)
    salary = forms.CharField(max_length=255, label='Salario', required=True)
    position_name = forms.CharField(max_length=255, label='Cargo', required=True)
    
    file = open(settings.STATIC_ROOT /'json/ss_entities.json',encoding="utf8")
    json_file = json.loads(file.read().encode().decode('utf-8-sig'))
    
    eps_choices = [('','Selecciona...')]
    pension_choices = [('','Selecciona...')]
    cesantias_choices = [('','Selecciona...')]
    
    for entity in json_file['eps']:
        eps_choices.append((entity.get('id'),entity.get('name')))
    for entity in json_file['pension']:
        pension_choices.append((entity.get('id'),entity.get('name')))
    for entity in json_file['cesantias']:
        cesantias_choices.append((entity.get('id'),entity.get('name')))  
        
    eps = forms.ChoiceField(choices=eps_choices, required=False, label='EPS')
    pension = forms.ChoiceField(choices=pension_choices, required=False, label='Pensión')
    cesantias = forms.ChoiceField(choices=cesantias_choices, required=False, label='Cesantías')

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop('is_create', True)
        super().__init__(*args, **kwargs)

        if not self.is_create:
            for field_name in ('cv_support', 'contract_support', 'bank_certificate'):
                self.fields[field_name].required = False

        self.helper = FormHelper()
        self.helper.form_id = 'form-collaborator'
        self.helper.form_class = 'ui form'
        file_segment_class = 'ui segment required' if self.is_create else 'ui segment'
        self.helper.layout = Layout(
            HTML(
                '<p class="ui tiny message">'
                'Los campos marcados con <strong>*</strong> son obligatorios.'
                '</p>'
            ),
            Div(
               Div(
                   Div(
                        inlineField('col_document'),
                    ),
                    css_class='field'
                ),
                Div(
                    HTML('<label>Nombre <span style="color:#db2828">*</span></label>'),
                    Div(
                        Field('col_first_name',placeholder='Nombre'),
                        Field('col_last_name',placeholder='Apellidos'),
                        css_class='two fields required'
                    ),
                    css_class='required field'
                ),
                Div(
                    Div(
                        Field('col_phone'),
                        Field('col_email'),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        dropdownField('scholarity'),
                        dateField('col_birth_date',onkeypress="return false;"),
                        css_class='two fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        dropdownField('country',css_class='search'),
                        dropdownField('state',css_class='search'),
                        dropdownField('city',css_class='search'),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Field('col_address'),
                    css_class='field'
                ),
                Div(
                    Div(
                        dropdownField('bank_entity',css_class='search'),
                        dropdownField('account_type',css_class=''),
                        Field('bank_account_number',css_class=''),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    Div(
                        dropdownField('eps',css_class='search'),
                        dropdownField('pension',css_class='search'),
                        dropdownField('cesantias',css_class='search'),
                        css_class='three fields'
                    ),
                    css_class='field'
                ),
                Div(
                    HTML('<h4 class="ui dividing header">Información de contrato</h4>'),
                    Div(
                        Field('position_name'),
                        css_class='required field'
                    ),
                    Div(
                        dropdownField('type_of_contract'),
                        PrependedText('salary','$',css_class='money text-center'),
                            css_class='two fields',
                    ),
                    Div(
                        dateField('initial_date',onkeypress="return false;"),
                        Field('duration',css_class='text-center',min=1),
                            css_class='two fields',
                    ),id='div-contract'
                ),
                Div(
                    Div(
                        Field('cv_support',css_class='',accept="application/pdf"),
                        Field('contract_support',css_class='',accept="application/pdf"),
                        Field('bank_certificate',css_class='',accept="application/pdf"),
                        css_class='three fields'
                    ),
                    css_class=file_segment_class,id='file-segment'
                ),
                Div(
                    Submit('sbmt','Registrar',css_class='ui right green button'),
                css_class='ui right aligned container fluid'),
                css_class='ui form'
            )
            
        )

    def _parse_semantic_date(self, value, required=False):
        if value in (None, ''):
            if required:
                raise forms.ValidationError('Este campo es obligatorio.')
            return None
        try:
            return parse_semantic_date(value, 'date').date()
        except (ValueError, TypeError):
            raise forms.ValidationError('Ingresa una fecha válida.')

    def clean_col_birth_date(self):
        return self._parse_semantic_date(
            self.cleaned_data.get('col_birth_date'), required=True)

    def clean_initial_date(self):
        return self._parse_semantic_date(
            self.cleaned_data.get('initial_date'), required=True)

    def clean_salary(self):
        value = self.cleaned_data.get('salary', '')
        if value in (None, ''):
            raise forms.ValidationError('Este campo es obligatorio.')
        try:
            return int(str(value).replace(',', ''))
        except ValueError:
            raise forms.ValidationError('Ingresa un salario válido.')

    def clean_bank_account_number(self):
        value = self.cleaned_data.get('bank_account_number')
        if value in (None, ''):
            return None
        return str(value)

    def clean_city(self):
        return self._optional_choice_int(self.cleaned_data.get('city'))

    def clean_state(self):
        return self._optional_choice_int(self.cleaned_data.get('state'))

    def clean_country(self):
        return self._optional_choice_int(self.cleaned_data.get('country'))

    def clean_eps(self):
        return self._optional_choice_int(self.cleaned_data.get('eps'))

    def clean_pension(self):
        return self._optional_choice_int(self.cleaned_data.get('pension'))

    def clean_cesantias(self):
        return self._optional_choice_int(self.cleaned_data.get('cesantias'))

    @staticmethod
    def _optional_choice_int(value):
        if value in (None, ''):
            return None
        return int(value)

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        if cleaned_data.get('type_of_contract') != 'Indefinido':
            duration = cleaned_data.get('duration')
            if duration in (None, ''):
                self.add_error(
                    'duration',
                    'La duración es obligatoria para contratos que no son indefinidos.'
                )
        else:
            cleaned_data['duration'] = None

        return cleaned_data

class collab_react(forms.Form):
    type_of_contract_react = forms.ChoiceField(label='Tipo de contrato', required=True, choices=(
        ('Fijo','Fijo'),
        ('Obra labor','Obra labor'),
        ('Indefinido','Indefinido'),
        ('Prestación de servicios','Prestación de servicios'),
    ))
    initial_date_react = forms.CharField(label='Fecha de inicio', required=True)
    duration_react = forms.IntegerField(
        label='Duración (en meses)', required=False, min_value=1)
    salary_react = forms.CharField(max_length=255, label='Salario', required=True)
    position_name_react = forms.CharField(max_length=255, label='Cargo', required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'form-reactivate'
        self.helper.form_class = 'ui form'
        self.helper.layout = Layout(
            HTML(
                '<p class="ui tiny message">'
                'Los campos marcados con <strong>*</strong> son obligatorios.'
                '</p>'
            ),
            Div(
                Div(
                    Div(
                        Field('position_name_react'),
                        css_class='required field'
                    ),
                    Div(
                        dropdownField('type_of_contract_react'),
                        dateField('initial_date_react',onkeypress="return false;"),
                            css_class='two fields',
                    ),
                    Div(
                        Field('duration_react',css_class='text-center',min=1),
                        PrependedText('salary_react','$',css_class='money text-center'),
                            css_class='two fields',
                    ),
                ),
                Div(
                    
                Submit('reactivate','Reactivar',css_class='ui green button'),
                    css_class='ui basic right aligned segment'
                )
            )
        )

    def clean_initial_date_react(self):
        value = self.cleaned_data.get('initial_date_react')
        if not value:
            raise forms.ValidationError('Este campo es obligatorio.')
        try:
            return parse_semantic_date(value, 'date')
        except (ValueError, TypeError):
            raise forms.ValidationError('Ingresa una fecha válida.')

    def clean_salary_react(self):
        value = self.cleaned_data.get('salary_react', '')
        if value in (None, ''):
            raise forms.ValidationError('Este campo es obligatorio.')
        try:
            return int(str(value).replace(',', ''))
        except ValueError:
            raise forms.ValidationError('Ingresa un salario válido.')

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        if cleaned_data.get('type_of_contract_react') != 'Indefinido':
            if cleaned_data.get('duration_react') in (None, ''):
                self.add_error(
                    'duration_react',
                    'La duración es obligatoria para contratos que no son indefinidos.'
                )
        else:
            cleaned_data['duration_react'] = None

        return cleaned_data
