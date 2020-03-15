__author__ = 'victor cheng'

import boto3
from flask import Flask
from config import config
from celery import Celery
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
celery = Celery(app.name, broker=config.CELERY_BROKER_URL)
ec2 = boto3.resource('ec2', aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                     aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                     region_name='us-east-1',
                     aws_session_token=config.AWS_SESSION_TOKEN)
ec2_client = boto3.client('ec2', aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                          region_name='us-east-1',
                          aws_session_token=config.AWS_SESSION_TOKEN)
cw = boto3.client('cloudwatch',  aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                  region_name='us-east-1',
                  aws_session_token=config.AWS_SESSION_TOKEN)
elb = boto3.client('elbv2', aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                   aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                   region_name='us-east-1',
                   aws_session_token=config.AWS_SESSION_TOKEN)

s3 = boto3.resource('s3', aws_access_key_id=config.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
                    region_name='us-east-1',
                    aws_session_token=config.AWS_SESSION_TOKEN)
db = SQLAlchemy()


def create_app():
    app.config.from_object('config.config')
    celery.conf.update(app.config)
    db.init_app(app)

    with app.app_context():
        from .worker.view import worker_blueprint
        from .panel.view import panel_blueprint
        from .autoscaling.view import autoscaling_blueprint
        from .manualscaling.view import manualscaling_blueprint
        # register blueprints
        app.register_blueprint(worker_blueprint, url_prefix='/worker')
        app.register_blueprint(autoscaling_blueprint,
                               url_prefix='/autoscaling')
        app.register_blueprint(panel_blueprint, url_prefix='/panel')
        app.register_blueprint(manualscaling_blueprint,
                               url_prefix='/manualscaling')
        db.drop_all()
        db.create_all()
        return app


app = create_app()
