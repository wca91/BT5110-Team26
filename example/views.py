from django.shortcuts import render
from django.db import connections
from django.shortcuts import redirect
from django.http import Http404
from django.db.utils import IntegrityError
from plotly.offline import plot
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import pandas as pd

from example.utils import namedtuplefetchall, clamp
from example.forms import ImoForm

# Create your views here.
PAGE_SIZE = 20

COLUMNS = [
    'performance',
    'mi_rate',
    'container',
    'cyc_time',
    'crane_key',
    'maintenance_due_date_key',
    'date_key',
    'verifier_key'
]

def index(request):
    """Shows the main page"""
    context = {'nbar': 'home'}
    return render(request, 'index.html', context)



def crane_information(request, page=1):
    """Shows the emissions table page"""
    msg = None
    order_by = request.GET.get('order_by', '')
    order_by = order_by if order_by in COLUMNS else 'crane_key'

    with connections['default'].cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM fact_table')
        count = cursor.fetchone()[0]
        num_pages = (count - 1) // PAGE_SIZE + 1
        page = clamp(page, 1, num_pages)

        offset = (page - 1) * PAGE_SIZE
        cursor.execute(f'''
            SELECT {", ".join(COLUMNS)}
            FROM fact_table
            ORDER BY {order_by}
            OFFSET %s
            LIMIT %s
        ''', [offset, PAGE_SIZE])
        rows = namedtuplefetchall(cursor)

    crane_deleted = request.GET.get('deleted', False)
    if crane_deleted:
        msg = f'✔ Crane Information {crane_deleted} deleted'

    context = {
        'nbar': 'crane_information',
        'page': page,
        'rows': rows,
        'num_pages': num_pages,
        'msg': msg,
        'order_by': order_by
    }
    return render(request, 'crane_information.html', context)

def insert_update_values(form, post, action, imo, date_key):
    """
    Inserts or updates database based on values in form and action to take,
    and returns a tuple of whether action succeded and a message.
    """
    if not form.is_valid():
        return False, 'There were errors in your form'

    # Set values to None if left blank
    cols = COLUMNS[:]
    values = [post.get(col, None) for col in cols]
    values = [val if val != '' else None for val in values]
    cols = COLUMNS
    cols_length = ''



    if action == 'update':
        # Remove imo from updated fields
        cols, values = cols[1:], values[1:]
        length_cols = len(cols)

        for col, value in zip(cols, values):
            if col == 'cyc_time' or col == 'maintenance_due_date_key' or col == 'date_key':
                value = "'" + str(value) + "'"
            if length_cols == 1:
                cols_length = cols_length + (col + ' = ' + str(value))
            else:
                cols_length = cols_length + (col + ' = ' + str(value) + ' , ')
            length_cols -= 1

        with connections['default'].cursor() as cursor:
            query = "UPDATE fact_table SET {0} WHERE crane_key = {1} and date_key = '{2}';".format(cols_length, imo, date_key)
            cursor.execute(query)
        return True, '✔ Crane Information updated successfully'

    # Else insert
    with connections['default'].cursor() as cursor:
        cursor.execute(f'''
            INSERT INTO fact_table ({", ".join(cols)})
            VALUES ({", ".join(["%s"] * len(cols))});
        ''', values)
    return True, '✔ Crane Information inserted successfully'


