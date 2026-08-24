# b/custom_filters.py


from django import template

register = template.Library()

@register.filter
def format_age(age_data):
    """Format age data to a readable string"""
    if not age_data:
        return '—'
    
    years = age_data.get('years', 0)
    months = age_data.get('months', 0)
    days = age_data.get('days', 0)
    
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    
    if not parts:
        return 'Newborn'
    
    return ', '.join(parts)