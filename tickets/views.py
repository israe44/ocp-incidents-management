from .models import Ticket, TicketHistory, Comment

from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from users.models import User


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

    tickets = tickets.order_by("-created_at")

    return render(request, "tickets/dashboard.html", {
        "tickets": tickets,
        "status": status,
        "urgency": urgency,
        "search": search
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

        if not title or not description:
            messages.error(request, "Title and description are required.")
            return redirect("ticket_create")

        t = Ticket.objects.create(
            title=title,
            description=description,
            urgency=urgency,
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