def crane_information_insert(request, crane=None,date_key = None):
    """Shows the form where the user can insert or update a crane information"""
    success, form, msg, initial_values = False, None, None, {}
    is_update = crane is not None

    if is_update and request.GET.get('inserted', False):
        success, msg = True, f'✔ Crane Information {crane}, {date_key} inserted'

    if request.method == 'POST':
        # Since we set imo=disabled for updating, the value is not in the POST
        # data so we need to set it manually. Otherwise if we are doing an
        # insert, it will be None but filled out in the form
        if crane:
            request.POST._mutable = True
            request.POST['crane_key'] = crane
        else:

            crane = request.POST['crane_key']
            date_key = request.POST['date_key']

        form = ImoForm(request.POST)
        action = request.POST.get('action', None)

        if action == 'delete':
            with connections['default'].cursor() as cursor:
                cursor.execute("DELETE FROM fact_table WHERE crane_key = {0} and date_key = '{1}';".format(crane,date_key))
            return redirect(f'/crane_information?deleted={crane}')
        try:
            success, msg = insert_update_values(form, request.POST, action, crane, date_key)
            if success and action == 'insert':
                return redirect(f'/crane_information/crane/{crane}/{date_key}?inserted=true')
        except IntegrityError:
            success, msg = False, 'Crane Information already exists'
        except Exception as e:
            success, msg = False, f'Some unhandled error occured: {e}'
    elif crane:  # GET request and imo is set
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT * FROM fact_table WHERE crane_key = %s', [crane])
            try:
                initial_values = namedtuplefetchall(cursor)[0]._asdict()
            except IndexError:
                raise Http404(f'Crane Information {crane} not found')

    # Set dates (if present) to iso format, necessary for form
    # We don't use this in class, but you will need it for your project
    for field in ['doc_issue_date', 'doc_expiry_date']:
        if initial_values.get(field, None) is not None:
            initial_values[field] = initial_values[field].isoformat()

    # Initialize form if not done already
    form = form or ImoForm(initial=initial_values)
    if is_update:
        form['crane_key'].disabled = True

    context = {
        'nbar': 'Crane Information',
        'is_update': is_update,
        'crane': crane,
        'date': date_key,
        'form': form,
        'msg': msg,
        'success': success
    }
    return render(request, 'crane_information_insert.html', context)


def create_checkboxes(params, checkboxes):
    for checkbox in checkboxes:
        for option in checkbox["options"]:
            if option["value"] in params.getlist(checkbox["id"], []):
                option["checked"] = True
            else:
                option["checked"] = False

    return checkboxes


def visual_view(request):
    """
    Displaying graph with plotly
    """
    request_dict = request.GET
    print(request_dict)
    with connections['default'].cursor() as cursor:
        if request_dict != {}:
            month_value = request_dict['month']
            query = 'select f.crane_key, d.month_name_abbreviated, round(avg(f.performance),0) as metric ' \
                    "from fact_table f, d_date d WHERE f.date_key = d.date_actual and d.month_name_abbreviated = '{0}' " \
                    'group by f.crane_key, d.month_name_abbreviated ' \
                    'order by f.crane_key;'.format(month_value)
        else:
            query = 'select f.crane_key, d.month_name_abbreviated, round(avg(f.performance),0) as metric ' \
                    'from fact_table f, d_date d WHERE f.date_key = d.date_actual ' \
                    'group by f.crane_key, d.month_name_abbreviated ' \
                    'order by f.crane_key;'
        """query = 'SELECT type, count(imo), min(technical_efficiency_number), avg(technical_efficiency_number), max(technical_efficiency_number) ' \
                'FROM co2emission_reduced GROUP BY type ORDER BY type;'"""
        cursor.execute(query)
        records = cursor.fetchall()

        dict_df = {'crane': [], 'month_name': [], 'metric': []}
        for rows in records:
            dict_df['crane'].append(rows[0])
            dict_df['month_name'].append(rows[1])
            dict_df['metric'].append(rows[2])


        # for pie chart
        query = 'select v.verifier_name, count(DISTINCT f.crane_key) as count ' \
                'from fact_table f, verifier v WHERE f.verifier_key = v.verifier_key ' \
                'group by v.verifier_name;'
        cursor.execute(query)
        records = cursor.fetchall()
        pie_df = {'Port Terminal': [], 'Crane Count': []}
        for rows in records:
            pie_df['Port Terminal'].append(rows[0])
            pie_df['Crane Count'].append(rows[1])


    # Setting layout of the figure.
    bar_layout = {
        'title': 'Per Crane monthly performance',
        'xaxis_title': 'Crane Number',
        'yaxis_title': 'Crane Performance',
        'height': 700,
        'width': 1200,
    }

    pie_layout = {
        'title': '% of Crane Per Port Terminal',
        'height': 700,
        'width': 1000,
    }

    box_layout = {
        'title': 'Distribution Overview of Crane Performance',
        'height': 700,
        'width': 1000,
    }



    # List of graph objects for figure.
    df_visual = pd.DataFrame(dict_df)
    unique_month = df_visual['month_name'].unique()


    bar_graphs = go.Figure(layout=bar_layout)
    for x in unique_month:
        individual_month = df_visual.loc[df_visual['month_name'] == x]
        range_min = df_visual['metric'].min()-5
        range_max = df_visual['metric'].max()+5
        bar_graphs.add_bar(x=individual_month['crane'], y=individual_month['metric'], name=x)
        bar_graphs.update_yaxes(range=[range_min,range_max])
        box_graphs = go.Figure(data=[go.Box(x=individual_month['metric'], name='Crane Monthly Performance', marker_color='indianred')],
                               layout=box_layout)
        box_graphs.update_yaxes(tickangle=270)
        box_graphs.update_layout(template="plotly_dark")
    bar_graphs.update_layout(barmode='group',template = "plotly_dark")

    pie_graphs = go.Figure(data=[go.Pie(labels=pie_df['Port Terminal'], values=pie_df['Crane Count'])], layout=pie_layout)
    pie_graphs.update_layout(template="plotly_dark")




    # Getting HTML needed to render the plot.
    bar_div = plot({'data': bar_graphs, 'layout': bar_layout}, output_type='div')
    pie_div = plot({'data': pie_graphs, 'layout': pie_layout}, output_type='div')
    box_div = plot({'data': box_graphs, 'layout': box_layout}, output_type='div')


    checkbox = [
        {
            'id': 'year',
            'label': 'Year',
            'options': [
                {
                    'value': '2020',
                    'label': '2020',
                    'checked': True
                },
                {
                    'value': '2021',
                    'label': '2021',
                    'checked': True
                }
            ]
        },
        {
            'id': 'month',
            'label': 'Month',
            'options': [
                {
                    'value': 'Sep',
                    'label': 'Sep',
                    'checked': True
                },
                {
                    'value': 'Aug',
                    'label': 'Aug',
                    'checked': True
                }
            ]
        },
    ]

    # Setting context
    context = {
        'graphs': [
            bar_div,
            pie_div,
            box_div
        ],
        'checkboxes': create_checkboxes(request.GET, checkbox)
    }

    return render(request, 'visual.html', context)

