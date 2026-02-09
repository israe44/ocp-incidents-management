from django.contrib import admin
from .models import Ticket, Comment, TicketHistory

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "urgency", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "urgency")
    search_fields = ("title", "description")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "author", "created_at")
    search_fields = ("content",)


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "action", "actor", "created_at")
    list_filter = ("action",)
