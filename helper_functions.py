import argparse
import shlex, subprocess
import pyodbc
import prob_distribution.decider as distribution
import threshold_method.threshold as threshold_method
import signal
import sys, traceback
import timeit
import kb_embeddings.kb_embeddings as kb_embeddings

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
        return "[WARNING]: No classes have been found, id: {}".format(id)

#function to resolve an id (i.e. Q567) into label (i.e. Angela Merkel)
def find_label(id, data):
    if id == '?':
        return id
    else:
        dictio_id_label = data["id_label"]
        if id in dictio_id_label:
            return dictio_id_label[id][0]
        else:
            return "[WARNING]: No label have been found, id: {}".format(id)

#function to create output with all data of each query --> return value
def get_output_data(tripel, results_KG, results_LM, debugging):
    data = {}
    data["tripel"] = tripel
    data["KG"] = [results_KG["complete"], results_KG["incomplete"]]
    data["LM"] = results_LM["final"]
    data["label_possible_entities"] = debugging["dictio_label_possible_entities"]
    data["already_existing"] = debugging["already_existing"]
    data["status_possible_result_LM_label"] = debugging["status_possible_result_LM_label"]
    data["status_possible_result_LM_ID"] = debugging["status_possible_result_LM_ID"]
    data["missing"] = debugging["not_in_dictionary"]
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
        if "[WARNING]" in label:
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
        if "[WARNING]" in label:
            errors.append(label) 
        else:
            results_KG_incomplete[result] = label
    
    for result in results_KG_incomplete:
        classes = find_class(result, data)
        if "[WARNING]" in str(classes):
            errors.append(classes)
        else:
            for c in classes:
                if c not in expected_classes:
                    expected_classes.append(c)
    return results_KG_incomplete, expected_classes, errors

def get_best_entity_id_for_label(tripel, possible_entities, parameter, data):
    if parameter["kbe"] != -1:
        min_loss = float("inf")
        chosen_entity = None
        dictio_entity_loss = {}
        error = None
        for entity in possible_entities:
            if entity in data["entity_popularity"]:
                popularity = data["entity_popularity"][entity]
            else:
                popularity = 0
            #popularity of the entity has to be >= as parameter["ps"] to be a "good" result of LM
            if popularity >= parameter["ps"]:
                loss, error = kb_embeddings.get_loss(data["kb_embedding"], tripel, entity)
                if loss != None:
                    if loss < min_loss:
                        min_loss = loss
                        chosen_entity = entity
                    dictio_entity_loss[entity] = loss
                else:
                    dictio_entity_loss[entity] = error
            else:
                dictio_entity_loss[entity] = "popularity < {}".format(parameter["ps"])
        return chosen_entity, dictio_entity_loss, error
    else:
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
        #popularity of the chosen entity has to be >= as parameter["ps"] to be a "good" result of LM
        if max_popularity >= parameter["ps"]:
            return chosen_entity, dictio_entity_popularity, None
        else:
            return None, dictio_entity_popularity, None

def find_results_LM(tripel, result_LM, results_KG_complete, expected_classes, parameter, data):
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
                if "[WARNING]" in str(classes_LM):
                    errors.append(classes_LM)
                else:
                    for c in classes_LM:
                        if c in expected_classes:
                            possible_entities.append(entity_id)
                            break
            
            chosen_entity, dictio_entity_popularity_or_loss, error = get_best_entity_id_for_label(tripel, possible_entities, parameter, data)
            if error:
                errors.append(error)
            if dictio_entity_popularity_or_loss:
                dictio_label_possible_entities[label] = dictio_entity_popularity_or_loss
            #choose the max probability if two labels are mapped to the same entity ID
            if chosen_entity != None:
                if parameter["kbe"] != -1:
                    probability = kb_embeddings.calculate_probability(chosen_entity, dictio_entity_popularity_or_loss, probability)
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

def find_LM_results_already_existing(results_LM, results_KG):
    num_of_already_existing = check_wheather_already_existing(results_LM["final"], results_KG["incomplete"])
    if num_of_already_existing > 0:
        already_existing = True
    else:
        already_existing = False
    count = 0
    for entity_id_url in results_LM["possible"]:
        if entity_id_url not in results_LM["final"] and count < num_of_already_existing:
            results_LM["final"][entity_id_url] = results_LM["possible"][entity_id_url]
            count = count + 1
    return already_existing

def get_data_LM(parameter, data, query, prop, threshold_method_confusion, threshold_method_percentage, results_KG, results_LM, debugging):
    results_LM["final"] = {}
    threshold, log = threshold_method.find(query, results_LM["possible"], threshold_method_confusion, parameter["tmn"], threshold_method_percentage)
    #print("calculated threshold of confusion:", threshold)
    for entity_id_url in results_LM["possible"]:
        confusion = results_LM["possible"][entity_id_url][1]
        if float(confusion) >= float(threshold):
            results_LM["final"][entity_id_url] = results_LM["possible"][entity_id_url]
        else:
            break
    debugging["already_existing"] = find_LM_results_already_existing(results_LM, results_KG)
    return threshold, log, results_LM, debugging

 
