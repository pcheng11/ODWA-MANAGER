from src import ec2, elb, celery, ec2_client, s3, cw
from operator import itemgetter
from config import config
from time import sleep
import pymysql
from celery.task import periodic_task
import random
from datetime import timedelta, datetime
import celery

def celery_create_worker():
    startup_script = """#cloud-config
runcmd:
 - cd /home/ubuntu/ODWA
 - sudo apt-get update
 - sudo apt-get install -y uwsgi
 - sudo apt-get install uwsgi-plugin-python3
 - sudo apt-get install python3-pip
 - sudo pip3 install -r requirements.txt
 - sudo pip3 install redis
 - sudo pip3 install celery
 - celery worker -A run.celery --loglevel=info -f celerylog.log --beat & uwsgi uwsgi.ini --plugin python3 --uid ubuntu --binary-path /home/ubuntu/.local/bin/uwsgi --logto mylog.log
"""
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

    print('----instance created!')
    register_instance_to_elb.apply_async(args=[instance.id])


@celery.task
def register_instance_to_elb(id):
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[id])

    IAMresponse = ec2_client.associate_iam_instance_profile(
        IamInstanceProfile=config.IAM_INSTANCE_PROFILE,
        InstanceId=id
    )
    print(IAMresponse)

    ELBresponse = elb.register_targets(
        TargetGroupArn=config.TARGET_GROUP_ARN,
        Targets=[
            {
                'Id': id,
                'Port': 5000,
            }
        ],
    )
    print(ELBresponse)


@periodic_task(run_every=timedelta(seconds=10))
def record_serving_instances():
    response = health_check()
    inservice_instances_id = set()
    for instance in response:
        if instance['TargetHealth']['State'] == 'healthy':
            inservice_instances_id.add(instance['Target']['Id'])

    response = cw.put_metric_data(
        Namespace='AWS/EC2',
        MetricData=[
            {
                'MetricName': 'numWorkers30',
                'Timestamp': datetime.now(),
                'Value': len(inservice_instances_id),
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
    print('HEALTHY INSTANCES: ' + str(len(inservice_instances_id)))

def health_check():
    response = elb.describe_target_health(TargetGroupArn=config.TARGET_GROUP_ARN)
    return response['TargetHealthDescriptions']

def get_serving_instances():
    response = health_check()
    inservice_instances_id = set()
    for instance in response:
        if instance['TargetHealth']['State'] == 'healthy':
            inservice_instances_id.add(instance['Target']['Id'])
    return inservice_instances_id, len(inservice_instances_id)

def random_destroy_worker():
    instances, num_running_workers = get_running_instances()

    if num_running_workers == 0:
        return None
    num_running_workers -= 1
    instance = random.sample(set(instances), 1)
    response = elb.deregister_targets(
        TargetGroupArn=config.TARGET_GROUP_ARN,
        Targets=[
            {
                'Id': instance[0].id,
                'Port': 5000,
            },
        ]
    )
    print(response)
    instance[0].terminate()
    return instance[0]


def get_running_instances():
    instances = ec2.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']},
                 {'Name': 'tag:Name', 'Values': ['worker']}])
    return instances, len(set(instances))


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


def get_cpu_utilization(id):
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
