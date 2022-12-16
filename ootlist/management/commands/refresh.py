from django.core.management.base import BaseCommand
from ootlist.scraper import scrape

# You run this code using python manage.py refresh, e.g. in a cronjob

class Command(BaseCommand): # must be called command, use file name to name the functionality
    def handle(self, *args, **options):
        scrape()

