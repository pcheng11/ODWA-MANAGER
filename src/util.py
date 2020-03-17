from src import ec2, elb, celery, ec2_client, s3, cw, app
from operator import itemgetter
from config import config
from time import sleep
import numpy as np
import pymysql
from celery.task import periodic_task
import random
import math
from datetime import timedelta, datetime
from celery import Celery
from config import config
from src.model import AutoScalingConfig

def celery_create_worker():
    startup_script = config.STARTUP_SCRIPT
    instance = ec2.create_instances(
        ImageId=config.AMI,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.small',
        UserData=startup_script,
        KeyName='odwa',
        SecurityGroupIds=config.SECURITY_GROUP_IDS,
        TagSpecifications=[{'ResourceType': 'instance',
                            'Tags': [{'Key': 'Name', 'Value': 'worker'}]}],
        Monitoring={'Enabled': True}
    )[0]

    print('new instance created!')
    register_instance_to_elb.apply_async(args=[instance.id])


@celery.task
def register_instance_to_elb(id):
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[id])

    IAMresponse = ec2_client.associate_iam_instance_profile(
        IamInstanceProfile=config.IAM_INSTANCE_PROFILE,
        InstanceId=id
    )

    ELBresponse = elb.register_targets(
        TargetGroupArn=config.TARGET_GROUP_ARN,
        Targets=[
            {
                'Id': id,
                'Port': 5000,
            }
        ],
    )
    print('instances registered to elb!')


@periodic_task(run_every=timedelta(seconds=60))
def record_serving_instances():
    inservice_instances_id, num_inserivce_instances = get_serving_instances()
    
    response = cw.put_metric_data(
        Namespace='AWS/EC2',
        MetricData=[
            {
                'MetricName': 'numWorkers30',
                'Timestamp': datetime.now(),
                'Value': num_inserivce_instances,
                'Dimensions': [
                    {
                        'Name': 'InstanceId',
                        'Value': 'i-078f69c8c9c0097d6'
                    },
                ],
                'StorageResolution': 60,
                'Unit': 'Count'
            },
        ]
    )
    print('number of healthy instances: ' + str(len(inservice_instances_id)))


@periodic_task(run_every=timedelta(seconds=60))
def auto_check_avg_cpu_utilization():
    """
        Only Get The Instances SERVING THE APP, NOT JUST RUNNNING
    """
    cpu_stats_list = []
    inservice_instances_id, num_workers = get_serving_instances()
    if len(inservice_instances_id) == 0:
        return

    for instance_id in inservice_instances_id:
        cpu_stats, _ = _get_cpu_stats(instance_id, 2)
        if len(cpu_stats) == 0:
            return
        cpu_stats_list.append(np.mean(cpu_stats))
    avg_cpu_util = np.mean(cpu_stats_list)

    with app.app_context():
        autoScalingConfig = AutoScalingConfig.query.first()
        print(autoScalingConfig)
    if not autoScalingConfig:
        return

    if autoScalingConfig.isOn and not has_pending_instances():
        print("auto scaling on, no pending instances")
        _, non_terminated_instances = get_non_terminated_instances()
        if non_terminated_instances >= 8:
            print('number of instances created reachs limit !')
            return

        # avg util > expand_threshold
        if avg_cpu_util > autoScalingConfig.expand_threshold:
            to_create = int(math.ceil((autoScalingConfig.expand_ratio - 1) * num_workers))
            if to_create + non_terminated_instances >= 8:
                to_create = max(9 - non_terminated_instances, 0)
                print("max number of workers reached! only creating {} additional workers".format(
                    to_create))
            print("CPU expand threshold: {} reached ---- creating {} new instances --- expand ratio: {}".format(
                autoScalingConfig.expand_threshold, to_create, autoScalingConfig.expand_ratio))
            for i in range(to_create):
                celery_create_worker()

        elif avg_cpu_util < autoScalingConfig.shrink_ratio:
            to_destroy = int(autoScalingConfig.shrink_ratio * num_workers)
            if to_destroy > 0:
                print("CPU shrink threshold: {} reached ---- destorying {} instances --- shrink ratio: {}".format(
                    autoScalingConfig.shrink_threshold, to_destroy, autoScalingConfig.shrink_ratio))
                random_destroy_worker(to_destroy)
        else:
            print("CPU utilization within range")

    elif has_pending_instances():
        print('there are pending instances')
    else:
        print('auto config is off')


