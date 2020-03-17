import json
import sys
sys.path.append("/home/kalo/conferences/iswc2020/LAMA/lama")
import pyodbc

from modules import build_model_by_name
from utils import print_sentence_predictions, load_vocab
import options as options
import evaluation_metrics as evaluation_metrics
import os
import dill
import itertools



def join_result_lists(results_list):
    #here I need some disambiguation tool
    joined_results = []
    for result in results_list:
        intermediate_topk = []
        for list in result:
            i = []
            for dict in list['topk']:
                i.append((dict['token_word_form'], dict['log_prob']))
            intermediate_topk.append(i)
        a = itertools.product(*intermediate_topk)

        #lets join the pairs to strings now and average the confusion values
        for multi_token_tuple in a:
            multi_token_string = ""
            multi_token_value = 0
            multi_token_counter = 0.0
            for token in multi_token_tuple:
                multi_token_counter += 1.0
                multi_token_string += token[0]
                multi_token_string += " "
                multi_token_value += token[1]
            multi_token_value = (multi_token_value/multi_token_counter)
            joined_results.append((multi_token_string.strip(), multi_token_value))


    return joined_results

def find_entities(label_results, entity_labels):
    entity_results = []
    for label, value in label_results:
        if label in entity_labels:
            entity_results.append((label, value))
    entity_results




def get_results(model, sentence):

    #number of tokens
    max_tokens = 3
    result_list = []
    for i in range(1,max_tokens+1):

        if i != 1:
            sentence = sentence.replace("[MASK]","[MASK] [MASK]", 1)
        print(sentence)
        sentences = [sentence]
        original_log_probs_list, [token_ids], [masked_indices] = model.get_batch_generation([sentences], try_cuda=True)
        index_list = None
        filtered_log_probs_list = original_log_probs_list
        ret = {}
        # build topk lists for this template and safe in ret1 and ret2
        if masked_indices and len(masked_indices) > 0:
            results = evaluation_metrics.get_ranking(filtered_log_probs_list[0], masked_indices, model.vocab,
                                                     index_list=index_list)

        result_list.append(results)
    return result_list

def get_multi_token_results(sentence, model, entity_labels):
    result_list = get_results(model, sentence)
    label_results = join_result_lists(result_list)
    return find_entities(label_results, entity_labels)


if __name__ == '__main__':


    #read all wikidata labels

    entity_labels = {}

    models = {}
    lm = "bert"
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as config_dictionary_file:
            models[lm] = dill.load(config_dictionary_file)
            # args = []
            # models[lm] = build_model_by_name(lm, args)

    for model_name, model in models.items():
        sent = "[MASK] is the president of the United States."
        result_list = get_results(model, sent)
        label_results = join_result_lists(result_list)
        find_entities(label_results, entity_labels)
