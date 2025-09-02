from django.contrib import admin
from django.urls import path
from main import views

urlpatterns = [
    path('',views.home,name="home"),
    path('schedule/',views.schedule,name="schedule"),
    path('batch/',views.batch,name="batch"),
    path('classroom/',views.classroom,name="classroom"),
    path('teacher/',views.teacher,name="teacher"),
    path('subject/',views.subject,name="subject"),
    path('export-timetable/', views.export_timetable_csv, name='export_timetable_csv'),
    path('publish_timetable/', views.publish_timetable, name='publish_timetable'),
]