def string_results_KG_LM(parameter, query_LM, threshold, threshold_log, auto_threshold, results_KG, results_LM):
    result_string = ""
    result_string = result_string + "should find threshold for confusion\n"
    result_string = result_string + threshold_log + "\n"
    result_string = result_string + "calculated threshold of confusion: " +  str(threshold) + "\n"
    result_string = result_string + "auto threshold of confusion: " +  str(auto_threshold) + "\n"
    
    result_string = result_string + "expected classes for the query: {}\n".format(results_KG["expected_classes"])
    result_string = result_string + "\nQUERY: {}".format(query_LM) + "\n"

    #get KG results (complete and incomplete)
    if len(results_KG["complete"]) <= 30:
        result_string = result_string + "Result KG complete:\n{}".format(results_KG["complete"]) + "\n"
        result_string = result_string + "Result KG incomplete:\n{}".format(results_KG["incomplete"]) + "\n"
    else:
        missing_entities = {}
        for result in results_KG["complete"]:
            if result not in results_KG["incomplete"]:
                missing_entities[result] = results_KG["complete"][result]
        result_string = result_string + "Missing entities in result KG incomplete:\n{}".format(missing_entities) + "\n"

    #get possible LM results (first 30) 
    frist_30_possible_results_LM = {}
    count = 0
    for res in results_LM["possible"]:
        if count == 30:
            break
        else:
            frist_30_possible_results_LM[res] = results_LM["possible"][res]
            count = count + 1
    #get all LM results (first 50) 
    frist_50_all_results_LM = []
    count = 0
    for res in results_LM["all"]:
        if count == 50:
            break
        else:
            frist_50_all_results_LM.append(res)
            count = count + 1
    
    result_string = result_string + "Result LM:\n{}".format(results_LM["final"]) + "\n"
    result_string = result_string + "Result LM possible:\n{}".format(frist_30_possible_results_LM) + "\n"
    result_string = result_string + "Result LM all:\n{}".format(frist_50_all_results_LM) + "\n"
    
    result_string = result_string + "\n"
    return result_string

def auto_calculate_threshold(results_KG, results_LM):
    #avg threshold
    threshold = 0
    count = 0
    for result in results_KG:
        if result in results_LM:
            threshold = threshold + results_LM[result][1]
            count = count + 1
    if threshold == 0 or count == 0:
        return None
    else:
        threshold = threshold / count
        return threshold

    #min threshold
    #threshold = float('inf')
    #for result in results_KG:
    #   if result in results_LM and results_LM[result][1] < threshold:
    #        threshold = results_LM[result][1]
    #if threshold == float('inf'):
    #    return None
    #else:
    #    return threshold

    #max threshold
    #threshold = float('-inf')
    #for result in results_KG:
    #    if result in results_LM and results_LM[result][1] > threshold:
    #        threshold = results_LM[result][1]
    #if threshold == float('-inf'):
    #    return None
    #else:
    #    return threshold
        

def get_all_results(parameter, data, tripel, query_LM, results_KG, results_LM, auto_threshold, debugging):
    if len(parameter["tmc"]) == 1 and len(parameter["tmp"]) == 1:
        threshold_method_confusion = parameter["tmc"][0]
        threshold_method_percentage = parameter["tmp"][0]
        threshold, threshold_log, results_LM, debugging = get_data_LM(parameter, data, query_LM, tripel[1], threshold_method_confusion, threshold_method_percentage, results_KG, results_LM, debugging)
        #handeling output of KG and LM
        data = [get_output_data(tripel, results_KG, results_LM, debugging)]
        log = [string_results_KG_LM(parameter, query_LM, threshold, threshold_log, auto_threshold, results_KG, results_LM)]
    elif len(parameter["tmc"]) > 1 and len(parameter["tmp"]) == 1:
        threshold_method_percentage = parameter["tmp"][0]
        data = []
        log = []
        for threshold_method_confusion in parameter["tmc"]:
            threshold, threshold_log, results_LM, debugging = get_data_LM(parameter, data, query_LM, tripel[1], threshold_method_confusion, threshold_method_percentage, results_KG, results_LM, debugging)
            #handeling output of KG and LM
            data.append(get_output_data(tripel, results_KG, results_LM, debugging))
            log.append(string_results_KG_LM(parameter, query_LM, threshold, threshold_log, auto_threshold, results_KG, results_LM))
    elif len(parameter["tmc"]) == 1 and len(parameter["tmp"]) > 1:
        threshold_method_confusion = parameter["tmc"][0]
        data = []
        log = []
        for threshold_method_percentage in parameter["tmp"]:
            threshold, threshold_log, results_LM, debugging = get_data_LM(parameter, data, query_LM, tripel[1], threshold_method_confusion, threshold_method_percentage, results_KG, results_LM, debugging)
            #handeling output of KG and LM
            data.append(get_output_data(tripel, results_KG, results_LM, debugging))
            log.append(string_results_KG_LM(parameter, query_LM, threshold, threshold_log, auto_threshold, results_KG, results_LM))
    return [data, log]