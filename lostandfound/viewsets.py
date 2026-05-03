from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import Item, ClaimRequest, Message, Notification
from .serializers import ItemSerializer, ClaimRequestSerializer, MessageSerializer, NotificationSerializer
from users.serializers import UserSerializer

class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related('owner').all()
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'status', 'location', 'owner']
    search_fields = ['title', 'description']

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        item = self.get_object()
        if self.request.user != item.owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to edit this item.")
        serializer.save()

    def perform_destroy(self, instance):
        # Allow deletion if user is owner OR an administrator (staff/superuser)
        if self.request.user == instance.owner or self.request.user.is_staff:
            instance.delete()
        else:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to delete this item.")

    @action(detail=True, methods=['get'], url_path='suggested_matches')
    def suggested_matches(self, request, pk=None):
        lost_item = self.get_object()
        if lost_item.status != 'LOST':
            return Response({'detail': 'Smart matching only works for LOST items.'}, status=status.HTTP_400_BAD_REQUEST)

        keywords = [word for word in lost_item.title.split() if len(word) > 2]
        from django.db.models import Q
        keyword_filter = Q()
        for kw in keywords:
            keyword_filter |= Q(title__icontains=kw)

        matches = Item.objects.filter(status='FOUND', category=lost_item.category).filter(keyword_filter).exclude(pk=lost_item.pk)
        serializer = self.get_serializer(matches, many=True, context={'request': request})
        return Response({
            'lost_item': lost_item.title,
            'match_count': matches.count(),
            'matches': serializer.data,
        })

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        total_lost = Item.objects.filter(status='LOST').count()
        total_found = Item.objects.filter(status='FOUND').count()
        total_claimed = Item.objects.filter(status='CLAIMED').count()
        return Response({
            'total_lost': total_lost,
            'total_found': total_found,
            'successfully_returned': total_claimed,
            'total_items': total_lost + total_found + total_claimed,
        })

class ClaimRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ClaimRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        return ClaimRequest.objects.select_related('item', 'requester', 'item__owner').filter(
            Q(requester=self.request.user) | Q(item__owner=self.request.user)
        ).order_by('-created_at')

    def perform_create(self, serializer):
        item = serializer.validated_data.get('item')
        if item.owner == self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot submit a claim for your own item.")
            
        claim = serializer.save(requester=self.request.user)
        # Notify the item owner that someone has claimed their item
        Notification.objects.create(
            user=claim.item.owner,
            message=f"Someone has submitted a claim for your item: '{claim.item.title}'."
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        claim = self.get_object()
        if claim.item.owner != request.user:
            return Response({"detail": "Only the item owner can approve claims."}, status=status.HTTP_403_FORBIDDEN)
        
        claim.status = 'APPROVED'
        claim.save()

        # Automatically mark the item as CLAIMED
        item = claim.item
        item.status = 'CLAIMED'
        item.save()
        
        # Send an official Notification
        Notification.objects.create(
            user=claim.requester,
            message=f"Your claim for '{item.title}' has been approved! You can now message the owner."
        )

        # Send an automatic direct message to facilitate collection
        Message.objects.create(
            sender=request.user,
            receiver=claim.requester,
            item=item,
            body=f"Your claim for '{item.title}' has been approved! Your item is ready for collection. Please reply here to coordinate the handover."
        )

        return Response({"status": "Claim approved"})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        claim = self.get_object()
        if claim.item.owner != request.user:
            return Response({"detail": "Only the item owner can reject claims."}, status=status.HTTP_403_FORBIDDEN)
        
        claim.status = 'REJECTED'
        claim.save()
        
        Notification.objects.create(
            user=claim.requester,
            message=f"Your claim for '{claim.item.title}' was declined by the owner."
        )
        return Response({"status": "Claim rejected"})

    def perform_destroy(self, instance):
        if instance.requester != self.request.user and instance.item.owner != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete this claim request.")
        instance.delete()

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        return Message.objects.select_related('sender', 'receiver', 'item').filter(
            (Q(sender=self.request.user) & Q(deleted_by_sender=False)) | 
            (Q(receiver=self.request.user) & Q(deleted_by_receiver=False))
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        message = self.get_object()
        if message.receiver != request.user:
            return Response({"detail": "Only the receiver can mark a message as read."}, status=status.HTTP_403_FORBIDDEN)
        message.is_read = True
        message.save()
        return Response({"status": "Message marked as read"})

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.sender == user and instance.receiver == user:
            instance.delete()
        elif instance.sender == user:
            instance.deleted_by_sender = True
            instance.save()
            if instance.deleted_by_receiver:
                instance.delete()
        elif instance.receiver == user:
            instance.deleted_by_receiver = True
            instance.save()
            if instance.deleted_by_sender:
                instance.delete()
        else:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete this message.")

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.select_related('user').filter(user=self.request.user).order_by('-created_at')

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You cannot delete this notification.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "Notification marked as read"})
class BootstrapView(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request):
        data = {
            'stats': {
                'total_lost': Item.objects.filter(status='LOST').count(),
                'total_found': Item.objects.filter(status='FOUND').count(),
                'successfully_returned': Item.objects.filter(status='CLAIMED').count(),
                'total_items': Item.objects.count(),
            },
            'user': None,
            'notifications': [],
            'unread_messages': 0
        }

        if request.user.is_authenticated:
            data['user'] = UserSerializer(request.user).data
            data['notifications'] = NotificationSerializer(
                Notification.objects.filter(user=request.user).order_by('-created_at')[:5], 
                many=True
            ).data
            data['unread_messages'] = Message.objects.filter(receiver=request.user, is_read=False, deleted_by_receiver=False).count()
            data['unread_notifications'] = Notification.objects.filter(user=request.user, is_read=False).count()

        return Response(data)
