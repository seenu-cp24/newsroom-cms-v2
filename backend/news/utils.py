from datetime import datetime, timedelta
from django.utils import timezone


def get_editorial_date():

    now = timezone.localtime()

    if now.hour < 3:
        return (now - timedelta(days=1)).date()

    return now.date()
