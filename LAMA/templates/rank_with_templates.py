
import sys
sys.path.append("/home/kalo/conferences/iswc2020/LAMA/lama")
import json
import multi_token as mt
from itertools import islice
import pyodbc
#TODO: Can be deleted later
def readTemplates():
    if os.path.exists("templates.json"):
        with open("templates.json", "r") as prop_templates_file:
            prop_templates = json.load(prop_templates_file)
            prop_templates_file.close()


    return prop_templates

#TODO: delete later, method just for testing
def get_entities(relation):
    entityPairs = set()
    entity2Labels = {}
    label2Entities = {}
    #write query to virtuoso to get entity pairs

    data_virtuoso = "DRIVER={{/home/fichtel/virtodbc_r.so}};HOST=134.169.32.169:{};DATABASE=Virtuoso;UID=dba;PWD=F4B656JXqBG".format(1112)
    cnxn_current = pyodbc.connect(data_virtuoso)
    cnxn_current.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
    cnxn_current.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
    cursor =  cnxn_current.cursor()
    query = "sparql SELECT DISTINCT ?s ?o ?sLabel ?oLabel WHERE {?s <"+relation+"> ?o. ?s <http://www.w3.org/2000/01/rdf-schema#label> ?sLabel. ?o <http://www.w3.org/2000/01/rdf-schema#label> ?oLabel. FILTER(LANG(?sLabel)=\"en\" and LANG(?oLabel)=\"en\")}"
    print(query)
    cursor.execute(query)
    while True:
        row = cursor.fetchone()

        if not row:
            break

        entityPairs.add((row.s,row.o))
        entity2Labels[row.s] = row.sLabel
        entity2Labels[row.o] = row.oLabel

        if row.sLabel in label2Entities:
            label2Entities[row.sLabel].append(row.s)
        else:
            label2Entities[row.sLabel] = [row.s]
        if row.oLabel in label2Entities:
            label2Entities[row.oLabel].append(row.o)
        else:
            label2Entities[row.oLabel] = [row.o]

    return entityPairs, entity2Labels, label2Entities

#TODO: Check whether this method is leading to good results
#TODO: Maybe include confu
def merge_rankings(results_per_template):
    forbidden_results = set(["i", "you", "he", "she", "it", "we", "you", "they", "me", "you", "him", "her", "us", "them"])
    intermediate_rank = {}

    for results in results_per_template:
        label_tuple, template_confidence = results
        for label, confusion in label_tuple:
            if label.lower() not in forbidden_results and label.lower().islower():
                if label in intermediate_rank:
                    #if the new confusion value is better, override the old one
                    if intermediate_rank[label] < confusion:
                        intermediate_rank[label] = confusion
                else:
                    intermediate_rank[label] = confusion

    return [(k, v) for k, v in intermediate_rank.items()]

def get_ranking(e1, r, e2, model, entity_labels, templatesDictionary, no_templates):

    merged_ranking = []

    #get rankings for property and sort by confidence ranking
    templates = templatesDictionary[r]
    #get results for each template
    result_per_templates = []
    for template, confidence in dict(islice(templates.items(), no_templates)).items():
        #build sentence for query

        if e1 == "?":
            instantiated_template = template.replace("[S]","[MASK]")
            instantiated_template = instantiated_template.replace("[O]", e2)
        else:
            instantiated_template = template.replace("[O]","[MASK]")
            instantiated_template = instantiated_template.replace("[S]", e1)

        result_per_templates.append((mt.get_multi_token_results(instantiated_template, model, entity_labels), confidence))

    return merge_rankings(result_per_templates)

import dill
import os
if __name__ == '__main__':

    lm = "bert"
    prop = "P1412"
    entity = "Q183"
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as config_dictionary_file:
            bert = dill.load(config_dictionary_file)
            #load entity labels
            entities, entity2Labels, label2Entities = get_entities("http://www.wikidata.org/prop/direct/{}".format(prop))


            #get templates
            template = readTemplates()

            # start ranking
            rank = get_ranking(entity2Labels["http://www.wikidata.org/entity/{}".format(entity)],prop,"?", bert, label2Entities, template, 10)
            print(rank)