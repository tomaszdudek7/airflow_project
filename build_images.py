import docker
import argparse
import logging
import sys
import os.path
from pathlib import Path

import shutil, errno

LIBRARIES_TO_COPY = ['papermill_runner', 'result_saver']

def copy_dirs(src, dst):
    try:
        shutil.copytree(src, dst)
    except OSError as exc: # python >2.5
        if exc.errno == errno.ENOTDIR:
            shutil.copy(src, dst)
        else: raise

root = logging.getLogger()
root.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
root.addHandler(handler)

log = logging.getLogger("build_images")

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--task", dest="taskname",
                    help="If you wish to build only specific task, specify its catalog name", required=False)

args = parser.parse_args()

taskname = args.taskname
directories = []
if taskname is not None:
    log.info(f"Taskname specified as {taskname}. Will build only that docker image.")
    path = f"./docker/{taskname}"
    if not os.path.isdir(path):
        raise Exception(f'''Directory /docker/{taskname} does not exists.''' )
    directories = [path]
else:
    log.info(f"No particular task name specified. Will build every image in /docker/.")
    directories = [x for x in os.listdir('./docker') if not x.startswith('.') and os.path.isdir(f'./docker/{x}')]

log.info(f"Browsing {directories}")

for directory in directories:
    log.info(f"Handling task {directory}")
    try:
        for library in LIBRARIES_TO_COPY:
            src = f'./python/libraries/{library}'
            dest = f'./docker/{directory}/{library}'
            log.info(f"Copying {src} to {dest}")
            copy_dirs(src, dest)

    finally:
        log.info("Cleaning up.")
        for library in LIBRARIES_TO_COPY:
            dest = f'./docker/{directory}/{library}'
            log.info(f"Removing {dest}")
            shutil.rmtree(dest)





