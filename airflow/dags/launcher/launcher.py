import logging
import shlex

import docker
import tarfile
import json
import os
import tempfile

from airflow.models import TaskInstance
from docker import Client
from docker.errors import NotFound

log = logging.getLogger(__name__)


def combine_xcom_values(xcoms):
    if xcoms is None or xcoms == [] or xcoms == () or xcoms == (None, ):
        return {}
    elif len(xcoms) == 1:
        return dict(xcoms)

    result = {}
    egible_xcoms = (d for d in xcoms if d is not None and len(d) > 0)
    for d in egible_xcoms:
        for k, v in d.items():
            result[k] = v
    return result


def untar_file_and_get_result_json(client, container):
    try:
        tar_data_stream, stat = client.get_archive(container=container, path='/tmp/result.tgz')
    except NotFound:
        return dict()

    with tempfile.NamedTemporaryFile() as tmp:
        for chunk in tar_data_stream.stream():
            tmp.write(chunk)
        tmp.seek(0)
        with tarfile.open(mode='r', fileobj=tmp) as tar:
            tar.extractall()
            tar.close()

    with tarfile.open('result.tgz') as tf:
        for member in tf.getmembers():
            f = tf.extractfile(member)
            result = json.loads(f.read())
            os.remove('result.tgz')
            return result


def pull_all_parent_xcoms(context):
    parent_ids = context['task'].upstream_task_ids
    log.info(f"Pulling xcoms from all parent tasks: {parent_ids}")
    xcoms = context['task_instance'].xcom_pull(task_ids=parent_ids, key='result')
    xcoms_combined = combine_xcom_values(xcoms)
    log.info(f"Sending {xcoms_combined} to the container.")

    json_quotes_escaped = shlex.quote(json.dumps(xcoms_combined))
    return json_quotes_escaped


def launch_docker_container(**context):
    image_name = context['image_name']
    client: Client = docker.from_env()

    log.info(f"Creating image {image_name}")

    execution_id = context['dag_run'].run_id
    environment = {
        'EXECUTION_ID': execution_id
    }

    args_json_escaped = pull_all_parent_xcoms(context)
    container = client.create_container(image=image_name, environment=environment, command=args_json_escaped)

    container_id = container.get('Id')
    log.info(f"Running container with id {container_id}")
    client.start(container=container_id)

    logs = client.logs(container_id, follow=True, stderr=True, stdout=True, stream=True, tail='all')

    try:
        while True:
            l = next(logs)
            log.info(f"Task log: {l}")
    except StopIteration:
        log.info("Docker has finished!")

    result = untar_file_and_get_result_json(client, container)
    log.info(f"Result was {result}")
    context['task_instance'].xcom_push('result', result, context['execution_date'])
