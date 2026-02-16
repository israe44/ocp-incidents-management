#!/usr/bin/env python
"""Script to create sample data for the OCP Incidents system"""

from datetime import timedelta
from django.utils import timezone
from tickets.models import Ticket, TicketHistory, Comment
from users.models import User
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def create_sample_tickets():
    # Get users
    admin = User.objects.get(username='israe44')
    user1 = User.objects.get(username='user1')
    user2 = User.objects.get(username='user2')
    user3 = User.objects.get(username='user3')
    tech1 = User.objects.get(username='tech1')
    tech_network = User.objects.get(username='tech_network')
    tech_software = User.objects.get(username='tech_software')

    # Create diverse sample tickets
    tickets_data = [
        {
            'title': 'Server Down - Production Environment',
            'description': 'The main production server is not responding. All applications are offline.',
            'urgency': 'CRITICAL',
            'category': 'INFRASTRUCTURE',
            'created_by': user1,
            'assigned_to': tech1,
            'status': 'IN_PROGRESS'
        },
        {
            'title': 'Cannot Access Email System',
            'description': 'Unable to login to Outlook. Getting authentication error.',
            'urgency': 'HIGH',
            'category': 'ACCESS',
            'created_by': user2,
            'assigned_to': tech_software,
            'status': 'NEW'
        },
        {
            'title': 'Slow Internet Connection in Building A',
            'description': 'Network speed is very slow, affecting all departments in Building A.',
            'urgency': 'MEDIUM',
            'category': 'CONNECTIVITY',
            'created_by': user1,
            'assigned_to': tech_network,
            'status': 'IN_PROGRESS'
        },
        {
            'title': 'Printer Not Working - Finance Department',
            'description': 'HP LaserJet printer shows error code 49. Need urgent fix for reports.',
            'urgency': 'MEDIUM',
            'category': 'HARDWARE',
            'created_by': user3,
            'status': 'NEW'
        },
        {
            'title': 'Software License Renewal',
            'description': 'Microsoft Office licenses expiring next week. Need renewal.',
            'urgency': 'LOW',
            'category': 'SOFTWARE',
            'created_by': user2,
            'status': 'NEW'
        },
        {
            'title': 'Database Performance Issues',
            'description': 'Queries taking too long to execute. Database needs optimization.',
            'urgency': 'HIGH',
            'category': 'DATA',
            'created_by': user1,
            'assigned_to': tech1,
            'status': 'RESOLVED'
        },
        {
            'title': 'New Employee Workstation Setup',
            'description': 'Need to setup computer, email, and access rights for new employee starting Monday.',
            'urgency': 'MEDIUM',
            'category': 'OTHER',
            'created_by': user3,
            'assigned_to': tech_software,
            'status': 'CLOSED'
        },
    ]

    print('Creating sample tickets...\n')
    for i, data in enumerate(tickets_data, 1):
        ticket = Ticket.objects.create(
            title=data['title'],
            description=data['description'],
            urgency=data['urgency'],
            category=data['category'],
            created_by=data['created_by'],
            assigned_to=data.get('assigned_to'),
            status=data['status']
        )

        # Adjust created_at for variety
        ticket.created_at = timezone.now() - timedelta(days=i, hours=i*2)

        # Set resolved_at for resolved tickets
        if data['status'] == 'RESOLVED':
            ticket.resolved_at = ticket.created_at + timedelta(hours=12)
            ticket.save()
        elif data['status'] == 'CLOSED':
            ticket.resolved_at = ticket.created_at + timedelta(hours=6)
            ticket.closed_at = ticket.created_at + timedelta(hours=8)
            ticket.save()
        else:
            ticket.save()

        # Create history
        TicketHistory.objects.create(
            ticket=ticket,
            actor=data['created_by'],
            action='CREATED',
            to_status=ticket.status,
            note='Ticket created',
            created_at=ticket.created_at
        )

        if data.get('assigned_to'):
            TicketHistory.objects.create(
                ticket=ticket,
                actor=admin,
                action='ASSIGNED',
                note=f'Assigned to {data["assigned_to"].username}',
                created_at=ticket.created_at + timedelta(minutes=30)
            )

        # Add comments for some tickets
        if i % 2 == 0:
            Comment.objects.create(
                ticket=ticket,
                author=data['created_by'],
                content='This is affecting multiple users. Please prioritize.',
                created_at=ticket.created_at + timedelta(hours=1)
            )

            if data.get('assigned_to'):
                Comment.objects.create(
                    ticket=ticket,
                    author=data['assigned_to'],
                    content='Working on it. Will update soon.',
                    created_at=ticket.created_at + timedelta(hours=2)
                )

        print(
            f'✓ Ticket #{ticket.id}: {ticket.title} [{ticket.status}] - {ticket.urgency}')

    print(f'\n=== TICKETS CREATED ===')
    print(f'Total Tickets: {Ticket.objects.count()}')
    print(f'NEW: {Ticket.objects.filter(status="NEW").count()}')
    print(
        f'IN_PROGRESS: {Ticket.objects.filter(status="IN_PROGRESS").count()}')
    print(f'RESOLVED: {Ticket.objects.filter(status="RESOLVED").count()}')
    print(f'CLOSED: {Ticket.objects.filter(status="CLOSED").count()}')


if __name__ == '__main__':
    create_sample_tickets()
