from django.db import models

class Classroom(models.Model):
    LECTURE = 'Lecture'
    LAB = 'Lab'
    SEMINAR = 'Seminar'
    ROOM_TYPES = [(LECTURE, 'Lecture'), (LAB, 'Lab'), (SEMINAR, 'Seminar')]

    class_name = models.CharField(max_length=50)
    capacity = models.IntegerField()
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    availability = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.class_name} ({self.room_type})"


class Batch(models.Model):
    batch_name = models.CharField(max_length=50)
    course = models.CharField(max_length=50)
    year = models.IntegerField()
    student_count = models.IntegerField()
    classroom = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.batch_name} - {self.course}"


class Subject(models.Model):
    subject_code = models.CharField(max_length=20)
    subject_name = models.CharField(max_length=50)
    credits = models.IntegerField()
    semester = models.IntegerField()
    course = models.CharField(max_length=50)
    hours_per_week = models.IntegerField(default=3)

    def __str__(self):
        return f"{self.subject_name} ({self.subject_code})"
    
    
class TimeSlot(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"


class Faculty(models.Model):
    PROFESSOR = 'Professor'
    ASST_PROF = 'Asst. Professor'
    LECTURER = 'Lecturer'

    DESIGNATIONS = [
        (PROFESSOR, 'Professor'),
        (ASST_PROF, 'Asst. Professor'),
        (LECTURER, 'Lecturer'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_no = models.CharField(max_length=20)
    designation = models.CharField(max_length=50, choices=DESIGNATIONS)
    max_classes_per_day = models.IntegerField(default=4)
    max_classes_per_week = models.IntegerField(default=20)
    availability = models.CharField(max_length=100, default="Mon-Fri 9-3")

    def __str__(self):
        return self.name


class FacultySubject(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.faculty.name} teaches {self.subject.subject_name}"


class FacultyLeave(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    leave_date = models.DateField()
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')])

    def __str__(self):
        return f"{self.faculty.name} leave on {self.leave_date}"


class Timetable(models.Model):
    DAYS = [('Mon', 'Monday'), ('Tue', 'Tuesday'), ('Wed', 'Wednesday'),
            ('Thu', 'Thursday'), ('Fri', 'Friday'), ('Sat', 'Saturday')]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAYS)
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.batch.batch_name} - {self.subject.subject_name} - {self.day} {self.time_slot}"
