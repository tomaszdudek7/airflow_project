import logging
import docker
import tarfile
import json
import os
import tempfile

from docker import Client
from docker.errors import NotFound

log = logging.getLogger(__name__)


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


def launch_docker_container(**context):
    image_name = context['image_name']
    client: Client = docker.from_env()

    log.info(f"Creating image {image_name}")
    container = client.create_container(image=image_name)

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

    log.info(f"Task ends!")
    my_id = context['my_id']
    context['task_instance'].xcom_push('data', f'my name is {my_id}', context['execution_date'])
