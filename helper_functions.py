import argparse
import shlex, subprocess
import pyodbc
import prob_distribution.decider as distribution
import threshold_method.threshold as threshold_method
import signal
import sys, traceback
import timeit

#function to find the classes of a given entity (i.e. item_id_url=http://www.wikidata.org/entity/Q567)
def find_class(id, data):
    instance_of_dict = data["id_p31"]
    subclass_of_dict = data["id_p279"]
    try:
        if id in instance_of_dict:
            classes = []
            for c in instance_of_dict[id]:
                if c not in classes:
                    classes.append(c)
                for subclass in subclass_of_dict[c]:
                    if subclass not in classes:
                        classes.append(subclass)
            #print(id, classes)
            return classes
        else:
            classes = []
            for c in subclass_of_dict[id]:
                if c not in classes:
                    classes.append(c)
                for subclass in subclass_of_dict[c]:
                    if subclass not in classes:
                        classes.append(subclass)
            #print(id, classes)
            return classes
    except KeyError:
        return "WARNING: No classes have been found, id: {}".format(id)

#function to resolve an id (i.e. Q567) into label (i.e. Angela Merkel)
def find_label(id, data):
    if id == '?':
        return id
    else:
        dictio_id_label = data["id_label"]
        if id in dictio_id_label:
            return dictio_id_label[id][0]
        else:
            return "WARNING: No label have been found, id: {}".format(id)

#function to create output with all data of each query --> return value
def get_output_data(tripel, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities):
    data = {}
    data["tripel"] = tripel
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
    
    for result in results_KG_incomplete:
        classes = find_class(result, data)
        if "WARNING" in str(classes):
            errors.append(classes)
        else:
            for c in classes:
                if c not in expected_classes:
                    expected_classes.append(c)
    return results_KG_incomplete, expected_classes, errors

def find_results_LM(result_LM, results_KG_complete, expected_classes, parameter, data):
    #return all possible results which fits to the classes of the KG results
    possible_results_LM = {}
    not_in_dictionary = {}         
    errors = []
    dictio_label_possible_entities = {}
    status_possible_result_LM_label = None
    if result_LM == []:
        status_possible_result_LM_label = "non"
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
        dictio_label_id = data["label_id"]
        if label in dictio_label_id:
            #for k in results_KG_complete:
            #    if results_KG_complete[k] == label:
            #        if k not in dictio_label_id[label]:
            #            not_in_dictionary[label] = "label exists, but ID {} missing".format(k)
            
            #check if LM results fits to the expected classes of the query
            possible_entities = []
            for entity_id in dictio_label_id[label]:
                classes_LM = find_class(entity_id, data)
                if "WARNING" in str(classes_LM):
                    errors.append(classes_LM)
                else:
                    for c in classes_LM:
                        if c in expected_classes:
                            possible_entities.append(entity_id)
                            break
            #check the popularity of the possible entities of the actu label
            max_popularity = -1
            chosen_entity = None
            dictio_entity_popularity = {}
            for entity in possible_entities:
                if entity in data["entity_popularity"]:
                    popularity = data["entity_popularity"][entity]
                else:
                    popularity = 0
                if popularity > max_popularity:
                    max_popularity = popularity
                    chosen_entity = entity
                dictio_entity_popularity[entity] = popularity
            if dictio_entity_popularity:
                dictio_label_possible_entities[label] = dictio_entity_popularity
            #popularity of the chosen entity has to be >= as parameter["ps"] to be a "good" result of LM
            if max_popularity >= parameter["ps"]:
                #chose the max probability if two labels are mapped to the same entity ID
                if chosen_entity in possible_results_LM:
                    if probability > possible_results_LM[chosen_entity][1]:
                        possible_results_LM[chosen_entity] = [label, probability]
                else:
                    possible_results_LM[chosen_entity] = [label, probability]
        #else:
        #    for k in results_KG_complete:
        #        if results_KG_complete[k] == label:
        #            not_in_dictionary[label] = "label complete missing"
    
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

