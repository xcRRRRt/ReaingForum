from django.urls import path
from forum import views

urlpatterns = [
    path('', views.homepage, name="home"),
    path('editor', views.editor, name="editor"),
]
