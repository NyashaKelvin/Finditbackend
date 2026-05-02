from rest_framework import serializers
from .models import Item, ClaimRequest, Message, Notification

class ItemSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source='owner.username')
    date_spotted = serializers.DateTimeField(style={'input_type': 'text'})

    class Meta:
        model = Item
        fields = [
            'id', 'owner', 'owner_username',
            'title', 'description', 'category', 'status',
            'location', 'image', 'thumbnail', 'date_spotted',
            'verification_question',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['owner', 'thumbnail', 'created_at', 'updated_at']

    def validate_status(self, value):
        request = self.context.get('request', None)
        if value == 'CLAIMED':
            instance = self.instance
            if instance and request and request.user != instance.owner:
                raise serializers.ValidationError("Only the owner can mark an item as CLAIMED.")
        return value

class ClaimRequestSerializer(serializers.ModelSerializer):
    requester_username = serializers.ReadOnlyField(source='requester.username')
    item_title = serializers.ReadOnlyField(source='item.title')
    item_owner = serializers.ReadOnlyField(source='item.owner.id')

    class Meta:
        model = ClaimRequest
        fields = ['id', 'item', 'item_title', 'item_owner', 'requester', 'requester_username', 'answer_to_question', 'status', 'created_at', 'updated_at']
        read_only_fields = ['requester', 'status', 'created_at', 'updated_at']

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    receiver_username = serializers.ReadOnlyField(source='receiver.username')

    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_username', 'receiver', 'receiver_username', 'item', 'body', 'created_at']
        read_only_fields = ['sender', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read', 'created_at']
        read_only_fields = ['user', 'message', 'created_at']