def get_avg_cpu_utilization():
    cpu_stats_list = []
    inservice_instances_id, num_workers = get_serving_instances()
    if len(inservice_instances_id) == 0:
        return
    for instance_id in inservice_instances_id:
        cpu_stats, _ = _get_cpu_stats(instance_id, 2)
        cpu_stats_list.append(np.mean(cpu_stats))
    avg_cpu_util = np.mean(cpu_stats_list)
    return avg_cpu_util


def random_destroy_worker(to_destroy):
    print("destroying worker!")
    workers_id, num_running_workers = get_serving_instances()

    if num_running_workers == 0:
        return False
    else:
        workers_to_destroy_id = random.sample(workers_id, to_destroy)
        for worker_id in workers_to_destroy_id:
            destroy_a_worker(worker_id)

def destroy_a_worker(id):
    _deregister_from_elb(id)
    instance = list(ec2.instances.filter(InstanceIds=[id]))[0]
    instance.terminate()


def get_all_instances():
    instances = ec2.instances.filter(
    Filters=[{'Name': 'tag:Name', 'Values': ['worker']}])
    return instances, len(set(instances))


def get_running_instances():
    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']},
                 {'Name': 'tag:Name', 'Values': ['worker']}])
    return instances, len(set(instances))


def get_non_terminated_instances():
    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'pending', 'shutting-down']},
                 {'Name': 'tag:Name', 'Values': ['worker']}])
    return instances, len(set(instances))


def has_pending_instances():
    instances = list(ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['pending']},
                 {'Name': 'tag:Name', 'Values': ['worker']}]))
    if len(instances) == 0:
        return False
    return True


def get_serving_instances():
    response = _health_check()
    inservice_instances_id = set()
    for instance in response:
        if instance['TargetHealth']['State'] == 'healthy':
            inservice_instances_id.add(instance['Target']['Id'])
    return inservice_instances_id, len(inservice_instances_id)


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


def get_cpu_utilization(id, minutes):
    _, cpu_stats_and_label = _get_cpu_stats(id, minutes)
    labels = [
        item[0] for item in cpu_stats_and_label
    ]
    values = [
        item[1] for item in cpu_stats_and_label
    ]
    max_percent = 0
    if len(cpu_stats_and_label) != 0:
        max_percent = max(cpu_stats_and_label, key=itemgetter(1))[1]

    return labels, values, max_percent


def get_num_workers_30():
    workers = cw.get_metric_statistics(
        Period=1*60,
        StartTime=datetime.utcnow() - timedelta(seconds=30*60),
        EndTime=datetime.utcnow() - timedelta(seconds=0),
        MetricName='numWorkers30',
        Namespace='AWS/EC2',
        Statistics=['Average'],
        Dimensions=[{'Name': 'InstanceId', 'Value': 'i-078f69c8c9c0097d6'}]
    )
    workers_stats = []
    for point in workers['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        workers_stats.append(["%d:%02d" % (hour, minute), point['Average']])
    workers_stats = sorted(workers_stats, key=itemgetter(0))
    labels = [
        item[0] for item in workers_stats
    ]
    values = [
        item[1] for item in workers_stats
    ]
    max_percent = 0
    if len(workers_stats) != 0:
        max_percent = max(workers_stats, key=itemgetter(1))[1]

    return labels, values, max_percent


def _get_cpu_stats(id, minutes):
    cpu = cw.get_metric_statistics(
        Period=1*60,
        StartTime=datetime.utcnow() - timedelta(seconds=minutes*60),
        EndTime=datetime.utcnow() - timedelta(seconds=0),
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',
        Statistics=['Average'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    cpu_stats_and_label = []
    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        cpu_stats.append(point['Average'])
        cpu_stats_and_label.append(["%d:%02d" % (hour, minute), point['Average']])
    cpu_stats_and_label = sorted(cpu_stats_and_label, key=itemgetter(0))
    return cpu_stats, cpu_stats_and_label


def _health_check():
    response = elb.describe_target_health(
        TargetGroupArn=config.TARGET_GROUP_ARN)
    return response['TargetHealthDescriptions']


def _deregister_from_elb(id):
    elb.deregister_targets(
        TargetGroupArn=config.TARGET_GROUP_ARN,
        Targets=[
            {
                'Id': id,
                'Port': 5000,
            },
        ]
    )
