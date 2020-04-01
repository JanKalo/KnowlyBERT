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



def join_result_lists(results_list, trie):
    #remove pronouns from result list
    forbidden_results = set(["i", "you", "he", "she", "it", "we", "you", "they", "me", "you", "him", "her", "us", "them"])


    joined_results = []
    #iterate over all MASK outputs
    for result in results_list:
        lists = []
        for list in result:
            i = []
            #list topk contains the top 100 list of words and there confidence
            for dict in list['topk']:
                label = dict['token_word_form']
                #we exclude pronouns & labels need to consist of at least one letter
                if label.lower() not in forbidden_results and label.lower().islower():
                    i.append((dict['token_word_form'], dict['log_prob']))
            lists.append(i)

        if len(lists) == 1:
            for token, value in lists[0]:
                if in_trie(trie, token):
                    joined_results.append((token, value))

        else:
            currentTokensToMatch = []
            for tok, value in lists[0]:
                # get the nodes from the first level
                if get_next_tokens(trie, tok):
                    currentTokensToMatch.append((tok, value))

            for i in range(1, len(lists)):
                matching_partners = lists[i]

                nextTokensToMatch = []
                while currentTokensToMatch:
                    last_token, last_value = currentTokensToMatch.pop()

                    for next_token, next_value in matching_partners:
                        joined_token = last_token + " " + next_token
                        if get_next_tokens(trie, joined_token):
                            average_confidence = (last_value + next_value) / 2
                            nextTokensToMatch.append((joined_token, average_confidence))
                            if in_trie(trie, joined_token):
                                joined_results.append((joined_token, average_confidence))
                currentTokensToMatch = nextTokensToMatch



    return joined_results




#should not be needed anymore
def find_entities(label_results, entity_labels):
    entity_results = []

    for label, value in label_results:
        if label in entity_labels:
            entity_results.append((label, value))
    return entity_results


_end = '_end_'
def make_trie(words):
    root = dict()
    for word in words:
        current_dict = root
        for token in word.split():
            current_dict = current_dict.setdefault(token, {})
        current_dict[_end] = _end
    return root

def in_trie(trie, word):
    current_dict = trie
    for letter in word.split():
        if letter not in current_dict:
            return False
        current_dict = current_dict[letter]
    return _end in current_dict

def get_next_tokens(trie, word):
    current_dict = trie
    for token in word.split():
        if token not in current_dict:
            return False
        current_dict = current_dict[token]
    return current_dict.keys()


def get_results(model, sentence):

    #number of tokens
    max_tokens = 3
    result_list = []
    for i in range(1,max_tokens+1):

        if i != 1:
            sentence = sentence.replace("[MASK]","[MASK] [MASK]", 1)
        #print(sentence)
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

def get_multi_token_results(sentence, model, trie):
    #TODO: Not Sorted
    result_list = get_results(model, sentence)
    label_results = join_result_lists(result_list, trie)
    #results = find_entities(label_results, entity_labels)
    return label_results


if __name__ == '__main__':


    #read all wikidata labels

    label2entity_file = open('/home/kalo/conferences/iswc2020/data/label2entity.json', 'r')
    entity_labels = json.load(label2entity_file)

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
        entity_trie = make_trie(entity_labels.keys())
        label_results = join_result_lists(result_list, entity_trie)
        print(label_results)