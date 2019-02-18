import logging
import docker


def do_test_docker():
    log = logging.getLogger('_test_docker')
    for image in docker.from_env().images.list():
        log.info(image)

