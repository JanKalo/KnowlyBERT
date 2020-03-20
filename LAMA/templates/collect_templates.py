import json
import sys
sys.path.append("/home/kalo/conferences/iswc2020/LAMA/lama")
import pyodbc

import options as options
import evaluation_metrics as evaluation_metrics
import multi_token
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

                                    sent = sent[:e1['boundaries'][0]] + entityLabels[e1['uri']] + sent[e1['boundaries'][1]:]
                                    sent = sent[:e2['boundaries'][0]] + entityLabels[e2['uri']] + sent[e2['boundaries'][1]:]

                                    if e1['boundaries'][0] < e1['boundaries'][0]:
                                        e1_boundary_diff = len(entityLabels[e1['uri']]) - (e1['boundaries'][1] - e1['boundaries'][0])

                                        entry['e1'] = e1['boundaries']
                                        entry['e1'][1] = entry['e1'][0] + len(entityLabels[e1['uri']])
                                        entry['e2'] = e2['boundaries']
                                        entry['e2'][0] = entry['e2'][0] + e1_boundary_diff
                                        entry['e2'][1] = entry['e2'][0] + len(entityLabels[e2['uri']])

                                    else:
                                        e2_boundary_diff = len(entityLabels[e2['uri']]) - (
                                                    e2['boundaries'][1] - e2['boundaries'][0])

                                        entry['e2'] = e2['boundaries']
                                        entry['e2'][1] = entry['e2'][0] + len(entityLabels[e2['uri']])
                                        entry['e1'] = e1['boundaries']
                                        entry['e1'][0] = (entry['e1'][0] + e2_boundary_diff)
                                        entry['e1'][1] = (entry['e1'][0] + len(entityLabels[e1['uri']]))

                                    entry['sentence'] = sent
                                    index.append(entry)

                # done for file fn
    return index

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
            if results[0]['topk'][i]['token_word_form'] in correct_e1_labels:
                output_rank += 1
            if results[1]['topk'][i]['token_word_form'] in correct_e2_labels:
                output_rank += 1

    return output_rank


import multi_token as mt

#Rank entities with regard to second metric of paper by
def rank_sentences_2(model, index_entry, entityPairs, entity2Labels, label2Entities):

    orig_sentence = index_entry['sentence']

    #sentence_1 = orig_sentence.replace(entity2Labels[index_entry['e1'][0]], '[MASK]')
    #sentence_2 = orig_sentence.replace(entity2Labels[index_entry["entities"][1]], '[MASK]')

    sentence_1 = orig_sentence[:index_entry['e1'][0]] + "[MASK]" + orig_sentence[index_entry['e1'][1]:]
    sentence_2 = orig_sentence[:index_entry['e2'][0]] + "[MASK]" + orig_sentence[index_entry['e2'][1]:]
    sentences = []
    sentences.append(sentence_1)
    sentences.append(sentence_2)
    #new multi token function

    # print("\n{}:".format(model_name))
    # original_log_probs_list, [token_ids], [masked_indices] = model.get_batch_generation([sentences], try_cuda=True)
    # index_list = None
    # filtered_log_probs_list = original_log_probs_list
    # ret = {}
    # if masked_indices and len(masked_indices) > 0:
    #     results = evaluation_metrics.get_ranking(filtered_log_probs_list[0], masked_indices, model.vocab,
    #                                          index_list=index_list)

    results1 = []
    results2 = []
    for result, value in multi_token.get_multi_token_results(sentence_1, model, label2Entities):
        results1.append(result)
    for result, value in multi_token.get_multi_token_results(sentence_2, model, label2Entities):
        results2.append(result)
    #compute the overlap with correct labels
    s_labels = set()
    o_labels = set()
    for (s,o) in entityPairs:
        s_labels.add(entity2Labels[s])
        o_labels.add(entity2Labels[o])

    overlap_s = len(s_labels.intersection(results1))
    overlap_o = len(o_labels.intersection(results2))
    print(overlap_s+overlap_o)
    return (overlap_s+overlap_o)

