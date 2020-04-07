import pyodbc
import simplejson as json
import os
import pickle

#function to find the classes (p31 and pp279) of given entity ids
def find_class(ids, data):
    instance_of_dict = data["id_p31"]
    subclass_of_dict = data["id_p279"]
    classes = {}
    for id in ids:
        if id in instance_of_dict:
            for c in instance_of_dict[id]:
                if c in classes:
                    classes[c] = classes[c] + 1
                else:
                    classes[c] = 1
                if c in subclass_of_dict:
                    for subclass in subclass_of_dict[c]:
                        if subclass in classes:
                            classes[subclass] = classes[subclass] + 1
                        else:
                            classes[subclass] = 1
        else:
            if id in subclass_of_dict:
                for c in subclass_of_dict[id]:
                    if c in classes:
                        classes[c] = classes[c] + 1
                    else:
                        classes[c] = 1
                    if c in subclass_of_dict:
                        for subclass in subclass_of_dict[c]:
                            if subclass in classes:
                                classes[subclass] = classes[subclass] + 1
                            else:
                                classes[subclass] = 1
    sorted_classes = {k: v for k, v in sorted(classes.items(), reverse=True, key=lambda item: item[1])}
    return sorted_classes

def get_most_common_classes(classes):
    most_common_classes = {}
    biggest_amount = -1
    for c in classes:
        if most_common_classes == {}:
            biggest_amount = classes[c]
            most_common_classes[c] = classes[c]
        else:
            if classes[c]/biggest_amount > 0.4:
                most_common_classes[c] = classes[c]
            else:
                break
    return most_common_classes

def read_config_file():
    #parsing the config file
    config_file = open("../config.json", "r")
    dictio_config = json.load(config_file)
    config_file.close()
    return dictio_config

def read_p31_p279_file(dictio_config):
    id_p31_file = open(dictio_config["id_p31_path"], "rb")
    id_p279_file = open(dictio_config["id_p279_path"], "rb")
    dictio_id_p31 = pickle.load(id_p31_file)
    dictio_id_p279 = pickle.load(id_p279_file)
    id_p31_file.close()
    id_p279_file.close()
    return dictio_id_p31, dictio_id_p279

def read_dataset_file(dictio_config):   
    #parsing the wikidata datasets
    dictio_wikidata_objects = {} #maps objects to given subject an property of complete and incomplete wikidata
    wikidata_missing_tripels = open(dictio_config["wikidata_missing_tripel_path"], "r")
    for line in wikidata_missing_tripels:
        tripel = (line.replace("\n", "")).split(" ")
        subj = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        obj = str(tripel[2]).split('/')[-1].replace('>', "")
        if prop not in dictio_wikidata_objects:
            dictio_wikidata_objects[prop] = {}
        else:
            if subj not in dictio_wikidata_objects[prop]:
                dictio_wikidata_objects[prop][subj] = {}
                dictio_wikidata_objects[prop][subj] = []

            dictio_wikidata_objects[prop][subj].append(obj)
    wikidata_missing_tripels.close()
    return dictio_wikidata_objects

def main():
    dictio_config = read_config_file()
    dictio_id_p31, dictio_id_p279 = read_p31_p279_file(dictio_config)
    dictio_wikidata_objects = read_dataset_file(dictio_config)
    data = {}
    data["id_p31"] = dictio_id_p31
    data["id_p279"] = dictio_id_p279
    data["wikidata_objects"] = dictio_wikidata_objects
    print("read all data files")
    props = ['P19', 'P20', 'P279', 'P37', 'P413', 'P166', 'P449', 'P69', 'P47', 'P138', 'P364', 'P54', 'P463', 'P101', 'P1923', 'P106', 'P527', 'P102', 'P530', 'P176', 'P27', 'P407', 'P30', 'P178', 'P1376', 'P131', 'P1412', 'P108', 'P136', 'P17', 'P39', 'P264', 'P276', 'P937', 'P140', 'P1303', 'P127', 'P103', 'P190', 'P1001', 'P31', 'P495', 'P159', 'P36', 'P740', 'P361']
    dictio_classes = {}
    for p in props:
        try:
            #tripel: (item, prop, value)
            items = []
            values = []
            subjects = dictio_wikidata_objects[p]
            for subj in subjects:
                for _ in range(0, len(dictio_wikidata_objects[p][subj])):
                    items.append(subj)
                objects = dictio_wikidata_objects[p][subj]
                for obj in objects:
                    values.append(obj)
            item_classes = find_class(items, data)            
            values_classes = find_class(values, data)
            temp = {}
            temp["?PQ"] = get_most_common_classes(item_classes)
            temp["QP?"] = get_most_common_classes(values_classes)
            dictio_classes[p] = temp
        except Exception as e:
            print(p)
            print(e)
            continue
    #open a json-file to save the data
    print("open file...")
    if os.path.exists("/home/fichtel/conferences/iswc2020/data/dictio_prop_class_instances.json"):
        os.remove("/home/fichtel/conferences/iswc2020/data/dictio_prop_class_instances.json")
    file = open("/home/fichtel/conferences/iswc2020/data/dictio_prop_class_instances.json", "w")
    for prop in dictio_classes:
        temp = {}
        temp[prop] = dictio_classes[prop]
        json.dump(temp, file)
        file.write("\n")
    file.close()
    print("...result written to json :)")

if __name__ == '__main__':
    main()
