from flask import Blueprint, url_for, render_template, redirect
from src import ec2, cw
from operator import itemgetter
from config import config
import src.util as Util
import src.cpu as Cpu


worker_blueprint = Blueprint('worker', __name__)

@worker_blueprint.route('/<id>', methods=['GET'])
def worker_view(id):
    instance = ec2.Instance(id)
    CPUlabels, CPUvalues, CPUmax = Cpu.get_cpu_utilization_30(id)
    HTTPlabels, HTTPvalues, HTTPmax = Util.get_http_rate(id)
    return render_template('detail.html', title='Instance Info', 
        CPUlabels=CPUlabels, 
        CPUvalues=CPUvalues, 
        CPUmax=CPUmax, 
        HTTPlabels=HTTPlabels,
        HTTPvalues=HTTPvalues,
        HTTPmax=HTTPmax,
        instance=instance)



@worker_blueprint.route('/delete/<id>', methods=['POST'])
def destroy_worker(id):
    Util.destroy_a_worker(id)
    return redirect(url_for('panel.list_workers'))


@worker_blueprint.route('/delete/all', methods=['POST'])
def destroy_all():
    instances = ec2.instances.filter(
        Filters=[{'Name': 'tag:Name', 'Values': ['worker']}])
    for instance in instances:
        Util.destroy_a_worker(instance.id)
    return redirect(url_for('panel.list_workers'))





