from datetime import datetime, date
from django import forms
import locale
from django.db.models.query_utils import Q
from django.utils.regex_helper import Choice
from django.forms import DateInput
from finance.models import Payment_methods, SolicitudRecibo, cost_center
from mcd_site.utils import parse_semantic_date
from terceros.models import Clients
from mcd_site.models import Bank_entities, Projects
from sales.models import Sales, Sales_plans
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Div, Field, HTML
from crispy_forms.bootstrap import AppendedText, PrependedAppendedText, PrependedText, StrictButton, InlineRadios
from mcd_site.crispycustomfields import checkbox, dropdownField, inlineField, dateField, iconField

locale.setlocale(locale.LC_ALL,'es_CO.UTF-8')

class new_sale_income_form(forms.Form):
    sale = forms.ModelChoiceField(
        Sales.objects.filter(Q(status='Pendiente')|Q(status='Aprobado')),
        label='Cliente',required=True)
    payment_date = forms.DateField(label='Fecha de pago')
    
    today = datetime.today()
    dt_today = datetime.strftime(today, '%B %d, %Y')
    add_date = forms.DateField(label='Fecha de registro',initial=dt_today)
    receipt_number = forms.CharField(max_length=255,label='Recibo')
    payment_method_1 = forms.ModelChoiceField(
        Payment_methods.objects.exclude(name='Anulaciones'),
        label='Forma de pago 1',empty_label='Selecciona...'
    )
    value_1 = forms.CharField(max_length=255,label='Valor')
    payment_method_2 = forms.ModelChoiceField(
        Payment_methods.objects.exclude(name='Anulaciones'),
        label='Forma de pago 2',empty_label='Selecciona...',
        required=False
    )
    value_2 = forms.CharField(max_length=255,label='Valor',
                              required=False)
    description = forms.CharField(max_length=255,label='Descripción',widget=
                                  forms.Textarea({'rows':2}))
    
    def __init__(self,*args,**kwargs):
        project = kwargs.pop('project')
        super().__init__(*args,**kwargs)
        if project:
            self.fields['sale'].queryset = Sales.objects.filter(
                Q(status='Pendiente')|Q(status='Aprobado'),
                project=project
            )
        self.helper = FormHelper()
        self.helper.form_id = 'form_new_sale_income'
        self.helper.form_class = 'ui form mb-3'
        self.helper.layout = Layout(
            Div(
                Div(
                    dropdownField('sale'),
                    css_class='eight wide field'
                ),
                Div(
                    dateField('add_date'),
                    css_class='four wide right field'
                ),
                Div(
                    dateField('payment_date'),
                    css_class='four wide right field'
                ),
                css_class='fields'
            ),
            Div(
                Div(
                    dropdownField('payment_method_1', css_class='clearable'),
                    css_class='four wide field'
                    ),
                
                Div(
                    PrependedText('value_1','$',css_class='money text-center value'),
                    css_class='four wide field'
                    ),
                Div(
                    dropdownField('payment_method_2', css_class='clearable'),
                    css_class='four wide field'
                    ),
                
                Div(
                    PrependedText('value_2','$',css_class='money text-center value'),
                    css_class='four wide field'
                    ),
                css_class='fields'
            ),
            Div(
                   Field('description') 
                ),
            Div(
                StrictButton('Grabar',type='submit',css_class='ui right floated button'),
                css_class='ui basic segment'
                ),
            
        )
        
