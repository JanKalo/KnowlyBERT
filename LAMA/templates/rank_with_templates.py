
import sys
sys.path.append("/home/kalo/conferences/iswc2020/LAMA/lama")

def readTemplates(input_path):

    template_file = open(input_path, 'r')
    template_dict = {}
    for line in template_file:
        relation, dictionary = line.split()
        relation_template_dict = eval(dictionary)
        template_dict[relation] = relation_template_dict
    return template_dict


import multi_token as mt
def get_ranking(e1, r, e2):
    #TODO Rankings in Liste packen
    templates = []

    #get results for each template
    for template in templates:
        #build sentence for query
        sentence = template.replace("")

        mt.get_multi_token_results(sentence, model, entity_labels)


import dill
import os
def load_files():
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as config_dictionary_file:
            bert = dill.load(config_dictionary_file)