import argparse
import shlex, subprocess
import pyodbc
import prob_distribution.decider as distribution
import threshold_method.threshold as threshold_method
import signal
import sys, traceback
import timeit

#TODO without virtuoso
# Specifying the ODBC driver, server name, database, etc. directly
cnxn_current = pyodbc.connect('DSN=MyVirtuoso;UID=dba;PWD=F4B656JXqBG')
cnxn_current.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
cnxn_current.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
# Create a cursor from the connection
cursor_current = cnxn_current.cursor()
    

#function to find the classes of a given entity (i.e. item_id_url=http://www.wikidata.org/entity/Q567)
def find_class(id):
    classes = []
    #finding instance
    query = """SELECT ?instance 
            WHERE {{
                <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/direct/P31> ?instance
            }}""".format(id)
    cursor_current.execute("SPARQL "+query)
    while True:
        row = cursor_current.fetchone()
        if not row:
            break
        actu = row.instance
        classes.append(actu)
    #finding superclass if no instances are found
    if classes == []:
        query = """SELECT ?supclass
                WHERE {{
                    <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/direct/P279> ?supclass
                }}""".format(id)
        cursor_current.execute("SPARQL "+query)
        while True:
            row = cursor_current.fetchone()
            if not row:
                break
            actu = row.supclass
            classes.append(actu)
    #finding part if no instances and no superclasses are found
    if classes == []:
        query = """SELECT ?part
                WHERE {{
                    <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/direct/P361> ?part
                }}""".format(id)
        cursor_current.execute("SPARQL "+query)
        while True:
            row = cursor_current.fetchone()
            if not row:
                break
            actu = row.part
            classes.append(actu)
    return classes

#function to resolve a id (i.e. Q567) into label (i.e. Angela Merkel)
def find_label(id, data):
    if id == '?':
        return id
    else:
        dictio_id_label = data["id_label"]
        if id in dictio_id_label:
            return dictio_id_label[id]
        else:
            return "WARNING: No label have been found, id: {}".format(id)

#function to create output with all data of each query --> return value
def get_output_data(prop, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities):
    data = {}
    data["prop"] = prop
    data["KG"] = [results_KG_complete, results_KG_incomplete]
    if results_LM_estimation == 0 or results_LM_estimation == -1:
        data["LM"] = results_LM
    else:
        data["LM"] = results_LM_estimation
    data["label_possible_entities"] = dictio_label_possible_entities
    data["already_existing"] = already_existing
    data["status_possible_result_LM_label"] = status_possible_result_LM_label
    data["status_possible_result_LM_ID"] = status_possible_result_LM_ID
    data["missing"] = not_in_dictionary
    return data

#function to find the results to the tripel-query of the complete KG
def find_results_KG_complete(tripel, data):
    results_KG_complete = {}
    errors = []
    subj = tripel[0]
    prop = tripel[1]
    obj = tripel[2]
    results = set()
    if subj == '?':
        results = data["wikidata_subjects"][prop][obj]["complete"]
    elif obj == '?':
        results = data["wikidata_objects"][prop][subj]["complete"]
    else:
        errors.append("Tripel is in a wrong format {}".format(tripel))
    for result in results:
        label = find_label(result, data)
        if "WARNING" in label:
            errors.append(label) 
        else:
            results_KG_complete[result] = label
    return results_KG_complete, errors
        
#function to find the results to the tripel-query of the incomplete KG
def find_results_KG_incomplete(tripel, parameter, data):
    results_KG_incomplete = {}
    expected_classes = []
    errors = []
    subj = tripel[0]
    prop = tripel[1]
    obj = tripel[2]
    results = set()
    if subj == "?":
        results = data["wikidata_subjects"][prop][obj][parameter["wikidata_incomplete"]]
    elif obj == "?":
        results = data["wikidata_objects"][prop][subj][parameter["wikidata_incomplete"]]
    else:
        errors.append("Tripel is in a wrong format {}".format(tripel))

    for result in results:
        label = find_label(result, data)
        if "WARNING" in label:
            errors.append(label) 
        else:
            results_KG_incomplete[result] = label
    
    with cursor_current:
        for result in results_KG_incomplete:
            classes = find_class(result)
            if "WARNING" in str(classes):
                errors.append(classes)
            else:
                for c in classes:
                    if c not in expected_classes:
                        expected_classes.append(c)
    return results_KG_incomplete, expected_classes, errors

