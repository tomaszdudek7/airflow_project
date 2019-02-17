# Don't build images directly, use `build_images.py` in the directory above instead.

## adding new Jupyter task
If you want to add another Jupyter-like task - recreate virtual environment from `requirements.txt` and create your notebook. Then create a new directory, call it `example_task`, copy Dockerfile and the `.ipynb` inside and run `build_images.py`. Your image should be then available to use in DAGs.

## adding new non-Jupyter Docker task
Just use your image name in the DAG.
* If you want to pass the data downstream, save `/tmp/result.tgz` containing `result.json` file with proper json. It will be propagated automatically if you use `ContainerLauncher().run` callable as `PythonOperator`.
* If you want to receive data, the first argument will contain a proper json. Parse and use it.
