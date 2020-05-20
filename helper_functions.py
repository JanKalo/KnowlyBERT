import threshold_method.threshold as threshold_method
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



#function to find the results to the query of the complete KG
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
        
#function to find the results to the query of the incomplete KG
def find_results_KG_incomplete(tripel, parameter, data):
    results_KG_incomplete = {}
    expected_classes = []
    errors = []
    subj = tripel[0]
    prop = tripel[1]
    obj = tripel[2]
    results = set()
    if subj == "?":
        results = data["wikidata_subjects"][prop][obj]["random_incomplete"]
    elif obj == "?":
        results = data["wikidata_objects"][prop][subj]["random_incomplete"]
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
    errors = []
    for (label, probability) in result_LM:
        #LM result has to be in the dictio, which maps labels to Wikidata Ids
        dictio_label_id = data["label_id"]
        if label in dictio_label_id:
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
            #choose the max probability if two labels are mapped to the same entity ID
            if chosen_entity != None:
                if parameter["kbe"] != -1:
                    probability = kb_embeddings.calculate_probability(chosen_entity, dictio_entity_popularity_or_loss, probability)
                if chosen_entity in possible_results_LM:
                    if probability > possible_results_LM[chosen_entity][1]:
                        possible_results_LM[chosen_entity] = [label, probability]
                else:
                    possible_results_LM[chosen_entity] = [label, probability]
        else:
            errors.append("[WARNING] {} not in dictio_label_id".format(label))
    
    sorted_possible_results_LM = {k: v for k, v in sorted(possible_results_LM.items(), key=lambda item: item[1][1], reverse=True)}
    return sorted_possible_results_LM, errors

def auto_calculate_threshold(results_KG, results_LM):
    #avg threshold if LM found more than one result of partial result of KG
    threshold = 0
    count = 0
    for result in results_KG:
        if result in results_LM:
            threshold = threshold + results_LM[result][1]
            count = count + 1
    if threshold == 0 or count == 0:
        #LM found no result of partial result of KG
        return None
    else:
        threshold = threshold / count
        return threshold
        

def get_all_results(parameter, data, tripel, query_LM, results_KG, results_LM, auto_threshold):
    query_results = []
    for threshold_method_confusion in parameter["tmc"]:
        results_LM["final"] = {}
        threshold, log = threshold_method.find(query_LM, results_LM["possible"], threshold_method_confusion)
        for entity_id_url in results_LM["possible"]:
            confusion = results_LM["possible"][entity_id_url][1]
            if float(confusion) >= float(threshold):
                results_LM["final"][entity_id_url] = results_LM["possible"][entity_id_url]
            else:
                break
        #save output of KG and LM with current threshold
        query_data = {}
        query_data["tripel"] = tripel
        query_data["KG"] = {"complete": results_KG["complete"], "incomplete": results_KG["incomplete"]}
        query_data["LM"] = results_LM["final"]
        query_results.append(query_data)

    return query_results