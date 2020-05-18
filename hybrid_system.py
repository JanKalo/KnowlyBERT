import argparse
import shlex, subprocess
import signal
import sys, traceback
from time import sleep
import copy
import timeit
import simplejson as json
import helper_functions
import LAMA.templates.rank_with_templates as rank_with_templates
import build_language_model as lm

#execute the queries at KG and LM
def execute_query(tripel, parameter, data):
    dictio_data = {}
    errors = []
    try:
        #print("start process")
        #results of complete Knowledge Graph
        results_KG_complete, errors_KG_complete = helper_functions.find_results_KG_complete(tripel, data)
        for error in errors_KG_complete:
            errors.append(error)

        #results of incomplete Knowledge Graph
        results_KG_incomplete, expected_classes, errors_KG_incomplete = helper_functions.find_results_KG_incomplete(tripel, parameter, data)
        for error in errors_KG_incomplete:
            errors.append(error)
        #print("KG result complete", results_KG_complete, "KG result incomplete", results_KG_incomplete)
        #Language Model
        label_subj = helper_functions.find_label(tripel[0], data)
        label_obj = helper_functions.find_label(tripel[2], data)
        if "[WARNING]" in label_subj:
            errors.append(label_subj) 
        if "[WARNING]" in label_obj:
            errors.append(label_obj) 
        
        if ("[WARNING]" not in label_subj and "[WARNING]" not in label_obj):
            if parameter["apc"] or results_KG_incomplete == {}:
                if label_subj == '?':
                    expected_classes = data["prop_classes"][tripel[1]]["?PQ"]
                elif label_obj == '?':
                    expected_classes = data["prop_classes"][tripel[1]]["QP?"]
                else:
                    raise Exception("Tripel is in a wrong format {}".format(tripel))
            #print("expected classes ", expected_classes)
            #print("START LAMA")
            all_result_LM = rank_with_templates.get_ranking(tripel, label_subj, label_obj, data["lm_build"], data["trie"], data["prop_template"], parameter["ts"], data["paragraphs"], parameter["trm"], parameter["mmd"])
            possible_results_LM, not_in_dictionary, errors_LM, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID = helper_functions.find_results_LM(tripel, all_result_LM, results_KG_complete, expected_classes, parameter, data)
            for error in errors_LM:
                errors.append(error)

            #calculate threshold for log prob automatically if it is wanted
            threshold = None
            if "auto" in parameter["tmc"]:
                #parameter["tmc"].remove("auto")
                threshold = helper_functions.auto_calculate_threshold(results_KG_incomplete, possible_results_LM)
            
            #no error occured
            dictio_data["error"] = errors
            #tripel of the query
            dictio_data["tripel"] = tripel
            #KG results
            dictio_data["results_KG"] = {"complete": results_KG_complete, "incomplete": results_KG_incomplete, "expected_classes": expected_classes}
            #LM results
            dictio_data["results_LM"] = {"all": all_result_LM, "possible": possible_results_LM}
            #current threshold for this query
            dictio_data["auto_threshold"] = threshold
            #debugg data
            dictio_data["debugging"] = {"not_in_dictionary": not_in_dictionary, "dictio_label_possible_entities": dictio_label_possible_entities, "status_possible_result_LM_label": status_possible_result_LM_label, "status_possible_result_LM_ID": status_possible_result_LM_ID}
        else:
            dictio_data["error"] = errors
            dictio_data["tripel"] = tripel
    except KeyboardInterrupt:
        sys.exit("Keyboard Interrupt in process")
        return None
    except:
        print("Exception in Process")
        traceback.print_exc(file=sys.stdout)
        if len(tripel) == 3:
            query = "{} {} {}".format(tripel[0], tripel[1], tripel[2])
            error_string = query + "\n" + traceback.format_exc()
        else:
            error_string = str(tripel) + "\n" + traceback.format_exc()
        errors.append(error_string)
        dictio_data["error"] = errors
        dictio_data["tripel"] = tripel
    finally:
        return dictio_data

#execute the hybrid system
def execute(parameter, data):
    #read example file for queries
    queries_file = open(parameter["queries_path"], "r")
    queries = []
    line = queries_file.readline().replace("\n", "")
    LAMA_props = ['P20', 'P39', 'P937', 'P108', 'P1303', 'P361', 'P1376', 'P101', 'P413', 'P127', 'P36', 'P190', 'P364', 'P138', 'P140', 'P31', 'P27', 'P17', 'P449', 'P463', 'P37', 'P264', 'P527', 'P530', 'P407', 'P740', 'P106', 'P1001', 'P30', 'P1412', 'P159', 'P495', 'P103', 'P47', 'P136', 'P131', 'P279', 'P178', 'P176', 'P276', 'P19']
    while line != "":
        tripel = line.split(" ")
        subj = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        obj = str(tripel[2]).split('/')[-1].replace('>', "")
        #if prop in data["prop_template"]:
        if prop in LAMA_props:
            queries.append([subj, prop, obj])
        line = queries_file.readline().replace("\n", "")
    queries_file.close()
    print("parsed example file")
    #build language model
    data["lm_build"] = lm.build(parameter["lm"])

    results_all_processes = []
    log = []
    errors = []
    try:
        print("start hybrid system")
        #queries = []
        #queries.append(['?', 'P37', 'Q7411'])
        query_data = []
        retry_queries = []
        count = 0
        for tripel in queries:
            #if count == 7:
            #    break
            result = execute_query(tripel, parameter, data)
            if result == None:
                sys.exit("Stop program")
            elif result["error"] != [] and "results_KG" not in result:
                retry_queries.append(result["tripel"])
            else:
                query_data.append(result)
            count = count + 1
            print("{}/{}".format(count, len(queries)))
        
        if retry_queries != []:
            print("Try it again: {}".format(retry_queries))
            for tripel in retry_queries:
                result = execute_query(tripel, parameter, data)
                query_data.append(result)

        #calculate avg threshold over all queries of the automatically calculated thresholds
        if "auto" in parameter["tmc"]:
            avg_auto_threshold = 0
            count = 0
            for result in query_data:
                if "auto_threshold" in result and result["auto_threshold"] != None:
                    count = count + 1
                    avg_auto_threshold = avg_auto_threshold + result["auto_threshold"]
            if avg_auto_threshold == 0 or count == 0:
                avg_auto_threshold = -100
            else:
                avg_auto_threshold = avg_auto_threshold / count
            parameter["tmc"].remove("auto")
            parameter["tmc"].append(avg_auto_threshold)

        for result in query_data:
            for err in result["error"]:
                errors.append(err)
            if "results_KG" in result:
                label_subj = helper_functions.find_label(result["tripel"][0], data)
                label_obj = helper_functions.find_label(result["tripel"][2], data)
                string_query_LM = "{} --> {} {} {}".format(result["tripel"], label_subj, result["tripel"][1], label_obj)
                return_list = helper_functions.get_all_results(parameter, data, result["tripel"], string_query_LM, result["results_KG"], result["results_LM"], result["auto_threshold"], result["debugging"]) 
                results_all_processes.append(return_list[0])
                log.append(return_list[1])
        
    except KeyboardInterrupt:
        print ("Keyboard interrupt in main")
        results_all_processes = []
    except:
        print("Exception in Main")
        traceback.print_exc(file=sys.stdout)
        results_all_processes = []
    finally:
        print ("Cleaning up Main")
        return parameter, results_all_processes, log, errors
