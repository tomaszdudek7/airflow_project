import logging

log = logging.getLogger(__name__)

def launch_docker_container(**context):
    log.info(context['ti'])
    log.info(context['image_name'])
    log.info(context['variable'])