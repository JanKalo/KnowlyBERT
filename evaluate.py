import hybrid_system
import sys
from random import randint
import time
import os
import timeit
import simplejson as json
import pickle

dictio_props = None

def get_LM_results(data_dictio, output_hybrid, i):
    dictio_querynr_lm_result = {}
    if len(output_hybrid) > 0:
        data_output_hybrid = []
        for d in output_hybrid:
            data_output_hybrid.append(d[i])
        for data in data_output_hybrid:
            string_tripel = "{}{}{}".format(data["tripel"][0], data["tripel"][1], data["tripel"][2])
            results_LM = data["LM"]
            nr = data_dictio["query_id"][string_tripel]
            dictio_querynr_lm_result[nr] = list(results_LM.keys())
            
    return dictio_querynr_lm_result    

def handeling_output(data, parameter, result_all_queries, list_errors):
    if not os.path.exists("evaluation/"):
        os.mkdir("evaluation")
    if result_all_queries != []:
        date_time = time.strftime("%d.%m._%H:%M:%S")
        tp_string = parameter["tp"].split('/')[-1].replace('.json', "").replace("templates_allEntityPairs_", "").replace("prop_sentence_","").replace("_templates", "")
        folder = "{}_tmc_tp{}_ts{}_trm{}_ps{}_kbe{}_cp{}_mmd{}".format(date_time, tp_string, parameter["ts"], parameter["trm"], parameter["ps"], parameter["kbe"], parameter["cp"], parameter["mmd"])
        os.mkdir("evaluation/{}".format(folder))
        os.mkdir("evaluation/{}/data".format(folder))
        for i in range (0, len(parameter["tmc"])):
            tmc = parameter["tmc"][i]
            dictio_querynr_lm_result = get_LM_results(data, result_all_queries, i)
            file_id_lmresult = open("evaluation/{}/data/{}_tp{}_ts{}_trm{}_tmc{}_ps{}_kbe{}_cp{}_mmd{}.json".format(folder, date_time, tp_string, parameter["ts"], parameter["trm"], tmc, parameter["ps"], parameter["kbe"], parameter["cp"], parameter["mmd"]), "w")
            json.dump(dictio_querynr_lm_result, file_id_lmresult)
            file_id_lmresult.close()
            if not os.path.exists("evaluation/{}/{}_query_groups.json".format(folder, date_time)):
                obj_subj_query_groups_file = open("/home/kalo/conferences/iswc2020/data/eval_querytype.json", "r")
                obj_subj_query_groups = json.load(obj_subj_query_groups_file)
                obj_subj_query_groups_file.close()
                final_query_groups = {}
                final_query_groups["all"] = list(dictio_querynr_lm_result.keys())
                final_query_groups["object"] = []
                final_query_groups["subject"] = []
                for ID in final_query_groups["all"]:
                    if ID in obj_subj_query_groups["object"]:
                        final_query_groups["object"].append(ID)
                    elif ID in obj_subj_query_groups["subject"]:
                        final_query_groups["subject"].append(ID)
                    else:
                        print("ERROR")
                file_query_groups = open("evaluation/{}/{}_query_groups.json".format(folder, date_time), "w")
                json.dump(final_query_groups, file_query_groups)
                file_query_groups.close()
        if len(list_errors) > 0:
            #file to save the warnings and errors
            error_file = open("evaluation/{}/err.txt".format(folder), "w")
            for err in list_errors:
                error_file.write(err+"\n")
            error_file.close()
    else:
        print("Hybrid system returns no results")

def read_config_file():
    #parsing the config file
    config_file = open("config.json", "r")
    dictio_config = json.load(config_file)
    config_file.close()
    return dictio_config

