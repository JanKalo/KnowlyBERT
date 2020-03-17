import argparse
import shlex, subprocess
import pyodbc
import prob_distribution.decider as distribution
import triangle_method.threshold as triangle_method
import signal
import sys, traceback
import LM_sentence.find_sentence as LM_sentence
from time import sleep
from multiprocessing import Lock, Pool
import copy
import timeit
import json
import helper_functions

class KeyboardInterruptError(Exception): pass

#global variables
lock = None
lm = None
bool_whole_sentence = None
dictio_examples_random_results = None
dictio_whole_sentence = None
dictio_prop_classes = None
always_prop_classes = None

#execute the queries at KG and LM
def execute_query(port, query):
    global lock
    cnxn_current = None
    cursor_current = None
    return_list = [None, None, None, None]
    errors = []
    items = query.split(" ")
    try:
        print("start process")
        # Specifying the ODBC driver, server name, database, etc. directly
        cnxn_current = pyodbc.connect('DSN=MyVirtuoso;UID=dba;PWD=F4B656JXqBG')
        cnxn_current.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
        cnxn_current.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')

        # Create a cursor from the connection
        cursor_current = cnxn_current.cursor()
        if(items[0] == "?" and "P" in items[1] and "Q" in items[2]):
            #Knowlege Graph: Wikidata 2019 (current)
            query_KG =  """SELECT ?var ?varLabel
                        WHERE {{
                            ?var <http://www.wikidata.org/prop/direct/{}> <http://www.wikidata.org/entity/{}>.
                            OPTIONAL {{
                                ?var <http://www.w3.org/2000/01/rdf-schema#label> ?varLabel.
                                FILTER(LANG(?varLabel) = "en").
                            }} 
                        }}""".format(items[1], items[2])
            results_KG_current, classes_KG_current, number_of_KG_results_current, errors_KG_current = helper_functions.execute_query_KG_current(query_KG, cursor_current)
            for error in errors_KG_current:
                errors.append(error)
            
            #Knowledge Graph: random
            results_KG_random, classes_KG_random, errors_KG_random = helper_functions.find_results_KG_random(dictio_examples_random_results[query], cursor_current)
            number_of_KG_results_random = len(results_KG_random)
            for error in errors_KG_random:
                errors.append(error)

            #Language Model
            label_prop = helper_functions.find_label(items[1], cursor_current)
            if "WARNING" in label_prop:
                errors.append(label_prop)
            label_enti = helper_functions.find_label(items[2], cursor_current)
            if "WARNING" in label_enti:
                errors.append(label_enti)
            if ("WARNING" not in label_enti and "WARNING" not in label_prop):
                if always_prop_classes or results_KG_random == {}:
                    classes_KG_random = dictio_prop_classes[items[1]]["?PQ"]
                if bool_whole_sentence:
                    query_LM = LM_sentence.find(dictio_whole_sentence, items[1], "?PQ")
                    query_LM = query_LM.replace("Q", label_enti)
                    if query_LM == -1:
                        errors.append("WARNING sentence for ?PQ of {} is missing".format(items[1]))
                        query_LM = "[MASK] {} {}.".format(label_prop, label_enti)
                else:
                    query_LM = "[MASK] {} {}.".format(label_prop, label_enti)
                print("START LAMA",query_LM)
                if lm == "roberta":
                    path = "/data/fichtel/roberta.large/"
                    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--rmd", path, "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
                    #print(result)
                elif lm == "bert":
                    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--bmn", "bert-large-cased", "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
                else:
                    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
                possible_results_LM, not_in_dictionary, errors_LM, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID = helper_functions.find_results_LM(result, results_KG_current, classes_KG_random, cursor_current)
                for error in errors_LM:
                    errors.append(error)
                return_list = helper_functions.get_all_results(items[1], query_LM, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_random, classes_KG_random, number_of_KG_results_random,cursor_current,dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID, errors)
            else:
                return_list = [None, None, None, errors]
        elif("Q" in items[0] and "P" in items[1] and items[2] == "?"):
            #Knowlege Graph: Wikidata
            query_KG =  """SELECT ?var ?varLabel
                        WHERE {{
                            <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/direct/{}> ?var.
                            OPTIONAL {{
                                ?var <http://www.w3.org/2000/01/rdf-schema#label> ?varLabel.
                                FILTER(LANG(?varLabel) = "en").
                            }} 
                        }}""".format(items[0], items[1])
            results_KG_current, classes_KG_current, number_of_KG_results_current, errors_KG_current = helper_functions.execute_query_KG_current(query_KG, cursor_current)
            for error in errors_KG_current:
                errors.append(error)
            #Knowledge Graph: random
            results_KG_random, classes_KG_random, errors_KG_random = helper_functions.find_results_KG_random(dictio_examples_random_results[query], cursor_current)
            number_of_KG_results_random = len(results_KG_random)
            for error in errors_KG_random:
                errors.append(error)

            #Language Model
            label_prop = helper_functions.find_label(items[1], cursor_current)
            if "WARNING" in label_prop:
                errors.append(label_prop)
            label_enti = helper_functions.find_label(items[0], cursor_current)
            if "WARNING" in label_enti:
                errors.append(label_enti)
            if ("WARNING" not in label_enti and "WARNING" not in label_prop):
                if always_prop_classes or results_KG_random == {}:
                    classes_KG_random = dictio_prop_classes[items[1]]["QP?"]
                if bool_whole_sentence:
                    query_LM = LM_sentence.find(dictio_whole_sentence, items[1], "QP?")
                    query_LM = query_LM.replace("Q", label_enti)
                    if query_LM == -1:
                        errors.append("WARNING sentence for QP? of {} is missing".format(items[1]))
                        query_LM = "{} {} [MASK].".format(label_enti, label_prop)
                else:
                    query_LM = "{} {} [MASK].".format(label_enti, label_prop)
                print("START LAMA",query_LM)
                if lm == "roberta":
                    path = "/data/fichtel/roberta.large/"
                    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--rmd", path, "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
                    #print(result)
                elif lm == "bert":
                    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--bmn", "bert-large-cased", "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
                else:
                    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
                possible_results_LM, not_in_dictionary, errors_LM, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID = helper_functions.find_results_LM(result, results_KG_current, classes_KG_random, cursor_current)
                for error in errors_LM:
                    errors.append(error)
                return_list = helper_functions.get_all_results(items[1], query_LM, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_random, classes_KG_random, number_of_KG_results_random,cursor_current,dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID, errors)
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
        if len(items) == 3:
            query = "{} {} {}".format(items[0], items[1], items[2])
            error_string = query + "\n" + traceback.format_exc()
        else:
            error_string = str(items) + "\n" + traceback.format_exc()
        errors.append(error_string)
        return_list = [None, [items], None, errors]
    finally:
        print("finally end process")
        if cursor_current:
            cursor_current.close()
            del cursor_current
        if cnxn_current:
            cnxn_current.close()
            del cnxn_current
        return return_list

