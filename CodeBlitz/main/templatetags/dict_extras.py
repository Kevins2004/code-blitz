from django import template

register = template.Library()

@register.filter
def timeslot(slot):
    return f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"

@register.filter
def get_item(dictionary, key):
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return None
