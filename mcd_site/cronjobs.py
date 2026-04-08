from django_cron import CronJobBase, Schedule
from finance.models import Sales_extra_info
from mcd_site.models import Notifications_email, Perfil, Projects
from mcd_site.utils import send_email_template

class cronjobcollect(CronJobBase):
    code = 'mcd_site.cronjobcollect'
    schedule = Schedule(run_every_mins=2)
    
    def do(self):
        
        projects = Projects.objects.all()
    
        collector_users = Perfil.objects.filter(rol__descripcion__in=['Gestor de Cartera'])
        for project in projects:
            sales = Sales_extra_info.objects.filter(project = project.name)
            for collector in collector_users:
                email = collector.usuario.email
                sales = sales.filter(sale_collector__collector_user = collector.pk)
                msj = f'''A continuación encontrarás los clientes del proyecto <strong>{project.name_to_show}</strong>, asignados a tu cartera que tienen fecha de pago pactada para hoy,
                o en su defecto su ultima cuota estaba pactada para este día:<br><br>
                <ol>
                    '''
                i = 0
                for sale in sales:
                    budget = sale.budget()
                    if sale.is_pay_day() and budget.get('budget_pending') > 0:
                        i += 1
                        msj += f'''
                                <li>
                                <strong>Contrato #{sale.contract_number}</strong>
                                {sale.first_owner.full_name()}, valor pendiente $
                                {budget.get('budget_pending'):,.0f} con {budget.get('arrears_days')}
                                dias de mora
                            '''
                msj += '</ol>'
                if i > 0:
                    email_context = {
                        'email_title': 'Cobros de cartera',
                        'email_message': msj,
                        'user':collector.usuario,
                        'email_title':'Recordatorio de cartera'
                    }
                    send_email_template(f'Recordatorio cobros del día {project.name_to_show}',
                                    [email,],
                                    template='email_notification.html',
                                    template_context=email_context)
            
            #send to others
            notifications = Notifications_email.objects.filter(name='Envios fijos recordatorio email')
            if notifications.exists():
                for user in notifications[0].users_to_send.all():
                    msj = f'''A continuación encontrarás los clientes del proyecto <strong>{project.name_to_show}</strong> que tienen fecha de pago pactada para hoy,
                        o en su defecto su ultima cuota estaba pactada para este día:<br><br>
                        <ol>
                            '''
                    i = 0
                    for sale in sales:
                        budget = sale.budget()
                        
                        if sale.is_pay_day() and budget.get('budget_pending') > 0:
                            i += 1
                            collector_name = 'NINGUNO'
                            if None != budget.get('collector_sale') != "":
                                collector_name = budget.get('collector_sale').get_full_name()
                            msj += f'''
                                    <li>
                                    <strong>Contrato:</strong> {sale.contract_number}
                                    {sale.first_owner.full_name()}, valor pendiente $
                                    {budget.get('budget_pending'):,.0f} con {budget.get('arrears_days')}
                                    de mora (asignado a {collector_name})
                            '''
                        
                    msj += '</ol>'
                    if i > 0:
                        email_context = {
                            'email_title': 'Cobros de cartera',
                            'email_message': msj,
                            'user':user
                        }
                    
                        send_email_template(f'Recordatorio cobros del día {project.name_to_show}',
                                        [user.email,],
                                        template='email_notification.html',
                                        template_context=email_context)

                