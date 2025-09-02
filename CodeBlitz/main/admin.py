from django.contrib import admin

from .models import *

admin.site.register(Subject)
admin.site.register(Classroom)
admin.site.register(TimeSlot)
admin.site.register(Batch)
admin.site.register(Faculty)
admin.site.register(FacultySubject)
admin.site.register(FacultyLeave)
admin.site.register(Timetable)