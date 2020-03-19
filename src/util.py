from config import config
from datetime import timedelta, datetime
from operator import itemgetter
from src import ec2, s3, cw
import numpy as np
import pymysql
import random
import src.instances as Instance
import src.loadbalancer as Loadbalancer


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
    Loadbalancer.register_instance_to_elb.apply_async(args=[instance.id])


def random_destroy_worker(to_destroy):
    print("destroying worker!")
    workers_id, num_running_workers = Instance.get_serving_instances()

    if num_running_workers == 0:
        return False
    else:
        workers_to_destroy_id = random.sample(workers_id, to_destroy)
        for worker_id in workers_to_destroy_id:
            destroy_a_worker(worker_id)


def destroy_a_worker(id):
    Loadbalancer.deregister_from_elb(id)
    instance = list(ec2.instances.filter(InstanceIds=[id]))[0]
    instance.terminate()


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


def get_http_rate(id):
    http = cw.get_metric_statistics(
        Period=1*60,
        StartTime=datetime.utcnow() - timedelta(seconds=30*60),
        EndTime=datetime.utcnow() - timedelta(seconds=0),
        MetricName='httpRequestRate',
        Namespace='AWS/EC2',
        Statistics=['Sum'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    
    return return_label_values(http)
    

def return_label_values(stats):
    storage_list = []
    for point in stats['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        storage_list.append(["%d:%02d" % (hour, minute), point['Average']])
    storage_list = sorted(storage_list, key=itemgetter(0))
    labels = [
        item[0] for item in storage_list
    ]
    values = [
        item[1] for item in storage_list
    ]
    max_val = 0
    if len(storage_list) != 0:
        max_val = max(storage_list, key=itemgetter(1))[1]

    return labels, values, max_val
