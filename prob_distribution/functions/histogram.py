import numpy as np
import matplotlib as mp
mp.use('Agg')
import matplotlib.pyplot as plt
import sys
import json
import time
import os

def histo_compatible(bins_array):
    max_data = np.amax(bins_array)
    range_bins = []
    for bins in bins_array:
        range_bins.append(bins)
    range_bins.append(max_data+1)
    return range_bins

def execute(prop, all_data, all_bins, save_enable):
    #save histogram in a file
    if save_enable:
        date_time = time.strftime("%d.%m._%H:%M:%S")
        os.mkdir("prob_distribution/{}".format(date_time))
        plt.hist(all_data, bins=histo_compatible(all_bins), align='left')
        plt.title('Property: {}'.format(prop))
        plt.savefig("prob_distribution/{}/P1412_histogram.png".format(date_time))
        #plt.clf()

def calculate_percentage(actu_bin, dictio_bins_percent, at_least_one_result):
    #whole percantage is onyl from 2 to max_bin
    if at_least_one_result:
        whole_percantage = 0
        for bins in dictio_bins_percent:
            if int(bins) > 1:
                whole_percantage = whole_percantage + dictio_bins_percent[bins]
    else:
        whole_percantage = 1
    #calculate percantage from actu_bin to max_bin with factor 1/whole_percantage
    if whole_percantage == 0:
        return 0
    else:
        percentage = 0
        bigger_bins = []
        for bins in dictio_bins_percent:
            if int(bins) > actu_bin:
                bigger_bins.append(bins)
        for i in range(0, len(bigger_bins)):
            percentage = percentage + dictio_bins_percent[bigger_bins[i]]
        return percentage * (1/whole_percantage)