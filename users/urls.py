from django.urls import path
from .views import RegisterAPIView, login_view, logout_view, GoogleLogin

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
]
