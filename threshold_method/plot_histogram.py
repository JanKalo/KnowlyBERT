import numpy as np
import matplotlib as mp
mp.use('Agg')
import matplotlib.pyplot as plt
import os
import time

def save(query, values_confusion, distances):
    date_time = time.strftime("%d.%m._%H:%M:%S")
    os.mkdir("triangle_method/{}".format(date_time))
    y_pos = np.arange(len(distances))
    plt.bar(y_pos, distances, align='center',width=1.0)
    plt.title('Query: {}, Distances'.format(query))
    plt.savefig("triangle_method/{}/distance.png".format(date_time))
    plt.clf()
    y_pos = np.arange(len(values_confusion))
    plt.bar(y_pos, values_confusion, align='center',width=1.0)
    plt.title('Query: {}, Confusion'.format(query))
    plt.savefig("triangle_method/{}/confusion.png".format(date_time))
