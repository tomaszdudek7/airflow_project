FROM python:3.6.8-jessie

COPY requirements.txt /

# will be overwriten should `docker run` pass a proper env
ENV EXECUTION_ID 111111

# they HAVE to match the name of jupyter's kernel
RUN pip install virtualenv
RUN virtualenv -p python3 airflow_jupyter
RUN /bin/bash -c "source /airflow_jupyter/bin/activate"
RUN pip install -r /requirements.txt

############### this will be provided build-time by the script, don't build it yourself
COPY result_saver /tmp/result_saver
RUN cd /tmp/result_saver && pip install . && cd / && rm -rf /tmp/result_saver
##############

RUN ipython kernel install --user --name=airflow_jupyter

############## this will be provided build-time by the script, don't build it yourself
COPY papermill_runner /tmp/papermill_runner
RUN cd /tmp/papermill_runner && pip install . && cd / && rm -rf /tmp/papermill_runner
##############

RUN mkdir notebook
RUN mkdir notebook/output

COPY code.ipynb ./notebook/code.ipynb
COPY params.yaml ./notebook/params.yaml

WORKDIR notebook
ENTRYPOINT ["python", "-c", "from papermill_runner import PapermillRunner;PapermillRunner().run()"]