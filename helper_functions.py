import argparse
import shlex, subprocess
import pyodbc
import prob_distribution.decider as distribution
import triangle_method.threshold as triangle_method
import signal
import sys, traceback
import LM_sentence.find_sentence as LM_sentence
import timeit
#global variables
entities = None
max_confusions = None
triangle_method_confusions = None
triangle_method_number = None
bool_whole_sentence = None
max_results_LM =  None
cardinality_estimation_sampling = None
cardinality_estimation_percentages = None
dictio_prob_distribution = None
dictio_whole_sentence = None
triangle_method_percentages = None
at_least_one_result = None

#function to find the classes of a given entity (i.e. item_id_url=http://www.wikidata.org/entity/Q567)
def find_class(id, cursor_current):
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
    dictio_id_label = data["id_label"]
    if id in dictio_id_label:
        return dictio_id_label[id]
    else:
        return "WARNING: No label have been found, id: {}".format(id)

#function to create output with all data of each query --> return value
def get_output_data(prop, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities):
    data = {}
    data["prop"] = prop
    data["KG"] = [results_KG_current, results_KG_o_r]
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
    if subj == "?":
        results = data["wikidata_subjects"][prop][obj]["complete"]
    elif obj == "?":
        results = data["wikidata_objects"][prop][subj]["complete"]
    else:
        errors.append("Tripel is in a wrong format {}".format(tripel))
    
    for result in results:
        label = find_label(result, data["id_label"])
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
        label = find_label(result, data["id_label"])
        if "WARNING" in label:
            errors.append(label) 
        else:
            results_KG_incomplete[result] = label

    # Specifying the ODBC driver, server name, database, etc. directly
    cnxn_current = pyodbc.connect('DSN=MyVirtuoso;UID=dba;PWD=F4B656JXqBG')
    cnxn_current.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
    cnxn_current.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
    # Create a cursor from the connection
    cursor_current = cnxn_current.cursor()
    with cursor_current:
        for result in results_KG_incomplete:
            classes = find_class(result, cursor_current)
            if "WARNING" in str(classes):
                errors.append(classes)
            else:
                for c in classes:
                    if c not in expected_classes:
                        expected_classes.append(c)
    return results_KG_incomplete, expected_classes, errors

def find_results_LM(result_LM, results_KG_complete, expected_classes, data):
    #return all possible results which fits to the classes of the KG results
    results_LM = {}
    not_in_dictionary = {}         
    lines = result.split("\n")
    errors = []
    dictio_label_possible_entities = {}
    status_possible_result_LM_label = None
    for line in lines:
        if line != "Better speed can be achieved with apex installed from https://www.github.com/nvidia/apex.":
            if(line != ''):
                values = line.split(" ")
                label = values[0]
                if status_possible_result_LM_label == None:
                    label_KG = []
                    for r in result_KG:
                        label_KG.append(result_KG[r])
                    if label in label_KG:
                        status_possible_result_LM_label = "correct_label"
                    else:
                        status_possible_result_LM_label = "incorrect_label"
                confusion = values[1] #TODO ist das der richtige wert? was ist mit dem allgemeinen Wert perplexy?
                #check if LM has a correct result, but the dictio is not complete
                
                if label in entities:
                    for k in result_KG:
                        if result_KG[k] == label:
                            if k not in entities[label]:
                                not_in_dictionary[label] = "label exists, but ID {} missing".format(k)
                    #check if LM results fits to the classes of the KG results
                    inserted = False
                    possible_entities = []
                    for entity_id_url in entities[label]:
                        classes_LM = find_class(entity_id_url, cursor_current)
                        if "WARNING" in str(classes_LM):
                            errors.append(classes_LM)
                        else:
                            for c in classes_LM:
                                if c in classes_KG:
                                    if not inserted:
                                        results_LM[entity_id_url] = [label, confusion]
                                        possible_entities.append(entity_id_url)
                                        inserted = True
                                    else:
                                        possible_entities.append(entity_id_url)
                                    break
                    if len(possible_entities) > 1:
                        dictio_label_possible_entities[label] = possible_entities
                else:
                    for k in result_KG:
                        if result_KG[k] == label:
                            not_in_dictionary[label] = "label complete missing"
    
    if results_LM == {}:
        status_possible_result_LM_ID = "non"
    else:
        for possible_result in results_LM:
            if possible_result in result_KG:
                status_possible_result_LM_ID = "correct_ID"
            else:
                status_possible_result_LM_ID = "incorrect_ID"
            break
    return results_LM, not_in_dictionary, errors, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID

def check_wheather_already_existing(results_LM, results_KG_o_r):
    already_existing = []
    for res in results_LM:
        #print(res)
        if res in results_KG_o_r:
            already_existing.append(res)
    #print(already_existing)
    return len(already_existing)

