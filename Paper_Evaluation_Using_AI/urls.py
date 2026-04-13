from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('Accounts.urls')), 
    path('dashboard/', include('Dashboards.urls')), 
    path('exam/', include('Exams.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('aboutproject/', TemplateView.as_view(template_name='aboutproject.html'), name='aboutproject'),
    path('contactus/', TemplateView.as_view(template_name='contactus.html'), name='contactus'),
    path('profile/', TemplateView.as_view(template_name='profile.html'), name='profile')
    
]
if settings.ENVIRONMENT == "local":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)