import papermill as pm
import sys
import json
import yaml
import os

import logging


class PapermillRunner:
    CODE_PATH = 'code.ipynb'

    def __init__(self):
        self._overwrite_papermill_logger()
        self.log = logging.getLogger("papermill_runner")
        self.execution_id = self._get_execution_id()
        self.log.info(f"Execution id seems to be {self.execution_id}")
        self.yaml_params = self._get_yaml_params()
        self.log.info(f"Yaml params are {self.yaml_params}")
        self.arg_params = self._get_args_params()
        self.log.info(f"Arg Params are {self.arg_params}")

    def run(self):
        output_path = f'output/code_{self.execution_id}.ipynb'
        params = {**self.yaml_params, **self.arg_params}
        pm.execute_notebook(self.CODE_PATH, output_path, parameters=params, progress_bar=False, log_output=True)

    def _overwrite_papermill_logger(self):
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)

    def _get_yaml_params(self):
        try:
            with open("params.yaml", 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {}

    def _get_args_params(self):
        args = sys.argv
        self.log.info(f"Args are {args}")
        if args is not None and len(args) > 1:
            try:
                return json.loads(args[1])
            except ValueError:
                self.log.info('Failed to parse args.')
                return {}
        return {}

    def _get_execution_id(self):
        try:
            return os.environ['EXECUTION_ID']
        except KeyError:
            return 0