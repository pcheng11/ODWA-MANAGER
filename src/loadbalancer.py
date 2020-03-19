from src import ec2, elb, background_task, ec2_client
from celery.task import periodic_task
from config import config
from src.model import AutoScalingConfig
from datetime import timedelta, datetime

def health_check():
    response = elb.describe_target_health(
        TargetGroupArn=config.TARGET_GROUP_ARN)
    return response['TargetHealthDescriptions']


def deregister_from_elb(id):
    elb.deregister_targets(
        TargetGroupArn=config.TARGET_GROUP_ARN,
        Targets=[
            {
                'Id': id,
                'Port': 5000,
            },
        ]
    )


@periodic_task(run_every=timedelta(seconds=60))
def record_serving_instances_avg_cpu_util():
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

    cpu_stats_list = []
    avg_cpu_util = 0

    if len(inservice_instances_id) != 0:
        for instance_id in inservice_instances_id:
            cpu_stats = get_single_instance_cpu_util(instance_id, 2)
            if len(cpu_stats) != 0:
                cpu_stats_list.append(np.mean(cpu_stats))
        if len(cpu_stats_list) != 0:
            avg_cpu_util = np.mean(cpu_stats_list)

    response = cw.put_metric_data(
        Namespace='AWS/EC2',
        MetricData=[
            {
                'MetricName': 'avgCPUutil',
                'Timestamp': datetime.now(),
                'Value': avg_cpu_util,
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

@background_task.task
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
