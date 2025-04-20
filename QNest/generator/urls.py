from django.urls import path
from . import views
from .views import home, question_view, register, user_logout, upload_files, create_template,template_view, mcq, download_pdf
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("", home, name="home"), 
    path("register/", register, name="register"),
    path("logout/", user_logout, name="logout"),
    path("upload/", upload_files, name="upload_files"), 
    path("create-template/", create_template, name="create_template"),
    path('templates/', template_view, name='template_view'),
    path('view-question/', question_view, name='question_view'),
    path('mcq/', mcq, name='mcq'),
    path('download-pdf/', download_pdf, name='download_pdf'),

]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
