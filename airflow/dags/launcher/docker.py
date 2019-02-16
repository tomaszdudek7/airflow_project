import logging
import docker


def do_test_docker():
    client = docker.from_env()
    for image in client.images().list():
        logging.info(str(image))