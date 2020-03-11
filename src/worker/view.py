from flask import Blueprint, request, session, url_for, render_template, redirect
from flask_login import login_required, current_user
from src import ec2, cw
from datetime import datetime, timedelta
from operator import itemgetter
from config import config

worker_blueprint = Blueprint('worker', __name__)

@worker_blueprint.route('/<id>', methods=['GET'])
def worker_view(id):
    instance = ec2.Instance(id)
    CPUlabels, CPUvalues, CPUmax = _get_cpu_utilization(id)
    HTTPlabels, HTTPvalues, HTTPmax = _get_http_rate(id)
    return render_template('detail.html', title='Instance Info', 
        CPUlabels=CPUlabels, 
        CPUvalues=CPUvalues, 
        CPUmax=CPUmax, 
        HTTPlabels=HTTPlabels,
        HTTPvalues=HTTPvalues,
        HTTPmax=HTTPmax,
        instance=instance)



@worker_blueprint.route('/delete/<id>', methods=['POST'])
def delete_worker(id):
    ec2.instances.filter(InstanceIds=[id]).terminate()
    return redirect(url_for('panel.list_workers'))


def _get_http_rate(id):
    http = cw.get_metric_statistics(
        Period=1*60,
        StartTime=datetime.utcnow() - timedelta(seconds=30*60),
        EndTime=datetime.utcnow() - timedelta(seconds=0),
        MetricName='httpRequestRate',
        Namespace='AWS/EC2',
        Statistics=['Sum'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    http_stats = []
    for point in http['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        http_stats.append(["%d:%02d" % (hour, minute), point['Sum']])
    http_stats = sorted(http_stats, key=itemgetter(0))
    print(http_stats)
    print(datetime.utcnow().hour)
    print(datetime.utcnow().minute)
    # figure out a way list past 30 minutes of day time
    print(datetime.utcnow() - timedelta(seconds=30*60))
    labels = [
        item[0] for item in http_stats
    ]
    values = [
        item[1] for item in http_stats
    ]

    max_count = 0
    if len(http_stats) != 0:
        max_count = max(http_stats, key=itemgetter(1))[1] 

    return labels, values, max_count


def _get_cpu_utilization(id):
    cpu = cw.get_metric_statistics(
        Period=1*60,
        StartTime=datetime.utcnow() - timedelta(seconds=30*60),
        EndTime=datetime.utcnow() - timedelta(seconds=0),
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistics=['Average'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        cpu_stats.append(["%d:%02d" % (hour, minute), point['Average']])
    cpu_stats = sorted(cpu_stats, key=itemgetter(0))
    labels = [
        item[0] for item in cpu_stats
    ]
    values = [
        item[1] for item in cpu_stats
    ]
    max_percent = 0
    if len(cpu_stats) != 0:
        max_percent = max(cpu_stats, key=itemgetter(1))[1]

    return labels, values, max_percent
