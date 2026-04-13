from django.contrib import admin
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # path('register/', views.register, name='register'),
    path('slogin/',views.slogin,name="slogin"),
    path('tlogin/',views.tlogin,name="tlogin"),
    path('adminlogin/',views.adminlogin,name="adminlogin"),
    path('logout/',views.logout_user,name="logout"),
]
if settings.ENVIRONMENT == "local":
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)