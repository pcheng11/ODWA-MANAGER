from config import config
from datetime import timedelta, datetime

from src.model import AutoScalingConfig
from src import background_task, cw, app
from background_task.task import periodic_task
from celery import Celery
import numpy as np
import random
import math
from src.instances import get_serving_instances, get_non_terminated_instances, has_pending_instances
from src.cpu import get_single_instance_cpu_util
from src.worker import celery_create_worker, random_destroy_worker


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
        cpu_stats = get_single_instance_cpu_util(instance_id, 2)
        # if this instance does not have utilization, that means it has no service
        if len(cpu_stats) == 0:
            return
        cpu_stats_list.append(np.mean(cpu_stats))
    avg_cpu_util = np.mean(cpu_stats_list)

    with app.app_context():
        autoScalingConfig = AutoScalingConfig.query.first()
        print(autoScalingConfig)
    if not autoScalingConfig:
        return

    if autoScalingConfig.isOn:
        print("auto scaling on")
        # only getting the instances that are serving the app
        _, num_workers = get_serving_instances()
        _, non_terminated_instances = get_non_terminated_instances()

        # avg util > expand_threshold
        if avg_cpu_util > autoScalingConfig.expand_threshold:
            if non_terminated_instances >= 8:
                print('number of instances created reaches limit !')
                return
            to_create = int(
                math.ceil((autoScalingConfig.expand_ratio - 1) * num_workers))
            if to_create + non_terminated_instances >= 8:
                to_create = max(8 - non_terminated_instances, 0)
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
