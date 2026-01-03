"""
Management command to sync data from agents to Django models.
"""

from django.core.management.base import BaseCommand
from dashboard.utils import sync_post_log, sync_trend_data


class Command(BaseCommand):
    help = 'Sync data from agent log files to Django database'

    def handle(self, *args, **options):
        self.stdout.write('Syncing post logs...')
        sync_post_log()
        self.stdout.write(self.style.SUCCESS('Post logs synced'))
        
        self.stdout.write('Syncing trend data...')
        sync_trend_data()
        self.stdout.write(self.style.SUCCESS('Trend data synced'))
        
        self.stdout.write(self.style.SUCCESS('Sync completed!'))


