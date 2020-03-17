import numpy as np
from matplotlib import pyplot as mp
import sys
import json
from scipy import integrate
import math

def histo_compatible(bins_array):
    max_data = np.amax(bins_array)
    range_bins = []
    for bins in bins_array:
        range_bins.append(bins)
    range_bins.append(max_data+1)
    return range_bins

#verschoben, damit 0 nicht mehr vorkommt
def exponential_formula(x, lam):
    return lam* np.exp(-lam*(x-1))

def calculate_area(number_of_kb_result, lam):
    area = integrate.quad(exponential_formula, number_of_kb_result+1, math.inf, args=(lam))[0]
    return area

#check wheather the function fits for the data and returns value confusion
def calculate_confusion(prop, mean, sigma, all_data, all_bins, complete_all_bins, plot_enable):
    #calculate median
    all_data.sort()
    n = len(all_data)
    median = -1
    if n % 2:
        #ungerade
        index = int(((n+1)/2) - 1)
        median = all_data[index]
    else:
        #gerade
        index = int((n/2) - 1)
        median = 0.5*(all_data[index]+all_data[index+1])
    #print(median)

    #calculate lambda TODO calculate it with median, mean or sigma?
    lam1 = 1/mean
    lam2 = np.log(2)/median
    lam3 = 1/sigma

    #Methode der kleinsten Quadrate
    lambdas = [lam1, lam2, lam3]
    confusion = []
    for lam in lambdas:
        sum_least_squares = 0
        hist = np.histogram(all_data, bins=histo_compatible(all_bins), density=1)[0]
        for i in range(0, len(all_bins)):
            expo = exponential_formula(all_bins[i], lam)
            y = hist[i]
            sum_least_squares = sum_least_squares + (expo-y)**2
        confusion.append(sum_least_squares)
    min_confusion = np.amin(confusion)
    lam = lambdas[confusion.index(min_confusion)]
    array = ["mean", "median", "sigma"]
    print(array[confusion.index(min_confusion)])

    #matplotlip
    if plot_enable:
        mp.hist(all_data, bins=histo_compatible(complete_all_bins), density=1)
        max_x = complete_all_bins[len(complete_all_bins)-1]
        x_values = np.linspace(1, max_x)
        mp.plot(x_values, exponential_formula(x_values, lam1), label="mean")
        mp.plot(x_values, exponential_formula(x_values, lam2), label="median")
        mp.plot(x_values, exponential_formula(x_values, lam3), label="sigma")
        mp.legend()
        #mp.xticks(np.arange(0, max_x, 5))
        mp.show()
    return min_confusion, lam