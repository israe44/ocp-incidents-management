from django.db import models
from django.conf import settings

class Ticket(models.Model):
    STATUS_CHOICES = (
        ("NEW", "New"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    )

    URGENCY_CHOICES = (
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("CRITICAL", "Critical"),
    )

    title = models.CharField(max_length=150)
    description = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="NEW")
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default="MEDIUM")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tickets_created"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_assigned"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"#{self.id} {self.title} [{self.status}]"


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on Ticket #{self.ticket.id}"


class TicketHistory(models.Model):
    ACTION_CHOICES = (
        ("CREATED", "Created"),
        ("ASSIGNED", "Assigned"),
        ("STATUS_CHANGED", "Status Changed"),
        ("COMMENT_ADDED", "Comment Added"),
        ("CLOSED", "Closed"),
    )

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    from_status = models.CharField(max_length=20, blank=True, null=True)
    to_status = models.CharField(max_length=20, blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on Ticket #{self.ticket.id}"
