from src import ec2, elb, celery, ec2_client
from operator import itemgetter
from config import config
from time import sleep
import random

@celery.task
def celery_create_worker():
    startup_script = """#cloud-config
runcmd:
 - cd /home/ubuntu/ODWA
 - sudo apt-get update
 - sudo apt-get install -y uwsgi
 - sudo apt-get install uwsgi-plugin-python3
 - sudo apt-get install python3-pip
 - sudo pip3 install -r requirements.txt
 - uwsgi uwsgi.ini --plugin python3 --uid ubuntu --binary-path /home/ubuntu/.local/bin/uwsgi --logto mylog.log
"""
    instance = ec2.create_instances(
        ImageId=config.AMI,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.small',
        UserData=startup_script,
        KeyName='odwa',
        SecurityGroupIds=config.SECURITY_GROUP_IDS,
        Monitoring={'Enabled': True}
    )[0]

    print('----instance created!')
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance.id])

    IAMresponse = ec2_client.associate_iam_instance_profile(
        IamInstanceProfile=config.IAM_INSTANCE_PROFILE,
        InstanceId=instance.id
    )
    print(IAMresponse)

    ELBresponse = elb.register_targets(
        TargetGroupArn=config.TARGET_GROUP_ARN,
        Targets=[
            {
                'Id': instance.id,
                'Port': 5000,
            }
        ],
    )
    print(ELBresponse)

def random_destroy_worker():
    instances, num_running_workers = get_running_instances()

    if num_running_workers == 0:
        return None
    num_running_workers -=1;
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
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    return instances, len(set(instances))
