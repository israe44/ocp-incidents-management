from django.utils import timezone
from users.models import User
import json
import csv
from datetime import timedelta, date
from .models import Ticket, TicketHistory, Comment

from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Avg, Q, F
from django.db.models.functions import TruncDate


@login_required
def ticket_delete(request, ticket_id):
    if request.user.role != "admin":
        return HttpResponseForbidden("Only admins can delete tickets")

    t = get_object_or_404(Ticket, id=ticket_id)
    t.delete()
    messages.success(request, "Ticket deleted successfully.")
    return redirect("dashboard")


@login_required
def dashboard(request):
    u = request.user

    tickets = Ticket.objects.all()

    if u.role == "technician":
        tickets = tickets.filter(assigned_to=u)
    elif u.role == "user":
        tickets = tickets.filter(created_by=u)

    status = request.GET.get("status")
    urgency = request.GET.get("urgency")
    search = request.GET.get("search")

    if status:
        tickets = tickets.filter(status=status)

    if urgency:
        tickets = tickets.filter(urgency=urgency)

    if search:
        tickets = tickets.filter(title__icontains=search)

    tickets_list = tickets.order_by("-created_at")

    # Calculate summary statistics
    all_tickets = Ticket.objects.all()
    if u.role == "technician":
        all_tickets = all_tickets.filter(assigned_to=u)
    elif u.role == "user":
        all_tickets = all_tickets.filter(created_by=u)

    summary = {
        'total': all_tickets.count(),
        'new': all_tickets.filter(status="NEW").count(),
        'in_progress': all_tickets.filter(status="IN_PROGRESS").count(),
        'resolved': all_tickets.filter(status="RESOLVED").count(),
        'critical': all_tickets.filter(urgency="CRITICAL").count(),
        'overdue': sum(1 for t in all_tickets.filter(status__in=["NEW", "IN_PROGRESS"]) if t.is_overdue),
    }

    return render(request, "tickets/dashboard.html", {
        "tickets": tickets_list,
        "status": status,
        "urgency": urgency,
        "search": search,
        "summary": summary,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        login_value = request.POST.get("login", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=login_value, password=password)

        # if they typed an email, try finding username by email
        if user is None:
            try:
                u = User.objects.get(email=login_value)
                user = authenticate(
                    request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        messages.error(request, "Invalid username/email or password.")

    return render(request, "auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


# --- placeholders (we will implement next) ---
@login_required
def ticket_create(request):
    # technicians cannot create tickets
    if request.user.role == "technician":
        return HttpResponseForbidden("Access denied")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        urgency = request.POST.get("urgency", "MEDIUM")
        category = request.POST.get("category", "OTHER")

        if not title or not description:
            messages.error(request, "Title and description are required.")
            return redirect("ticket_create")

        t = Ticket.objects.create(
            title=title,
            description=description,
            urgency=urgency,
            category=category,
            created_by=request.user
        )

        TicketHistory.objects.create(
            ticket=t,
            actor=request.user,
            action="CREATED",
            to_status=t.status,
            note="Ticket created"
        )

        return redirect("ticket_detail", ticket_id=t.id)

    return render(request, "tickets/create.html")


@login_required
def ticket_detail(request, ticket_id):
    t = get_object_or_404(Ticket, id=ticket_id)

    # Access rules
    if request.user.role == "user" and t.created_by != request.user:
        return HttpResponseForbidden("Access denied")
    if request.user.role == "technician" and t.assigned_to != request.user:
        return HttpResponseForbidden("Access denied")

    technicians = User.objects.filter(role="technician").order_by(
        "username") if request.user.role == "admin" else None

    return render(request, "tickets/detail.html", {
        "ticket": t,
        "technicians": technicians
    })


@login_required
def ticket_assign(request, ticket_id):
    if request.user.role != "admin":
        return HttpResponseForbidden("Access denied")

    t = get_object_or_404(Ticket, id=ticket_id)
    tech_id = request.POST.get("technician_id")
    tech = get_object_or_404(User, id=tech_id, role="technician")

    t.assigned_to = tech
    t.save()

    TicketHistory.objects.create(
        ticket=t, actor=request.user, action="ASSIGNED",
        note=f"Assigned to {tech.username}"
    )

    return redirect("ticket_detail", ticket_id=t.id)


@login_required
def ticket_status(request, ticket_id):
    t = get_object_or_404(Ticket, id=ticket_id)

    if request.user.role not in ["admin", "technician"]:
        return HttpResponseForbidden("Access denied")
    if request.user.role == "technician" and t.assigned_to != request.user:
        return HttpResponseForbidden("Access denied")

    new_status = request.POST.get("status")
    old_status = t.status
    t.status = new_status

    # Track resolved and closed timestamps
    if new_status == "RESOLVED" and not t.resolved_at:
        t.resolved_at = timezone.now()
    if new_status == "CLOSED" and not t.closed_at:
        t.closed_at = timezone.now()

    t.save()

    TicketHistory.objects.create(
        ticket=t, actor=request.user, action="STATUS_CHANGED",
        from_status=old_status, to_status=new_status, note="Status updated"
    )

    return redirect("ticket_detail", ticket_id=t.id)


@login_required
def ticket_comment(request, ticket_id):
    t = get_object_or_404(Ticket, id=ticket_id)

    if request.user.role == "user" and t.created_by != request.user:
        return HttpResponseForbidden("Access denied")
    if request.user.role == "technician" and t.assigned_to != request.user:
        return HttpResponseForbidden("Access denied")

    content = request.POST.get("content", "").strip()
    if content:
        Comment.objects.create(ticket=t, author=request.user, content=content)
        TicketHistory.objects.create(
            ticket=t, actor=request.user, action="COMMENT_ADDED", note="Comment added")

    return redirect("ticket_detail", ticket_id=t.id)


@login_required
def ticket_take(request, ticket_id):
    t = get_object_or_404(Ticket, id=ticket_id)

    if request.user.role != "technician":
        return HttpResponseForbidden("Only technicians can take tickets")

    if t.assigned_to is not None:
        return HttpResponseForbidden("Ticket already assigned")

    t.assigned_to = request.user
    t.save()

    TicketHistory.objects.create(
        ticket=t,
        actor=request.user,
        action="ASSIGNED",
        note="Technician took the ticket"
    )

    return redirect("ticket_detail", ticket_id=t.id)


@login_required
def board(request):
    u = request.user

    tickets = Ticket.objects.all()

    if u.role == "technician":
        tickets = tickets.filter(assigned_to=u)
    elif u.role == "user":
        tickets = tickets.filter(created_by=u)

    cols = {
        "NEW": tickets.filter(status="NEW").order_by("-created_at"),
        "IN_PROGRESS": tickets.filter(status="IN_PROGRESS").order_by("-created_at"),
        "RESOLVED": tickets.filter(status="RESOLVED").order_by("-created_at"),
        "CLOSED": tickets.filter(status="CLOSED").order_by("-created_at"),
    }

    return render(request, "tickets/board.html", {"cols": cols})


@login_required
@require_POST
def api_move_ticket(request, ticket_id):
    t = get_object_or_404(Ticket, id=ticket_id)

    # access rules
    if request.user.role == "user" and t.created_by != request.user:
        return JsonResponse({"ok": False, "error": "Access denied"}, status=403)

    if request.user.role == "technician":
        if t.assigned_to != request.user:
            return JsonResponse({"ok": False, "error": "Access denied"}, status=403)

    new_status = request.POST.get("status")
    if new_status not in ["NEW", "IN_PROGRESS", "RESOLVED", "CLOSED"]:
        return JsonResponse({"ok": False, "error": "Invalid status"}, status=400)

    old_status = t.status
    t.status = new_status

    # Track resolved and closed timestamps
    if new_status == "RESOLVED" and not t.resolved_at:
        t.resolved_at = timezone.now()
    if new_status == "CLOSED" and not t.closed_at:
        t.closed_at = timezone.now()

    t.save()

    TicketHistory.objects.create(
        ticket=t,
        actor=request.user,
        action="STATUS_CHANGED",
        from_status=old_status,
        to_status=new_status,
        note="Moved on board"
    )

    return JsonResponse({"ok": True})


@login_required
def analytics(request):
    """Analytics dashboard with comprehensive statistics"""

    # Base queryset - admins see all, others see their scope
    tickets = Ticket.objects.all()
    if request.user.role == "technician":
        tickets = tickets.filter(assigned_to=request.user)
    elif request.user.role == "user":
        tickets = tickets.filter(created_by=request.user)

    # Status distribution
    status_stats = tickets.values('status').annotate(
        count=Count('id')).order_by('status')

    # Urgency distribution
    urgency_stats = tickets.values('urgency').annotate(
        count=Count('id')).order_by('urgency')

    # Category distribution
    category_stats = tickets.values('category').annotate(
        count=Count('id')).order_by('category')

    # Time-based statistics (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tickets = tickets.filter(created_at__gte=thirty_days_ago)

    # Tickets created per day (last 30 days)
    tickets_by_day = recent_tickets.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(count=Count('id')).order_by('date')

    # Average resolution time (in hours) for resolved tickets
    resolved_tickets = tickets.filter(resolved_at__isnull=False)
    avg_resolution_time = None
    if resolved_tickets.exists():
        total_time = sum([t.time_to_resolve or 0 for t in resolved_tickets])
        avg_resolution_time = round(total_time / resolved_tickets.count(), 2)

    # Overdue tickets
    overdue_count = sum(1 for t in tickets.filter(
        status__in=["NEW", "IN_PROGRESS"]
    ) if t.is_overdue)

    # Technician performance (admin only)
    tech_stats = None
    if request.user.role == "admin":
        technicians = User.objects.filter(role="technician")
        tech_stats = []
        for tech in technicians:
            tech_tickets = Ticket.objects.filter(assigned_to=tech)
            resolved = tech_tickets.filter(
                status__in=["RESOLVED", "CLOSED"]).count()
            in_progress = tech_tickets.filter(status="IN_PROGRESS").count()
            tech_stats.append({
                'technician': tech,
                'total': tech_tickets.count(),
                'resolved': resolved,
                'in_progress': in_progress,
            })

    # Recent activity
    recent_history = TicketHistory.objects.select_related(
        'ticket', 'actor'
    ).order_by('-created_at')[:10]

    # Summary counts
    summary = {
        'total': tickets.count(),
        'new': tickets.filter(status="NEW").count(),
        'in_progress': tickets.filter(status="IN_PROGRESS").count(),
        'resolved': tickets.filter(status="RESOLVED").count(),
        'closed': tickets.filter(status="CLOSED").count(),
        'critical': tickets.filter(urgency="CRITICAL").count(),
        'overdue': overdue_count,
    }

    # Prepare JSON for charts
    import json
    # Convert date objects to strings for JSON serialization
    tickets_by_day_serializable = [
        {**d, 'date': d['date'].isoformat() if hasattr(d['date'],
                                                       'isoformat') else str(d['date'])}
        for d in tickets_by_day
    ]
    context = {
        'summary': summary,
        'status_stats': list(status_stats),
        'urgency_stats': list(urgency_stats),
        'category_stats': list(category_stats),
        'tickets_by_day': list(tickets_by_day),
        'avg_resolution_time': avg_resolution_time,
        'tech_stats': tech_stats,
        'recent_history': recent_history,
        'status_stats_json': json.dumps(list(status_stats)),
        'urgency_stats_json': json.dumps(list(urgency_stats)),
        'category_stats_json': json.dumps(list(category_stats)),
        'tickets_by_day_json': json.dumps(tickets_by_day_serializable),
    }

    return render(request, "tickets/analytics.html", context)


@login_required
def export_tickets(request):
    """Export tickets to CSV"""
    tickets = Ticket.objects.all()

    if request.user.role == "technician":
        tickets = tickets.filter(assigned_to=request.user)
    elif request.user.role == "user":
        tickets = tickets.filter(created_by=request.user)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Title', 'Status', 'Urgency', 'Category',
        'Created By', 'Assigned To', 'Created At', 'Resolved At',
        'Time to Resolve (hours)', 'Is Overdue'
    ])

    for ticket in tickets:
        writer.writerow([
            ticket.id,
            ticket.title,
            ticket.status,
            ticket.urgency,
            ticket.category,
            ticket.created_by.username,
            ticket.assigned_to.username if ticket.assigned_to else 'Unassigned',
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            ticket.resolved_at.strftime(
                '%Y-%m-%d %H:%M') if ticket.resolved_at else '',
            ticket.time_to_resolve if ticket.time_to_resolve else '',
            'Yes' if ticket.is_overdue else 'No',
        ])

    return response