from difflib import SequenceMatcher
def similar_string(a, b):
    return SequenceMatcher(None, a, b).ratio()

import re
def find_similar_sentences(index, entity2Labels):
    similar_templates = {}
    unique_templates = {}
    filtered_index = []
    for sentence in index:
        orig_sentence = sentence["sentence"]
        subject_object_template = orig_sentence[:sentence['e1'][0]] + "[S]" + orig_sentence[sentence['e1'][1]:]
        subject_object_template = subject_object_template[:sentence['e2'][0]] + "[O]" + subject_object_template[sentence['e2'][1]:]

        if subject_object_template not in unique_templates:
            if not re.match(".*[0-9][0-9][0-9][0-9].*", subject_object_template):
                unique_templates[subject_object_template] = sentence

    for template in unique_templates:
        find_suitable_key_template = False
        for key_template in similar_templates:
            if find_suitable_key_template == True:
                break
            elif similar_string(key_template, template) > 0.8:
                find_suitable_key_template = True
                similar_templates[key_template].append(template)
            else:
                for similar_template in similar_templates[key_template]:
                    if similar_string(similar_template, template) > 0.8:
                        find_suitable_key_template = True
                        similar_templates[key_template].append(template)
                        break
        if find_suitable_key_template == False:
            similar_templates[template] = []

    #for sent in similar_templates:
    #    print("{} --> {}\n".format(sent, similar_templates[sent]))
    #print(len(index))
    #print(len(similar_templates))
    for key_template in similar_templates:
        shortest_template = key_template
        for similar in similar_templates[key_template]:
            if len(similar) < len(shortest_template):
                shortest_template = similar
        filtered_index.append(unique_templates[shortest_template])
    #print(filtered_index)
    return filtered_index

if __name__ == '__main__':
    lm = "bert"
    models = {}
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as lm_build_file:
            models[lm] = dill.load(lm_build_file)

    prop = "P36"
    for model_name, model in models.items():
        if os.path.exists("{}_data".format(prop)):
            with open("{}_data".format(prop), 'rb') as prop_data_file:
                prop_data = dill.load(prop_data_file)
                print("read prop data file")
                print('Found {} entity pairs for the relation.'.format(len(prop_data["ent"])))
        else:
            entities, entity2Labels, label2Entities = get_entities("http://www.wikidata.org/prop/direct/{}".format(prop))
            print('Found {} entity pairs for the relation.'.format(len(entities)))
            index = index_sentences("/home/kalo/TREx", entities, "http://www.wikidata.org/prop/direct/{}".format(prop), entity2Labels)

            with open("{}_data".format(prop), 'wb') as prop_data_file:
                prop_data = {}
                prop_data["ent"] = entities
                prop_data["ent2Label"] = entity2Labels
                prop_data["label2ent"] = label2Entities
                prop_data["index"] = index
                dill.dump(prop_data, prop_data_file)

        results = {}

        filtered_index = find_similar_sentences(prop_data["index"], prop_data["ent2Label"])
        #filtered_index = prop_data["index"]

        for sentence in filtered_index:
            score = rank_sentences_2(model, sentence, prop_data["ent"] , prop_data["ent2Label"], prop_data["label2ent"])
            subject_object_template = (sentence["sentence"].replace(prop_data["ent2Label"][sentence["entities"][0]], '[S]')).replace(prop_data["ent2Label"][sentence["entities"][1]], '[O]')
            results[subject_object_template] = score
        sorted_results = {k: v for k, v in sorted(results.items(), reverse=True, key=lambda item: item[1])}

        if os.path.exists("templates.json"):
            with open("templates.json", "r") as prop_templates_file:
                prop_templates = json.load(prop_templates_file)
                prop_templates_file.close()
                os.remove("templates.json")
        else:
            prop_templates = {}

        with open("templates.json", "w") as prop_templates_file:
            prop_templates[prop] = sorted_results
            json.dump(prop_templates, prop_templates_file)
