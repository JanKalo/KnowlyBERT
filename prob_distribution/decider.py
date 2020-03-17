import numpy as np
import sys
import bisect 
import json
#import prob_distribution.functions.gaussian as gaussian
#import prob_distribution.functions.exponential as exponential
import prob_distribution.functions.histogram as histogram
#import functions.histogram as histogram

#decides which function fits best and returns the number of results which should be add by the LM
# number of adds -1: too small sampling
# number of adds 0: nothing should be add
# number of adds >0: add at least one result would be a good idea

def decide(dictio, prop, threshold_sampling, threshold_percentage, number_of_kb_result, at_least_one_result):
    #constants
    save_enable = False
    d = dictio[prop]
    #mean = d["mean"]
    #sigma = d["sigma"]
    all_data = d["data"]
    n = len(all_data) #number of results
    #all_bins = d["bins"][0]
    complete_all_bins = d["bins"][1] 
    dictio_bins_percent = d["dictio_bin_percent"]
    flags = d["flags"]

    #dictio = {}
    #for bins in complete_all_bins:
    #    dictio[bins] = 0 #initialized with 0
    #for data in all_data:
    #    dictio[data] = dictio[data] + 1 #add number group by bin (e.g. {2: 3000}, 3000 entities have 2 results)
    #print(dictio)

    if n >= threshold_sampling:
        #find bin which has a percentage bigger than 0.98
        #bigger_98 = -1
        #for bins in dictio_bins_percent:
        #    if dictio_bins_percent[bins] > 0.98:
        #        bigger_98 = int(bins)
        #        break
        #if bigger_98 != -1:
        #    print("bigger 98")
        #    actu_bin = bigger_98
        #    if(actu_bin > number_of_kb_result):
        #        number_of_adds = actu_bin - number_of_kb_result
        #    else:
        #        number_of_adds = 0
        if flags["gapless"] or not flags["gapless"]:
            #print("histogram")
            #plotting histogram
            histogram.execute(prop, all_data, complete_all_bins, save_enable)
            actu_bin = number_of_kb_result + 1
            #print(dictio_bins_percent)
            while True:                
                percentage = histogram.calculate_percentage(actu_bin, dictio_bins_percent, at_least_one_result)
                #print("calculated percenatge",percentage)
                if percentage >= threshold_percentage:
                    #add a element would be a good idea because there is a big percentage of bins bigger than actu_bin
                    #print("add element")
                    actu_bin = actu_bin + 1
                else:
                    break
            number_of_adds = actu_bin - number_of_kb_result                        
        #else:
        #    print("function needed")
        #    #TODO DBCC SHOW_STATISTICS wirklich notwendig oder einfach annehmen, dass es eben manche mit 0 gibt?
        #    
        #    confusion_expo, lam = exponential.calculate_confusion(prop, mean, sigma, all_data, all_bins, complete_all_bins, save_enable)
        #    confusion_gauss = gaussian.calculate_confusion(prop, mean, sigma, all_data, all_bins, complete_all_bins, save_enable)
        #    if confusion_expo <= confusion_gauss:
        #        print("expo")
        #        actu_bin = number_of_kb_result
        #        while True:
        #            area = exponential.calculate_area(actu_bin, lam)
        #            print(area)
        #            if area >= threshold_percentage:
        #                #add a element would be a good idea because there is a big percentage of bins bigger than actu_bin
        #               actu_bin = actu_bin + 1
        #            else:
        #                break
        #    else:
        #        print("gauss")
        #        actu_bin = number_of_kb_result
        #        while True:
        #            area = gaussian.calculate_area(actu_bin, mean, sigma)
        #            print(area)
        #            if area >= threshold_percentage:
        #                #add a element would be a good idea because there is a big percentage of bins bigger than actu_bin
        #                actu_bin = actu_bin + 1
        #            else:
        #                break
        #    number_of_adds = actu_bin - number_of_kb_result
        #    #if number_of_adds > 0:
        #    #    print(number_of_kb_result, number_of_adds, dictio_bins_percent)
    else:
        #print("too small sampling")
        number_of_adds = -1
    return number_of_adds