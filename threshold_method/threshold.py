import numpy as np
import threshold_method.plot_histogram as histogram

def find(query, results_LM, max_confusion, max_number, max_percentage):
    save_histogram = False
    values_confusion =  []
    count = 0
    log = ""
    for actu in results_LM:
        #if float(results_LM[actu][1]) < max_confusion or count == max_number:
        if count == max_number:
            break
        else:
            count = count + 1
            values_confusion.append(results_LM[actu][1])
    log = log + "confusion array: {}\n".format(values_confusion)
    if len(values_confusion) == 0:
        log = log + "no values in array"
        return max_confusion, log
    elif len(values_confusion) == 1:
        log = log + "only one value in array"
        if float(values_confusion[0]) > max_confusion:
            return values_confusion[0], log
        else:
            return max_confusion, log
    elif float(values_confusion[0]) < max_confusion:
        log = log + "first value is too small"
        return max_confusion, log
    
    #calculate mean value to next data point
    gaps = []
    value = 0
    for i in range(0, len(values_confusion)):
        if i != len(values_confusion) -1:
            gaps.append((float(values_confusion[i+1]) - float(values_confusion[i])))
    log = log + "gaps array: {}\n".format(gaps)
    if save_histogram:
        histogram.save(query, values_confusion, gaps)
    max_gap = np.amin(gaps)
    index = gaps.index(max_gap)
    log = log + "max gap: {}, at index: {}\n".format(max_gap, index)
    if index == 0:
        log = log + "first gap is the biggest one"
        if float(values_confusion[0]) > max_confusion:
            return values_confusion[0], log
        else:
            return max_confusion, log
    else:
        new_gaps = gaps[:index]
        log = log + "new gaps array: {}\n".format(new_gaps)
        value = 0
        for gap in new_gaps:
            value = value + gap
        mean_value = value/len(new_gaps)
        log = log + "mean gap: {}\n".format(mean_value)
        
        new_values_confusion = values_confusion[:index+1]
        log = log + "new confusion array: {}\n".format(new_values_confusion)
        #for confusion in new_values_confusion:
        #    value = value + float(confusion)
        #mean_value = value/len(new_values_confusion)
        #log = log + "mean confusion: {}\n".format(mean_value)
        #for i in range(0, len(new_values_confusion)):
        #    if i != len(new_values_confusion) -1:
        #        if float(new_values_confusion[i]) <= mean_value:
        #            if new_gaps[i]/max_gap > max_percentage:
        #                log = log + "actu confusion {} is smaller than mean confusion and gap is more than {} procent equal to max gap".format(new_values_confusion[i], max_percentage*100)
        #                if float(values_confusion[i]) > max_confusion:
        #                    log = log + "calculated confusion threshold ({}) is okay".format(values_confusion[i])
        #                    return values_confusion[i], log
        #                else:
        #                    log = log + "calculated confusion threshold ({}) is smaller than max_confusion".format(values_confusion[i])
        #                    return max_confusion, log
        #            else:
        #                log = log + "actu confusion {} is smaller than mean confusion, but max gap is proportionately bigger".format(new_values_confusion[i])
        #                if float(values_confusion[index]) > max_confusion:
        #                    log = log + "calculated confusion threshold ({}) is okay".format(values_confusion[index])
        #                    return values_confusion[index], log
        #                else:
        #                    log = log + "calculated confusion threshold ({}) is smaller than max_confusion".format(values_confusion[index])
         #                   return max_confusion, log
        #log = log + "no confusion is smaller than mean confusion"
        #if float(values_confusion[index]) > max_confusion:
        #    log = log + "calculated confusion threshold ({}) is okay".format(values_confusion[index])
        #    return values_confusion[index], log
        #else:
        #    log = log + "calculated confusion threshold ({}) is smaller than max_confusion".format(values_confusion[index])
        #    return max_confusion, log
        
        for i in range(0, len(new_values_confusion)):
            if i != len(new_values_confusion) -1:
                if (float(new_values_confusion[i+1]) - float(new_values_confusion[i])) <= mean_value:
                    if new_gaps[i]/max_gap > max_percentage:
                        log = log + "actu gap {} is smaller than mean gap and more than {} procent equal to max gap\n".format(new_gaps[i], max_percentage*100)
                        if float(values_confusion[i]) > max_confusion:
                            log = log + "calculated confusion threshold ({}) is okay".format(values_confusion[i])
                            return values_confusion[i], log
                        else:
                            log = log + "calculated confusion threshold ({}) is smaller than max_confusion".format(values_confusion[i])
                            return max_confusion, log
                    else:
                        log = log + "actu gap {} is smaller than mean gap, but max gap is proportionately bigger\n".format(new_gaps[i])
                        if float(values_confusion[index]) > max_confusion:
                            log = log + "calculated confusion threshold ({}) is okay".format(values_confusion[index])
                            return values_confusion[index], log
                        else:
                            log = log + "calculated confusion threshold ({}) is smaller than max_confusion".format(values_confusion[index])
                            return max_confusion, log
        log = log + "all gaps are bigger than mean gap\n"
        if float(values_confusion[index]) > max_confusion:
            log = log + "calculated confusion threshold ({}) is okay".format(values_confusion[index])
            return values_confusion[index], log
        else:
            log = log + "calculated confusion threshold ({}) is smaller than max_confusion".format(values_confusion[index])
            return max_confusion, log
    
    