def read_dataset_files(dictio_config, queries_string):   
    #parsing the wikidata datasets
    dictio_wikidata_subjects = {} #maps subjects to given property and object of complete and incomplete wikidata
    dictio_wikidata_objects = {} #maps objects to given subject an property of complete and incomplete wikidata
    
    wikidata_gold_file = open(dictio_config["wikidata_gold_path"][queries_string], "r")
    for line in wikidata_gold_file:
        tripel = (line.replace("\n", "")).split(" ")
        subj = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        obj = str(tripel[2]).split('/')[-1].replace('>', "")
        if prop not in dictio_wikidata_subjects:
            dictio_wikidata_subjects[prop] = {}
        else:
            if obj not in dictio_wikidata_subjects[prop]:
                dictio_wikidata_subjects[prop][obj] = {}
                dictio_wikidata_subjects[prop][obj]["complete"] = []
                dictio_wikidata_subjects[prop][obj]["random_incomplete"] = []
            
            dictio_wikidata_subjects[prop][obj]["complete"].append(subj)

        if prop not in dictio_wikidata_objects:
            dictio_wikidata_objects[prop] = {}
        else:
            if subj not in dictio_wikidata_objects[prop]:
                dictio_wikidata_objects[prop][subj] = {}
                dictio_wikidata_objects[prop][subj]["complete"] = []
                dictio_wikidata_objects[prop][subj]["random_incomplete"] = []

            dictio_wikidata_objects[prop][subj]["complete"].append(obj)
    wikidata_gold_file.close()
    del wikidata_gold_file

    wikidata_missing_tripels = open(dictio_config["wikidata_missing_tripel_path"][queries_string], "r")
    for line in wikidata_missing_tripels:
        tripel = (line.replace("\n", "")).split(" ")
        subj = str(tripel[0]).split('/')[-1].replace('>', "")
        prop = str(tripel[1]).split('/')[-1].replace('>', "")
        obj = str(tripel[2]).split('/')[-1].replace('>', "")
        if prop not in dictio_wikidata_subjects:
            print("WARNING something wrong with missing tripels dataset --> property not existing")
        else:
            if obj in dictio_wikidata_subjects[prop]:
                dictio_wikidata_subjects[prop][obj]["random_incomplete"].append(subj)

        if prop not in dictio_wikidata_objects:
            print("WARNING something wrong with missing tripels dataset --> property not existing")
        else:
            if subj in dictio_wikidata_objects[prop]:
                dictio_wikidata_objects[prop][subj]["random_incomplete"].append(obj)
    wikidata_missing_tripels.close()
    del wikidata_missing_tripels
    return dictio_wikidata_subjects, dictio_wikidata_objects

def read_label_id_file(dictio_config, queries_string):
    #parsing the label-ID-dictionary
    dictio_label_id = {}
    label_id_file = open(dictio_config["label_id_rdfLabel_path"][queries_string], "r")
    dictio_label_id = json.load(label_id_file)
    label_id_file.close()
    return dictio_label_id

def read_id_label_file(dictio_config, queries_string):
    #parsing the ID-label-dictionary
    dictio_id_label = {}
    id_label_file = open(dictio_config["id_label_rdfLabel_path"][queries_string], "r")
    dictio_id_label = json.load(id_label_file)
    id_label_file.close()
    return dictio_id_label

def read_p31_p279_file(dictio_config):
    id_p31_file = open(dictio_config["id_p31_path"], "rb")
    id_p279_file = open(dictio_config["id_p279_path"], "rb")
    dictio_id_p31 = pickle.load(id_p31_file)
    dictio_id_p279 = pickle.load(id_p279_file)
    id_p31_file.close()
    id_p279_file.close()
    return dictio_id_p31, dictio_id_p279

def read_cardinality_estimation_file(dictio_config):
    #read json file if cardinality estimation is activated
    dictio_prop_probdistribution = {}
    file_prop_mu_sig = open(dictio_config["cardinality_estimation_path"], "r")
    line = file_prop_mu_sig.readline().split("\n")[0]
    while line != "":
        d = json.loads(line)
        dictio_prop_probdistribution[d["prop"]] = d
        line = file_prop_mu_sig.readline().split("\n")[0]
    file_prop_mu_sig.close()
    return dictio_prop_probdistribution

def read_template_file(path):
    #read json file for templates
    dictio_prop_templates = {}
    file_prop_sentence = open(path, "r", encoding="utf8")
    dictio_prop_templates = json.load(file_prop_sentence)
    file_prop_sentence.close()
    return dictio_prop_templates

def read_prop_classes_file(dictio_config):
    dictio_prop_classes = {}
    file_prop_class = open(dictio_config["prop_class_path"], "r")
    line = file_prop_class.readline().split("\n")[0]
    while line != "":
        data = json.loads(line)
        prop = list(data.keys())
        dictio_prop_classes[prop[0]] = data[prop[0]]
        line = file_prop_class.readline().split("\n")[0]
    file_prop_class.close()
    return dictio_prop_classes

