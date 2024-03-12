from django.urls import path
from user import views

urlpatterns = [
    path('', views.userinfo, name="userinfo"),

    path('login/', views.login, name="login"),
    path('register/', views.register, name="register"),
    path('logout/', views.logout, name="logout"),
    path('verify/', views.verify, name='verify'),
    path('reset_verify/', views.reset_password_verify, name='reset_verify'),
    path('reset/', views.reset_password, name='reset'),

    path('profile/', views.profile, name='profile'),
    path('edit-avatar/', views.edit_avatar, name='edit_avatar'),
    path('edit-userinfo/', views.edit_userinfo, name='edit_userinfo'),
    path('save-addr/', views.save_addresses, name='save_addresses')
]
