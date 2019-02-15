# partitioning
* **part one** creates the container _(we are in this one right now)_
* **part two** spins up the airflow and builds DAGs
* **part three** calls the cloud of choice to execute our tasks


# what will get done
We will create a **dockered parametrizable Jupyter notebook** that will be later used as baseline for DAGs and scheduled by Apache Airflow. All that while running in the cloud. Woah.

# technologies used
* data science starter pack (`pandas`, `numpy`, `seaborn`)
* `Jupyter` (with `papermill` extension)
* `Docker` 
* a sprlinke of Python to execute the container

# set up jupyter "basic lab environment"
```bash
mkvirtualenv airflow_jupyter --python=python3.6
pip install jupyter ipython [and whatever else you need]
ipython kernel install --user --name=airflow_jupyter
pip install nteract_on_jupyter
pip install papermill[s3]
jupyter nteract
```

**warning** - the name of virtualenv of choice, in this case `airflow_jupyter`, will be used later - because we'd rather not clutter our workstation, we could want to use separate kernels for each task. But in the end, the notebook getting scheduled 
expects the kernel to actually exists. We will make sure it actually does, by creating it later in the Dockerfile, just before spinning up the notebook.  

#create example notebook
```python
%matplotlib inline
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
x = np.arange(0, input_size, 1)
y = np.random.gamma(2., 2., input_size)
plt.figure(figsize=(18,10))
plt.scatter(x, y, c='r')
plt.show()
```
# add parameters cell
![enable tags](enabletags.png)

and then create parameters cell:

![enable tags](createparameters.png)


# run papermill
depending on your catalog structure the command will look approximately like this:
```bash
papermill task_1/code.ipynb task_1/output/code_exectuion_1.ipynb -f task_1/params.yaml
```

# wrap up in docker container
first off, dump and trim requirements txt to task folder as each task should have its own, as tiny as possible, virtual environment
```python
pip freeze > requirements.txt
```
now create a basic Dockerfile that spins up `run.sh`(which we will create later)

**Note that while `jessie` is not always the best choice of Docker base image taking its size into consideration, the benefit of `alpine` quickly diminishes when using huge libraries like numpy, scipy or pandas.** If you are comfort with Docker and Linux, feel free to use `alpine` as your base image. This will require however, tweaking the Dockerfiles a lot.

Make sure that your name of virtualenv matches in the following file where necessary:
```dockerfile
FROM python:3.6.8-jessie

COPY requirements.txt /

# will be overwriten should `docker run` pass a proper env
ENV EXECUTION_ID 111111

# they HAVE to match the name of jupyter's kernel
RUN pip install virtualenv
RUN virtualenv -p python3 airflow_jupyter
RUN /bin/bash -c "source /airflow_jupyter/bin/activate"
RUN pip install -r /requirements.txt
RUN ipython kernel install --user --name=airflow_jupyter

RUN mkdir notebook
RUN mkdir notebook/output

COPY code.ipynb ./notebook/code.ipynb
COPY params.yaml ./notebook/params.yaml
COPY run.sh ./notebook/run.sh

WORKDIR notebook
ENTRYPOINT ["bash", "./run.sh"]
```