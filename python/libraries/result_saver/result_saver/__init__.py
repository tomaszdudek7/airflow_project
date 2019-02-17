import json
import tarfile
import os
import sys
import logging


class ResultSaver:

    def __init__(self):
        self._add_stdout()
        self.log = logging.getLogger("result_saver")

    def _add_stdout(self):
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)

    def save_result(self, result_dictionary):
        self.log.info('Saving result to /tmp/result.json')
        result_json = json.dumps(result_dictionary)
        with open('/tmp/result.json', 'w') as file:
            file.write(result_json)

        with tarfile.open('/tmp/result.tgz', "w:gz") as tar:
            abs_path = os.path.abspath('/tmp/result.json')
            tar.add(abs_path, arcname=os.path.basename('/tmp/result.json'), recursive=False)
        self.log.info('Successfully saved tgz file.')
