import json
import sys
sys.path.insert(0, "/opt/KnowlyBERT/LAMA/lama")
import pyodbc

import options as options
import evaluation_metrics as evaluation_metrics
import multi_token
import os
import dill
import random
from itertools import islice
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
        relation = ent['uri'].replace("http://www.wikidata.org/prop/direct/","")
        output_set.add(relation)

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


def index_sentences(input_path, entityPairDict, props, entityLabels):

    maxLength = 50
    index = {}
    number_of_files = len(os.listdir(input_path))
    current_file_no = 0
    for file in os.listdir(input_path):
        current_file_no += 1
        print("Reading file number {} of {} files".format(current_file_no, number_of_files))
        with open(os.path.join(input_path,file), "r") as f:
            jsonf = json.load(f)

        # go through every abstract associated to an entity
        for abstract in jsonf:

            # get sentences from "sentences_boundaries"
            for sent_b in abstract["sentences_boundaries"]:
                sent = abstract["text"][sent_b[0]:sent_b[1]]
                if len(sent.split()) <= maxLength:
                    # get entities in this boundary
                    sent_rels = get_rels_in_sent(sent_b, abstract["entities"])
                    #if relation in set(sent_rels):
                    sent_ents = get_ents_in_sent(sent_b, abstract["entities"])

                    # index sentences containing entity pairs (e1,e2) from input relation r
                    if len(sent_ents) >= 2:
                        for e1 in sent_ents:
                            for e2 in sent_ents:
                                if e1 != e2:
                                    try:
                                        e1['uri'] = e1['uri'].replace("http://www.wikidata.org/entity/", "")
                                        e2['uri'] = e2['uri'].replace("http://www.wikidata.org/entity/", "")
                                        #check for sentence whether it belongs to one of the input relations in props
                                        for prop in props:
                                            entityPairs = entityPairDict[prop]
                                            if (e1['uri'],e2['uri']) in entityPairs:
                                                e1_too_short_surfaceform = False

                                                if e1['boundaries'][1] - e1['boundaries'][0] != len(entityLabels[e1['uri']][0]):
                                                    e1_label_token = entityLabels[e1['uri']][0].split(" ")
                                                    for token in e1_label_token:
                                                        if token in e1["surfaceform"].split(" "):
                                                            e1_too_short_surfaceform = True
                                                            #print("too short surfaceform")
                                                            #print("label:{}, surfaceform:{}\n".format(entityLabels[e1['uri']], e1["surfaceform"]))
                                                            break
                                                e2_too_short_surfaceform = False
                                                if e2['boundaries'][1] - e2['boundaries'][0] != len(entityLabels[e2['uri']][0]):
                                                    e2_label_token = entityLabels[e2['uri']][0].split(" ")
                                                    for token in e2_label_token:
                                                        if token in e2["surfaceform"].split(" "):
                                                            e2_too_short_surfaceform = True
                                                            #print("too short surfaceform")
                                                            #print("label:{}, surfaceform:{}\n".format(entityLabels[e2['uri']], e2["surfaceform"]))
                                                            break

                                                if e1_too_short_surfaceform == False and e2_too_short_surfaceform == False:
                                                    entry = {}
                                                    #check wheather label has maximum length of 3, because multi_token.py handles maximum 3 [MASK]
                                                    if len(entityLabels[e1['uri']][0].split(" ")) <= 3 and len(entityLabels[e2['uri']][0].split(" ")) <= 3:
                                                        #replace the current surfaceform with the label of wikidata, which are used
                                                        if e1['boundaries'][0] < e2['boundaries'][0]:
                                                            sentence = sent[:e1['boundaries'][0]] + entityLabels[e1['uri']][0] + sent[e1['boundaries'][1]:e2['boundaries'][0]] + entityLabels[e2['uri']][0] + sent[e2['boundaries'][1]:]
                                                        elif e1['boundaries'][0] > e2['boundaries'][0]:
                                                            sentence = sent[:e2['boundaries'][0]] + entityLabels[e2['uri']][0] + sent[e2['boundaries'][1]:e1['boundaries'][0]] + entityLabels[e1['uri']][0] + sent[e1['boundaries'][1]:]
                                                        else:
                                                            sentence = -1
                                                            print("subject==object --> sentence: {}, surfaceform: {}".format(sent ,e1["surfaceform"]))

                                                        if sentence != -1:
                                                            entry['sentence'] = sentence
                                                            entry['entities'] = (e1['uri'],e2['uri'])

                                                            #adjust boundaries
                                                            if e1['boundaries'][0] < e2['boundaries'][0]:
                                                                e1_boundary_diff = len(entityLabels[e1['uri']][0]) - (e1['boundaries'][1] - e1['boundaries'][0])
                                                                entry['e1'] = e1['boundaries'][:]
                                                                entry['e1'][1] = entry['e1'][0] + len(entityLabels[e1['uri']][0])
                                                                entry['e2'] = e2['boundaries']
                                                                entry['e2'][0] = entry['e2'][0] + e1_boundary_diff
                                                                entry['e2'][1] = entry['e2'][0] + len(entityLabels[e2['uri']][0])
                                                            elif e1['boundaries'][0] > e2['boundaries'][0]:
                                                                e2_boundary_diff = len(entityLabels[e2['uri']][0]) - (e2['boundaries'][1] - e2['boundaries'][0])
                                                                entry['e2'] = e2['boundaries'][:]
                                                                entry['e2'][1] = entry['e2'][0] + len(entityLabels[e2['uri']][0])
                                                                entry['e1'] = e1['boundaries']
                                                                entry['e1'][0] = entry['e1'][0] + e2_boundary_diff
                                                                entry['e1'][1] = entry['e1'][0] + len(entityLabels[e1['uri']][0])

                                                            if prop in index:
                                                                index[prop].append(entry)
                                                            else:
                                                                index[prop] = [entry]

                                    except KeyError:
                                        print("WARNING: KeyError")
                                        continue
                # done for file fn
    return index

