from django.shortcuts import render, redirect
from .models import *
from .utils import generate_timetables, validate_timetable
from django.contrib import messages
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from django.contrib import messages

@csrf_exempt
def publish_timetable(request):
    if request.method == "POST":
        try:
            # Example: your generated timetable stored in session
            timetable_grid = request.session.get("timetable_grid")
            batch_id = request.session.get("batch_id")
            if not batch_id:
                messages.error(request, "No batch selected to publish.")
                return redirect("schedule")  # your timetable page URL name

            batch = Batch.objects.get(id=batch_id)


            if not timetable_grid:
                messages.error(request, "No timetable available to publish.")
                return redirect("schedule_page")  # replace with your URL name

            # Iterate over timetable_grid to insert entries
            for time_range, days_data in timetable_grid.items():
                start_str, end_str = time_range.split("-")
                start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
                end_time = datetime.strptime(end_str.strip(), "%H:%M").time()

                time_slot, created = TimeSlot.objects.get_or_create(
                    start_time=start_time,
                    end_time=end_time
                )

                for day, entry in days_data.items():
                    if entry["subject"] == "Lunch Break":
                        continue  # skip lunch

                    subject = Subject.objects.get(subject_name=entry["subject"])
                    faculty = Faculty.objects.get(name=entry["faculty"])
                    classroom = Classroom.objects.get(class_name=entry["room"])
                    batch = Batch.objects.get(id=batch_id)

                    Timetable.objects.create(
                        batch=batch,
                        subject=subject,
                        faculty=faculty,
                        classroom=classroom,
                        day=day,
                        time_slot=time_slot
                    )

            messages.success(request, "Timetable published successfully!")
            return redirect("schedule")

        except Exception as e:
            messages.error(request, f"Error publishing timetable: {str(e)}")
            return redirect("schedule")
    
    

def export_timetable_csv(request):
    timetable_grid = request.session.get("timetable_grid", {})
    time_slots = request.session.get("time_slots", [])
    days = request.session.get("days", [])

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="timetable.csv"'

    writer = csv.writer(response)
    writer.writerow(["Time"] + days)  # Header row

    for slot in time_slots:
        row = [slot]
        for day in days:
            cell = ""
            if slot in timetable_grid and day in timetable_grid[slot]:
                entry = timetable_grid[slot][day]
                if entry:
                    cell = f"{entry.get('subject','')} | {entry.get('faculty','')} | {entry.get('room','')}"
            row.append(cell)
        writer.writerow(row)

    return response


class ExpandedSlot:
    def __init__(self, start, end, is_break=False):
        self.start_time = start
        self.end_time = end
        self.is_break = is_break
        

def expand_time_slots(time_slots):
    expanded = []
    for slot in time_slots:
        start = slot.start_time
        end = slot.end_time
        current = start
        while current < end:
            next_hour = (datetime.combine(datetime.today(), current) + timedelta(hours=1)).time()
            expanded.append(ExpandedSlot(current, next_hour, is_break=(current.hour == 12)))
            current = next_hour
    return expanded


def home(request):
    # Fetch published timetable entries
    timetable_entries = Timetable.objects.all().select_related(
        "batch", "subject", "faculty", "classroom", "time_slot"
    )
    
    active_classrooms = Classroom.objects.filter(availability=True).count()
    total_faculty = Faculty.objects.count()

    # Prepare timetable grid
    timetable_grid = defaultdict(lambda: defaultdict(dict))  # slot -> day -> entry
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    time_slots = []

    for entry in timetable_entries:
        slot_str = f"{entry.time_slot.start_time.strftime('%H:%M')} - {entry.time_slot.end_time.strftime('%H:%M')}"
        time_slots.append(slot_str)
        timetable_grid[slot_str][entry.day] = {
            "subject": entry.subject.subject_name,
            "faculty": entry.faculty.name,
            "room": entry.classroom.class_name
        }

    # Remove duplicates & sort slots
    time_slots = sorted(list(set(time_slots)))

    context = {
        "timetable_grid": timetable_grid,
        "time_slots": time_slots,
        "days": days,
        "active_classrooms" : active_classrooms,
        "total_faculty" : total_faculty,
    }

    return render(request, "main/index.html", context)