def find_results_LM(result_LM, results_KG_complete, expected_classes, data):
    #return all possible results which fits to the classes of the KG results
    possible_results_LM = {}
    not_in_dictionary = {}         
    errors = []
    dictio_label_possible_entities = {}
    status_possible_result_LM_label = None
    for (label, probability) in result_LM:
        if status_possible_result_LM_label == None:
            label_KG = []
            for r in results_KG_complete:
                label_KG.append(results_KG_complete[r])
            if label in label_KG:
                status_possible_result_LM_label = "correct_label"
            else:
                status_possible_result_LM_label = "incorrect_label"
        
        #check if LM has a correct result, but the dictio is not complete
        if label in data["label_id"]:
            for k in results_KG_complete:
                if results_KG_complete[k] == label:
                    if k not in data["label_id"][label]:
                        not_in_dictionary[label] = "label exists, but ID {} missing".format(k)
            #check if LM results fits to the classes of the KG results
            inserted = False
            possible_entities = []
            for entity_id in data["label_id"][label]:
                classes_LM = find_class(entity_id)
                if "WARNING" in str(classes_LM):
                    errors.append(classes_LM)
                else:
                    for c in classes_LM:
                        if c in expected_classes:
                            if not inserted:
                                possible_results_LM[entity_id] = [label, probability]
                                possible_entities.append(entity_id)
                                inserted = True
                            else:
                                possible_entities.append(entity_id)
                            break
            if len(possible_entities) > 1:
                dictio_label_possible_entities[label] = possible_entities
        else:
            for k in results_KG_complete:
                if results_KG_complete[k] == label:
                    not_in_dictionary[label] = "label complete missing"
    
    if possible_results_LM == {}:
        status_possible_result_LM_ID = "non"
    else:
        for possible_result in possible_results_LM:
            if possible_result in results_KG_complete:
                status_possible_result_LM_ID = "correct_ID"
            else:
                status_possible_result_LM_ID = "incorrect_ID"
            break
    sorted_possible_results_LM = {k: v for k, v in sorted(possible_results_LM.items(), key=lambda item: item[1][1], reverse=True)}
    return sorted_possible_results_LM, not_in_dictionary, errors, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID

def check_wheather_already_existing(results_LM, results_KG_incomplete):
    already_existing = []
    for res in results_LM:
        #print(res)
        if res in results_KG_incomplete:
            already_existing.append(res)
    #print(already_existing)
    return len(already_existing)

def find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_incomplete, maximum_confusion, maximum_results_LM):
    num_before = 0
    num_of_already_existing = check_wheather_already_existing(results_LM, results_KG_incomplete)
    ready = False
    if num_of_already_existing > 0:
        already_existing = True
    else:
        already_existing = False
    while num_of_already_existing - num_before > 0 and not ready:
        num_before = num_of_already_existing
        count = 0
        for entity_id_url in possible_results_LM:
            confusion = possible_results_LM[entity_id_url][1]
            if float(confusion) >= float(maximum_confusion):
                if count < (maximum_results_LM+num_of_already_existing):
                    results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                    count = count + 1
                else:
                    break
            else:
                ready = True
                break
        num_of_already_existing = check_wheather_already_existing(results_LM, results_KG_incomplete)
    return already_existing