def get_entitis_file(input_path):
    relation_dict = {}
    triple_file = open(input_path, 'r')
    for line in triple_file:
        try:
            s,p,o = line.split("> <")
            s = s.replace("<", "")
            o = o.replace("> .\n","")
            s = s.replace("http://www.wikidata.org/entity/", "")
            o = o.replace("http://www.wikidata.org/entity/", "")
            p = p.replace("http://www.wikidata.org/prop/direct/","")
            if p in relation_dict:
                relation_dict[p].add((s,o))
            else:
                pairs = set()
                pairs.add((s,o))
                relation_dict[p] = pairs
        except ValueError:
            continue
    return relation_dict


def get_entity_labels_files(label2entity_path, entity2label_path):
    label2entity_file = open(label2entity_path, 'r')
    entity2label_file = open(entity2label_path, 'r')
    label2entity_dict = json.load(label2entity_file)
    entity2label_dict = json.load(entity2label_file)
    return label2entity_dict, entity2label_dict


def get_entities_db(relation):
    entityPairs = set()
    entity2Labels = {}
    label2Entities = {}
    #write query to virtuoso to get entity pairs

    datavirtuoso = ""
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

import random
# Implementation of rank1 method from Bouroui et al.
def rank_sentences_1(model, index_entry, paragraphDict, entityPairs, entityLabels, labelTrie, randomEntities):
    output_rank = 0
    orig_sentence = index_entry['sentence']
    print(orig_sentence)
    for idx, (e1,e2) in enumerate(randomEntities):
        e1_label = entityLabels[e1][0]
        e2_label = entityLabels[e2][0]
        e1_paragraph = paragraphDict["http://www.wikidata.org/entity/" + e1]
        e2_paragraph = paragraphDict["http://www.wikidata.org/entity/" + e2]
        correct_e1_labels = set(entityLabels[e1])
        correct_e2_labels = set(entityLabels[e2])
        #insert mask tokens

        #TODO: IST HIER WAS FALSCH?!
        e1 = orig_sentence[index_entry['e1'][0]:index_entry['e1'][1]]
        e2 = orig_sentence[index_entry['e2'][0]:index_entry['e2'][1]]
        sentence_1 = orig_sentence[:index_entry['e1'][0]] + "[MASK]" + orig_sentence[index_entry['e1'][1]:]
        sentence_2 = orig_sentence[:index_entry['e2'][0]] + "[MASK]" + orig_sentence[index_entry['e2'][1]:]
        #insert entities from pair
        sentence_1 = sentence_1.replace(e2,e2_label)
        sentence_2 = sentence_2.replace(e1,e1_label)
        sentences = []
        sentences.append(sentence_1)
        sentences.append(sentence_2)

        for result, value in multi_token.get_multi_token_results(sentence_1, e1_paragraph, model, labelTrie):
            if result in correct_e1_labels:
                output_rank += 1
        for result, value in multi_token.get_multi_token_results(sentence_2, e2_paragraph, model, labelTrie):
            if result in correct_e2_labels:
                output_rank += 1
    print(output_rank)
    return output_rank


