import contextlib
from flask import Blueprint, request, session, url_for, render_template, redirect, flash
from src import ec2, cw, elb, ec2_client, s3
import time
from datetime import datetime, timedelta
from operator import itemgetter
from config import config
from time import sleep
from src.util import delete_rds_data, delete_s3_data, get_serving_instances, get_num_workers_30, get_avg_cpu_utilization

panel_blueprint = Blueprint('panel', __name__)
'''
    control panel
'''


@panel_blueprint.route('/', methods=['GET'])
def index():
    _, num_serving_instance = get_serving_instances()
    avg_cpu_util = get_avg_cpu_utilization()
    return render_template('panel.html', num_serving_instance=num_serving_instance, avg_cpu_util=avg_cpu_util)


@panel_blueprint.route('/workers', methods=['GET'])
def list_workers():
    instances = ec2.instances.filter(Filters=[{'Name': 'tag:Name', 'Values': ['worker']}])
    inservice_instances_id, worker_pool_size = get_serving_instances()
    instances_list = []
    for instance in instances:
        tmp_instance = {
            "id": instance.id,
            "public_ip_address": instance.public_ip_address,
            "instance_type": instance.instance_type,
            "availability_zone": instance.placement['AvailabilityZone'],
            "state": instance.state['Name'],
            "inservice": 'Yes' if instance.id in inservice_instances_id else 'No'
        }
        instances_list.append(tmp_instance)
    labels, values, maxNumWorkers = get_num_workers_30()
    return render_template('list.html', 
        instances=instances_list, 
        worker_pool_size=len(inservice_instances_id),
        workerLabels=labels,
        workerValues=values,
        workerMax=maxNumWorkers)


@panel_blueprint.route('delete_data', methods=['POST'])
def delete_data():
    delete_s3_data()
    delete_rds_data()
    flash("All Data Deleted Successfully")
    return redirect(url_for('panel.index'))
 

@panel_blueprint.route('/autoscaling', methods=['GET'])
def goto_autoscaling():
    return redirect(url_for('autoscaling.index'));


@panel_blueprint.route('/manualscaling', methods=['GET'])
def goto_manualscaling():
    return redirect(url_for('manualscaling.index'))
