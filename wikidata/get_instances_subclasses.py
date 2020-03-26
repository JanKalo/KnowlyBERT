import json
import os

if __name__ == '__main__':
    if os.path.exists("dictio_id_classes.json"):
        with open("dictio_id_classes.json", "r") as dictio_id_classes_file:
            dictio_id_classes = json.load(dictio_id_classes_file)
    else:
        print("create dictio_id_classes")
        if not os.path.exists("dictio_id_p31_P279.json"):
            print("create dictio_id_p31_P279")
            wikidata_file = open("/data/kalo/wikidata-20200206-truthy-BETA.nt", "r")
            dictio_id_p31_P279 = {}
            for line in wikidata_file:
                tripel = (line.replace("\n", "")).split(" ")
                entity = str(tripel[0]).split('/')[-1].replace('>', "")
                prop = str(tripel[1]).split('/')[-1].replace('>', "")
                classes = str(tripel[2]).split('/')[-1].replace('>', "")
                if entity not in dictio_id_p31_P279:
                    dictio_id_p31_P279[entity] = {}
                    dictio_id_p31_P279[entity]["P31"] = []
                    dictio_id_p31_P279[entity]["P279"] = []
                if prop == "P31":
                    dictio_id_p31_P279[entity]["P31"].append(classes)
                elif prop == "P279":
                    dictio_id_p31_P279[entity]["P279"].append(classes)
                else:
                    print("other prop existing then P31 and P279")
            wikidata_file.close()
            print("ready")
            with open("dictio_id_p31_P279.json", "w") as dictio_id_p31_P279_file:
                json.dump(dictio_id_p31_P279, dictio_id_p31_P279_file)
            print("ready")
       
        with open("dictio_id_p31_P279.json", "r") as dictio_id_p31_P279_file:
            dictio_id_p31_P279 = json.load(dictio_id_p31_P279_file)

        dictio_id_classes = {}
        for entity in dictio_id_p31_P279:
            if dictio_id_p31_P279[entity]["P31"] != []:
                dictio_id_classes[entity] = dictio_id_p31_P279[entity]["P31"]
                for instance_class in dictio_id_classes[entity]:
                    if instance_class in dictio_id_p31_P279:
                        subclasses = dictio_id_p31_P279[instance_class]["P279"]
                        for subclass in subclasses:
                            if subclass not in dictio_id_classes:
                                dictio_id_classes[entity].append(subclass)
            else:
                if dictio_id_p31_P279[entity]["P279"] != []:
                    dictio_id_classes[entity] = dictio_id_p31_P279[entity]["P279"]
            
        with open("dictio_id_classes.json", "w") as dictio_id_classes_file:
            json.dump(dictio_id_classes, dictio_id_classes_file)
        print("ready")

    dictio_label_id = {}
    label_id_file = open("dictio_label_id.json", "r")
    dictio_label_id = json.load(label_id_file)
    label_id_file.close()
    
    must_have_entities = set()
    for label in dictio_label_id:
        ids = dictio_label_id[label]
        for ID in ids:
            if ID not in must_have_entities:
                must_have_entities.add(ID)

    entities = set(dictio_id_classes.keys())
    for entity in must_have_entities:
        if entity not in entities:
            print("WARNING entity missing: {}".format(entity))
        