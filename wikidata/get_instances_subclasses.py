import os
import pickle

#building a class dictionary for all entities in our gold standard
#first lets find all entities in our dataset
gold_file = open("/home/kalo/conferences/iswc2020/data/gold_dataset.nt", "r")
all_entities = set()

for line in gold_file:
    tripel = (line.replace("\n", "")).split(" ")
    subject_entity = str(tripel[0]).split('/')[-1].replace('>', "")
    prop = str(tripel[1]).split('/')[-1].replace('>', "")
    object_entity = str(tripel[2]).split('/')[-1].replace('>', "")
    if prop != "P279":
        all_entities.add(subject_entity)
        all_entities.add(object_entity)
		
from collections import defaultdict
#build dictionaries for 
wikidata_file = open("/data/kalo/wikidata-20200206-truthy-BETA.nt", "r")
instance_of_dict = defaultdict(set)
subclass_of_dict = defaultdict(set)

for line in wikidata_file:
    if "<http://www.wikidata.org/prop/direct/P31>" in line:
        tripel = (line.replace("\n", "")).split(" ")
        entity = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        class_ = str(tripel[2]).split('/')[-1].replace('>', "")
        if entity in all_entities:
            if class_ not in instance_of_dict[entity]:
                instance_of_dict[entity].add(class_)
    elif "<http://www.wikidata.org/prop/direct/P279>" in line:
        tripel = (line.replace("\n", "")).split(" ")
        entity = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        class_ = str(tripel[2]).split('/')[-1].replace('>', "")
        if class_ not in subclass_of_dict[entity]:
            subclass_of_dict[entity].add(class_)
wikidata_file.close()

#pickle the dictionaries
with open("/home/kalo/conferences/iswc2020/data/entity_class.pickle", "rb") as entity_class_file:
    pickle.dump(instance_of_dict, entity_class_file)
with open("/home/kalo/conferences/iswc2020/data/subclass_dict.pickle", "rb") as subclass_file:
    pickle.dump(subclass_of_dict, subclass_file)