from django.contrib import admin
from django.utils.html import format_html
from .models import Item, ClaimRequest, Message, Notification

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'owner', 'category', 'colored_status', 'location', 'date_spotted', 'created_at']
    list_filter = ['status', 'category', 'date_spotted']
    search_fields = ['title', 'description', 'location', 'owner__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {'fields': ('owner', 'title', 'description', 'category', 'status')}),
        ('Location & Time', {'fields': ('location', 'date_spotted')}),
        ('Media & Verification', {'fields': ('image', 'verification_question')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    @admin.display(description='Status')
    def colored_status(self, obj):
        colors = {'LOST': '#FF6B6B', 'FOUND': '#51CF66', 'CLAIMED': '#339AF0'}
        color = colors.get(obj.status, '#aaa')
        return format_html('<span style="color:{}; font-weight:bold;">{}</span>', color, obj.status)

@admin.register(ClaimRequest)
class ClaimRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'item', 'requester', 'status', 'created_at']
    list_filter = ['status']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender', 'receiver', 'item', 'created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'message', 'is_read', 'created_at']