import multi_token as mt

#Rank entities with regard to second metric of paper by
def rank_sentences_2(model, index_entry, paragraphDict, entityPairs, entity2Labels, label2Entities, subjectLabels, objectLabels):

    orig_sentence = index_entry['sentence']
    print(orig_sentence)
    
    sentence_1 = orig_sentence[:index_entry['e1'][0]] + "[MASK]" + orig_sentence[index_entry['e1'][1]:]
    sentence_2 = orig_sentence[:index_entry['e2'][0]] + "[MASK]" + orig_sentence[index_entry['e2'][1]:]
    e1_paragraph = paragraphDict[index_entry['entities'][0]]
    e2_paragraph = paragraphDict[index_entry['entities'][1]]
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
    for result, value in multi_token.get_multi_token_results(sentence_1, e1_paragraph, model, label2Entities):
        results1.append(result)
    for result, value in multi_token.get_multi_token_results(sentence_2, e2_paragraph, model, label2Entities):
        results2.append(result)

    print("results 1 has length {}".format(len(results1)))
    print("results 2 has length {}".format(len(results2)))
    overlap_s = len(s_labels.intersection(results1))
    overlap_o = len(o_labels.intersection(results2))
    print(overlap_s+overlap_o)
    return (overlap_s+overlap_o)

from difflib import SequenceMatcher
def similar_string(a, b):
    return SequenceMatcher(None, a, b).ratio()

from SetSimilaritySearch import all_pairs
import networkx as nx

