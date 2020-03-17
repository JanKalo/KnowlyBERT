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

def gaussian_formula(x, mu, sig):
    return 1./(np.sqrt(2.*np.pi)*sig)*np.exp(-np.power((x - mu)/sig, 2.)/2)

def calculate_area(number_of_kb_result, mean, sigma):
    whole_area = integrate.quad(gaussian_formula, 1, math.inf, args=(mean, sigma))[0]
    area = integrate.quad(gaussian_formula, number_of_kb_result+1, math.inf, args=(mean, sigma))[0] * 1/whole_area
    return area

#check wheather the function fits for the data and returns value confusion
def calculate_confusion(prop, mean, sigma, all_data, all_bins, complete_all_bins, plot_enable):
    #Methode der kleinsten Quadrate
    sum_least_squares = 0
    hist = np.histogram(all_data, bins=histo_compatible(all_bins), density=1)[0]
    for i in range(0, len(all_bins)):
        gauss = gaussian_formula(all_bins[i], mean, sigma)
        y = hist[i]
        sum_least_squares = sum_least_squares + (gauss-y)**2
    
    #matplotlip
    if plot_enable:
        mp.hist(all_data, bins=histo_compatible(complete_all_bins), density=1, align='left')
        max_x = all_bins[len(all_bins)-1]
        x_values = np.linspace(0, max_x)
        mp.plot(x_values, gaussian_formula(x_values, mean, sigma))
        mp.show()
    return sum_least_squares