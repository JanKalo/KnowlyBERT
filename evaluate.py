import hybrid_system
import sys
from random import randint
import time
import os
import timeit
import simplejson as json
import pickle

dictio_props = None

def evaluate(data_dictio, output_hybrid, i):
    global dictio_props
    dictio_props = {}
    string_eval = ""
    string_eval_props = ""
    list_query_assign = []
    perfect_queries = {}
    bad_queries = {}
    popularity_scores = {}
    dictio_querynr_lm_result = {}
    if len(output_hybrid) > 0:
        data_output_hybrid = []
        for d in output_hybrid:
            data_output_hybrid.append(d[i])
        data_amount = len(data_output_hybrid)
        no_results = 0
        incorrect = 0
        begin_incorrect = 0
        begin_correct_mixed = 0
        correct_already_existing_incorrect = 0
        correct_already_existing = 0
        completely_correct_incorrect = 0
        at_least_one_correct_incorrect = 0
        completely_correct = 0
        at_least_one_correct = 0
        missing = {}
        props_no_result = {}
        props_only_incorrect_result = {}
        props_begin_incorrect = {}
        props_begin_correct_mixed = {}
        props_completely_correct_incorrect = {}
        props_correct_already_existing_incorrect = {}
        props_correct_already_existing = {}
        props_at_least_one_correct_incorrect = {}
        props_completely_correct = {}
        count_already_existing = 0
        dictio_prop_label_possible_entities = {}
        count_no_entry_o_r = 0
        count_possible_result_LM_non_label = 0
        count_possible_result_LM_correct_label = 0
        count_possible_result_LM_incorrect_label = 0
        count_possible_result_LM_non_ID = 0
        count_possible_result_LM_correct_ID = 0
        count_possible_result_LM_incorrect_ID = 0
        for data in data_output_hybrid:
            props_at_least_one_correct = {}
            prop = data["prop"]
            if prop in dictio_props:
                count = dictio_props[prop]
                dictio_props[prop] = count + 1
            else:
                dictio_props[prop] = 1
        for nr, data in enumerate(data_output_hybrid):
            prop = data["prop"]
            dictio_label_possible_entities = data["label_possible_entities"]
            if dictio_label_possible_entities != {}:
                if prop in dictio_prop_label_possible_entities:
                    actu_list = dictio_prop_label_possible_entities[prop]
                    actu_list.append(dictio_label_possible_entities)
                    dictio_prop_label_possible_entities[prop] = actu_list
                else:
                    dictio_prop_label_possible_entities[prop] = [dictio_label_possible_entities]
            results_KG_current = data["KG"][0]
            keys_results_KG_current = []
            for k in results_KG_current.keys():
                keys_results_KG_current.append(k)

            results_KG_o_r = data["KG"][1]
            keys_results_KG_o_r = []
            for k in results_KG_o_r.keys():
                keys_results_KG_o_r.append(k)
                if k in data_dictio["entity_popularity"]:
                    popularity = data_dictio["entity_popularity"][k]
                else:
                    popularity = 0
                if popularity not in popularity_scores:
                    popularity_scores[popularity] = 1
                else:
                    popularity_scores[popularity] = popularity_scores[popularity] +1

            num_results_KG_current = len(results_KG_current)
            num_results_KG_o_r = len(results_KG_o_r)

            if num_results_KG_o_r == 0:
                count_no_entry_o_r = count_no_entry_o_r +1

            results_LM = data["LM"]
            dictio_querynr_lm_result[nr] = list(results_LM.keys())
            already_existing = data["already_existing"]
            if already_existing:
                count_already_existing = count_already_existing +1

            actu_status_label = data["status_possible_result_LM_label"]
            if actu_status_label == "non":
                count_possible_result_LM_non_label = count_possible_result_LM_non_label +1
            elif actu_status_label == "correct_label":
                count_possible_result_LM_correct_label = count_possible_result_LM_correct_label +1
            else:
                count_possible_result_LM_incorrect_label = count_possible_result_LM_incorrect_label +1

            actu_status_ID = data["status_possible_result_LM_ID"]
            if actu_status_ID == "non":
                count_possible_result_LM_non_ID = count_possible_result_LM_non_ID +1
            elif actu_status_ID == "correct_ID":
                count_possible_result_LM_correct_ID = count_possible_result_LM_correct_ID +1
            else:
                count_possible_result_LM_incorrect_ID = count_possible_result_LM_incorrect_ID +1

            not_in_dictionary = data["missing"]

            num_results_LM = len(results_LM)
            num_correct_results_LM = 0
            num_correct_results_LM_new = 0
            num_correct_results_LM_already_existing = 0
            bool_begin_incorrect = False
            bool_begin_correct_only_wrong_following = False
            bool_begin_correct_following = False
            #append to missing dictio
            for nid in not_in_dictionary:
                if nid in missing:
                    list_values = missing[nid]
                    if not_in_dictionary[nid] not in list_values:
                        list_values.append(not_in_dictionary[nid])
                else:
                    missing[nid] = [not_in_dictionary[nid]]
                    
            #find matching LM results and KG results
            for entity_id_url in results_LM:
                if entity_id_url in keys_results_KG_current:
                    bool_begin_correct_only_wrong_following = False
                    if entity_id_url not in keys_results_KG_o_r:
                        #find one cor+rect AND new result of LM
                        num_correct_results_LM_new = num_correct_results_LM_new + 1
                    else:
                        #find one correct result of LM, but it was already in KG
                        num_correct_results_LM_already_existing = num_correct_results_LM_already_existing + 1
                    num_correct_results_LM = num_correct_results_LM_new + num_correct_results_LM_already_existing
                elif num_correct_results_LM == 0:
                    bool_begin_incorrect = True
                elif num_correct_results_LM > 0 and not bool_begin_incorrect and not bool_begin_correct_following:
                    bool_begin_correct_following = True
                    bool_begin_correct_only_wrong_following = True

            #queries with no results
            if num_results_LM == 0:
                list_query_assign.append("no_results")
                no_results = no_results + 1
                #properties of queries with no results
                if prop in props_no_result:
                    count = props_no_result[prop][0]
                    props_no_result[prop][0] = count + 1
                else:
                    props_no_result[prop] = [1, dictio_props[prop]]
            #queries with only incorrect results
            elif num_correct_results_LM == 0 and bool_begin_incorrect:
                list_query_assign.append("incorrect")
                incorrect = incorrect  + 1
                #properties of queries with only incorrect results
                if prop in props_only_incorrect_result:
                    count = props_only_incorrect_result[prop][0]
                    props_only_incorrect_result[prop][0] = count + 1
                else:
                    props_only_incorrect_result[prop] = [1, dictio_props[prop]]
            #quries with a wrong result at the beginning
            elif num_correct_results_LM > 0 and bool_begin_incorrect:
                list_query_assign.append("begin_incorrect")
                begin_incorrect = begin_incorrect + 1
                if prop in props_begin_incorrect:
                    count = props_begin_incorrect[prop][0]
                    props_begin_incorrect[prop][0] = count + 1
                else:
                    props_begin_incorrect[prop] = [1, dictio_props[prop]]
            #queries with  mixed incorrect and correct results, but a correct result at the beginning
            elif bool_begin_correct_following and not bool_begin_correct_only_wrong_following:
                list_query_assign.append("begin_correct_mixed")
                begin_correct_mixed = begin_correct_mixed + 1
                if prop in props_begin_correct_mixed:
                    count = props_begin_correct_mixed[prop][0]
                    props_begin_correct_mixed[prop][0] = count + 1
                else:
                    props_begin_correct_mixed[prop] = [1, dictio_props[prop]]
            #queries with only aready existing results but wrong results following
            elif num_results_LM == num_correct_results_LM_already_existing and bool_begin_correct_only_wrong_following:
                list_query_assign.append("correct_already_existing_incorrect")
                correct_already_existing_incorrect = correct_already_existing_incorrect + 1
                if prop in props_correct_already_existing_incorrect:
                    count = props_correct_already_existing_incorrect[prop][0]
                    props_correct_already_existing_incorrect[prop][0] = count + 1
                else:
                    props_correct_already_existing_incorrect[prop] = [1, dictio_props[prop]]
            #queries with only aready existing results
            elif num_results_LM == num_correct_results_LM_already_existing:
                list_query_assign.append("correct_already_existing")
                correct_already_existing = correct_already_existing + 1
                if prop in props_correct_already_existing:
                    count = props_correct_already_existing[prop][0]
                    props_correct_already_existing[prop][0] = count + 1
                else:
                    props_correct_already_existing[prop] = [1, dictio_props[prop]]
            #queries with completely correct results but wrong results following
            elif num_correct_results_LM_new == (num_results_KG_current-num_results_KG_o_r) and bool_begin_correct_only_wrong_following:
                list_query_assign.append("completely_correct_incorrect")
                completely_correct_incorrect = completely_correct_incorrect + 1
                if prop in props_completely_correct_incorrect:
                    count = props_completely_correct_incorrect[prop][0]
                    props_completely_correct_incorrect[prop][0] = count + 1
                else:
                    props_completely_correct_incorrect[prop] = [1, dictio_props[prop]]
            #queries with at least one correct results but wrong results following
            elif num_correct_results_LM < num_results_KG_current and bool_begin_correct_only_wrong_following:
                list_query_assign.append("at_least_one_correct_incorrect")
                at_least_one_correct_incorrect = at_least_one_correct_incorrect + 1
                if prop in props_at_least_one_correct_incorrect:
                    count = props_at_least_one_correct_incorrect[prop][0]
                    props_at_least_one_correct_incorrect[prop][0] = count + 1
                else:
                    props_at_least_one_correct_incorrect[prop] = [1, dictio_props[prop]]
            #queries with completely correct results
            elif num_correct_results_LM_new == (num_results_KG_current-num_results_KG_o_r):
                list_query_assign.append("completely_correct")
                completely_correct = completely_correct + 1
                if prop in props_completely_correct:
                    count = props_completely_correct[prop][0]
                    props_completely_correct[prop][0] = count + 1
                else:
                    props_completely_correct[prop] = [1, dictio_props[prop]]
            #queries with at least on correct results
            elif num_correct_results_LM < num_results_KG_current:
                list_query_assign.append("at_least_one_correct")
                at_least_one_correct = at_least_one_correct + 1
                if prop in props_at_least_one_correct:
                    count = props_at_least_one_correct[prop][0]
                    props_at_least_one_correct[prop][0] = count + 1
                else:
                    props_at_least_one_correct[prop] = [1, dictio_props[prop]]
            else:
                list_query_assign.append("Da habe ich wohl was vergessen :(")
                
        if(data_amount != 0):

            string_eval = string_eval + "\nEvaluation: Results of Language Model\n\n"

            string_eval = string_eval + "Possible results of Language Model\n"
            string_eval = string_eval + "{}/{} queries with correct possible label at first position --> {}%\n".format(count_possible_result_LM_correct_label, data_amount, round(count_possible_result_LM_correct_label/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with incorrect possible label at first position --> {}%\n".format(count_possible_result_LM_incorrect_label, data_amount, round(count_possible_result_LM_incorrect_label/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with no results --> {}%\n\n".format(count_possible_result_LM_non_label, data_amount, round(count_possible_result_LM_non_label/data_amount*100, 2))

            string_eval = string_eval + "{}/{} queries with correct possible ID at first position after classifying --> {}%\n".format(count_possible_result_LM_correct_ID, data_amount, round(count_possible_result_LM_correct_ID/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with incorrect possible ID at first position after classifying --> {}%\n".format(count_possible_result_LM_incorrect_ID, data_amount, round(count_possible_result_LM_incorrect_ID/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with no possible result after classifying --> {}%\n\n".format(count_possible_result_LM_non_ID, data_amount, round(count_possible_result_LM_non_ID/data_amount*100, 2))
            
            string_eval = string_eval + "Chosen results of Language Model\n"
            string_eval = string_eval + "{}/{} queries with completely correct results --> {}%\n".format(completely_correct, data_amount, round(completely_correct/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with not completely but at least one correct result --> {}%\n".format(at_least_one_correct, data_amount, round(at_least_one_correct/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with only aready existing correct results --> {}%\n\n".format(correct_already_existing, data_amount, round(correct_already_existing/data_amount*100, 2))
            
            string_eval = string_eval + "{}/{} queries with completely correct results but also with incorrect results following --> {}%\n".format(completely_correct_incorrect, data_amount, round(completely_correct_incorrect/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with only aready existing correct results but also with incorrect following --> {}%\n".format(correct_already_existing_incorrect, data_amount, round(correct_already_existing_incorrect/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with not completely but at least one correct result but also with incorrect results following --> {}%\n".format(at_least_one_correct_incorrect, data_amount, round(at_least_one_correct_incorrect/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with mixed correct and incorrect results but beginning with correct result --> {}%\n".format(begin_correct_mixed, data_amount, round(begin_correct_mixed/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with only incorrect results --> {}%\n".format(incorrect, data_amount, round(incorrect/data_amount*100, 2))
            string_eval = string_eval + "{}/{} queries with a incorrect result at the beginning --> {}%\n\n".format(begin_incorrect, data_amount, round(begin_incorrect/data_amount*100, 2))
            
            string_eval = string_eval + "{}/{} queries with no results --> {}%\n\n".format(no_results, data_amount, round(no_results/data_amount*100, 2))
            
            string_eval = string_eval + "Number of queries which had or still has already existing results: {}\n".format(count_already_existing)
            string_eval = string_eval + "Number of queries where outdated/random KG has no entry: {}".format(count_no_entry_o_r)

            string_eval_props = string_eval_props + "Properties of queries with completely correct results: {}\n".format(props_completely_correct)
            string_eval_props = string_eval_props + "Properties of queries with not completely but at least one correct result: {}\n".format(props_at_least_one_correct)
            string_eval_props = string_eval_props + "Properties of queries with only aready existing correct results: {}\n\n".format(props_correct_already_existing)

            string_eval_props = string_eval_props + "Properties of queries with completely correct results but also with incorrect results following: {}\n".format(props_completely_correct_incorrect)
            string_eval_props = string_eval_props + "Properties of queries with only aready existing correct results but also with incorrect following: {}\n".format(props_correct_already_existing_incorrect)
            string_eval_props = string_eval_props + "Properties of queries with not completely but at least one correct result but also with incorrect results following: {}\n".format(props_at_least_one_correct_incorrect)
            string_eval_props = string_eval_props + "Properties of queries with mixed correct and incorrect results but beginning with correct result: {}\n\n".format(props_begin_correct_mixed)            
            
            string_eval_props = string_eval_props + "Properties of queries with only incorrect results: {}\n".format(props_only_incorrect_result)
            string_eval_props = string_eval_props + "Properties of queries with a incorrect result at the beginning: {}\n".format(props_begin_incorrect)
            string_eval_props = string_eval_props + "Properties of queries with no results: {}".format(props_no_result)

            for prop in props_completely_correct:
                perfect_queries[prop] = props_completely_correct[prop]
            for prop in props_at_least_one_correct:
                if prop in perfect_queries:
                    count = props_at_least_one_correct[prop][0]     
                    perfect_queries[prop][0] = perfect_queries[prop][0] + count
                else:
                    perfect_queries[prop] = props_at_least_one_correct[prop]
            for prop in props_correct_already_existing:
                if prop in perfect_queries:
                    count = props_correct_already_existing[prop][0]     
                    perfect_queries[prop][0] = perfect_queries[prop][0] + count
                else:
                    perfect_queries[prop] = props_correct_already_existing[prop]
            count_perfect_queries = completely_correct+at_least_one_correct+correct_already_existing
            percentage_perfect_queries =  round((completely_correct+at_least_one_correct+correct_already_existing)/data_amount*100, 2)

            for prop in props_completely_correct_incorrect:
                bad_queries[prop] = props_completely_correct_incorrect[prop]
            for prop in props_correct_already_existing_incorrect:
                if prop in bad_queries:
                    count = props_correct_already_existing_incorrect[prop][0]     
                    bad_queries[prop][0] = bad_queries[prop][0] + count
                else:
                    bad_queries[prop] = props_correct_already_existing_incorrect[prop]
            for prop in props_at_least_one_correct_incorrect:
                if prop in bad_queries:
                    count = props_at_least_one_correct_incorrect[prop][0]     
                    bad_queries[prop][0] = bad_queries[prop][0] + count
                else:
                    bad_queries[prop] = props_at_least_one_correct_incorrect[prop]
            for prop in props_begin_correct_mixed:
                if prop in bad_queries:
                    count = props_begin_correct_mixed[prop][0]     
                    bad_queries[prop][0] = bad_queries[prop][0] + count
                else:
                    bad_queries[prop] = props_begin_correct_mixed[prop]
            for prop in props_only_incorrect_result:
                if prop in bad_queries:
                    count = props_only_incorrect_result[prop][0]     
                    bad_queries[prop][0] = bad_queries[prop][0] + count
                else:
                    bad_queries[prop] = props_only_incorrect_result[prop]
            for prop in props_begin_incorrect:
                if prop in bad_queries:
                    count = props_begin_incorrect[prop][0]     
                    bad_queries[prop][0] = bad_queries[prop][0] + count
                else:
                    bad_queries[prop] = props_begin_incorrect[prop]
            count_bad_queries = completely_correct_incorrect+correct_already_existing_incorrect+at_least_one_correct_incorrect+begin_correct_mixed+begin_incorrect+incorrect
            percentage_bad_queries =  round((completely_correct_incorrect+correct_already_existing_incorrect+at_least_one_correct_incorrect+begin_correct_mixed+begin_incorrect+incorrect)/data_amount*100, 2)
            
    return dictio_querynr_lm_result, popularity_scores, string_eval, string_eval_props, list_query_assign, perfect_queries, count_perfect_queries, percentage_perfect_queries, bad_queries, count_bad_queries, percentage_bad_queries, props_no_result, no_results, round(no_results/data_amount*100, 2), data_amount, missing, dictio_prop_label_possible_entities

def correct_parameter(mc, cep, tmc, tmp, ts):
    if ts < 1:
        return False
    if len(mc) == 1 and len(cep) == 1 and len(tmc) == 1 and len(tmp) == 1:
        return True
    elif len(mc) > 1 and len(cep) == 1 and len(tmc) == 1 and len(tmp) == 1:
        if tmc[0] == 0:
            return True
        else:
            return False
    elif len(mc) == 1 and len(cep) > 1 and len(tmc) == 1 and len(tmp) == 1:
        return True
    elif len(mc) == 1 and len(cep) == 1 and len(tmc) > 1 and len(tmp) == 1:
        return True
    elif len(mc) == 1 and len(cep) == 1 and len(tmc) == 1 and len(tmp) > 1:
        if tmc[0] == 0:
            return False
        else:
            return True
        return True
    else:
        return False

def write_into_files(i, folder, mc, cep, tmc, tmp, file_evaluation, hybrid_output, list_hybrid_log, list_errors, data, parameter):
    actu_list_hybrid_log = []
    for log in list_hybrid_log:
        actu_list_hybrid_log.append(log[i])
    dictio_querynr_lm_result, popularity_scores, string_evaluation, string_eval_props, list_query_assign, perfect_queries, count_perfect_queries, percentage_perfect_queries, bad_queries, count_bad_queries, percentage_bad_queries, props_no_result, count_no_result_queries, percentage_no_result, data_amount, missing, dictio_prop_label_possible_entities = evaluate(data, hybrid_output, i)
    file_phil = open("evaluation/{}/eval_phil_{}.json".format(folder, i), "w")
    json.dump(dictio_querynr_lm_result, file_phil)
    file_phil.close()
    if missing:
        file_missing = open("evaluation/{}/dictio_missing".format(folder), "w")
        file_missing.write("Results of LM, which are not in dictionary, but would be correct\n")
        string_missing = "{}".format(missing)
        file_missing.write(string_missing)
        file_missing.close()
    if dictio_prop_label_possible_entities != {}:
        file_dictio_prop_label_possible_entities = open("evaluation/{}/dictio_prop_label_possible_entities".format(folder), "w")
        file_dictio_prop_label_possible_entities.write("Labels with the possible entities for each property\n")
        for prop in dictio_prop_label_possible_entities:
            string_prop_ids = "{}:\n{}\n\n".format(prop, dictio_prop_label_possible_entities[prop])
            file_dictio_prop_label_possible_entities.write(string_prop_ids)
        file_dictio_prop_label_possible_entities.close()
    if len(list_errors) > 0:
        #file to save the warnings and errors
        error_file = open("evaluation/{}/err_{}.txt".format(folder, i), "w")
        for err in list_errors:
            error_file.write(err+"\n")
        error_file.close()
    file_log_and_evaluation = open("evaluation/{}/log_eval_{}.txt".format(folder, i), "w")
    file_log_and_evaluation.write(parameter["queries_path"]+"\n")
    file_log_and_evaluation.write("Language Model: {}, max_confusion: {}, max_result_LM: {}, cardinality_estimation_sampling: {}, cardinality_estimation_percentage: {}, threshold_method_confusion: {}, threshold_method_number: {}, threshold_method_percentage: {}, template_path: {}, template_sampling: {}, template_ranking_method: {}, always_prop_classes: {}, min popularity score: {}\n\n".format(parameter["lm"], mc, parameter["mr"], parameter["ces"], cep, tmc, parameter["tmn"], tmp, parameter["tp"], parameter["ts"], parameter["trm"], parameter["apc"], parameter["ps"]))
    if len(actu_list_hybrid_log) == len(list_query_assign):
        for i in range(0, len(actu_list_hybrid_log)):
            file_log_and_evaluation.write(list_query_assign[i]+"\n")
            file_log_and_evaluation.write(actu_list_hybrid_log[i]+"\n")
    else:
        print("ERROR len(actu_list_hybrid_log) != len(list_query_assign)")
        for log in actu_list_hybrid_log:
            file_log_and_evaluation.write(log+"\n")
        for assign in list_query_assign:
            file_log_and_evaluation.write(assign+"\n")
    file_log_and_evaluation.write("\n"+string_evaluation+"\n")
    file_log_and_evaluation.write("\n"+string_eval_props)
    file_log_and_evaluation.close()
    if file_evaluation:
        sorted_popularity_scores = {k: v for k, v in sorted(popularity_scores.items(), key=lambda item: item)}
        file_evaluation.write("popularity scores: {}\n\n".format({k: sorted_popularity_scores[k] for k in list(sorted_popularity_scores)[:100]}))
        file_evaluation.write("Language Model: {}, max_confusion: {}, max_result_LM: {}, cardinality_estimation_sampling: {}, cardinality_estimation_percentage: {}, threshold_method_confusion: {}, threshold_method_number: {}, threshold_method_percentage: {}, template_path: {}, template_sampling: {}, template_ranking_method: {}, always_prop_classes: {}, min popularity score: {}\n\n".format(parameter["lm"], mc, parameter["mr"], parameter["ces"], cep, tmc, parameter["tmn"], tmp, parameter["tp"], parameter["ts"], parameter["trm"], parameter["apc"], parameter["ps"]))
        file_evaluation.write(string_evaluation+"\n\n")
        temp_perfect_queries = {}
        for prop in perfect_queries:
            temp_perfect_queries[prop] = perfect_queries[prop][0]
        temp_bad_queries = {}
        for prop in bad_queries:
            temp_bad_queries[prop] = bad_queries[prop][0]
        temp_no_result_queries = {}
        for prop in props_no_result:
            temp_no_result_queries[prop] = props_no_result[prop][0]
        file_evaluation.write("{}/{} perfect queries --> {}%:\n{}\n\n".format(count_perfect_queries, data_amount, percentage_perfect_queries, temp_perfect_queries))
        file_evaluation.write("{}/{} bad queries --> {}%:\n{}\n\n".format(count_bad_queries, data_amount, percentage_bad_queries, temp_bad_queries))
        file_evaluation.write("{}/{} no result queries --> {}%:\n{}\n\n".format(count_no_result_queries, data_amount,percentage_no_result, temp_no_result_queries))
        perfect_props = {}
        good_props = {}
        bad_props = {}
        for prop in dictio_props:
            count = 0
            all_count = dictio_props[prop]
            if prop in perfect_queries:
                count = count + perfect_queries[prop][0]
            if count / all_count > 0.2:
                if prop in props_no_result:
                    count = count + props_no_result[prop][0]
                if count / all_count > 0.8:
                    perfect_props[prop] = [count, all_count]
                else:
                    bad_props[prop] = [all_count-count, all_count]
            else:
                if prop in props_no_result:
                    count = count + props_no_result[prop][0]
                if count / all_count > 0.8:
                    good_props[prop] = [count, all_count]
                else:
                    bad_props[prop] = [all_count-count, all_count]

        file_evaluation.write("Perfect properties:\n{}\n\n".format(perfect_props))
        file_evaluation.write("Good properties:\n{}\n\n".format(good_props))
        file_evaluation.write("Bad properties:\n{}\n\n\n".format(bad_props))


def handeling_output(data, parameter, hybrid_output, list_hybrid_log, list_errors, string_random_outdated):
    if not os.path.exists("evaluation/"):
        os.mkdir("evaluation")
    if hybrid_output != []:
        if len(parameter["mc"]) == 1 and len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["tmp"]) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            os.mkdir("evaluation/{}_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"]))
            file_evaluation = open("evaluation/{}_trm_{}_{}_{}/eval_trm_{}_{}_{}_{}.txt".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"], parameter["trm"], string_random_outdated, parameter["lm"], date_time), "w")
            folder = "{}_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"])
            file_evaluation.write(parameter["queries_path"]+"\n\n")
            mc_value = parameter["mc"][0]
            cep_value = parameter["cep"][0]
            tmc_value = parameter["tmc"][0]
            tmp_value = parameter["tmp"][0]
            write_into_files(0, folder, mc_value, cep_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors,data, parameter)
            file_evaluation.close()
        elif len(parameter["mc"]) > 1 and len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["tmp"]) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            os.mkdir("evaluation/{}_mc_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"]))
            file_evaluation = open("evaluation/{}_mc_trm_{}_{}_{}/eval_trm_{}_{}_{}_{}.txt".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"], parameter["trm"], string_random_outdated, parameter["lm"], date_time), "w")
            folder = "{}_mc_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"])
            file_evaluation.write("mc "+str(parameter["mc"])+"\n")
            file_evaluation.write(parameter["queries_path"]+"\n\n")
            cep_value = parameter["cep"][0]
            tmc_value = parameter["tmc"][0]
            tmp_value = parameter["tmp"][0]
            for i in range (0, len(parameter["mc"])):
                mc_value = parameter["mc"][i]
                write_into_files(i, folder, mc_value, cep_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors,data, parameter) 
            file_evaluation.close()
        elif len(parameter["mc"]) == 1 and len(parameter["cep"]) > 1 and len(parameter["tmc"]) == 1 and len(parameter["tmp"]) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            os.mkdir("evaluation/{}_tp_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"]))
            file_evaluation = open("evaluation/{}_tp_trm_{}_{}_{}/eval_trm_{}_{}_{}_{}.txt".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"], parameter["trm"], string_random_outdated, parameter["lm"], date_time), "w")
            folder = "{}_tp_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"])
            file_evaluation.write("cep "+str(parameter["cep"])+"\n")
            file_evaluation.write(parameter["queries_path"]+"\n\n")
            mc_value = parameter["mc"][0]
            tmc_value = parameter["tmc"][0]
            tmp_value = parameter["tmp"][0]
            for i in range (0, len(parameter["cep"])):
                cep_value = parameter["cep"][i]
                write_into_files(i, folder, mc_value, cep_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors,data, parameter) 
            file_evaluation.close()
        elif len(parameter["mc"]) == 1 and len(parameter["cep"]) == 1 and len(parameter["tmc"]) > 1 and len(parameter["tmp"]) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            os.mkdir("evaluation/{}_tmc_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"]))
            file_evaluation = open("evaluation/{}_tmc_trm_{}_{}_{}/eval_trm_{}_{}_{}_{}.txt".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"], parameter["trm"], string_random_outdated, parameter["lm"], date_time), "w")
            folder = "{}_tmc_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"])
            file_evaluation.write("tmc "+str(parameter["tmc"])+"\n")
            file_evaluation.write(parameter["queries_path"]+"\n\n")
            mc_value = parameter["mc"][0]
            cep_value = parameter["cep"][0]
            tmp_value = parameter["tmp"][0]
            for i in range (0, len(parameter["tmc"])):
                tmc_value = parameter["tmc"][i]
                write_into_files(i, folder, mc_value, cep_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors,data, parameter) 
            file_evaluation.close()
        elif len(parameter["mc"]) == 1 and len(parameter["cep"]) == 1 and len(parameter["tmc"]) == 1 and len(parameter["tmp"]) > 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            os.mkdir("evaluation/{}_tmp_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"]))
            file_evaluation = open("evaluation/{}_tmp_trm_{}_{}_{}/eval_trm_{}_{}_{}_{}.txt".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"], parameter["trm"], string_random_outdated, parameter["lm"], date_time), "w")
            folder = "{}_tmp_trm_{}_{}_{}".format(date_time, parameter["trm"], string_random_outdated, parameter["lm"])
            file_evaluation.write("tmp "+str(parameter["tmp"])+"\n")
            file_evaluation.write(parameter["queries_path"]+"\n\n")
            mc_value = parameter["mc"][0]
            cep_value = parameter["cep"][0]
            tmc_value = parameter["tmc"][0]
            for i in range (0, len(parameter["tmp"])):
                tmp_value = parameter["tmp"][i]
                write_into_files(i, folder, mc_value, cep_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors,data, parameter) 
            file_evaluation.close()
    else:
        print("Hybrid returns no results")

def read_config_file():
    #parsing the config file
    config_file = open("config.json", "r")
    dictio_config = json.load(config_file)
    config_file.close()
    return dictio_config

def read_dataset_files(dictio_config):   
    #parsing the wikidata datasets
    dictio_wikidata_subjects = {} #maps subjects to given property and object of complete and incomplete wikidata
    dictio_wikidata_objects = {} #maps objects to given subject an property of complete and incomplete wikidata
    #only for debugging
    #actu_prop = "P103"
    #if os.path.exists("{}_dictio_wikidata_objects.json".format(actu_prop)) and os.path.exists("{}_dictio_wikidata_subjects.json".format(actu_prop)):
    #    with open("{}_dictio_wikidata_subjects.json".format(actu_prop), "r") as subjects:
    #        dictio_wikidata_subjects = json.load(subjects)
    #    with open("{}_dictio_wikidata_objects.json".format(actu_prop), "r") as objects:
    #        dictio_wikidata_objects = json.load(objects)
    #    print("read saved dictionaries for {}".format(actu_prop))
    #else:
    wikidata_gold_file = open(dictio_config["wikidata_gold_path"], "r")
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

    wikidata_missing_tripels = open(dictio_config["wikidata_missing_tripel_path"], "r")
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

    #file_objects = open("{}_dictio_wikidata_objects.json".format(actu_prop), "w")
    #temp = {}
    #temp[actu_prop] = dictio_wikidata_objects[actu_prop]
    #json.dump(temp, file_objects)
    #file_objects.close()
    #file_subjects = open("{}_dictio_wikidata_subjects.json".format(actu_prop), "w")
    #temp = {}
    #temp[actu_prop] = dictio_wikidata_subjects[actu_prop]
    #json.dump(temp, file_subjects)
    #file_subjects.close()

    #file_objects = open("dictio_wikidata_objects.json", "w")
    #json.dump(dictio_wikidata_objects, file_objects)
    #file_objects.close()
    #file_subjects = open("dictio_wikidata_subjects.json", "w")
    #json.dump(dictio_wikidata_subjects, file_subjects)
    #file_subjects.close()
    return dictio_wikidata_subjects, dictio_wikidata_objects

def read_label_id_file(dictio_config):
    #parsing the label-ID-dictionary
    dictio_label_id = {}
    #label_id_file = open(dictio_config["label_id_path"], "r")
    label_id_file = open(dictio_config["label_id_rdfLabel_path"], "r")
    dictio_label_id = json.load(label_id_file)
    label_id_file.close()
    return dictio_label_id

def read_id_label_file(dictio_config):
    #parsing the ID-label-dictionary
    dictio_id_label = {}
    #id_label_file = open(dictio_config["id_label_path"], "r")
    id_label_file = open(dictio_config["id_label_rdfLabel_path"], "r")
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

if __name__ == '__main__':
    dictio_config = read_config_file()
    dictio_wikidata_subjects, dictio_wikidata_objects = read_dataset_files(dictio_config)
    dictio_label_id = read_label_id_file(dictio_config)
    dictio_id_label = read_id_label_file(dictio_config)
    dictio_id_p31, dictio_id_p279 = read_p31_p279_file(dictio_config)
    #dictio_prop_probdistribution = read_cardinality_estimation_file(dictio_config)
    dictio_prop_classes = read_prop_classes_file(dictio_config)
    dictio_entity_popularity = read_entity_popularity_file(dictio_config)

    data = {}
    data["config"] = dictio_config
    data["wikidata_subjects"] = dictio_wikidata_subjects
    data["wikidata_objects"] = dictio_wikidata_objects
    data["label_id"] = dictio_label_id
    data["id_label"] = dictio_id_label
    data["trie"] = make_trie(set(data["label_id"].keys()))
    data["id_p31"] = dictio_id_p31
    data["id_p279"] = dictio_id_p279
    #data["prop_probdistribution"] = dictio_prop_probdistribution
    data["prop_classes"] = dictio_prop_classes
    data["entity_popularity"] = dictio_entity_popularity
    print("read all data files")

    evaluations = []
    #wikidata_incomplete: version how incomplete wikidata was created: "random_incomplete" (or "outdated_incomplete")
    #file_queries: path to an query file
    #lm: name of the Language Model(LM)
    #mc: hardcoded maximum confusion
    #mr: hardcoded max results which LM should add
    #ces: threshold for sampling size at cardinality estimation --> not activated: -1
    #cep: threshold for percentage at cardinality estimation --> not activated: -1
    #tmc: threshold for probability at threshold calculation for probability --> not activated: 0
    #tmn: threshold for number of results at threshold calculation for probability --> not activated: 0
    #tmp: threshold for percentage at threshold calculation for probability --> not activated: 0
    #tp: path to the templates which are used
    #ts: value how many templates should be used
    #trm: string which ranking method should be used for the labels of different templates: "avg" oder "max"
    #apc: value wheather the property classes should always be used
    #ps: min value for entity popularity score (no negativ values)

    #evaluation 1
    parameter = {}
    parameter["wikidata_incomplete"] = "random_incomplete"
    parameter["queries_path"] = dictio_config["queries_path"]
    parameter["lm"] = "bert"
    parameter["mc"] = [-7]
    parameter["mr"] = 1000
    parameter["ces"] = -1
    parameter["cep"] = [-1]
    parameter["tmc"] = [-0.01, -0.1, -0.5, -1, -1.4, -1.5, -2, -3, -4, -100]
    parameter["tmn"] = 10
    parameter["tmp"] = [0.5]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    if correct_parameter(parameter["mc"], parameter["cep"], parameter["tmc"], parameter["tmp"], parameter["ts"]):
        evaluations.append(parameter)
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")

    #evaluation 2
    parameter = {}
    parameter["wikidata_incomplete"] = "random_incomplete"
    parameter["queries_path"] = dictio_config["queries_path"]
    parameter["lm"] = "bert"
    parameter["mc"] = [-7]
    parameter["mr"] = 1000
    parameter["ces"] = -1
    parameter["cep"] = [-1]
    parameter["tmc"] = [-0.01, -0.1, -0.5, -1, -1.4, -1.5, -2, -3, -4, -100]
    parameter["tmn"] = 10
    parameter["tmp"] = [0.5]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 5
    parameter["trm"] = "avg"
    parameter["apc"] = False
    parameter["ps"] = 1
    if correct_parameter(parameter["mc"], parameter["cep"], parameter["tmc"], parameter["tmp"], parameter["ts"]):
        evaluations.append(parameter)
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")

    #evaluation 3
    parameter = {}
    parameter["wikidata_incomplete"] = "random_incomplete"
    parameter["queries_path"] = dictio_config["queries_path"]
    parameter["lm"] = "bert"
    parameter["mc"] = [-7]
    parameter["mr"] = 1000
    parameter["ces"] = -1
    parameter["cep"] = [-1]
    parameter["tmc"] = [-0.01, -0.1, -0.5, -1, -1.4, -1.5, -2, -3, -4, -100]
    parameter["tmn"] = 10
    parameter["tmp"] = [0.5]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 1
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    #if correct_parameter(parameter["mc"], parameter["cep"], parameter["tmc"], parameter["tmp"], parameter["ts"]):
    #    evaluations.append(parameter)
    #else:
    #    print("at least one of the paramter mc, cep, tmc or tmp are wrong")

    #evaluation 4
    parameter = {}
    parameter["wikidata_incomplete"] = "random_incomplete"
    parameter["queries_path"] = dictio_config["queries_path"]
    parameter["lm"] = "bert"
    parameter["mc"] = [-7]
    parameter["mr"] = 1000
    parameter["ces"] = -1
    parameter["cep"] = [-1]
    parameter["tmc"] = [-0.01, -0.1, -0.5, -1, -1.4, -1.5, -2, -3, -4, -100]
    parameter["tmn"] = 10
    parameter["tmp"] = [0.5]
    parameter["tp"] = dictio_config["template_path"]["ranking2"]
    parameter["ts"] = 10
    parameter["trm"] = "max"
    parameter["apc"] = False
    parameter["ps"] = 1
    #if correct_parameter(parameter["mc"], parameter["cep"], parameter["tmc"], parameter["tmp"], parameter["ts"]):
    #    evaluations.append(parameter)
    #else:
    #    print("at least one of the paramter mc, cep, tmc or tmp are wrong")

    runtime = []
    for parameter in evaluations:
        data["prop_template"] = read_template_file(parameter["tp"])
        start = timeit.default_timer()
        hybrid_output, list_hybrid_log, list_errors = hybrid_system.execute(parameter, data)
        stop = timeit.default_timer()
        handeling_output(data, parameter, hybrid_output, list_hybrid_log, list_errors, parameter["wikidata_incomplete"].split("_")[0])
        print('Time: {}min'.format((stop - start)/60))
        runtime.append(str((stop - start)/60)+"min")
    print(runtime)
                
        