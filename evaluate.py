import outdated_hybrid
import random_hybrid
import sys
from random import randint
import time
import os
import timeit

dictio_props = None

def evaluate(output_hybrid, i):
    global dictio_props
    dictio_props = {}
    string_eval = ""
    string_eval_props = ""
    list_query_assign = []
    perfect_queries = {}
    bad_queries = {}
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
        for data in data_output_hybrid:
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

            num_results_KG_current = len(results_KG_current)
            num_results_KG_o_r = len(results_KG_o_r)

            if num_results_KG_o_r == 0:
                count_no_entry_o_r = count_no_entry_o_r +1

            results_LM = data["LM"]
            already_existing = data["already_existing"]
            if already_existing:
                count_already_existing = count_already_existing +1

            actu_status_label = data["status_possible_result_LM_label"]
            if actu_status_label == "correct_label":
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
            string_eval = string_eval + "{}/{} queries with incorrect possible label at first position --> {}%\n\n".format(count_possible_result_LM_incorrect_label, data_amount, round(count_possible_result_LM_incorrect_label/data_amount*100, 2))
            
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
            
    return string_eval, string_eval_props, list_query_assign, perfect_queries, count_perfect_queries, percentage_perfect_queries, bad_queries, count_bad_queries, percentage_bad_queries, props_no_result, no_results, round(no_results/data_amount*100, 2), data_amount, missing, dictio_prop_label_possible_entities

def correct_parameter(mc, cep, tmc, tmp):
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

def write_into_files(i, folder, mc, cep, tmc, tmp, file_evaluation, hybrid_output, list_hybrid_log, list_errors, file_examples):
    actu_list_hybrid_log = []
    for log in list_hybrid_log:
        actu_list_hybrid_log.append(log[i])
    string_evaluation, string_eval_props, list_query_assign, perfect_queries, count_perfect_queries, percentage_perfect_queries, bad_queries, count_bad_queries, percentage_bad_queries, props_no_result, count_no_result_queries, percentage_no_result, data_amount, missing, dictio_prop_label_possible_entities = evaluate(hybrid_output, i)
    if missing:
        file_missing = open("evaluation/{}/dictio_missing".format(folder), "w")
        file_missing.write("Results of LM, which are not in dictionary, but would be correct\n")
        string_missing = "{}".format(missing)
        file_missing.write(string_missing)
        file_missing.close()
    if dictio_prop_label_possible_entities != {}:
        file_dictio_prop_label_possible_entities = open("evaluation/{}/dictio_prop_label_possible_entities".format(folder), "w")
        file_dictio_prop_label_possible_entities.write("Labels which has more than one possible entity id for each property\n")
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
    if "txt" in str(file_examples) or "json" in str(file_examples):
        file_log_and_evaluation.write(file_examples+"\n")
    else:
        file_log_and_evaluation.write(random_file_path + ", random_count: "+ str(random_count)+"\n")
        file_log_and_evaluation.write("Random examples: {}\n".format(random_examples))
    file_log_and_evaluation.write("Language Model: {}, max_confusion: {}, max_result_LM: {}, cardinality_estimation_sampling: {}, cardinality_estimation_percentage: {}, threshold_method_confusion: {}, threshold_method_number: {}, threshold_method_percentage: {}, whole_sentence: {}, always_prop_classes: {}\n\n".format(lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc))
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
        file_evaluation.write("Language Model: {}, max_confusion: {}, max_result_LM: {}, cardinality_estimation_sampling: {}, cardinality_estimation_percentage: {}, threshold_method_confusion: {}, threshold_method_number: {}, threshold_method_percentage: {}, whole_sentence: {}, always_prop_classes: {}\n".format(lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc))
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


