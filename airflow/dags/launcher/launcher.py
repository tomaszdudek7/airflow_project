import logging
import shlex
from typing import Dict, List

import docker
import tarfile
import json
import os
import tempfile

from docker.errors import NotFound
from docker.models.containers import Container

log = logging.getLogger(__name__)


class ContainerLauncher:

    RESULT_TGZ_NAME = "result.tgz"
    RESULT_PATH = f"/tmp/{RESULT_TGZ_NAME}"

    def __init__(self, image_name: str, run_kwargs={}):
        '''Run kwargs: kwargs passed to self.cli.containers.run. It can be used to mount volumes to task containers during launch'''
        self.cli = docker.from_env()
        self.image_name = image_name
        self.run_kwargs = run_kwargs

    def run(self, **context):
        log.info(f"Creating image {self.image_name}")

        environment = {
            'EXECUTION_ID': (context['dag_run'].run_id)
        }
        args_json_escaped = self._pull_all_parent_xcoms(context)
        container: Container = self.cli.containers.run(detach=True, image=self.image_name, environment=environment,
                                            command=args_json_escaped, **self.run_kwargs)

        container_id = container.id
        log.info(f"Running container with id {container_id}")

        logs = container.logs(follow=True, stderr=True, stdout=True, stream=True, tail='all')

        try:
            while True:
                l = next(logs)
                log.info(f"{l}")
        except StopIteration:
            log.info("Docker has finished!")

        inspect = self.cli.api.inspect_container(container_id)
        log.info(inspect)
        if inspect['State']['ExitCode'] != 0:
            raise Exception("Container has not finished with exit code 0")

        result = self._untar_file_and_get_result_json(container)
        log.info(f"Result was {result}")
        context['task_instance'].xcom_push('result', result, context['execution_date'])

    def _combine_xcom_values(self, xcoms: List[Dict]):
        if xcoms is None or xcoms == [] or xcoms == () or xcoms == (None,):
            return {}
        elif len(xcoms) == 1:
            return dict(xcoms)

        result = {}
        egible_xcoms = (d for d in xcoms if d is not None and len(d) > 0)
        for d in egible_xcoms:
            for k, v in d.items():
                result[k] = v
        return result

    def _untar_file_and_get_result_json(self, container: Container):
        try:
            tar_data_stream, _ = container.get_archive(path=self.RESULT_PATH)
        except NotFound:
            return dict()

        with tempfile.NamedTemporaryFile() as tmp:
            for chunk in tar_data_stream:
                tmp.write(chunk)
            tmp.seek(0)
            with tarfile.open(mode='r', fileobj=tmp) as tar:
                tar.extractall()
                tar.close()

        with tarfile.open(self.RESULT_TGZ_NAME) as tf:
            for member in tf.getmembers():
                f = tf.extractfile(member)
                result = json.loads(f.read())
                try:
                    os.remove(self.RESULT_TGZ_NAME)
                except OSError:
                    pass
                return result

    def _pull_all_parent_xcoms(self, context: Dict):
        parent_ids = context['task'].upstream_task_ids
        log.info(f"Pulling xcoms from all parent tasks: {parent_ids}")
        xcoms = context['task_instance'].xcom_pull(task_ids=parent_ids, key='result')
        xcoms_combined = self._combine_xcom_values(xcoms)
        log.info(f"Sending {xcoms_combined} to the container.")

        json_quotes_escaped = shlex.quote(json.dumps(xcoms_combined))
        return json_quotes_escaped
