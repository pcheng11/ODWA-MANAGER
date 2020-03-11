from sqlalchemy import MetaData
import contextlib
import pymysql
from flask import Blueprint, request, session, url_for, render_template, redirect, flash
from flask_login import login_required, current_user
from src import ec2, cw, elb, ec2_client, s3
import time
from datetime import datetime, timedelta
from operator import itemgetter
from config import config
from time import sleep
panel_blueprint = Blueprint('panel', __name__)
'''
    control panel
'''


@panel_blueprint.route('/')
def index():
    return render_template('panel.html')


@panel_blueprint.route('/workers')
def list_workers():
    instances = ec2.instances.all()
    return render_template('list.html', instances=instances)


@panel_blueprint.route('delete_data', methods=['POST'])
def delete_data():
    delete_s3_data()
    delete_rds_data()
    flash("All Data Deleted Successfully")
    return redirect(url_for('panel.index'))

def delete_s3_data():
    bucket = s3.Bucket('odwa')
    bucket.objects.delete()


def delete_rds_data():
    con = pymysql.connect(config.DB_ENDPOINT, config.DB_MASTER,
                          config.DB_PASSWORD, config.DB_NAME)
    
    with con:
        cur = con.cursor()
        cur.execute("DELETE FROM users")
        cur.execute("DELETE FROM photos")

@panel_blueprint.route('/autoscaling', methods=['GET'])
def goto_autoscaling():
    return redirect(url_for('autoscaling.index'));


@panel_blueprint.route('/manualscaling', methods=['GET'])
def goto_manualscaling():
    return redirect(url_for('manualscaling.index'))