def handeling_output(hybrid_output, list_hybrid_log, list_errors, string_random_outdated, language_model):
    if hybrid_output != []:
        if len(mc) == 1 and len(cep) == 1 and len(tmc) == 1 and len(tmp) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            if ws:
                os.mkdir("evaluation/{}_ws_true_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_ws_true_{}_{}/eval_ws_true_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_ws_true_{}_{}".format(date_time, string_random_outdated, language_model)
            else:
                os.mkdir("evaluation/{}_ws_false_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_ws_false_{}_{}/eval_ws_false_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_ws_false_{}_{}".format(date_time, string_random_outdated, language_model)
            if "txt" in str(file_examples) or "json" in str(file_examples):
                file_evaluation.write(file_examples+"\n\n")
            else:
                file_evaluation.write(random_file_path + ", random_count: "+ str(random_count)+"\n")
                file_evaluation.write("Random examples: {}\n\n".format(random_examples))
            mc_value = mc[0]
            tp_value = cep[0]
            tmc_value = tmc[0]
            tmp_value = tmp[0]
            write_into_files(0, folder, mc_value, tp_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors, file_examples)
            file_evaluation.close()
        elif len(mc) > 1 and len(cep) == 1 and len(tmc) == 1 and len(tmp) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            if ws:
                os.mkdir("evaluation/{}_mc_ws_true_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_mc_ws_true_{}_{}/eval_mc_ws_true_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_mc_ws_true_{}_{}".format(date_time, string_random_outdated, language_model)
            else:
                os.mkdir("evaluation/{}_mc_ws_false_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_mc_ws_false_{}_{}/eval_mc_ws_false_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_mc_ws_false_{}_{}".format(date_time, string_random_outdated, language_model)
            file_evaluation.write("mc "+str(mc)+"\n")
            if "txt" in str(file_examples) or "json" in str(file_examples):
                file_evaluation.write(file_examples+"\n\n")
            else:
                file_evaluation.write(random_file_path + ", random_count: "+ str(random_count)+"\n")
                file_evaluation.write("Random examples: {}\n\n".format(random_examples))
            tp_value = cep[0]
            tmc_value = tmc[0]
            tmp_value = tmp[0]
            for i in range (0, len(mc)):
                mc_value = mc[i]
                write_into_files(i, folder, mc_value, tp_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors, file_examples) 
            file_evaluation.close()
        elif len(mc) == 1 and len(cep) > 1 and len(tmc) == 1 and len(tmp) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            if ws:
                os.mkdir("evaluation/{}_tp_ws_true_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_tp_ws_true_{}_{}/eval_tp_ws_true_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_tp_ws_true_{}_{}".format(date_time, string_random_outdated, language_model)
            else:
                os.mkdir("evaluation/{}_tp_ws_false_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_tp_ws_false_{}_{}/eval_tp_ws_false_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_tp_ws_false_{}_{}".format(date_time, string_random_outdated, language_model)
            file_evaluation.write("cep "+str(cep)+"\n")
            if "txt" in str(file_examples) or "json" in str(file_examples):
                file_evaluation.write(file_examples+"\n\n")
            else:
                file_evaluation.write(random_file_path + ", random_count: "+ str(random_count)+"\n")
                file_evaluation.write("Random examples: {}\n\n".format(random_examples))
            mc_value = mc[0]
            tmc_value = tmc[0]
            tmp_value = tmp[0]
            for i in range (0, len(cep)):
                tp_value = cep[i]
                write_into_files(i, folder, mc_value, tp_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors, file_examples) 
            file_evaluation.close()
        elif len(mc) == 1 and len(cep) == 1 and len(tmc) > 1 and len(tmp) == 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            if ws:
                os.mkdir("evaluation/{}_tmc_ws_true_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_tmc_ws_true_{}_{}/eval_tmc_ws_true_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_tmc_ws_true_{}_{}".format(date_time, string_random_outdated, language_model)
            else:
                os.mkdir("evaluation/{}_tmc_ws_false_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_tmc_ws_false_{}_{}/eval_tmc_ws_false_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_tmc_ws_false_{}_{}".format(date_time, string_random_outdated, language_model)
            file_evaluation.write("tmc "+str(tmc)+"\n")
            if "txt" in str(file_examples) or "json" in str(file_examples):
                file_evaluation.write(file_examples+"\n\n")
            else:
                file_evaluation.write(random_file_path + ", random_count: "+ str(random_count)+"\n")
                file_evaluation.write("Random examples: {}\n\n".format(random_examples))
            mc_value = mc[0]
            tp_value = cep[0]
            tmp_value = tmp[0]
            for i in range (0, len(tmc)):
                tmc_value = tmc[i]
                write_into_files(i, folder, mc_value, tp_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors, file_examples) 
            file_evaluation.close()
        elif len(mc) == 1 and len(cep) == 1 and len(tmc) == 1 and len(tmp) > 1:
            date_time = time.strftime("%d.%m._%H:%M:%S")
            if ws:
                os.mkdir("evaluation/{}_tmp_ws_true_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_tmp_ws_true_{}_{}/eval_tmp_ws_true_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_tmp_ws_true_{}_{}".format(date_time, string_random_outdated, language_model)
            else:
                os.mkdir("evaluation/{}_tmp_ws_false_{}_{}".format(date_time, string_random_outdated, language_model))
                file_evaluation = open("evaluation/{}_tmp_ws_false_{}_{}/eval_tmp_ws_false_{}_{}_{}.txt".format(date_time, string_random_outdated, language_model, string_random_outdated, language_model, date_time), "w")
                folder = "{}_tmp_ws_false_{}_{}".format(date_time, string_random_outdated, language_model)
            file_evaluation.write("tmp "+str(tmp)+"\n")
            if "txt" in str(file_examples) or "json" in str(file_examples):
                file_evaluation.write(file_examples+"\n\n")
            else:
                file_evaluation.write(random_file_path + ", random_count: "+ str(random_count)+"\n")
                file_evaluation.write("Random examples: {}\n\n".format(random_examples))
            mc_value = mc[0]
            tp_value = cep[0]
            tmc_value = tmc[0]
            for i in range (0, len(tmp)):
                tmp_value = tmp[i]
                write_into_files(i, folder, mc_value, tp_value, tmc_value, tmp_value, file_evaluation, hybrid_output, list_hybrid_log, list_errors, file_examples) 
            file_evaluation.close()
    else:
        print("Hybrid returns no results")

import json
if __name__ == '__main__':
    #parsing the label-ID-dictionary
    entities = {}
    dicto = open("wikidata/dictio_label_id.json", "r")
    line = dicto.readline().split("\n")[0]
    while line != "":
        data = json.loads(line)
        label = list(data.keys())
        entities[label[0]] = data[label[0]]
        line = dicto.readline().split("\n")[0]
    dicto.close()
    print("INFO: Label_ID_Dictio parsed")

    random = False
    random_count = 200
    random_file_path = "examples/personal/all_possible/1114_port_examples_random_200.txt"
    random_examples = []
    if random:
        file = open(random_file_path, "r")
        examples = []
        line = file.readline().split("\n")[0]
        while line != "":
            examples.append(line)
            line = file.readline().split("\n")[0]
        file.close()
        max_index = len(examples)-1
        for _ in range(random_count):
            index = randint(0, max_index)
            line = examples[index]
            items = line.split(" ")
            random_examples.append(items)

    evaluations = []
    #port: port for the outdated versioon of wikidata
    #file_example: path to an example file
    #lm: name of the Language Model(LM)
    #mc: hardcoded maximum confusion
    #mr: hardcoded max results which LM should add
    #ces: threshold for sampling size at cardinality estimation
    #cep: threshold for percentage at cardinality estimation
    #tmc: threshold for confusion at threshold calculation for confusion
    #tmn: threshold for number of results at threshold calculation for confusion
    #tmp: threshold for percentage at threshold calculation for confusion
    #ws: value wheather keyword or whole sentence should be used for LM
    #apc: value wheather the proptery classes should always be used

    #evaluation test
    port = "1114"
    #file_examples = "examples/personal/test.txt"
    file_examples_outdated = "examples/outdated/alor_True/1114_port_examples_random_200_alor_True.txt"
    file_examples_random = "examples/random/random_examples_random_1_alor_True.json"
    #file_examples = random_examples
    lm = "bert"
    mc = [-7]
    mr = 1
    ces = 1000
    cep = [0.5]
    tmc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    tmn = 10
    tmp = [0.5]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_test_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_test_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        evaluations.append([None, eval_test_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")

    #evaluation test
    port = "1114"
    file_examples_outdated = "examples/personal/all_possible/outdated/alor_True/1114_port_examples_random_200_alor_True_1.txt"
    file_examples_random = "examples/personal/all_possible/random/alor_True/random_examples_random_200_alor_True_1.json"
    lm = "bert"
    mc = [-7]
    mr = 1
    ces = 1000
    cep = [0.5]
    tmc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    tmn = 10
    tmp = [0.5]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_test2_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_test2_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        #evaluations.append([None, eval_test2_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")

    #evaluation test
    port = "1114"
    file_examples_outdated = "examples/personal/all_possible/outdated/alor_True/1114_port_examples_random_200_alor_True_2.txt"
    file_examples_random = "examples/personal/all_possible/random/alor_True/random_examples_random_200_alor_True_2.json"
    lm = "bert"
    mc = [-7]
    mr = 1
    ces = 1000
    cep = [0.5]
    tmc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    tmn = 10
    tmp = [0.5]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_test3_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_test3_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        #evaluations.append([None, eval_test3_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")


    #evaluation 1
    port = "1114"
    #file_examples = "examples/personal/test.txt"
    file_examples_outdated = "examples/personal/all_possible/outdated/alor_True/1114_port_examples_random_200_alor_True_0.txt"
    file_examples_random = "examples/personal/all_possible/random/alor_True/random_examples_random_200_alor_True_2.json"
    #file_examples = random_examples
    lm = "bert"
    mc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    mr = 10
    ces = -1
    cep = [-1]
    tmc = [0]
    tmn = 0
    tmp = [0]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_1_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_1_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        #evaluations.append([None, eval_1_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")
    
    #evaluation 2
    port = "1114"
    #file_examples = "examples/personal/test.txt"
    file_examples_outdated = "examples/personal/all_possible/outdated/alor_True/1114_port_examples_random_200_alor_True_1.txt"
    file_examples_random = "examples/personal/all_possible/random/alor_False/random_examples_random_200_alor_False_one_result_0.json"
    #file_examples = random_examples
    lm = "bert"
    mc = [-7]
    mr = 10
    ces = 1000
    cep = [0.5]
    tmc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    tmn = 10
    tmp = [0.5]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_2_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_2_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        #evaluations.append([None, eval_2_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")
    
    #evaluation 3
    port = "1114"
    #file_examples = "examples/personal/test.txt"
    file_examples_outdated = "examples/personal/all_possible/outdated/alor_True/1114_port_examples_random_200_alor_True_2.txt"
    file_examples_random = "examples/personal/all_possible/random/alor_True/random_examples_random_200_alor_True_1.json"
    #file_examples = random_examples
    lm = "bert"
    mc = [-7]
    mr = 10
    ces = -1
    cep = [-1]
    tmc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    tmn = 10
    tmp = [0.5]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_3_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_3_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        #evaluations.append([None, eval_3_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")
    
    #evaluation 4
    port = "1114"
    #file_examples = "examples/personal/test.txt"
    file_examples_outdated = "examples/personal/all_possible/outdated/alor_True/1114_port_examples_random_200_alor_True.txt"
    file_examples_random = "examples/personal/all_possible/random/alor_True/random_examples_random_200_alor_True_2.json"
    #file_examples = random_examples
    lm = "bert"
    mc = [-7]
    mr = 10
    ces = -1
    cep = [-1]
    tmc = [-1, -1.1, -1.2, -1.3, -1.4, -1.5, -2, -3, -4]
    tmn = 10
    tmp = [0.5]
    ws = True
    apc = False
    if correct_parameter(mc, cep, tmc, tmp):
        eval_4_outdated = [port, file_examples_outdated, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        eval_4_random = [port, file_examples_random, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc]
        #evaluations.append([None, eval_4_random])
    else:
        print("at least one of the paramter mc, cep, tmc or tmp are wrong")
    
    runtime = []
    for eval_outdated_random in evaluations:
        outdated = eval_outdated_random[0]
        if outdated:
            port = outdated[0]
            file_examples = outdated[1]
            lm = outdated[2]
            mc = outdated[3]
            mr = outdated[4]
            ces = outdated[5]
            cep = outdated[6]
            tmc = outdated[7]
            tmn = outdated[8]
            tmp = outdated[9]
            ws = outdated[10]
            apc = outdated[11]
            start = timeit.default_timer()
            hybrid_output, list_hybrid_log, list_errors = outdated_hybrid.execute(port, file_examples, entities, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc)
            stop = timeit.default_timer()
            handeling_output(hybrid_output, list_hybrid_log, list_errors, "outdated", lm)
            print('Time: {}min'.format((stop - start)/60))
            runtime.append(str((stop - start)/60)+"min")
        random = eval_outdated_random[1]
        if random:
            port = random[0]
            file_examples = random[1]
            lm = random[2]
            mc = random[3]
            mr = random[4]
            ces = random[5]
            cep = random[6]
            tmc = random[7]
            tmn = random[8]
            tmp = random[9]
            ws = random[10]
            apc = random[11]
            start = timeit.default_timer()
            hybrid_output, list_hybrid_log, list_errors = random_hybrid.execute(port, file_examples, entities, lm, mc, mr, ces, cep, tmc, tmn, tmp, ws, apc)
            stop = timeit.default_timer()
            handeling_output(hybrid_output, list_hybrid_log, list_errors, "random", lm)
            print('Time: {}min'.format((stop - start)/60))
            runtime.append(str((stop - start)/60)+"min")
    print(runtime)
                
        