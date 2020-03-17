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




def join_result_lists(results_list):
    #here I need some disambiguation tool
    i = 0
    for results in results_list:
        if i == 0:
            continue
            i += 1
        t = ((result1 + " " + result2) for result1 in results[i]["topk"] for result2 in results[i+1]["topk"])
        print (t)
        i += 1



def get_results(model, sentence):

    #number of tokens
    max_tokens = 3

    for i in range(1,max_tokens+1):
        result_list = []
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

if __name__ == '__main__':

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
        join_result_lists(result_list)
