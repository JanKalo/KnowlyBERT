
import sys
sys.path.append("/home/kalo/conferences/iswc2020/LAMA/lama")
import json
import multi_token as mt
from itertools import islice
import pyodbc
import math
#TODO: Can be deleted later
def readTemplates():
    if os.path.exists("templates.json"):
        with open("templates.json", "r") as prop_templates_file:
            prop_templates = json.load(prop_templates_file)
            prop_templates_file.close()


    return prop_templates


def get_entity_labels_files(label2entity_path, entity2label_path):
    label2entity_file = open(label2entity_path, 'r')
    entity2label_file = open(entity2label_path, 'r')
    label2entity_dict = json.load(label2entity_file)
    entity2label_dict = json.load(entity2label_file)
    return label2entity_dict, entity2label_dict

_end = '_end_'
def make_trie(words):
    root = dict()
    for word in words:
        current_dict = root
        for token in word.split():
            current_dict = current_dict.setdefault(token, {})
        current_dict[_end] = _end
    return root


def merge_rankings_minmax(results_per_template, min_max_diff = 0.1):
    intermediate_rank = {}
    max_confusion = {}
    min_confusion = {}
    for results in results_per_template:
        label_tuple, template_confidence = results
        for label, confusion in label_tuple:
            if label in max_confusion:
                #if the new confusion value is better, override the old one
                if max_confusion[label] < confusion:
                    max_confusion[label] = confusion
            else:
                max_confusion[label] = confusion

            if label in min_confusion:
                #if the new confusion value is smaller, override the old one
                if min_confusion[label] > confusion:
                    min_confusion[label] = confusion
            else:
                min_confusion[label] = confusion
    #compute difference of max an min as in 3.4 of paper
    for label in max_confusion.keys():
        max = math.exp(max_confusion[label])
        min = math.exp(min_confusion[label])
        if max > min_max_diff - min:
            intermediate_rank[label] = max_confusion[label]

    return [(k, v) for k, v in sorted(intermediate_rank.items(), reverse=True, key=lambda item: item[1])]






#TODO: Check whether this method is leading to good results
#TODO: Maybe include confu
def merge_ranking_avg(results_per_template, min_max_diff = 0.1):
    intermediate_rank = {}
    max_confusion = {}
    min_confusion = {}
    sum_confusion = {}
    denominator_confusion = {}

    for results in results_per_template:
        label_tuple, template_confidence = results
        for label, confusion in label_tuple:
            if label in sum_confusion:
                sum_confusion[label] += confusion
                denominator_confusion[label] += 1
            else:
                sum_confusion[label] = confusion
                denominator_confusion[label] = 1

            if label in max_confusion:
                #if the new confusion value is better, override the old one
                if max_confusion[label] < confusion:
                    max_confusion[label] = confusion
            else:
                max_confusion[label] = confusion

            if label in min_confusion:
                #if the new confusion value is smaller, override the old one
                if min_confusion[label] > confusion:
                    min_confusion[label] = confusion
            else:
                min_confusion[label] = confusion
    #compute difference of max an min as in 3.4 of paper
    for label in max_confusion.keys():
        max = math.exp(max_confusion[label])
        min = math.exp(min_confusion[label])
        if max > min_max_diff - min:
            intermediate_rank[label] = (sum_confusion[label]/denominator_confusion[label])

    return [(k, v) for k, v in sorted(intermediate_rank.items(), reverse=True, key=lambda item: item[1])]

def get_ranking(tripel, label_e1, label_e2, model, entity_labels, templatesDictionary, no_templates,paragraphDict, trm, min_max_diff):
    id_e1 = tripel[0]
    r = tripel[1]
    id_e2 = tripel[2]

    #get rankings for property and sort by confidence ranking
    templates = templatesDictionary[r]
    #get results for each template
    result_per_templates = []
    for template, confidence in dict(islice(templates.items(), no_templates)).items():
        #build sentence for query

        if label_e1 == "?":
            try:
                paragraph = paragraphDict["http://www.wikidata.org/entity/"+id_e2]
            except KeyError:
                paragraph = ""
                print("WARNING NO CONTEXT PARAGRAPH FOUND")
            instantiated_template = template.replace("[S]","[MASK]")
            instantiated_template = instantiated_template.replace("[O]", label_e2)
        else:
            try:
                paragraph = paragraphDict["http://www.wikidata.org/entity/"+id_e1]
            except KeyError:
                paragraph = ""
                print("WARNING NO CONTEXT PARAGRAPH FOUND")
            instantiated_template = template.replace("[O]","[MASK]")
            instantiated_template = instantiated_template.replace("[S]", label_e1)

        result_per_templates.append((mt.get_multi_token_results(instantiated_template, paragraph, model, entity_labels), confidence))

    if trm == "avg":
        return merge_ranking_avg(result_per_templates, min_max_diff)
    if trm == "max":
        return merge_rankings_minmax(result_per_templates, min_max_diff)

import dill
import os
import json
if __name__ == '__main__':

    lm = "bert"
    prop = "P69"
    entities = ["Q17003309"]
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as config_dictionary_file:
            bert = dill.load(config_dictionary_file)
            #load entity labels
            label2Entities, entity2Labels = get_entity_labels_files('/home/kalo/conferences/iswc2020/data/label2entity.json','/home/kalo/conferences/iswc2020/data/entity2label.json')
            paragraph_file = open("/home/kalo/conferences/iswc2020/data/paragraph_dict.json")
            paragraphDict = json.load(paragraph_file)
            entity_trie = make_trie(label2Entities.keys())
            #get templates
            template = readTemplates()
            for entity in entities:
                # start ranking
                rank = get_ranking(entity2Labels[entity][0] ,prop,"?", bert, entity_trie, template, 5, paragraphDict, trm="max")
                print(rank)
