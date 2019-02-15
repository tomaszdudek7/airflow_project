# set up jupyter "basic" environment:
```bash
mkvirtualenv airflow_jupyter --python=python3.6
pip install -r requirements.txt
ipython kernel install --user --name=airflow_jupyter
pip install nteract_on_jupyter
pip install papermill[s3]
jupyter nteract
```

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




