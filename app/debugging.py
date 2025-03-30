from datetime import datetime, timedelta
from .models import *
from django.utils import timezone

now = timezone.localtime(timezone.now())
start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

exams_scheduled = ScheduledExam.objects.filter(
    scheduled_datetime__range=(start_of_day, end_of_day)
)

# hour_start = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
# hour_end = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
# available_hours = []
# current_hour = hour_start
# while current_hour <= hour_end:
#     available_hours.append(current_hour.hour)
#     current_hour += timedelta(hours=1)

# print(available_hours)
    
    