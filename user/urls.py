from django.urls import path
from user import views

urlpatterns = [
    # path('', views.userinfo, name="userinfo"),
    path('userinfo/<username>/', views.userinfo, name="userinfo"),

    path('login/', views.LoginView.as_view(), name="login"),
    path('register/', views.RegisterView.as_view(), name="register"),
    path('logout/', views.logout, name="logout"),
    path('verify/', views.VerifyView.as_view(), name='verify'),
    path('reset-verify/', views.reset_password_verify, name='reset_verify'),
    path('reset/', views.reset_password, name='reset'),

    path('profile/', views.profile, name='profile'),
    path("profile/<username>/", views.profile_other, name='user_profile'),
    path('edit-avatar/', views.edit_avatar, name='edit_avatar'),
    path('edit-userinfo/', views.edit_userinfo, name='edit_userinfo'),
    path('save-addr/', views.save_addresses, name='save_addresses'),

    path('is_login/', views.is_login, name='is_login')

]
