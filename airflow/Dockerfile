FROM puckel/docker-airflow:1.10.2

USER root

# linux
RUN groupadd --gid 999 docker \
    && usermod -aG docker airflow

USER airflow