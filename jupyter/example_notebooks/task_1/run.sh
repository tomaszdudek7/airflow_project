#!/usr/bin/env bash

papermill code.ipynb output/code_execution_${EXECUTION_ID}.ipynb -f task_1/params.yaml --log-output