def read_entity_popularity_file(dictio_config):
    #read json file for entity popularity
    dictio_entity_popularity = {}
    file_entity_popularity = open(dictio_config["entity_popularity_path"], "r")
    dictio_entity_popularity = json.load(file_entity_popularity)
    file_entity_popularity.close()
    return dictio_entity_popularity

def make_trie(words):
    _end = '_end_'
    root = dict()
    for word in words:
        current_dict = root
        for token in word.split():
            current_dict = current_dict.setdefault(token, {})
        current_dict[_end] = _end
    return root

def read_query_id_file(dictio_config, queries_string):
    #read json file for dictio of query and ID for Phil ;)
    dictio_query_id = {}
    file_query_id = open(dictio_config["query_id_path"][queries_string], "r")
    dictio_query_id = json.load(file_query_id)
    file_query_id.close()
    return dictio_query_id

sys.path.insert(1, "/home/fichtel/KnowliBERT/kb_embeddings/RelAlign/")
from thirdParty.OpenKE import models
from embedding import Embedding
def get_kb_embedding(dictio_config, queries_string, kbe):
    MODELS = {"rescal": models.RESCAL, \
            "transe": models.TransE, \
            "transh": models.TransH, \
            "transr": models.TransR, \
            "transd": models.TransD, \
            "distmult": models.DistMult, \
            "hole": models.HolE, \
            "complex": models.ComplEx, \
            "analogy": models.Analogy}
    benchmark_dir = dictio_config["kb_embeddings"][queries_string]["benchmark_path"]
    embedding_dir = dictio_config["kb_embeddings"][queries_string]["embedding_path"][kbe]
    return Embedding(benchmark_dir, embedding_dir, MODELS[kbe], embedding_dimensions=50)

def read_context_paragraphs_file(dictio_config, cp):
    if cp == True:
        print("using context paragraphs")
        file_paragraphs = open(dictio_config["paragraph_path"])
        dictio_id_paragraphs = json.load(file_paragraphs)
        file_paragraphs.close()
        return dictio_id_paragraphs
    else:
        print("not using context paragraphs")
        return {}

def check_parameter(parameter):
        print("start parameter check")
        correct_parameter = True
        if not os.path.isfile(parameter["queries_path"]):
            print("queries_path has to be a valid path to a file with one query per line; current path: {}".format(parameter["queries_path"]))
            correct_parameter = False
        if parameter["lm"] != "bert":
            print("only bert.large is accpeted at the moment")
            correct_parameter = False
        if not isinstance(parameter["tmc"], list):
            print("tmc has to be a list of values")
            correct_parameter = False
        else:
            for value in parameter["tmc"]:
                if not isinstance(value, float) and not isinstance(value, str):
                    print("tmc values have to be a number (float) or a string; current tmc value: {}".format(value))
                    correct_parameter = False
                elif isinstance(value, float) and value > 0:
                    print("tmc value has to be negative number or 0; current tmc value: {}".format(value))
                    correct_parameter = False
                elif isinstance(value, str) and value != "auto":
                    print("tmc value has to be the string \"auto\"; current tmc value: {}".format(value))
                    correct_parameter = False
        if isinstance(parameter["ts"], int):
            if parameter["ts"] <= 0:
                print("ts has to be 1 or bigger (int); current ts value: {}".format(parameter["ts"]))
                correct_parameter = False
        else:
            print("ts has to be a number (int); current ts value: {}".format(parameter["ts"]))
            correct_parameter = False
        if parameter["trm"] != "max" and parameter["trm"] != "avg":
            print("trm has to be \"max\" or \"avg\"; current trm value: {}".format(parameter["trm"]))
            correct_parameter = False
        if not isinstance(parameter["apc"], bool):
            print("apc has to be a bool value; current apc value: {}".format(parameter["apc"]))
            correct_parameter = False
        if isinstance(parameter["ps"], int):
            if parameter["ps"] < 0:
                print("ps has to be 0 or bigger (int); current ps value: {}".format(parameter["ps"]))
                correct_parameter = False
        else:
            print("ps has to be a number (int); current ps value: {}".format(parameter["ps"]))
            correct_parameter = False
        if parameter["kbe"] != -1 and parameter["kbe"] != "hole":
            print("only the hole kb embedding is accepted or -1; current kbe value: {}".format(parameter["kbe"]))
            correct_parameter = False
        if not isinstance(parameter["cp"], bool):
            print("cp has to be a bool value; current cp value: {}".format(parameter["cp"]))
            correct_parameter = False
        if isinstance(parameter["mmd"], float):
            if parameter["mmd"] < 0 and parameter["mmd"] > 1:
                print("mmd has to be between 0 and 1 (float); current mmd value: {}".format(parameter["mmd"]))
                correct_parameter = False
        else:
            print("mmd has to be a number (float); current mmd value: {}".format(parameter["mmd"]))
        return correct_parameter

