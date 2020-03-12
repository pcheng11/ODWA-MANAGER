from flask import Blueprint, url_for, redirect, render_template, flash
from time import sleep
from src.util import celery_create_worker, random_destroy_worker, get_running_instances, get_serving_instances

manualscaling_blueprint = Blueprint('manualscaling', __name__)
'''
    manual scaling panel
'''
@manualscaling_blueprint.route('/', methods=['GET'])
def index():
    _, num_instances = get_running_instances()
    _, num_workers = get_serving_instances()
    return render_template('manualscaling.html', num_workers=num_workers, num_instances=num_instances)

@manualscaling_blueprint.route('/create_worker', methods=['POST'])
def create_worker():
    celery_create_worker()
    sleep(1)
    flash("A new instance has been created successfully", "success")
    return redirect(url_for('manualscaling.index'))


@manualscaling_blueprint.route('/destroy_worker', methods=['POST'])
def destroy_worker():
    instance = random_destroy_worker()
    if instance == None:
        flash("No available running workers!", "danger")
    else:
        flash("instance: " + instance.id +
              " has been deleted successfully", "success")
    return redirect(url_for('manualscaling.index'))
