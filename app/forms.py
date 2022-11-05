from django import forms
from django.db import connections
from django.core.cache import cache

DAY_IN_SEC = 24 * 60 * 60


def get_choices(col: str):
    # Try to get choices from cache
    col_choices_key = f'{col}-CHOICES'
    if col_choices_key in cache:
        return cache[col_choices_key]

    # If choices are not in cache, query db, set cache and then return
    with connections['default'].cursor() as cursor:
        cursor.execute(f'SELECT DISTINCT {col} FROM fact_table')
        choices = [('', '---------')]
        for row in cursor.fetchall():
            choices.append((row[0], row[0]))

    cache.set(col_choices_key, choices, timeout=DAY_IN_SEC)
    return choices


class ImoForm(forms.Form):
    performance = forms.IntegerField(label='Crane Performance', min_value=0, max_value=100)
    mi_rate = forms.IntegerField(label='Manual Intervention Count')
    container = forms.IntegerField(label='Container Handled')
    cyc_time = forms.TimeField(label='Cycle Time')
    crane_key = forms.IntegerField(label='Crane Name')
    date_key = forms.CharField(label='Reported Date')
    maintenance_due_date_key = forms.DateField(label='Maintenance Due Date')
    verifier_key = forms.IntegerField(label='Verifier Key')
    # my_choice_field = forms.ChoiceField(choices=get_choices('col'), required=False)
    # my_date_field = forms.DateField(widget=forms.widgets.DateInput(attrs={'type': 'date'}), required=False)
