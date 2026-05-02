from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import ItemViewSet, ClaimRequestViewSet, MessageViewSet, NotificationViewSet, BootstrapView

router = DefaultRouter()
router.register(r'items', ItemViewSet, basename='items')
router.register(r'claims', ClaimRequestViewSet, basename='claims')
router.register(r'messages', MessageViewSet, basename='messages')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'bootstrap', BootstrapView, basename='bootstrap')

urlpatterns = [
    path('', include(router.urls)),
]