class incomes_form(forms.Form):
    today = datetime.today()
    dt_today = datetime.strftime(today, '%Y-%m-%d')
    add_date = forms.DateField(label='Fecha de registro')
    payment_day = forms.DateField(label='Fecha de pago')
    payment_method_1 = forms.ModelChoiceField(
        Payment_methods.objects.exclude(name='Anulaciones'),
        label='Forma de pago 1',empty_label='Selecciona...'
    )
    value_1 = forms.CharField(max_length=255,label='Valor')
    payment_method_2 = forms.ModelChoiceField(
        Payment_methods.objects.exclude(name='Anulaciones'),
        label='Forma de pago 2',empty_label='Selecciona...',
        required=False
    )
    value_2 = forms.CharField(max_length=255,label='Valor',
                              required=False)
    arrears_condonate = forms.IntegerField(min_value=0,max_value=100,
                                           label='Condonación mora',initial=0)
    
    sale = forms.ModelChoiceField(
        Sales.objects.filter(status='Adjudicado'),
    label='Cliente')
    description = forms.CharField(max_length=255,label='Descripción',widget=
                                  forms.Textarea({'rows':2}))
    tasa_mora = forms.CharField(label='Tasa Mora (%)', required=False, disabled=True)
    capital_payment = forms.BooleanField(label='El cliente paga más de lo que tiene vencido', required=False)
    TIPO_ABONO = [
        ('', '---------'),
        ('cuotas_futuras', 'Pago anticipado de cuotas'),
        ('reducir_tiempo', 'Abono a capital (reducir plazo)'),
        ('reducir_cuota', 'Abono a capital (reducir cuota)'),
    ]
    tipo_abono_capital = forms.ChoiceField(
        choices=TIPO_ABONO, required=False, label='¿Cómo aplicar el excedente?'
    )
    
    
    def __init__(self,*args,**kwargs):
        project = kwargs.pop('project')
        lock_add_date = kwargs.pop('lock_add_date', False)
        super().__init__(*args,**kwargs)
        if project:
            self.fields['sale'].queryset = Sales.objects.filter(
                status='Adjudicado',
                project=project
            ).order_by('first_owner__last_name')
        from mcd_site.models import Parameters
        try:
            tasa = Parameters.objects.get(name='tasa de mora mv').value
        except Exception:
            tasa = 'No definida'
        self.fields['tasa_mora'].initial = tasa
        #self.fields['tipo_abono_capital'].widget.attrs['style'] = 'display:none;'
        if lock_add_date:
            field = self.fields['add_date']
            prev_style = field.widget.attrs.get('style', '')
            extra_style = 'background: #f9fafb; cursor: not-allowed;'
            field.widget.attrs.update({
                'readonly': 'readonly',
                'style': f'{prev_style} {extra_style}'.strip()
            })

        self.helper = FormHelper()
        self.helper.form_class = 'ui form'
        self.helper.form_id = 'form-new-income'
        self.helper.layout = Layout(
            Div(
                Div(dropdownField('sale',css_class='search'), css_class='six wide field'),
                Div(dateField('add_date',date=self.dt_today), css_class='three wide field'),
                Div(dateField('payment_day'), css_class='three wide field'),
                Div(Field('tasa_mora', css_class='disabled', readonly=True, style='background: #f9fafb; font-weight: bold; text-align: center;'), css_class='two wide field', style='padding-right:0.2em;'),
                Div(AppendedText('arrears_condonate','%',css_class='text-center', readonly=True), css_class='two wide field', style='padding-left:0;'),
                css_class='fields'
            ),
            Div(
                Div(dropdownField('payment_method_1', css_class='clearable'), css_class='four wide field'),
                Div(PrependedText('value_1','$',css_class='money text-center value'), css_class='three wide field'),
                Div(dropdownField('payment_method_2', css_class='clearable'), css_class='four wide field'),
                Div(PrependedText('value_2','$',css_class='money text-center value'), css_class='three wide field'),
                Div(checkbox('capital_payment'), css_class='two wide field'),
                dropdownField('tipo_abono_capital'),
                css_class='fields'
            ),
            HTML(
            '''
            <div class='ui basic segment'>
                <table class='ui celled selectable table' id='tableRcdosVentas' style="width:100%">
                    <thead>
                        <tr class='center aligned'>
                            <th rowspan="2">Fecha</th>
                            <th rowspan="2">Cuota</th>
                            <th colspan="5">Pendiente</th>
                            <th colspan="4">Aplicado</th>
                        </tr>
                        <tr class='center aligned'>
                            <th>Capital</th>
                            <th>Interes</th>
                            <th>Mora</th>
                            <th>Dias Mora</th>
                            <th>Total</th>
                            <th>Capital</th>
                            <th>Interes</th>
                            <th>Mora</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                </table>
            </div>
            '''    
            ),
            Field('description'),
            Div(
                Submit('btnRegistrar','Registrar',css_class='ui disabled green button'),
                css_class='ui basic right aligned segment'
            )
        )
        
class new_expense_form(forms.Form):
    date = forms.DateField(label='Fecha')
    description = forms.CharField(max_length=255,widget=forms.Textarea({'rows':2,}),label='Descripcion')
    costcenter = forms.ModelChoiceField(cost_center.objects.all(),label='Centro de costo',
                                        empty_label='Selecciona...')
    value = forms.CharField(max_length=50,label='Valor')
    
    def __init__(self,*args, **kwargs):
        project = kwargs.pop('project')
        super().__init__(*args,**kwargs)
        if project:
            self.fields['costcenter'].queryset = cost_center.objects.filter(project=project,
                to_date__isnull=True)
        
        self.helper = FormHelper()
        self.helper.form_class= 'ui form'
        self.helper.form_id = 'form-new-expense'
        self.helper.layout = Layout(
            dropdownField('costcenter'),
            Field('description'),
            Div(
                dateField('date'),
                PrependedText('value','$',css_class='money text-center'),
                css_class="two fields"
            ),
            Div(
                Submit('registrar','Registrar',css_class="ui green button"),
                css_class="ui basic right aligned segment"
            )
        ) 
        