if __name__ == '__main__':
    queries_string = "new"

    dictio_config = read_config_file()
    dictio_wikidata_subjects, dictio_wikidata_objects = read_dataset_files(dictio_config, queries_string)
    dictio_label_id = read_label_id_file(dictio_config, queries_string)
    dictio_id_label = read_id_label_file(dictio_config, queries_string)
    dictio_id_p31, dictio_id_p279 = read_p31_p279_file(dictio_config)
    dictio_prop_classes = read_prop_classes_file(dictio_config)
    dictio_entity_popularity = read_entity_popularity_file(dictio_config)
    dictio_query_id = read_query_id_file(dictio_config, queries_string)

    data = {}
    data["wikidata_subjects"] = dictio_wikidata_subjects
    data["wikidata_objects"] = dictio_wikidata_objects
    data["label_id"] = dictio_label_id
    data["id_label"] = dictio_id_label
    data["trie"] = make_trie(set(data["label_id"].keys()))
    data["id_p31"] = dictio_id_p31
    data["id_p279"] = dictio_id_p279
    data["prop_classes"] = dictio_prop_classes
    data["entity_popularity"] = dictio_entity_popularity
    data["query_id"] = dictio_query_id
    print("read all data files")

    
    #file_queries: path to an query file
    #lm: name of the Language Model(LM)
    #tmc: static threshold for log-probability (=confusion) --> automatically caluclated threshold: "auto"
    #tp: path to the templates which are used
    #ts: value how many templates should be used
    #trm: string which ranking method should be used for the labels of different templates: "avg" oder "max"
    #apc: value wheather the property classes should always be used
    #ps: min value for entity popularity score (no negativ values) --> not activated: 0
    #kbe: name of the kb embedding: "hole" --> not activated: -1
    #cp: bool value wheather context paragraphs should be used
    #mmd: min max difference of probability of a label if multiple templates are used

    evaluations = []
    #evaluation 1
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    print(parameter["queries_path"])
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = -1
    parameter["cp"] = True
    parameter["mmd"] = 0.1
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 2
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = "hole"
    parameter["cp"] = True
    parameter["mmd"] = 0.1
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 3
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = -1
    parameter["cp"] = True
    parameter["mmd"] = 0.5
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 4
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = "hole"
    parameter["cp"] = True
    parameter["mmd"] = 0.5
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 5
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = -1
    parameter["cp"] = True
    parameter["mmd"] = 0.6
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 6
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = "hole"
    parameter["cp"] = True
    parameter["mmd"] = 0.6
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 7
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "avg"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = -1
    parameter["cp"] = True
    parameter["mmd"] = 0.7
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 8
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "avg"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = "hole"
    parameter["cp"] = True
    parameter["mmd"] = 0.7
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 9
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "avg"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = -1
    parameter["cp"] = True
    parameter["mmd"] = 0.8
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    #evaluation 10
    parameter = {}
    parameter["queries_path"] = dictio_config["queries_path"][queries_string]
    parameter["lm"] = "bert"
    parameter["tmc"] = [float("-inf"), "auto"]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "avg"
    parameter["apc"] = False
    parameter["ps"] = 1
    parameter["kbe"] = "hole"
    parameter["cp"] = True
    parameter["mmd"] = 0.8
    if check_parameter(parameter):
        print("parameter correct")
        evaluations.append(parameter)
    else:
        print("parameter not correct")

    runtime = []
    for parameter in evaluations:
        data["prop_template"] = read_template_file(parameter["tp"])
        if parameter["kbe"] != -1:
           data["kb_embedding"] = get_kb_embedding(dictio_config, queries_string, parameter["kbe"])
        data["paragraphs"] = read_context_paragraphs_file(dictio_config, parameter["cp"])

        start = timeit.default_timer()
        parameter, result_all_queries, list_errors = hybrid_system.execute(parameter, data)
        stop = timeit.default_timer()
        handeling_output(data, parameter, result_all_queries, list_errors)
        print('Time: {}min'.format((stop - start)/60))
        runtime.append(str((stop - start)/60)+"min")
    print(runtime)