def get_data_LM(parameter, data,  query, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete):
    if parameter["ces"] == -1 or cardinality_estimation_percentage == [-1]:
        #print("no cardinality estimation, hard coded max_result:"label_enti = find_label(items[0], cursor_current)
        results_LM = {}
        if threshold_method_confusion == 0:
            #print("no threshold finding for confusion, hard coded max_confusion:", max_confusion)
            count = 0
            for entity_id_url in possible_results_LM:
                confusion = possible_results_LM[entity_id_url][1]
                if float(confusion) >= max_confusion and count < parameter["mr"]:
                    results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                    count = count + 1
                else:
                    break
            already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_incomplete, max_confusion, parameter["mr"])
            return -2, 0, -1, possible_results_LM, results_LM, 0, not_in_dictionary, already_existing
        else:
            threshold, log = threshold_method.find(query, possible_results_LM, threshold_method_confusion, parameter["tmn"], threshold_method_percentage)
            #print("calculated threshold of confusion:", threshold)
            count = 0
            for entity_id_url in possible_results_LM:
                confusion = possible_results_LM[entity_id_url][1]
                if float(confusion) >= float(threshold) and count < parameter["mr"]:
                    results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                    count = count + 1
                else:
                    break
            already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_incomplete, threshold, parameter["mr"])
            return -2, threshold, log, possible_results_LM, results_LM, 0, not_in_dictionary, already_existing
    #cardinality estimation activated
    else:
        #print("cardinality estimation, ces: {}, cep: {}".format(parameter["ces"], cardinality_estimation_percentage))
        number_of_adds = distribution.decide(data["prop_probdistribution"], prop, parameter["ces"], cardinality_estimation_percentage, number_of_KG_results_imcomplete, False)
        #print("number of adds of LM:", number_of_adds)
        if number_of_adds >= 0:
            results_LM_estimation = {}
            if threshold_method_confusion == 0:
                #print("no threshold finding for confusion, hard coded max_confusion:", max_confusion)
                results_LM = {}
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= max_confusion and count < number_of_adds:
                        results_LM_estimation[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM_estimation, possible_results_LM, results_KG_incomplete, max_confusion, number_of_adds)
                return number_of_adds, 0, -1, possible_results_LM, 0, results_LM_estimation, not_in_dictionary, already_existing
            else:
                #print("threshold confusion")
                threshold, log = threshold_method.find(query, possible_results_LM, threshold_method_confusion, parameter["tmn"], threshold_method_percentage)
                #print("calculated threshold of confsuion:", threshold)
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= float(threshold) and count < number_of_adds:
                        results_LM_estimation[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM_estimation, possible_results_LM, results_KG_incomplete, threshold, number_of_adds)
                return number_of_adds, threshold, log, possible_results_LM, 0, results_LM_estimation, not_in_dictionary, already_existing
        else:
            #print("sampling too small --> fallback no cardinality estimation, hard coded max_result:", parameter["mr"])
            results_LM = {}
            if threshold_method_confusion == 0:
                #print("no threshold finding for confusion, hard coded max_confusion:", max_confusion)
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= max_confusion and count < parameter["mr"]:
                        results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_incomplete, max_confusion, parameter["mr"])
                return number_of_adds, 0, -1, possible_results_LM, results_LM, -1, not_in_dictionary, already_existing
            else:
                #print("threshold confusion")
                threshold, log = threshold_method.find(query, possible_results_LM, threshold_method_confusion, parameter["tmn"], threshold_method_percentage)
                #print("calculated threshold of confusion:", threshold)
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= float(threshold) and count < parameter["mr"]:
                        results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_incomplete, threshold, parameter["mr"])
                return number_of_adds, threshold, log, possible_results_LM, results_LM, -1, not_in_dictionary, already_existing