class SolicitudReciboForm(forms.ModelForm):
    TIPO_ABONO = [
        ('', '---------'),
        ('cuotas_futuras', 'Pago anticipado de cuotas'),
        ('reducir_tiempo', 'Abono a capital (reducir plazo)'),
        ('reducir_cuota', 'Abono a capital (reducir cuota)'),
    ]
    tipo_abono_capital = forms.ChoiceField(
        choices=TIPO_ABONO, required=False, label='¿Cómo aplicar el excedente?'
    )
    
    class Meta:
        model = SolicitudRecibo
        exclude = ['recibo_generado', 'project', 'add_date', 'estado', 'creado_por', 'revisado_por', 'confirmado_en', 'observaciones_revision']
        widgets = {
            'payment_date': DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'YYYY-MM-DD',
                    'pattern': r'\d{4}-\d{2}-\d{2}'
                },
                format='%Y-%m-%d'
            )
        }

    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        # Cambiar el label del checkbox
        self.fields['capital_payment'].label = 'El cliente paga más de lo que tiene vencido'

        if project:
            # ✅ PERMITIR ventas NO adjudicadas también (Pendiente, Aprobado)
            self.fields['sale'].queryset = Sales.objects.filter(
                project=project,
                status__in=['Pendiente', 'Aprobado', 'Adjudicado']
            ).order_by('status', 'first_owner__last_name')
            self.fields['sale'].empty_label='Buscar cliente...'

            # Agregar atributos para cálculo de mora
            self.fields['sale'].widget.attrs.update({
                'onchange': 'calcularMoraFormulario(this.value)'
            })

        # Filtros en formas de pago si se desea excluir 'Anulaciones'
        self.fields['pm1'].queryset = Payment_methods.objects.exclude(name='Anulaciones')
        self.fields['pm2'].queryset = Payment_methods.objects.exclude(name='Anulaciones')

        # Configurar formato de fecha ISO estricto para evitar ambigüedades
        # El widget type="date" de HTML5 siempre envía en formato YYYY-MM-DD
        self.fields['payment_date'].input_formats = ['%Y-%m-%d']
        self.fields['payment_date'].widget.format = '%Y-%m-%d'
        self.fields['payment_date'].help_text = 'Formato: AAAA-MM-DD (año con 4 dígitos). Ejemplo: 2026-01-14'

        # Agregar atributo al campo de fecha para recalcular mora
        self.fields['payment_date'].widget.attrs.update({
            'onchange': 'calcularMoraFormulario()'
        })

        # Agregar atributo al campo de condonación
        self.fields['arrears_condonate'].widget.attrs.update({
            'oninput': 'calcularCondonacion()'
        })

        # Si es edición, mostrar archivo actual y hacer opcional
        if self.instance.pk and self.instance.soporte:
            self.fields['soporte'].required = False
            self.fields['soporte'].help_text = f'Archivo actual: {self.instance.soporte.name}'
            self.fields['soporte'].label = 'Cambiar soporte (opcional)'

        # ✅ OCULTAR campos innecesarios si la venta NO está adjudicada
        # Esto solo aplica cuando ya hay una instancia (edición) o cuando se pre-selecciona una venta
        if self.instance.pk and self.instance.sale:
            if self.instance.sale.status in ['Pendiente', 'Aprobado']:
                # Estas ventas no manejan condonación ni abono a capital
                self.fields['arrears_condonate'].widget = forms.HiddenInput()
                self.fields['arrears_condonate'].initial = 0
                self.fields['capital_payment'].widget = forms.HiddenInput()
                self.fields['capital_payment'].initial = False
                self.fields['tipo_abono_capital'].widget = forms.HiddenInput()
                self.fields['tipo_abono_capital'].initial = ''

        self.helper = FormHelper()
        self.helper.form_class = 'ui form'
        self.helper.form_id = 'form-solicitud-recibo'
        self.helper.layout = Layout(
            Div(
                Div(dropdownField('sale', css_class='search'), css_class='nine wide field'),
                Div(dateField('payment_date'), css_class='four wide field'),
                Div(AppendedText('arrears_condonate', '%', css_class='text-center'), css_class='three wide field'),
                css_class='fields'
            ),
            # Agregar información de mora después de la primera fila
            HTML('<div id="info-mora-container" style="display: none; margin: 10px 0;"></div>'),
            Div(
                Div(checkbox('capital_payment'), css_class='four wide field'),
                Div(dropdownField('tipo_abono_capital'), css_class='twelve wide field', id='div-tipo-abono'),
                css_class='fields'
            ),
            HTML('''
                <small>El excedente se aplicará después de pagar las cuotas vencidas<br><br></small>
                <script>
                $(document).ready(function() {
                    // Función para mostrar/ocultar el select de tipo de abono
                    function toggleTipoAbono() {
                        var capitalPayment = $('#id_capital_payment').is(':checked');
                        if (capitalPayment) {
                            $('#div-tipo-abono').show();
                        } else {
                            $('#div-tipo-abono').hide();
                            $('#id_tipo_abono_capital').val('');
                        }
                    }

                    // Ejecutar al cargar la página
                    toggleTipoAbono();

                    // Ejecutar cuando cambia el checkbox
                    $('#id_capital_payment').on('change', toggleTipoAbono);
                });
                </script>
            '''),
            Div(
                Div(dropdownField('pm1', css_class='clearable'), css_class='four wide field'),
                Div(PrependedText('value1', '$', css_class='money text-center value'), css_class='four wide field'),
                Div(dropdownField('pm2', css_class='clearable'), css_class='four wide field'),
                Div(PrependedText('value2', '$', css_class='money text-center value'), css_class='four wide field'),
                css_class='fields'
            ),
            Field('description'),
            Div(
                Field('obs_1'),
                Field('obs_2'),
                css_class='two fields'
            ),
            Field('soporte'),
            Div(
                Submit('btnGuardar', 'Guardar', css_class='ui green button'),
                css_class='ui basic segment right aligned'
            )
        )

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get('payment_date')

        # Si no hay fecha, retornar None
        if not payment_date:
            return payment_date

        # Si ya es un objeto date, validar
        if isinstance(payment_date, date):
            # Validar que el año no esté en el rango 1900-2050 de manera sospechosa
            # Si el año es menor a 2000, probablemente es un error de parseo
            if payment_date.year < 2000:
                raise forms.ValidationError(
                    f'La fecha parece incorrecta (año {payment_date.year}). '
                    'Verifique que ingresó el año completo con 4 dígitos (ej: 2026, no 26).'
                )

            if payment_date > datetime.today().date():
                raise forms.ValidationError('La fecha real de pago no puede ser mayor a la fecha actual.')
            return payment_date

        # Si es string, intentar parsear en formato ISO (YYYY-MM-DD)
        if isinstance(payment_date, str):
            from django.utils.dateparse import parse_date
            import re
            payment_date = payment_date.strip()

            # 🚨 VALIDAR: Detectar si el usuario escribió año con 2 dígitos
            # Patrones como DD-MM-YY, DD/MM/YY, YY-MM-DD con año de 2 dígitos
            pattern_2digit_year = r'^(\d{1,2})[/-](\d{1,2})[/-](\d{2})$|^(\d{2})[/-](\d{1,2})[/-](\d{1,2})$'
            if re.match(pattern_2digit_year, payment_date):
                raise forms.ValidationError(
                    'El año debe tener 4 dígitos. '
                    f'Escribió "{payment_date}", pero debe usar formato completo como "14-01-2026" o "2026-01-14".'
                )

            # Intentar parsear en formato ISO primero
            parsed_date = parse_date(payment_date)

            if not parsed_date:
                # Intentar otros formatos comunes
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        parsed_date = datetime.strptime(payment_date, fmt).date()
                        break
                    except ValueError:
                        continue

            if not parsed_date:
                raise forms.ValidationError('Formato de fecha inválido. Use YYYY-MM-DD.')

            # Validar año
            if parsed_date.year < 2000:
                raise forms.ValidationError(
                    f'La fecha parece incorrecta (año {parsed_date.year}). '
                    'Verifique que ingresó el año completo con 4 dígitos (ej: 2026, no 26).'
                )

            if parsed_date > datetime.today().date():
                raise forms.ValidationError('La fecha real de pago no puede ser mayor a la fecha actual.')

            return parsed_date

        return payment_date