def init(l):
    global lock
    lock = l

#execute the hybrid system
def execute (port, examples_data_filepath, dictio_entities, l, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc):
    global lm
    lm = l
    global bool_whole_sentence
    bool_whole_sentence = ws
    #read json file for property classes
    global dictio_prop_classes
    dictio_prop_classes = {}
    global always_prop_classes
    always_prop_classes = apc
    file_path = "wikidata/dictio_prop_class.json"
    file_prop_class = open(file_path, "r")
    line = file_prop_class.readline().split("\n")[0]
    while line != "":
        data = json.loads(line)
        prop = list(data.keys())
        dictio_prop_classes[prop[0]] = data[prop[0]]
        line = file_prop_class.readline().split("\n")[0]
    file_prop_class.close()
    #read json file if cardinality estimation is activated
    dictio_prob_distribution = {}
    if ces != -1 and cep != -1:
        file_path = "prob_distribution/prop_mu_sig.json"
        file_prop_mu_sig = open(file_path, "r")
        line = file_prop_mu_sig.readline().split("\n")[0]
        while line != "":
            d = json.loads(line)
            dictio_prob_distribution[d["prop"]] = d
            line = file_prop_mu_sig.readline().split("\n")[0]
        file_prop_mu_sig.close()
        print("parsed json file for cardinality estimation")
    #read json file if whole sentence is activated
    global dictio_whole_sentence
    dictio_whole_sentence = {}
    if bool_whole_sentence:
        file_path = "LM_sentence/prop_sentence.json"
        file_prop_sentence = open(file_path, "r")
        line = file_prop_sentence.readline().split("\n")[0]
        while line != "":
            data = json.loads(line)
            prop = list(data.keys())
            dictio_whole_sentence[prop[0]] = data[prop[0]]
            line = file_prop_sentence.readline().split("\n")[0]
        file_prop_sentence.close()
        print("parsed json file for whole sentence")
    #parsing the examples and try each example to exucute the query
    if "True" in examples_data_filepath:
            at_least_one_result = True
    else:
        at_least_one_result = False
    file = open(examples_data_filepath, "r")
    line = file.readline().split("\n")[0]
    global dictio_examples_random_results
    dictio_examples_random_results = {}
    while line != "":
        data = json.loads(line)
        query = list(data.keys())[0]
        items = query.split(" ")
        #if items[1] not in ["P69", "P1923", "P101", "P166", "P102", "P530", "P30", "P127"]:
        #    dictio_examples_random_results[query] = data[query]
        dictio_examples_random_results[query] = data[query]
        line = file.readline().split("\n")[0]
    file.close()
    print("parsed example file")

    helper_functions.set_global_varibales(dictio_entities, dictio_prob_distribution, dictio_whole_sentence, mc, mr, ces, cep, tmc, tmn, tmp, ws, at_least_one_result)

    pool = None
    results_all_processes = []
    log = []
    errors = []
    try:
        print("start hybrid system")
        l = Lock()
        pool = Pool(processes=20, initializer=init, initargs=(l,))
        results = [pool.apply_async(execute_query, args=(port, items)) for items in list(dictio_examples_random_results.keys())]
        output_first_try = [res.get() for res in results]
        pool.close()
        pool.join()
        global all_retry_queries
        all_retry_queries = []
        for o in output_first_try:
            for actu in o[1]:
                if actu != None:
                    all_retry_queries.append(actu)
        
        output_retry = []
        if all_retry_queries != []:
            print("Try it again: {}".format(all_retry_queries))
            pool = Pool(processes=20, initializer=init, initargs=(l,))
            results = [pool.apply_async(execute_query, args=(port, items)) for items in list(dictio_examples_random_results.keys())]
            output_retry = [res.get() for res in results]
            pool.close()
            pool.join()
        
        for o in output_first_try:
            for err in o[3]:
                errors.append(err)
            if o and o[0] != None:
                results_all_processes.append(o[0])
                log.append(o[2])
        for o in output_retry:
            for err in o[3]:
                errors.append(err)
            if o and o[0] != None:
                results_all_processes.append(o[0])
                log.append(o[2])
        
    except KeyboardInterrupt:
        print ("Keyboard interrupt in main")
        if pool:
            pool.terminate()
        results_all_processes = []
    except:
        print("Exception in Main")
        traceback.print_exc(file=sys.stdout)
        if pool:
            pool.terminate()
        results_all_processes = []
    finally:
        print ("Cleaning up Main")
        return results_all_processes, log, errors
