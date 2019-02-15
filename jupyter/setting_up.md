# set up jupyter basic environment:
```bash
mkvirtualenv airflow_jupyter --python=python3.6
pip install jupyter pandas numpy \
 ipykernel sqlalchemy psycopg2 matplotlib \
  seaborn mkl numexpr scipy scikit-learn
ipython kernel install --user --name=airflow_jupyter
pip install nteract_on_jupyter
jupyter nteract
```