def find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_o_r, maximum_confusion, maximum_results_LM):
    num_before = 0
    num_of_already_existing = check_wheather_already_existing(results_LM, results_KG_o_r)
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
        num_of_already_existing = check_wheather_already_existing(results_LM, results_KG_o_r)
    return already_existing

def get_data_LM(query, cardinality_estimation_percentage, triangle_method_confusion, triangle_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r):
    if cardinality_estimation_sampling == -1 or cardinality_estimation_percentage == -1:
        #print("no cardinality estimation, hard coded max_result:"label_enti = find_label(items[0], cursor_current)
        results_LM = {}
        if triangle_method_confusion == 0:
            #print("no threshold finding for confusion, hard coded max_confusion:", max_confusion)
            count = 0
            for entity_id_url in possible_results_LM:
                confusion = possible_results_LM[entity_id_url][1]
                if float(confusion) >= max_confusion and count < max_results_LM:
                    results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                    count = count + 1
                else:
                    break
            already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_o_r, max_confusion, max_results_LM)
            return -2, 0, -1, possible_results_LM, results_LM, 0, not_in_dictionary, already_existing
        else:
            threshold, log = triangle_method.find(query, possible_results_LM, triangle_method_confusion, triangle_method_number, triangle_method_percentage)
            #print("calculated threshold of confusion:", threshold)
            count = 0
            for entity_id_url in possible_results_LM:
                confusion = possible_results_LM[entity_id_url][1]
                if float(confusion) >= float(threshold) and count < max_results_LM:
                    results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                    count = count + 1
                else:
                    break
            already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_o_r, threshold, max_results_LM)
            return -2, threshold, log, possible_results_LM, results_LM, 0, not_in_dictionary, already_existing
    #cardinality estimation activated
    else:
        #print("cardinality estimation, ces: {}, cep: {}".format(cardinality_estimation_sampling, cardinality_estimation_percentage))
        number_of_adds = distribution.decide(dictio_prob_distribution, prop, cardinality_estimation_sampling, cardinality_estimation_percentage, number_of_KG_results_o_r, at_least_one_result)
        #print("number of adds of LM:", number_of_adds)
        if number_of_adds >= 0:
            results_LM_estimation = {}
            if triangle_method_confusion == 0:
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
                already_existing = find_LM_results_already_existing(results_LM_estimation, possible_results_LM, results_KG_o_r, max_confusion, number_of_adds)
                return number_of_adds, 0, -1, possible_results_LM, 0, results_LM_estimation, not_in_dictionary, already_existing
            else:
                #print("threshold confusion")
                threshold, log = triangle_method.find(query, possible_results_LM, triangle_method_confusion, triangle_method_number, triangle_method_percentage)
                #print("calculated threshold of confsuion:", threshold)
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= float(threshold) and count < number_of_adds:
                        results_LM_estimation[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM_estimation, possible_results_LM, results_KG_o_r, threshold, number_of_adds)
                return number_of_adds, threshold, log, possible_results_LM, 0, results_LM_estimation, not_in_dictionary, already_existing
        else:
            #print("sampling too small --> fallback no cardinality estimation, hard coded max_result:", max_results_LM)
            results_LM = {}
            if triangle_method_confusion == 0:
                #print("no threshold finding for confusion, hard coded max_confusion:", max_confusion)
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= max_confusion and count < max_results_LM:
                        results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_o_r, max_confusion, max_results_LM)
                return number_of_adds, 0, -1, possible_results_LM, results_LM, -1, not_in_dictionary, already_existing
            else:
                #print("threshold confusion")
                threshold, log = triangle_method.find(query, possible_results_LM, triangle_method_confusion, triangle_method_number, triangle_method_percentage)
                #print("calculated threshold of confusion:", threshold)
                count = 0
                for entity_id_url in possible_results_LM:
                    confusion = possible_results_LM[entity_id_url][1]
                    if float(confusion) >= float(threshold) and count < max_results_LM:
                        results_LM[entity_id_url] = possible_results_LM[entity_id_url]
                        count = count + 1
                    else:
                        break
                already_existing = find_LM_results_already_existing(results_LM, possible_results_LM, results_KG_o_r, threshold, max_results_LM)
                return number_of_adds, threshold, log, possible_results_LM, results_LM, -1, not_in_dictionary, already_existing

