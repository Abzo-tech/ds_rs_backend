import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('discover_senegal')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'purge-expired-stories-every-hour': {
        'task': 'feed.tasks.purge_expired_stories',
        'schedule': crontab(minute=0),
    },
    'check-report-threshold-every-6-hours': {
        'task': 'feed.tasks.check_report_threshold',
        'schedule': crontab(minute=0, hour='*/6'),
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
