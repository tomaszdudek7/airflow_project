import logging

log = logging.getLogger(__name__)

def launch_docker_container(**context):
    log.info(context['ti'])
    log.info(context['image_name'])
    my_id = context['my_id']
    context['task_instance'].xcom_push('data', f'my name is {my_id}', context['execution_date'])