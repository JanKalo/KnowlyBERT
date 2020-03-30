import argparse
import shlex, subprocess
import signal
import sys, traceback
from time import sleep
from multiprocessing import Lock, Pool
import copy
import timeit
import simplejson as json
import helper_functions
import LAMA.templates.rank_with_templates as rank_with_templates
import build_language_model as lm

class KeyboardInterruptError(Exception): pass

#global variables
lock = None

#execute the queries at KG and LM
def execute_query(tripel, parameter, data):
    global lock
    return_list = [None, None, None, None]
    errors = []
    try:
        #print("start process")
        #results of complete Knowledge Graph
        results_KG_complete, errors_KG_complete = helper_functions.find_results_KG_complete(tripel, data)
        for error in errors_KG_complete:
            errors.append(error)

        #results of incomplete Knowledge Graph
        results_KG_incomplete, expected_classes, errors_KG_incomplete = helper_functions.find_results_KG_incomplete(tripel, parameter, data)
        number_of_KG_results_incomplete = len(results_KG_incomplete)
        for error in errors_KG_incomplete:
            errors.append(error)
        #print("KG result complete", results_KG_complete, "KG result incomplete", results_KG_incomplete)
        #Language Model
        label_subj = helper_functions.find_label(tripel[0], data)
        label_obj = helper_functions.find_label(tripel[2], data)
        if "WARNING" in label_subj:
            errors.append(label_subj) 
        if "WARNING" in label_obj:
            errors.append(label_obj) 
        
        if ("WARNING" not in label_subj and "WARNING" not in label_obj):
            if parameter["apc"] or results_KG_incomplete == {}:
                if label_subj == '?':
                    expected_classes = data["prop_classes"][tripel[1]]["?PQ"]
                elif label_obj == '?':
                    expected_classes = data["prop_classes"][tripel[1]]["QP?"]
                else:
                    raise Exception("Tripel is in a wrong format {}".format(tripel))
            #print("expected classes ", expected_classes)
            labels = set(data["label_id"].keys())
            print("START LAMA")
            result_LM = rank_with_templates.get_ranking(label_subj, tripel[1], label_obj, data["lm_build"], labels, data["prop_template"], parameter["ts"])
            possible_results_LM, not_in_dictionary, errors_LM, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID = helper_functions.find_results_LM(result_LM, results_KG_complete, expected_classes, data)
            for error in errors_LM:
                errors.append(error)
            return_list = helper_functions.get_all_results(parameter, data, tripel[1], "{} {} {}".format(label_subj, tripel[1], label_obj), possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_incomplete, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID, errors)
        else:
            return_list = [None, None, None, errors]
    except KeyboardInterrupt:
        print("Keyboard interrupt in process")
        raise KeyboardInterruptError()
    except:
        lock.acquire()
        print("Exception in Process")
        traceback.print_exc(file=sys.stdout)
        lock.release()
        if len(tripel) == 3:
            query = "{} {} {}".format(tripel[0], tripel[1], tripel[2])
            error_string = query + "\n" + traceback.format_exc()
        else:
            error_string = str(tripel) + "\n" + traceback.format_exc()
        errors.append(error_string)
        return_list = [None, [tripel], None, errors]
    finally:
        #print("finally end process")
        #print(return_list)
        return return_list

def init(l):
    global lock
    lock = l

#execute the hybrid system
def execute(dictio_config, parameter, data):
    #read example file for queries
    queries_file = open(parameter["queries_path"], "r")
    queries = set()
    line = queries_file.readline().replace("\n", "")
    while line != "":
        tripel = line.split(" ")
        subj = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        obj = str(tripel[2]).split('/')[-1].replace('>', "")
        if prop == "P1412":
            queries.add((subj, prop, obj))
        line = queries_file.readline().replace("\n", "")
    print("parsed example file")

    #build language model
    data["lm_build"] = lm.build(parameter["lm"])

    #pool = None
    results_all_processes = []
    log = []
    errors = []
    try:
        print("start hybrid system")
        #l = Lock()
        #pool = Pool(processes=1, initializer=init, initargs=(l,))
        #results = [pool.apply_async(execute_query, args=(tripel, parameter, data)) for tripel in queries]
        #output_first_try = [res.get() for res in results]
        #pool.close()
        #pool.join()
        #queries = set()
        #queries.add(("Q4174681", "P1412", "?"))
        output_first_try = []
        count = 0
        for (s, p, o) in queries:
            if count == 10:
                break
            tripel = [s, p, o]
            print(tripel)
            result = execute_query(tripel, parameter, data)
            output_first_try.append(result)
            count = count + 1
        #print(output_first_try)
        global all_retry_queries
        all_retry_queries = []
        for o in output_first_try:
            if o[1] != None:
                for actu in o[1]:
                    if actu != None:
                        all_retry_queries.append(actu)
        
        output_retry = []
        if all_retry_queries != []:
            print("Try it again: {}".format(all_retry_queries))
            #pool = Pool(processes=1, initializer=init, initargs=(l,))
            #results = [pool.apply_async(execute_query, args=(tripel, parameter, data)) for tripel in all_retry_queries]
            #output_retry = [res.get() for res in results]
            #pool.close()
            #pool.join()
            for tripel in all_retry_queries:
                result = execute_query(tripel, parameter, data)
                output_retry.append(result)
        
        for o in output_first_try:
            if o != [None, None, None, None]:
                for err in o[3]:
                    errors.append(err)
                if o[0] != None:
                    results_all_processes.append(o[0])
                    log.append(o[2])
        for o in output_retry:
            if o != [None, None, None, None]:
                for err in o[3]:
                    errors.append(err)
                if o[0] != None:
                    results_all_processes.append(o[0])
                    log.append(o[2])
        
    except KeyboardInterrupt:
        print ("Keyboard interrupt in main")
        #if pool:
        #    pool.terminate()
        results_all_processes = []
    except:
        print("Exception in Main")
        traceback.print_exc(file=sys.stdout)
        #if pool:
        #    pool.terminate()
        results_all_processes = []
    finally:
        print ("Cleaning up Main")
        return results_all_processes, log, errors