def string_results_KG_LM(query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation):
    result_string = ""
    if number_of_adds == -2:
        result_string = result_string + "no cardinality estimation, hard coded max_result:" + str(max_results_LM) + "\n"
        if threshold == 0:
            result_string = result_string + "should not find threshold for confusion, hard coded max_confusion:" +  str(max_confusion) + "\n"
        else:
            result_string = result_string + "find threshold for confusion\n"
            result_string = result_string + threshold_log + "\n"
            result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
    else:
        result_string = result_string + "cardinality estimation, ces: {}, cep: {}".format(cardinality_estimation_sampling, cardinality_estimation_percentage) + "\n"
        result_string = result_string + "number of adds of LM:" + str(number_of_adds) + "\n"
        if number_of_adds >= 0:
            if threshold == 0:
                result_string = result_string + "should not find threshold for confusion, hard coded max_confusion:" +  str(max_confusion) + "\n"
            else:
                result_string = result_string + "find threshold for confusion\n"
                result_string = result_string + threshold_log + "\n"
                result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
        else:
            result_string = result_string + "sampling too small --> fallback no cardinality estimation, hard coded max_result:" +  str(max_results_LM) + "\n"
            if threshold == 0:
                result_string = result_string + "should not find threshold for confusion, hard coded max_confusion:" +  str(max_confusion) + "\n"
            else:
                result_string = result_string + "find threshold for confusion\n"
                result_string = result_string + threshold_log + "\n"
                result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
    result_string = result_string + "\nQUERY: {}".format(query_LM) + "\n"
    result_string = result_string + "Result KG current:\n{}".format(results_KG_current) + "\n"
    result_string = result_string + "Result KG outdated/random:\n{}".format(results_KG_o_r) + "\n"
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

def get_all_results(prop, query_LM, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r, cursor_current, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID, errors_actu):
    if len(cardinality_estimation_percentages) == 1 and len(triangle_method_confusions) == 1 and len(max_confusions) == 1 and len(triangle_method_percentages) == 1:
        cardinality_estimation_percentage = cardinality_estimation_percentages[0]
        triangle_method_confusion = triangle_method_confusions[0]
        max_confusion = max_confusions[0]
        triangle_method_percentage = triangle_method_percentages[0]
        number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(query_LM, cardinality_estimation_percentage, triangle_method_confusion, triangle_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r)
        #handeling output of KG and LM
        log_string_result = string_results_KG_LM(query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation)
        data = [get_output_data(prop, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities)]
        retry_queries = [None]
        log = [log_string_result]
    elif len(cardinality_estimation_percentages) > 1 and len(triangle_method_confusions) == 1 and len(max_confusions) == 1 and len(triangle_method_percentages) == 1:
        triangle_method_confusion = triangle_method_confusions[0]
        max_confusion = max_confusions[0]
        triangle_method_percentage = triangle_method_percentages[0]
        data = []
        retry_queries = []
        log = []
        for cardinality_estimation_percentage in cardinality_estimation_percentages:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(query_LM, cardinality_estimation_percentage, triangle_method_confusion, triangle_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    elif len(cardinality_estimation_percentages) == 1 and len(triangle_method_confusions) > 1 and len(max_confusions) == 1 and len(triangle_method_percentages) == 1:
        cardinality_estimation_percentage = cardinality_estimation_percentages[0]
        max_confusion = max_confusions[0]
        triangle_method_percentage = triangle_method_percentages[0]
        data = []
        retry_queries = []
        log = []
        for triangle_method_confusion in triangle_method_confusions:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(query_LM, cardinality_estimation_percentage, triangle_method_confusion, triangle_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    elif len(cardinality_estimation_percentages) == 1 and len(triangle_method_confusions) == 1 and len(max_confusions) > 1 and len(triangle_method_percentages) == 1:
        cardinality_estimation_percentage = cardinality_estimation_percentages[0]
        triangle_method_confusion = triangle_method_confusions[0]
        triangle_method_percentage = triangle_method_percentages[0]
        data = []
        retry_queries = []
        log = []
        for max_confusion in max_confusions:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(query_LM, cardinality_estimation_percentage, triangle_method_confusion, triangle_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    elif len(cardinality_estimation_percentages) == 1 and len(triangle_method_confusions) == 1 and len(max_confusions) == 1 and len(triangle_method_percentages) > 1:
        cardinality_estimation_percentage = cardinality_estimation_percentages[0]
        triangle_method_confusion = triangle_method_confusions[0]
        max_confusion = max_confusions[0]
        data = []
        retry_queries = []
        log = []
        for triangle_method_percentage in triangle_method_percentages:
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(query_LM, cardinality_estimation_percentage, triangle_method_confusion, triangle_method_percentage, max_confusion, prop, possible_results_LM, not_in_dictionary, results_KG_current, results_KG_o_r, classes_KG_o_r, number_of_KG_results_o_r)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation)
            data.append(get_output_data(prop, results_KG_current, results_KG_o_r, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    return [data, retry_queries, log, errors_actu]