def string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation):
    result_string = ""
    if number_of_adds == -2:
        result_string = result_string + "no cardinality estimation, hard coded max_result:" + str(parameter["mr"]) + "\n"
        if threshold == 0:
            result_string = result_string + "should not find threshold for confusion, hard coded max_confusion:" +  str(max_confusion) + "\n"
        else:
            result_string = result_string + "find threshold for confusion\n"
            result_string = result_string + threshold_log + "\n"
            result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
    else:
        result_string = result_string + "cardinality estimation, ces: {}, cep: {}".format(parameter["ces"], cardinality_estimation_percentage) + "\n"
        result_string = result_string + "number of adds of LM:" + str(number_of_adds) + "\n"
        if number_of_adds >= 0:
            if threshold == 0:
                result_string = result_string + "should not find threshold for confusion, hard coded max_confusion:" +  str(max_confusion) + "\n"
            else:
                result_string = result_string + "find threshold for confusion\n"
                result_string = result_string + threshold_log + "\n"
                result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
        else:
            result_string = result_string + "sampling too small --> fallback no cardinality estimation, hard coded max_result:" +  str(parameter["mr"]) + "\n"
            if threshold == 0:
                result_string = result_string + "should not find threshold for confusion, hard coded max_confusion:" +  str(max_confusion) + "\n"
            else:
                result_string = result_string + "find threshold for confusion\n"
                result_string = result_string + threshold_log + "\n"
                result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
    result_string = result_string + "\nQUERY: {}".format(query_LM) + "\n"
    result_string = result_string + "Result KG current:\n{}".format(results_KG_complete) + "\n"
    result_string = result_string + "Result KG outdated/random:\n{}".format(results_KG_incomplete) + "\n"
    frist_20_possible_results_LM = {}
    count = 0
    for res in possible_results_LM:
        if count == 20:
            break
        else:
            frist_20_possible_results_LM[res] = possible_results_LM[res]
            count = count + 1
    if results_LM_estimation == 0:
        result_string = result_string + "Result LM:\n{}".format(results_LM) + "\n"
        result_string = result_string + "Result LM possible:\n{}".format(frist_20_possible_results_LM) + "\n"
    elif results_LM_estimation == -1:
        result_string = result_string + "Result LM estimation: sampling to small --> fallback to hard coded max_results\n{}".format(results_LM) +"\n"
        result_string = result_string + "Result LM possible:\n{}".format(frist_20_possible_results_LM) + "\n"
    else:
        result_string = result_string + "Result LM estimation:\n{}".format(results_LM_estimation) + "\n"
        result_string = result_string + "Result LM possible:\n{}".format(frist_20_possible_results_LM) + "\n"
    result_string = result_string + "\n"
    return result_string

def get_all_results(parameter, data, prop, query_LM, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID, errors_actu):
    if len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["mc"]) == 1 and len(parameter["tmp"]) == 1:
        cardinality_estimation_percentage = parameter["cep"][0]
        threshold_method_confusion = parameter["tmc"][0]
        max_confusion = parameter["mc"][0]
        threshold_method_percentage = parameter["tmp"][0]
        number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
        #handeling output of KG and LM
        log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation)
        data = [get_output_data(prop, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities)]
        retry_queries = [None]
        log = [log_string_result]
    elif len(parameter["cep"]) > 1 and len(parameter["tmc"]) == 1 and len(parameter["mc"]) == 1 and len(parameter["tmp"]) == 1:
        threshold_method_confusion = parameter["tmc"][0]
        max_confusion = parameter["mc"][0]
        threshold_method_percentage = parameter["tmp"][0]
        data = []
        retry_queries = []
        log = []
        for cardinality_estimation_percentage in parameter["cep"]:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    elif len(parameter["cep"]) == 1 and len(parameter["tmc"]) > 1 and len(parameter["mc"]) == 1 and len(parameter["tmp"]) == 1:
        cardinality_estimation_percentage = parameter["cep"][0]
        max_confusion = parameter["mc"][0]
        threshold_method_percentage = parameter["tmp"][0]
        data = []
        retry_queries = []
        log = []
        for threshold_method_confusion in parameter["tmc"]:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    elif len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["mc"]) > 1 and len(parameter["tmp"]) == 1:
        cardinality_estimation_percentage = parameter["cep"][0]
        threshold_method_confusion = parameter["tmc"][0]
        threshold_method_percentage = parameter["tmp"][0]
        data = []
        retry_queries = []
        log = []
        for max_confusion in parameter["mc"]:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    elif len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["mc"]) == 1 and len(parameter["tmp"]) > 1:
        cardinality_estimation_percentage = parameter["cep"][0]
        threshold_method_confusion = parameter["tmc"][0]
        max_confusion = parameter["mc"][0]
        data = []
        retry_queries = []
        log = []
        for threshold_method_percentage in parameter["tmp"]:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    return [data, retry_queries, log, errors_actu]