def schedule(request):
    days = request.POST.getlist("days") or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    selected_timeslot_id = request.POST.get("timeslot")  # single choice now

    timeslots = TimeSlot.objects.all()  # original DB slots
    expanded_times = []
    formatted_times = []  # <-- always initialize

    if selected_timeslot_id:  
        selected_slot = TimeSlot.objects.get(id=selected_timeslot_id)
        expanded_times = expand_time_slots([selected_slot])  # expand only chosen slot
        formatted_times = [
            f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}"
            for s in expanded_times
        ]

    timetable_grid = {}
    metrics = {}  # <-- store metrics here
    
    if request.method == "POST" and formatted_times:
    # Get user-selected subjects or default to all
        selected_subjects = request.POST.getlist("subjects") or list(
            Subject.objects.values_list("subject_name", flat=True)
        )

        # Get rooms (user-selected or all)
        rooms = request.POST.getlist("classrooms") or list(
            Classroom.objects.values_list("class_name", flat=True)
        )

        # Fetch faculty-subject mapping dynamically from DB
        faculty_subjects = FacultySubject.objects.filter(
            subject__subject_name__in=selected_subjects
        )
        subject_faculty_map = {
            fs.subject.subject_name: fs.faculty.name for fs in faculty_subjects
        }

        # Generate timetable using dynamic mapping
        timetable_grid_full = generate_timetables(subject_faculty_map, rooms, formatted_times)
        timetable_grid = timetable_grid_full.get("Option 1", {})
        

        # Prepare slots for validation
        slots_for_validation = []
        for time_range, days_dict in timetable_grid.items():
            for day, entry in days_dict.items():
                slots_for_validation.append({
                    "time": f"{day}-{time_range}",
                    "subject": entry["subject"],
                    "faculty": entry["faculty"],
                    "room": entry["room"]
                })

        # Validate timetable
        errors, faculty_balance, room_utilization, learning_outcome = validate_timetable(
            {"slots": slots_for_validation},
            selected_subjects,
            list(subject_faculty_map.values()),
            rooms,
            formatted_times
        )

        metrics = {
            "errors": errors,
            "faculty_balance": faculty_balance,
            "room_utilization": room_utilization,
            "learning_outcome": learning_outcome
        }
        
        # Store timetable in session for CSV export
        batch_id = request.POST.get("batch")  # get selected batch from form
        request.session["batch_id"] = batch_id 
        request.session['timetable_grid'] = timetable_grid
        request.session['time_slots'] = formatted_times
        request.session['days'] = days


    context = {
        "batches": Batch.objects.all(),
        "subjects": Subject.objects.all(),
        "faculty": Faculty.objects.all(),
        "classrooms": Classroom.objects.all(),
        "timeslots": timeslots,        # for dropdown (big slots)
        "time_slots": formatted_times, # now strings instead of objects
        "timetable_grid": timetable_grid,
        "metrics": metrics,            # <-- pass metrics
        "days": days,
    }
    
    return render(request, "main/schedule.html", context)



def batch(request):
    classrooms = Classroom.objects.all()

    if request.method == "POST":
        batch_name = request.POST.get("batch_name")
        course = request.POST.get("course")
        year = request.POST.get("year")
        student_count = request.POST.get("student_count")
        classroom_id = request.POST.get("classroom")  # This is the ID from the <select>

        try:
            classroom = Classroom.objects.get(id=classroom_id)  # Convert ID to instance

            Batch.objects.create(
                batch_name=batch_name,
                course=course,
                year=year,
                student_count=student_count,
                classroom=classroom  # Assign the instance
            )

            messages.success(request, "Batch added successfully!")
            return redirect("batch")  # Redirect back to the batch page

        except Classroom.DoesNotExist:
            messages.error(request, "Selected classroom does not exist.")
        except Exception as e:
            messages.error(request, f"Error adding batch: {str(e)}")

    return render(request, "main/batch.html", {"classrooms": classrooms})



def classroom(request):
    if request.method == "POST":
        class_name = request.POST.get("class_name")
        capacity = request.POST.get("capacity")
        room_type = request.POST.get("room_type")
        availability = request.POST.get("availability")  # "Available" or "Unavailable"

        # Convert availability to boolean
        is_available = True if availability == "Available" else False

        # Optional validation
        if not all([class_name, capacity, room_type, availability]):
            messages.error(request, "All fields are required.")
            return redirect("classroom")  # or render with error

        # Save to database
        Classroom.objects.create(
            class_name=class_name,
            capacity=int(capacity),
            room_type=room_type,
            availability=is_available
        )

        messages.success(request, f"Classroom '{class_name}' added successfully!")
        return redirect("classroom")  # reload page after insert

    # GET request
    return render(request, "main/classroom.html")





def teacher(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            email = request.POST.get("email")
            phone_no = request.POST.get("phone")  # matches form field
            designation = request.POST.get("designation")
            max_classes_per_day = request.POST.get("max_classes_day")
            max_classes_per_week = request.POST.get("max_classes_week")
            availability = request.POST.get("availability")

            # Create Faculty instance
            Faculty.objects.create(
                name=name,
                email=email,
                phone_no=phone_no,
                designation=designation,
                max_classes_per_day=max_classes_per_day,
                max_classes_per_week=max_classes_per_week,
                availability=availability
            )

            messages.success(request, "Teacher added successfully!")
            return redirect("teacher")  # redirect back to the form

        except Exception as e:
            messages.error(request, f"Error adding teacher: {str(e)}")
            return redirect("teacher")

    return render(request, "main/teacher.html")



def subject(request) :
    return render(request,"main/subject.html")

