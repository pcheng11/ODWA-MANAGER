from flask import Blueprint, request, session, url_for, render_template, redirect, flash
from flask_login import login_required, current_user
from src import ec2, cw, elb, celery, ec2_client, db
from src.model import AutoScalingConfig
import time
from datetime import datetime, timedelta
from operator import itemgetter
from config import config

autoscaling_blueprint = Blueprint('autoscaling', __name__)
'''
    auto scaling panel
'''


@autoscaling_blueprint.route('/', methods=['GET'])
def index():
    return render_template('autoscaling.html')

@autoscaling_blueprint.route('/apply', methods=['POST'])
def apply():
    expand_threshold = request.form.get('expand-threshold')
    shrink_threshold = request.form.get('shrink-threshold')
    expand_ratio = request.form.get('expand-ratio')
    shrink_ratio = request.form.get('shrink-threshold')

    autoScalingConfig = AutoScalingConfig.query.first()
    if not autoScalingConfig:
        new_config = AutoScalingConfig(
            isOn=True, 
            shrink_ratio=shrink_ratio, 
            expand_ratio=expand_ratio, 
            shrink_threshold=shrink_threshold, 
            expand_threshold=expand_threshold)
        db.session.add(new_config)
        db.session.commit()
    else:
        autoScalingConfig.isOn=True
        autoScalingConfig.shrink_ratio = shrink_ratio
        autoScalingConfig.expand_ratio = expand_ratio
        autoScalingConfig.shrink_threshold = shrink_threshold
        autoScalingConfig.expand_threshold = expand_threshold
        db.session.commit()

    flash('new auto scaling policy applied', 'success')
    return redirect(url_for('autoscaling.index'))