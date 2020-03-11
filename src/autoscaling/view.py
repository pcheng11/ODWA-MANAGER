from flask import Blueprint, request, session, url_for, render_template, redirect
from flask_login import login_required, current_user
from src import ec2, cw, elb, celery, ec2_client
import time
from datetime import datetime, timedelta
from operator import itemgetter
from config import config

autoscaling_blueprint = Blueprint('autoscaling', __name__)
'''
    auto scaling panel
'''


@autoscaling_blueprint.route('/')
def index():
    return render_template('autoscaling.html')
