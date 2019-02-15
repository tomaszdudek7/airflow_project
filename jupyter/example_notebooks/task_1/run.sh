#!/usr/bin/env bash

papermill code.ipynb output/code_execution_${EXECUTION_ID}.ipynb -f params.yaml --log-output