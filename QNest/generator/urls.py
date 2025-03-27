from django.urls import path
from .views import home, register, user_logout, upload_files, create_template,template_view

urlpatterns = [
    path("", home, name="home"), 
    path("register/", register, name="register"),
    path("logout/", user_logout, name="logout"),
    path("upload/", upload_files, name="upload_files"), 
    # path("download_pdf/", download_pdf, name="download_pdf"),
    path("create-template/", create_template, name="create_template"),
    path('templates/', template_view, name='template_view'),
]
