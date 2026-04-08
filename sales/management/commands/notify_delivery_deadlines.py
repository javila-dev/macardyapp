from django.core.management.base import BaseCommand
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from datetime import date, timedelta
from sales.models import Sales
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Envía notificaciones por vencimientos de entrega y escrituración'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Días de anticipación para alertas (default: 7)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Modo prueba: solo muestra datos sin enviar emails'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar envío aunque no haya alertas críticas'
        )

    def handle(self, *args, **options):
        days_ahead = options['days']
        test_mode = options['test']
        force_send = options['force']
        today = date.today()
        alert_date = today + timedelta(days=days_ahead)
        
        self.stdout.write(f"🔍 Buscando alertas para {days_ahead} días de anticipación...")
        
        # Buscar entregas próximas a vencer
        entregas_vencen = Sales.objects.filter(
            status='Adjudicado',
            scheduled_delivery_date__lte=alert_date,
            scheduled_delivery_date__gte=today,
            actual_delivery_date__isnull=True
        ).select_related('first_owner', 'property_sold__project')
        
        # Buscar escrituraciones próximas a vencer
        escrituras_vencen = Sales.objects.filter(
            status='Adjudicado',
            scheduled_deed_date__lte=alert_date,
            scheduled_deed_date__gte=today,
            actual_deed_date__isnull=True
        ).select_related('first_owner', 'property_sold__project')
        
        # Buscar entregas vencidas
        entregas_vencidas = Sales.objects.filter(
            status='Adjudicado',
            scheduled_delivery_date__lt=today,
            actual_delivery_date__isnull=True
        ).select_related('first_owner', 'property_sold__project')
        
        # Buscar escrituraciones vencidas
        escrituras_vencidas = Sales.objects.filter(
            status='Adjudicado',
            scheduled_deed_date__lt=today,
            actual_deed_date__isnull=True
        ).select_related('first_owner', 'property_sold__project')
        
        # Estadísticas
        total_alertas = (entregas_vencen.count() + escrituras_vencen.count() + 
                        entregas_vencidas.count() + escrituras_vencidas.count())
        
        self.stdout.write(f"📊 Resumen de alertas:")
        self.stdout.write(f"  • Entregas próximas a vencer: {entregas_vencen.count()}")
        self.stdout.write(f"  • Escrituras próximas a vencer: {escrituras_vencen.count()}")
        self.stdout.write(f"  • Entregas vencidas: {entregas_vencidas.count()}")
        self.stdout.write(f"  • Escrituras vencidas: {escrituras_vencidas.count()}")
        self.stdout.write(f"  • Total alertas: {total_alertas}")
        
        if test_mode:
            self.stdout.write(self.style.WARNING("🧪 MODO PRUEBA - No se enviarán emails"))
            self._mostrar_detalles(entregas_vencen, escrituras_vencen, entregas_vencidas, escrituras_vencidas)
            return
        
        # Enviar solo si hay alertas o se fuerza el envío
        if total_alertas > 0 or force_send:
            resultado = self._enviar_notificacion(
                entregas_vencen, escrituras_vencen,
                entregas_vencidas, escrituras_vencidas,
                days_ahead
            )
            
            if resultado:
                self.stdout.write(self.style.SUCCESS('✅ Notificaciones enviadas correctamente'))
            else:
                self.stdout.write(self.style.ERROR('❌ Error al enviar notificaciones'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No hay alertas para enviar'))

    def _mostrar_detalles(self, entregas_vencen, escrituras_vencen, entregas_vencidas, escrituras_vencidas):
        """Muestra detalles en modo prueba"""
        
        if entregas_vencidas:
            self.stdout.write(self.style.ERROR("\n⚠️ ENTREGAS VENCIDAS:"))
            for sale in entregas_vencidas:
                dias_vencidos = (date.today() - sale.scheduled_delivery_date).days
                self.stdout.write(f"  • CTR{sale.contract_number} - {sale.first_owner.first_name} {sale.first_owner.last_name} - {dias_vencidos} días vencido")
        
        if entregas_vencen:
            self.stdout.write(self.style.WARNING("\n📅 ENTREGAS PRÓXIMAS:"))
            for sale in entregas_vencen:
                dias_restantes = (sale.scheduled_delivery_date - date.today()).days
                self.stdout.write(f"  • CTR{sale.contract_number} - {sale.first_owner.first_name} {sale.first_owner.last_name} - {dias_restantes} días restantes")

    def _enviar_notificacion(self, entregas_vencen, escrituras_vencen, entregas_vencidas, escrituras_vencidas, days_ahead):
        """Envía email con notificaciones de vencimientos"""
        
        context = {
            'entregas_vencen': entregas_vencen,
            'escrituras_vencen': escrituras_vencen,
            'entregas_vencidas': entregas_vencidas,
            'escrituras_vencidas': escrituras_vencidas,
            'days_ahead': days_ahead,
            'fecha_reporte': date.today(),
            'total_alertas': (entregas_vencen.count() + escrituras_vencen.count() + 
                            entregas_vencidas.count() + escrituras_vencidas.count()),
        }
        
        # Renderizar templates
        try:
            subject = f'🚨 Alertas de Entrega y Escrituración - {date.today().strftime("%d/%m/%Y")}'
            html_content = render_to_string('sales/emails/delivery_alerts.html', context)
            text_content = render_to_string('sales/emails/delivery_alerts.txt', context)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error renderizando templates: {e}"))
            return False
        
        # Obtener destinatarios
        recipients = getattr(settings, 'DELIVERY_ALERT_EMAILS', [])
        if not recipients:
            self.stdout.write(self.style.ERROR("❌ No hay destinatarios configurados en DELIVERY_ALERT_EMAILS"))
            return False
        
        # Intentar envío con múltiples métodos
        return self._intentar_envio_email(subject, text_content, html_content, recipients)

    def _intentar_envio_email(self, subject, text_content, html_content, recipients):
        """Intenta enviar email con diferentes métodos"""
        
        # Método 1: Django EmailMultiAlternatives
        try:
            self.stdout.write("📧 Intentando envío con Django EmailMultiAlternatives...")
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                to=recipients
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            self.stdout.write(self.style.SUCCESS(f"✅ Email enviado exitosamente a {recipients}"))
            logger.info(f"Alerta de vencimientos enviada a {recipients}")
            return True
            
        except smtplib.SMTPRecipientsRefused as e:
            self.stdout.write(self.style.ERROR(f"❌ Error SMTP - Destinatarios rechazados: {e}"))
            logger.error(f"SMTP Recipients refused: {e}")
            
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error SMTP - Autenticación: {e}"))
            logger.error(f"SMTP Authentication error: {e}")
            
        except smtplib.SMTPConnectError as e:
            self.stdout.write(self.style.ERROR(f"❌ Error SMTP - Conexión: {e}"))
            logger.error(f"SMTP Connection error: {e}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error general enviando email: {e}"))
            logger.error(f"General email error: {e}")
        
        # Método 2: Envío a emails individuales
        try:
            self.stdout.write("📧 Intentando envío individual...")
            exitos = 0
            
            for recipient in recipients:
                try:
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=text_content,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                        to=[recipient]
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                    
                    self.stdout.write(self.style.SUCCESS(f"✅ Email enviado a {recipient}"))
                    exitos += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error enviando a {recipient}: {e}"))
                    logger.error(f"Error enviando a {recipient}: {e}")
            
            if exitos > 0:
                self.stdout.write(self.style.SUCCESS(f"✅ {exitos}/{len(recipients)} emails enviados"))
                return True
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error en envío individual: {e}"))
            logger.error(f"Error en envío individual: {e}")
        
        return False