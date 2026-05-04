"""mcd_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from terceros import views as terceros_views
from mcd_site import views as site_views
from sales import views as sales_views
from finance import views as finance_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Override django-registration's auth_urls PasswordResetView so the HTML
    # template is sent as an alternative part (multipart), not as text/plain body.
    path(
        'accounts/password/reset/',
        auth_views.PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.txt',
            html_email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('auth_password_reset_done'),
        ),
        name='auth_password_reset',
    ),
    # After setting a new password, go straight to login.
    # This name is used by our invitation emails.
    path(
        'accounts/password/reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/login',
        ),
        name='auth_password_reset_confirm',
    ),
    path('accounts/', include('registration.backends.default.urls')),
    path('',include(site_views.urlpattern)),
    path('partners/',include(terceros_views.urls)),
    path('sales/',include(sales_views.urlpattern)),
    path('finance/',include(finance_views.urlpattern)),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
