import logging
from django.core.mail import get_connection, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)

def send_company_email(company, subject, template_name, context, recipient_list, cc_list=None):
    """
    Sends an email using the company's specific SMTP settings if available.
    Falls back to default Django settings if not configured.
    """
    try:
        smtp = getattr(company, 'smtp_settings', None)
    except Exception:
        smtp = None
        
    connection = None
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    if smtp and smtp.email_host_user and smtp.email_host_password:
        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=smtp.email_host,
                port=smtp.email_port,
                username=smtp.email_host_user,
                password=smtp.email_host_password,
                use_tls=smtp.email_use_tls,
                use_ssl=smtp.email_use_ssl,
                fail_silently=False,
            )
            from_email = smtp.default_from_email or smtp.email_host_user
        except Exception as e:
            logger.error(f"Failed to create SMTP connection for company {company.name}: {e}")
            # Fallback to default connection
            connection = get_connection()
    else:
        # Fallback to default django settings
        connection = get_connection()
        
    try:
        html_content = render_to_string(template_name, context)
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body="Please view this email in a client that supports HTML.",
            from_email=from_email,
            to=recipient_list,
            cc=cc_list or [],
            connection=connection
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {e}")
        return False
