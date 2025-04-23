from django.urls import path
from . import views
from .views import home, register, user_logout, upload_files, create_template,template_view, mcq,download_generated_pdf,view_generated_pdfs
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("", home, name="home"), 
    path("register/", register, name="register"),
    path("logout/", user_logout, name="logout"),
    path("upload/", upload_files, name="upload_files"), 
    path("create-template/", create_template, name="create_template"),
    path('templates/', template_view, name='template_view'),
    # path('view-question/', question_view, name='question_view'),
    path('mcq/', mcq, name='mcq'),
    path('download-pdf/', download_generated_pdf, name='download_generated_pdf'),
    path("generated-papers/", view_generated_pdfs, name="view_generated_pdfs"),
    # path('download-mcq-pdf/', views.download_mcq_pdf, name='download_mcq_pdf'),

]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# This serves media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