def extended_view(request):
    """ 
    Displaying chart with plotly
    """
    # get params request.
    request_dict = request.GET
    print(request_dict)
    date_combine = date(2021, 5, 3)
    if request_dict != {} and request_dict['y_axis'] != 'f.cyc_time':
        y_axis = request_dict['y_axis']
        if y_axis == 'c.elect_drive':
            query = "SELECT c.crane_key, c.brand, {0} as metric, " \
                    "ROUND(AVG(f.performance)::NUMERIC,2) as performance_rate,LN(COUNT(*)) as scaled_count, " \
                    "(CASE  WHEN c.crane_key ISNULL AND c.brand ISNULL THEN 'Grand Total' " \
                    "WHEN c.crane_key ISNULL THEN 'Subtotal'||' '||c.crane_key ELSE c.crane_key|| ' ' || c.brand END) as label " \
                    "FROM fact_table f, crane c WHERE f.crane_key = c.crane_key " \
                    "GROUP BY ROLLUP(c.crane_key, c.brand, c.elect_drive) " \
                    "ORDER BY c.crane_key DESC, c.brand DESC".format(y_axis)

        elif y_axis == 'f.maintenance_due_key':
            query = "SELECT c.crane_key, c.brand,  Round(AVG(CURRENT_DATE - f.maintenance_due_date_key),-1) as metric, " \
                    "ROUND(AVG(f.performance)::NUMERIC,2) as performance_rate,LN(COUNT(*)) as scaled_count, " \
                    "(CASE  WHEN c.crane_key ISNULL AND c.brand ISNULL THEN 'Grand Total' " \
                    "WHEN c.crane_key ISNULL THEN 'Subtotal'||' '||c.crane_key ELSE c.crane_key|| ' ' || c.brand END) as label " \
                    "FROM fact_table f, crane c WHERE f.crane_key = c.crane_key " \
                    "GROUP BY ROLLUP(c.crane_key, c.brand) " \
                    "ORDER BY c.crane_key DESC, c.brand DESC".format(y_axis)

        else:
            query = "SELECT c.crane_key, c.brand,  ROUND(AVG({0})::NUMERIC,2) as metric, " \
                    "ROUND(AVG(f.performance)::NUMERIC,2) as performance_rate,LN(COUNT(*)) as scaled_count, " \
                    "(CASE  WHEN c.crane_key ISNULL AND c.brand ISNULL THEN 'Grand Total' " \
                    "WHEN c.crane_key ISNULL THEN 'Subtotal'||' '||c.crane_key ELSE c.crane_key|| ' ' || c.brand END) as label " \
                    "FROM fact_table f, crane c WHERE f.crane_key = c.crane_key " \
                    "GROUP BY ROLLUP(c.crane_key, c.brand) " \
                    "ORDER BY c.crane_key DESC, c.brand DESC".format(y_axis)
    else:
        size = 'Ln(count) of Ships'
        y_axis = 'f.cyc_time'
        x_axis = 'Average Crane Performance'
        query = "SELECT c.crane_key, c.brand, AVG(f.cyc_time)::time as metric, " \
                "ROUND(AVG(f.performance)::NUMERIC,2) as performance_rate,LN(COUNT(*)) as scaled_count, " \
                "(CASE  WHEN c.crane_key ISNULL AND c.brand ISNULL THEN 'Grand Total' " \
                "WHEN c.crane_key ISNULL THEN 'Subtotal'||' '||c.crane_key ELSE c.crane_key|| ' ' || c.brand END) as label " \
                "FROM fact_table f, crane c WHERE f.crane_key = c.crane_key " \
                "GROUP BY ROLLUP(c.crane_key, c.brand) " \
                "ORDER BY c.crane_key DESC, c.brand DESC"

    with connections['default'].cursor() as cursor:
        cursor.execute(query)
        records = cursor.fetchall()

        dict_df = {'size':[],'y_axis':[], 'x_axis': [], 'label': []}
        for rows in records:
            if rows[2] != None:
                if y_axis == 'f.cyc_time':
                    dict_df['y_axis'].append(datetime.combine(date_combine,rows[2]))
                else:
                    dict_df['y_axis'].append(rows[2])
                dict_df['x_axis'].append(rows[3])
                dict_df['size'].append(rows[4])
                dict_df['label'].append(rows[5])
    
    # Setting layout of the figure.
    bubble_layout = {
        'height': 700,
        'width': 1000,
    }

    y_axis_title = {'f.cyc_time': 'Cycle Time',
                    'c.speed' : "Crane Speed",
                    'c.year_built': 'Year Built',
                    'c.elect_drive': 'Electrical Drive',
                    'f.container': 'Containers Handled',
                    'f.maintenance_due_key': 'Days overdue for maintenance',
                    'f.mi_rate': 'Manual intervention count'
                    }
    #print(dict_df['y_axis'])
    # List of graph objects for figure.
    graph_title = 'Average Crane Performance vs {} per Crane and Model type'.format(y_axis_title[y_axis])
    bubble_div = px.scatter(x=dict_df['x_axis'],
                            y=dict_df['y_axis'],
                            size=dict_df['size'],
                            color=dict_df['label'],
                            labels={'x':'Average Crane Performance', 'y':y_axis_title[y_axis], 'color':'Value of Bubbles'},
                            template = "plotly_dark",title=graph_title).update_layout(yaxis_tickformat="%M:%S")

    # Getting HTML needed to render the plot.
    bubble_graph = plot({'data': bubble_div, 'layout': bubble_layout}, output_type = 'div')

    # Setting context
    context={
        'graphs': [
            bubble_graph
        ],
        'selected_metrics': 'Current Selected Crane Metrics & Crane Features:',
        'chosen_metrics': y_axis_title[y_axis],
        'title': 'Crane Metrics/Features vs Crane Performance',
        'description': 'The chart will allow you to see the individual crane performance and will allow'
                       'you to compare different crane metrics/features. This will allow the user to understand'
                       'if there are any correlations between crane performance with the different crane metrics'
                       'and features.',
        'interaction': 'To select different crane metrics/features, use the dropdown below. '
                       'You can zoom into the graph for the individual crane information'
                       'by hovering over the bubbles on the chart.',
        'dropdowns': [
            {
                'id': 'y_axis',
                'label': 'Crane metrics/Features',
                'options': [
                    {
                        'value': 'f.cyc_time',
                        'label': 'Select here'
                    },
                    {
                        'value': 'f.cyc_time',
                        'label': 'Cycle Time'
                    },
                    {
                        'value': 'c.year_built',
                        'label': 'Year Built'
                    },
                    {
                        'value': 'c.elect_drive',
                        'label': 'Electrical Drive'
                    },
                    {
                        'value': 'f.container',
                        'label': 'Container handled'
                    },
                    {
                        'value': 'f.maintenance_due_key',
                        'label': 'Day overdue maintenance'
                    },
                    {
                        'value': 'f.mi_rate',
                        'label': 'Manual intervention count'
                    },
                    {
                        'value': 'c.speed',
                        'label': 'Crane Speed'
                    },

                ]
            }
        ]
    }

    return render(request, 'visual.html', context)


