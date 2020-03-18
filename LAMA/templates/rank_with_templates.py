
import sys
sys.path.append("/home/kalo/conferences/iswc2020/LAMA/lama")

def readTemplates():
    if os.path.exists("templates.json"):
        with open("templates.json", "r") as prop_templates_file:
            prop_templates = json.load(prop_templates_file)
            prop_templates_file.close()

    #TODO: Templates irgendwie in eine Datenstruktur werfen, so dass ich gleich damit queries beantworten kann
    template_dict = {}
    for line in template_file:
        relation, dictionary = line.split()
        relation_template_dict = eval(dictionary)
        template_dict[relation] = relation_template_dict
    return template_dict


import multi_token as mt
def get_ranking(e1, r, e2):
    merged_ranking = []
    #TODO Rankings in Liste packen
    templates = []

    #get results for each template
    for template in templates:
        #build sentence for query
        sentence = template.replace("")

        mt.get_multi_token_results(sentence, model, entity_labels)
    return merged_ranking
import dill
import os

def load_files():
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as config_dictionary_file:
            bert = dill.load(config_dictionary_file)