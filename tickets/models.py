from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


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

    CATEGORY_CHOICES = (
        ("HARDWARE", "Hardware"),
        ("SOFTWARE", "Software"),
        ("NETWORK", "Network"),
        ("ACCESS", "Access & Permissions"),
        ("EMAIL", "Email"),
        ("OTHER", "Other"),
    )

    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default="OTHER")

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="NEW")
    urgency = models.CharField(
        max_length=20, choices=URGENCY_CHOICES, default="MEDIUM")

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
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # SLA tracking (in hours)
    sla_response_time = models.IntegerField(
        null=True, blank=True)  # Time until first response
    sla_resolution_time = models.IntegerField(
        null=True, blank=True)  # Time until resolved

    def __str__(self):
        return f"#{self.id} {self.title} [{self.status}]"

    @property
    def time_to_resolve(self):
        """Calculate time to resolve in hours"""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
            return round(delta.total_seconds() / 3600, 2)
        return None

    @property
    def age_in_hours(self):
        """Calculate current age of ticket in hours"""
        delta = timezone.now() - self.created_at
        return round(delta.total_seconds() / 3600, 2)

    @property
    def is_overdue(self):
        """Check if ticket is overdue based on urgency"""
        if self.status in ["RESOLVED", "CLOSED"]:
            return False

        sla_hours = {
            "CRITICAL": 4,
            "HIGH": 24,
            "MEDIUM": 72,
            "LOW": 168,
        }

        max_hours = sla_hours.get(self.urgency, 72)
        return self.age_in_hours > max_hours


class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

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

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE)

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    from_status = models.CharField(max_length=20, blank=True, null=True)
    to_status = models.CharField(max_length=20, blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on Ticket #{self.ticket.id}"