def extended_view_graph3(request):
    # get params request.
    request_dict = request.GET
    print(request_dict)
    if request_dict != {}:
        x_axis = request_dict['x_axis']
        query = 'SELECT v.{0}, ROUND(PERCENTILE_CONT(0.25) ' \
                'WITHIN GROUP (ORDER BY f.performance ASC)::NUMERIC,2) AS percentile_25, ' \
                'ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY f.performance ASC)::NUMERIC,2) AS percentile_75 ' \
                'FROM fact_table f, verifier v WHERE f.verifier_key = v.verifier_key '  \
                'GROUP BY v.{0}'.format(x_axis)
    else:
        size = 'Count of Ships'
        y_axis = 'Average Crane Performance'
        x_axis = 'verifier_name'
        query = 'SELECT v.verifier_name, ROUND(PERCENTILE_CONT(0.25) ' \
                'WITHIN GROUP (ORDER BY f.performance ASC)::NUMERIC,2) AS percentile_25, ' \
                'ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY f.performance ASC)::NUMERIC,2) AS percentile_75 ' \
                'FROM fact_table f, verifier v WHERE f.verifier_key = v.verifier_key ' \
                'GROUP BY v.verifier_name;'

    with connections['default'].cursor() as cursor:
        cursor.execute(query)
        records = cursor.fetchall()

        dict_df = {'x_axis': [], 'y_axis': [], 'y_axis1': []}
        for rows in records:
            dict_df['x_axis'].append(rows[0])
            dict_df['y_axis'].append(rows[1])
            dict_df['y_axis1'].append(rows[2])

    x_axis_title = {'verifier_name': 'Port Terminal',
                    'verifier_location' : "Crane Location",
                    'verifier_section': 'Maintenance Section',
                    'verifier_substation': 'Power Substation'
                    }

    bar_layout = {
        'title': '25th and 75th Percentiles of {} for all crane performance based verifiers'.format(x_axis_title[x_axis]),
        'xaxis_title': x_axis_title[x_axis],
        'yaxis_title': 'Crane Performance',
        'height': 700,
        'width': 1000,

    }

    # List of graph objects for figure.
    graph_title = 'Percentile Bar Rank'
    bar_graphs = go.Figure(data=[go.Bar(x=dict_df['x_axis'], y=dict_df['y_axis'], name='25th Percentile'),
                                 go.Bar(x=dict_df['x_axis'], y=dict_df['y_axis1'], name='75th Percentile')],
                           layout=bar_layout)
    bar_graphs.update_layout(barmode='group',template = "plotly_dark")
    range_min = min(dict_df['y_axis']) - 5
    range_max = max(dict_df['y_axis1']) + 5
    bar_graphs.update_yaxes(range=[range_min,range_max])


    # Getting HTML needed to render the plot.
    bar_div = plot({'data': bar_graphs, 'layout': bar_layout}, output_type='div')

    # Setting context
    context = {
        'graphs': [
            bar_div
        ],
        'selected_metrics': 'Current Selected Efficiency Metrics:',
        'chosen_metrics': x_axis_title[x_axis],
        'dropdowns': [
            {
                'id': 'x_axis',
                'label': 'Different Verifiers',
                'options': [
                    {
                        'value': 'verifier_name',
                        'label': 'Select Here'
                    },
                    {
                        'value': 'verifier_name',
                        'label': 'Port Terminal'
                    },
                    {
                        'value': 'verifier_location',
                        'label': 'Crane Locations'
                    },
                    {
                        'value': 'verifier_section',
                        'label': 'Maintenance Section'
                    },
                    {
                        'value': 'verifier_substation',
                        'label': 'Power Substation'
                    }

                ]
            }
        ],
        'title': 'Measuring Crane Performance by Verifiers',
        'description': 'The Crane Performance were computed to the 25th and 75th percentile. '
                       'It is then compared with different verifiers. '
                       'From the graph we can then see if there are any correlation with the different '
                       'verfiers '
,
        'interaction': 'Choose the different verifiers by the dropdown box. '
                       'You can zoom into the graph for the individual crane information '
                       'by hovering over the individual bar chart.'
    }

    return render(request, 'visual.html', context)