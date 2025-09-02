import json
import statistics
import re
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key="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")  # replace with your key

# ----- Generate Timetable -----
def generate_timetables(subject_faculty_map, rooms, expanded_slots, n=1):
    """
    subject_faculty_map: dict like {"Maths": "Raju", "Hindi": "Ramesh"}
    rooms: list of classroom names
    expanded_slots: list of time slots like ["Mon-09:00-10:00", "Mon-10:00-11:00", ...]
    """

        # Convert mapping to string for GPT prompt
    mapping_str = "\n".join([f"{subj} -> {fac}" for subj, fac in subject_faculty_map.items()])

        # Build GPT prompt
    prompt = f"""
    You are expert timetable generator
    Generate {n} valid class timetables in JSON format.

    Subjects & Assigned Faculties:
    {mapping_str}

    Rooms: {rooms}
    Available Time slots: {expanded_slots}

    Rules:
    1. Each subject must be taught only by its assigned faculty.
    2. Lunch break: Either 11:00-12:00 or 12:00-13:00.
    3. No faculty or room conflicts.
    4. Max 2 periods per subject per day if blank slot continuous previous slot.
    5. Balance faculty workload across days.
    6. Fill all timeslots from Mon-Sat, except lunch break.

    Return JSON like:
    {{
        "timetables": [
            {{
            "name": "Option 1",
            "slots": [
                {{"room": "101", "time": "Mon-09:00-10:00", "subject": "Maths", "faculty": "Raju"}},
                {{"room": "-", "time": "Mon-12:00-13:00", "subject": "Lunch Break", "faculty": "-"}}
            ]
            }}
        ]
    }}
    """

    # Call GPT
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    # Post-process GPT output to timetable grid
    timetable_grid = {}
    for timetable in result["timetables"]:
        grid = {}
        for slot in timetable["slots"]:
            # Example slot["time"]: "Mon-09:00-10:00"
            match = re.match(r"^([A-Za-z]+)\s*-\s*(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})$", slot["time"])
            if not match:
                continue

            day = match.group(1).strip()
            start = match.group(2)
            end = match.group(3)
            time_range = f"{start} - {end}"

            # Enforce correct faculty assignment
            subject = slot["subject"].strip()
            if subject in subject_faculty_map:
                slot["faculty"] = subject_faculty_map[subject]

            if time_range not in grid:
                grid[time_range] = {}
            grid[time_range][day] = {
                "subject": subject,
                "faculty": slot["faculty"].strip(),
                "room": slot["room"].strip()
            }

        timetable_grid[timetable["name"]] = grid

    return timetable_grid


# ----- Validate Timetable -----
def validate_timetable(timetable, subjects, faculty, rooms, slots):
    """
    Validates timetable and returns errors, faculty balance, room utilization, learning outcome
    timetable: {"slots": [{"time": ..., "subject": ..., "faculty": ..., "room": ...}, ...]}
    subjects: list of subject names
    faculty: list of faculty names
    rooms: list of room names
    slots: list of time slots
    """
    errors = []
    seen = set()

    # Track usage
    faculty_load = {f: 0 for f in faculty}
    room_load = {r: 0 for r in rooms}
    subject_coverage = {s: 0 for s in subjects}

    for slot in timetable["slots"]:
        key_room = (slot["room"], slot["time"])
        key_faculty = (slot["faculty"], slot["time"])

        if key_room in seen:
            errors.append(f"Room conflict: {slot['room']} at {slot['time']}")
        if key_faculty in seen:
            errors.append(f"Faculty conflict: {slot['faculty']} at {slot['time']}")

        seen.add(key_room)
        seen.add(key_faculty)

        # Count usage
        faculty_name = slot["faculty"].strip()
        room_name = slot["room"].strip()
        subject_name = slot["subject"].strip()

        faculty_load[faculty_name] = faculty_load.get(faculty_name, 0) + 1
        room_load[room_name] = room_load.get(room_name, 0) + 1
        subject_coverage[subject_name] = subject_coverage.get(subject_name, 0) + 1

    total_classes = len(timetable["slots"])

    # Faculty balance
    faculty_classes = list(faculty_load.values())
    if len(faculty_classes) > 1:
        std_dev = statistics.pstdev(faculty_classes)
        faculty_balance = max(0, 100 - (std_dev * 30))
    else:
        faculty_balance = 100

    # Room utilization
    ideal_room_use = total_classes / len(rooms) if rooms else 1
    room_diff = sum(abs(room_load[r] - ideal_room_use) for r in rooms)
    room_utilization = max(0, 100 - (room_diff / (total_classes or 1) * 100))

    # Learning outcomes
    achieved_subjects = sum(1 for s in subject_coverage if subject_coverage[s] > 0)
    coverage_score = (achieved_subjects / len(subjects)) * 100
    subj_classes = list(subject_coverage.values())
    if len(subj_classes) > 1:
        subj_std = statistics.pstdev(subj_classes)
        distribution_score = max(0, 100 - subj_std * 40)
    else:
        distribution_score = 100
    learning_outcome = (coverage_score * 0.6) + (distribution_score * 0.4)

    return errors, round(max(0, min(faculty_balance, 100)),2), round(max(0, min(room_utilization, 100)),2), round(max(0, min(learning_outcome, 100)),2)