def string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, all_result_LM, results_LM, results_LM_estimation, expected_classes):
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
    result_string = result_string + "expected classes for the query: {}\n".format(expected_classes)
    result_string = result_string + "\nQUERY: {}".format(query_LM) + "\n"
    if len(results_KG_complete) <= 30:
        result_string = result_string + "Result KG complete:\n{}".format(results_KG_complete) + "\n"
        result_string = result_string + "Result KG incomplete:\n{}".format(results_KG_incomplete) + "\n"
    else:
        missing_entities = {}
        for result in results_KG_complete:
            if result not in results_KG_incomplete:
                missing_entities[result] = results_KG_complete[result]
        result_string = result_string + "Missing entities in result KG incomplete:\n{}".format(missing_entities) + "\n"
        
    frist_30_possible_results_LM = {}
    count = 0
    for res in possible_results_LM:
        if count == 30:
            break
        else:
            frist_30_possible_results_LM[res] = possible_results_LM[res]
            count = count + 1
    frist_50_all_results_LM = []
    count = 0
    for res in all_result_LM:
        if count == 50:
            break
        else:
            frist_50_all_results_LM.append(res)
            count = count + 1
    if results_LM_estimation == 0:
        result_string = result_string + "Result LM:\n{}".format(results_LM) + "\n"
        result_string = result_string + "Result LM possible:\n{}".format(frist_30_possible_results_LM) + "\n"
        result_string = result_string + "Result LM all:\n{}".format(frist_50_all_results_LM) + "\n"
    elif results_LM_estimation == -1:
        result_string = result_string + "Result LM estimation: sampling to small --> fallback to hard coded max_results\n{}".format(results_LM) +"\n"
        result_string = result_string + "Result LM possible:\n{}".format(frist_30_possible_results_LM) + "\n"
        result_string = result_string + "Result LM all:\n{}".format(frist_50_all_results_LM) + "\n"
    else:
        result_string = result_string + "Result LM estimation:\n{}".format(results_LM_estimation) + "\n"
        result_string = result_string + "Result LM possible:\n{}".format(frist_30_possible_results_LM) + "\n"
        result_string = result_string + "Result LM all:\n{}".format(frist_50_all_results_LM) + "\n"
    result_string = result_string + "\n"
    return result_string

def get_all_results(parameter, data, tripel, query_LM, possible_results_LM, all_result_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete, dictio_label_possible_entities, status_possible_result_LM_label, status_possible_result_LM_ID, errors_actu):
    if len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["mc"]) == 1 and len(parameter["tmp"]) == 1:
        cardinality_estimation_percentage = parameter["cep"][0]
        threshold_method_confusion = parameter["tmc"][0]
        max_confusion = parameter["mc"][0]
        threshold_method_percentage = parameter["tmp"][0]
        number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, tripel[1], possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
        #handeling output of KG and LM
        log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, all_result_LM, results_LM, results_LM_estimation, expected_classes)
        data = [get_output_data(tripel, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities)]
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
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, tripel[1], possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, all_result_LM, results_LM, results_LM_estimation, expected_classes)
            data.append(get_output_data(tripel, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
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
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, tripel[1], possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, all_result_LM, results_LM, results_LM_estimation, expected_classes)
            data.append(get_output_data(tripel, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
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
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, tripel[1], possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, all_result_LM, results_LM, results_LM_estimation, expected_classes)
            data.append(get_output_data(tripel, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
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
            number_of_adds, threshold, threshold_log, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing = get_data_LM(parameter, data,  query_LM, cardinality_estimation_percentage, threshold_method_confusion, threshold_method_percentage, max_confusion, tripel[1], possible_results_LM, not_in_dictionary, results_KG_complete, results_KG_incomplete, expected_classes, number_of_KG_results_imcomplete)
            #handeling output of KG and LM
            log_string_result = string_results_KG_LM(parameter, query_LM, max_confusion, cardinality_estimation_percentage, number_of_adds, threshold, threshold_log, results_KG_complete, results_KG_incomplete, possible_results_LM, all_result_LM, results_LM, results_LM_estimation, expected_classes)
            data.append(get_output_data(tripel, results_KG_complete, results_KG_incomplete, possible_results_LM, results_LM, results_LM_estimation, not_in_dictionary, already_existing, status_possible_result_LM_label, status_possible_result_LM_ID, dictio_label_possible_entities))
            retry_queries.append(None)
            log.append(log_string_result)
    return [data, retry_queries, log, errors_actu]