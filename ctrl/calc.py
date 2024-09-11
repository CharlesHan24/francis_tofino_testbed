import numpy as np

fin = open("delay100.txt", "r")
data = []
for i in range(10):
    data.append(list(map(float, fin.readline().split())))

data = np.array(data)
print(data.mean(axis=0))
print(data.var(axis=0) ** 0.5)