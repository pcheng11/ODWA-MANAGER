from flask import Blueprint, url_for, redirect, render_template, flash
from time import sleep
from src import db
from src.util import celery_create_worker, random_destroy_worker, get_running_instances, get_serving_instances, get_all_instances, get_running_pending_shutting_instances
from src.model import AutoScalingConfig

manualscaling_blueprint = Blueprint('manualscaling', __name__)
'''
    manual scaling panel
'''
@manualscaling_blueprint.route('/', methods=['GET'])
def index():
    _, num_instances = get_running_instances()
    _, num_workers = get_serving_instances()
    autoScaleOn = False
    config = AutoScalingConfig.query.first()
    if config and config.isOn:
        autoScaleOn = True
    return render_template('manualscaling.html', num_workers=num_workers, num_instances=num_instances, autoScaleOn=autoScaleOn)

@manualscaling_blueprint.route('/create_worker', methods=['POST'])
def create_worker():
    _, running_pending_shutting_instances = get_running_pending_shutting_instances()
    if running_pending_shutting_instances >= 8:
        flash("Number of instances reaches maximum limit! (10 instances allowed)", "danger")
    else:
        celery_create_worker()
        flash("A new instance has been created successfully", "success")
    return redirect(url_for('manualscaling.index'))


@manualscaling_blueprint.route('/destroy_worker', methods=['POST'])
def destroy_worker():
    isDeleted = random_destroy_worker(1)
    if isDeleted == False:
        flash("No available running workers!", "danger")
    else:
        flash("an instance has been deleted successfully", "success")
    return redirect(url_for('manualscaling.index'))


@manualscaling_blueprint.route('/turn_on', methods=['POST'])
def turn_on():
    config = AutoScalingConfig.query.first()
    config.isOn = False
    db.session.commit()
    return redirect(url_for('manualscaling.index'))