def find_similar_sentences(index, entity2Labels):
    sentence_list = []


    for index_entry in index:
        orig_sentence = index_entry["sentence"]

        if index_entry['e1'][0] < index_entry['e2'][0]:
            subject_object_template = orig_sentence[:index_entry['e1'][0]] + "[S]" + orig_sentence[
                                                                                  index_entry['e1'][1]:index_entry['e2'][
                                                                                      0]] + "[O]" + orig_sentence[
                                                                                                    index_entry['e2'][1]:]
        else:
            subject_object_template = orig_sentence[:index_entry['e2'][0]] + "[O]" + orig_sentence[
                                                                                  index_entry['e2'][1]:index_entry['e1'][
                                                                                      0]] + "[S]" + orig_sentence[
                                                                                     index_entry['e1'][1]:]
        sentence_list.append(subject_object_template.split())
    print(sentence_list)
    # all_pairs returns an iterable of tuples.
    pairs = all_pairs(sentence_list, similarity_func_name="jaccard",
                      similarity_threshold=0.7)

    G = nx.Graph()
    duplicate_sentences = set()
    non_duplicate_sentence_list = set()

    for p in pairs:
        G.add_edge(p[0], p[1], weight=p[2])
        duplicate_sentences.add(p[0])
        duplicate_sentences.add(p[1])
    for id, sentence in enumerate(sentence_list):
        if id not in duplicate_sentences:
            non_duplicate_sentence_list.add(id)
    components = nx.community.greedy_modularity_communities(G)
    good_sentences = set()
    for c in components:
        good_sentences.add(sorted(c)[0])

    output_index = []
    i = 0
    for index_entry in index:
        if i in good_sentences or i in non_duplicate_sentence_list:
            output_index.append(index_entry)
        i += 1
    # similar_templates = {}
    # unique_templates = {}
    # filtered_index = []
    # for sentence in index:
    #     orig_sentence = sentence["sentence"]
    #     if sentence['e1'][0] < sentence['e2'][0]:
    #         subject_object_template = orig_sentence[:sentence['e1'][0]] + "[S]" + orig_sentence[sentence['e1'][1]:sentence['e2'][0]] + "[O]" + orig_sentence[sentence['e2'][1]:]
    #     else:
    #         subject_object_template = orig_sentence[:sentence['e2'][0]] + "[O]" + orig_sentence[sentence['e2'][1]:sentence['e1'][0]] + "[S]" + orig_sentence[sentence['e1'][1]:]
    #     if subject_object_template not in unique_templates:
    #         #if not re.match(".*[0-9][0-9][0-9][0-9].*", subject_object_template):
    #         unique_templates[subject_object_template] = sentence
    #
    # for template in unique_templates:
    #     find_suitable_key_template = False
    #     for key_template in similar_templates:
    #         if find_suitable_key_template == True:
    #             break
    #         elif similar_string(key_template, template) > 0.8:
    #             find_suitable_key_template = True
    #             similar_templates[key_template].append(template)
    #         else:
    #             for similar_template in similar_templates[key_template]:
    #                 if similar_string(similar_template, template) > 0.8:
    #                     find_suitable_key_template = True
    #                     similar_templates[key_template].append(template)
    #                     break
    #     if find_suitable_key_template == False:
    #         similar_templates[template] = []
    #
    # #for sent in similar_templates:
    # #    print("{} --> {}\n".format(sent, similar_templates[sent]))
    # #print(len(index))
    # #print(len(similar_templates))
    # for key_template in similar_templates:
    #     shortest_template = key_template
    #     for similar in similar_templates[key_template]:
    #         if len(similar) < len(shortest_template):
    #             shortest_template = similar
    #     filtered_index.append(unique_templates[shortest_template])
    # #print(filtered_index)
    #return filtered_index
    return output_index

_end = '_end_'
def make_trie(words):
    root = dict()
    for word in words:
        current_dict = root
        for token in word.split():
            current_dict = current_dict.setdefault(token, {})
        current_dict[_end] = _end
    return root


