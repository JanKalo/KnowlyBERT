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

def get_rels_in_sent(
        sent_b,
        ents,
        mandatory_uri_substr="wikidata.org/prop"):
    # filter entities which are in boundaries
    # and whose uris contain the mandatory uri substring
    # (default: to filter only entities, not relations)
    sent_ents = list(filter(
        lambda ent: (
            ent["boundaries"][0] >= sent_b[0] and
            ent["boundaries"][0] < sent_b[1] and
            mandatory_uri_substr in ent["uri"]
            ),
        ents
        ))
    output_set = set()
    for ent in sent_ents:
        output_set.add(ent["uri"])

    return output_set


def get_ents_in_sent(
        sent_b,
        ents,
        mandatory_uri_substr="wikidata.org/entity/"):
    # filter entities which are in boundaries
    # and whose uris contain the mandatory uri substring
    # (default: to filter only entities, not relations)
    sent_ents = list(filter(
        lambda ent: (
            ent["boundaries"][0] >= sent_b[0] and
            ent["boundaries"][0] < sent_b[1] and
            mandatory_uri_substr in ent["uri"]
            ),
        ents
        ))

    # align boundaries from abstract level to sentence level
    for i in range(0, len(sent_ents)):
        sent_ents[i]["boundaries"][0] -= sent_b[0]
        sent_ents[i]["boundaries"][1] -= sent_b[0]
    return sent_ents




def index_sentences(input_path, entityPairs, relation, entityLabels):
    maxLength = 15
    index = []
    for file in os.listdir(input_path):
        with open(os.path.join(input_path,file), "r") as f:
            jsonf = json.load(f)
        if len(index) >= 500:
            break

        print(len(index))
        # go through every abstract associated to an entity
        for abstract in jsonf:

            # get sentences from "sentences_boundaries"
            for sent_b in abstract["sentences_boundaries"]:

                sent = abstract["text"][sent_b[0]:sent_b[1]]
                if len(sent.split()) <= maxLength:
                    # get entities in this boundary
                    #sent_rels = get_rels_in_sent(sent_b, abstract["entities"])
                    #if relation in set(sent_rels):
                    sent_ents = get_ents_in_sent(sent_b, abstract["entities"])
                    # index sentences containing entity pairs (e1,e2) from input relation r
                    if len(sent_ents) == 2:
                        for e1 in sent_ents:
                            for e2 in sent_ents:
                                if (e1['uri'],e2['uri']) in entityPairs:
                                    entry = {}
                                    entry['entities'] = (e1['uri'],e2['uri'])
                                    entry['e1']= e1['boundaries']
                                    entry['e2'] = e2['boundaries']
                                    sent = sent.replace(e1['surfaceform'], entityLabels[e1['uri']])
                                    sent = sent.replace(e2['surfaceform'], entityLabels[e2['uri']])

                                    entry['sentence'] = sent
                                    index.append(entry)
                                    print(sent)

                # done for file fn
    return index

def get_entities(relation):
    entityPairs = set()
    entityLabels = {}
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
        entityLabels[row.s] = row.sLabel
        entityLabels[row.o] = row.oLabel

    return entityPairs, entityLabels

from itertools import islice
# Implementation of rank1 method from Bouroui et al.
def rank_sentences_1(model, index_entry, entityPairs, entityLabels):
    output_rank = 0
    orig_sentence = index_entry['sentence']
    print(orig_sentence)
    for idx, (e1,e2) in enumerate(islice(entityPairs,0,1000)):
        e1_label = entityLabels[e1][0]
        e2_label = entityLabels[e2][0]

        correct_e1_labels = set(entityLabels[e1])
        correct_e2_labels = set(entityLabels[e2])
        sentence_1 = orig_sentence.replace(entityLabels[e1], '[MASK]')
        sentence_1 = sentence_1.replace(entityLabels[e2], e2_label)

        sentence_2 = orig_sentence.replace(entityLabels[e2], '[MASK]')
        sentence_2 = sentence_2.replace(entityLabels[e1], e1_label)
        sentences = []
        sentences.append(sentence_1)
        sentences.append(sentence_2)

        original_log_probs_list, [token_ids], [masked_indices] = model.get_batch_generation([sentences], try_cuda=True)
        index_list = None

        filtered_log_probs_list = original_log_probs_list

        # build topk lists for this template and safe in ret1 and ret2
        if masked_indices and len(masked_indices) > 0:
            results = evaluation_metrics.get_ranking(filtered_log_probs_list[0], masked_indices, model.vocab,
                                                 index_list=index_list)
        if idx % 100 == 0:
            sys.stdout.write('\r{} / {} '.format(idx, len(entityPairs)))
            sys.stdout.flush()
        for i in range(0,10):
            if results[0]['topk'][i]['token_word_form'] in correct_e2_labels:
                output_rank += 1
            if results[1]['topk'][i]['token_word_form'] in correct_e1_labels:
                output_rank += 1

    return output_rank




#Rank entities with regard to second metric of paper by
def rank_sentences_2(model, index_entry, entityPairs, entityLabels):

    orig_sentence = index_entry['sentence']

    sentence_1 = orig_sentence.replace(entityLabels[index_entry["entities"][0]], '[MASK]')
    sentence_2 = orig_sentence.replace(entityLabels[index_entry["entities"][1]], '[MASK]')

    sentences = []
    sentences.append(sentence_1)
    sentences.append(sentence_2)

    # print("\n{}:".format(model_name))
    original_log_probs_list, [token_ids], [masked_indices] = model.get_batch_generation([sentences], try_cuda=True)

    index_list = None

    filtered_log_probs_list = original_log_probs_list

    ret = {}
    # build topk lists for this template and safe in ret1 and ret2
    if masked_indices and len(masked_indices) > 0:
        results = evaluation_metrics.get_ranking(filtered_log_probs_list[0], masked_indices, model.vocab,
                                             index_list=index_list)

    results1 = []
    results2 = []
    for result in results[0]['topk']:
        results1.append(result['token_word_form'])
    for result in results[1]['topk']:
        results2.append(result['token_word_form'])
    #compute the overlap with correct labels
    s_labels = set()
    o_labels = set()
    for (s,o) in entityPairs:
        s_labels.update(entityLabels[s])
        o_labels.update(entityLabels[o])

    overlap_s = len(s_labels.intersection(results1))
    overlap_o = len(o_labels.intersection(results2))
    return (overlap_s+overlap_o)

if __name__ == '__main__':
    models = {}
    lm = "bert"
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as config_dictionary_file:
            models[lm] = dill.load(config_dictionary_file)
            #args = []
            #models[lm] = build_model_by_name(lm, args)


    for model_name, model in models.items():
        entities, entityLabels = get_entities("http://www.wikidata.org/prop/direct/P102")
        print('Found {} entity pairs for the relation.'.format(len(entities)))
        index = index_sentences("/home/kalo/TREx", entities, "http://www.wikidata.org/prop/direct/P102", entityLabels)
        results = {}
        for sentence in index:
            value = rank_sentences_2(model, sentence, entities, entityLabels)
            results[sentence['sentence']] = value
    print(results)
    #rank_sentences_2()

