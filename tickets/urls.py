from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("tickets/create/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:ticket_id>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:ticket_id>/assign/",
         views.ticket_assign, name="ticket_assign"),
    path("tickets/<int:ticket_id>/status/",
         views.ticket_status, name="ticket_status"),
    path("tickets/<int:ticket_id>/comment/",
         views.ticket_comment, name="ticket_comment"),
    path("tickets/<int:ticket_id>/take/",
         views.ticket_take, name="ticket_take"),

    path("board/", views.board, name="board"),
    path("analytics/", views.analytics, name="analytics"),
    path("export/", views.export_tickets, name="export_tickets"),

    path("api/tickets/<int:ticket_id>/move/",
         views.api_move_ticket, name="api_move_ticket"),
]