if __name__ == '__main__':
    lm = "bert"
    models = {}
    if os.path.exists("/data/fichtel/lm_builds/model_{}".format(lm)):
        with open("/data/fichtel/lm_builds/model_{}".format(lm), 'rb') as lm_build_file:
            models[lm] = dill.load(lm_build_file)
    label2Entities, entity2Labels = get_entity_labels_files('/home/kalo/conferences/iswc2020/data/label2entity.json','/home/kalo/conferences/iswc2020/data/entity2label.json')
    entity_trie = make_trie(label2Entities.keys())
    entities = get_entitis_file('/home/kalo/conferences/iswc2020/data/missing_data.new.nt')
    paragraph_file = open("/home/kalo/conferences/iswc2020/data/paragraph_dict.json")
    paragraphDict = json.load(paragraph_file)

    print("read entity dictionaries and built trie")
    props = ['P39', 'P264', 'P276', 'P937', 'P140', 'P1303', 'P127', 'P103', 'P190', 'P1001', 'P31', 'P495', 'P159', 'P740', 'P361']
   # props = ['P413', 'P166', 'P449', 'P69', 'P47', 'P138', 'P364', 'P54', 'P463', 'P101',
            # 'P1923', 'P106', 'P527', 'P102', 'P530', 'P176', 'P27', 'P407', 'P30', 'P178', 'P1376', 'P131', 'P1412',
            # 'P108', 'P136', 'P17', 'P39', 'P264', 'P276', 'P937', 'P140', 'P1303', 'P127', 'P103', 'P190', 'P1001',
            # 'P31', 'P495', 'P159', 'P740', 'P361']
    #props = [ 'P102', 'P530', 'P176', 'P27', 'P407', 'P30', 'P178', 'P1376', 'P131', 'P1412',
            # 'P108', 'P136', 'P17', 'P39', 'P264', 'P276', 'P937', 'P140', 'P1303', 'P127', 'P103', 'P190', 'P1001',
            # 'P31', 'P495', 'P159', 'P36', 'P740', 'P361']
    #props = ['P36']

    index = index_sentences("/home/kalo/TREx", entities, props,
                            entity2Labels)
    print("found template sentences")

    for prop in props:
        if prop not in index:
            continue
        for model_name, model in models.items():
            if os.path.exists("data/{}_data".format(prop)):
                with open("data/{}_data".format(prop), 'rb') as prop_data_file:
                    prop_data = dill.load(prop_data_file)
                    print("read prop data file")
                    print('Found {} entity pairs for the relation.'.format(len(prop_data["ent"])))
            else:

                # with open("data/{}_data".format(prop), 'wb') as prop_data_file:
                prop_data = {}
                prop_data["ent"] = entities[prop]
                prop_data["ent2Label"] = entity2Labels
                prop_data["label2ent"] = label2Entities
                prop_data["index"] = index[prop]
                prop_data['trie'] = entity_trie
                #     dill.dump(prop_data, prop_data_file)


            filtered_index = find_similar_sentences(prop_data["index"], prop_data["ent2Label"])
            # compute the overlap with correct labels
            s_labels = set()
            o_labels = set()

            for (s, o) in prop_data["ent"]:
                s_labels.add(entity2Labels[s][0])
                o_labels.add(entity2Labels[o][0])

            intermediate_results = {}
            print("starting to rank sentences for property {}".format(prop))
            #first filter by ranking method2
            for sentence in filtered_index:
                score = rank_sentences_2(model, sentence, paragraphDict ,prop_data["ent"] , prop_data["ent2Label"], prop_data["trie"], s_labels, o_labels)
                #score = rank_sentences_1(model, sentence, prop_data["ent"], prop_data["ent2Label"], prop_data["trie"])
                orig_sentence = sentence["sentence"]
                intermediate_results[orig_sentence] = score
            sorted_results = {k: v for k, v in sorted(intermediate_results.items(), reverse=True, key=lambda item: item[1])}

            #rank topk by ranking method 1
            results = {}
            top_k = 100
            top_templates = dict(islice(sorted_results.items(), top_k))
            randomEntities = random.sample(prop_data["ent"], 200)
            for sentence in filtered_index:
                if sentence['sentence'] in top_templates:
                    score = rank_sentences_1(model, sentence, paragraphDict, prop_data["ent"], prop_data["ent2Label"], prop_data["trie"],randomEntities)
                    orig_sentence = sentence["sentence"]

                    if sentence['e1'][0] < sentence['e2'][0]:
                        subject_object_template = orig_sentence[:sentence['e1'][0]] + "[S]" + orig_sentence[sentence['e1'][1]:sentence['e2'][0]] + "[O]" + orig_sentence[sentence['e2'][1]:]
                    else:
                        subject_object_template = orig_sentence[:sentence['e2'][0]] + "[O]" + orig_sentence[sentence['e2'][1]:sentence['e1'][0]] + "[S]" + orig_sentence[sentence['e1'][1]:]
                    results[subject_object_template] = score
            sorted_results = {k: v for k, v in sorted(results.items(), reverse=True, key=lambda item: item[1])}


        #TODO: check templates.json before the template mining process
            if os.path.exists("templates.json"):
                with open("templates.json", "r", encoding="utf8") as prop_templates_file:
                    prop_templates = json.load(prop_templates_file)
                    prop_templates_file.close()
                    os.remove("templates.json")
            else:
                prop_templates = {}

            with open("templates.json", "w") as prop_templates_file:
                prop_templates[prop] = sorted_results
                json.dump(prop_templates, prop_templates_file)
