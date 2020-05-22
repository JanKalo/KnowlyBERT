import simplejson as json
import os
from argparse import ArgumentParser

def remove_prefix(dictio):
    dictio_new = {}
    for prop_url in dictio:
        prop = int(str(prop_url).split('/')[-1].replace('>', "").replace("P", ""))
        dictio_new[prop] = dictio[prop_url]
    return {k: dictio_new[k] for k in sorted(dictio_new)}

def main():
    parser = ArgumentParser()
    parser.add_argument(
        "EVALUATION_FILE", nargs="+", type=str,
        help="The json files of the evaluation"
        )
    args = parser.parse_args()
    for entry in args.EVALUATION_FILE:
        dict_eval_file = open(entry, "r")
        dict_eval = json.load(dict_eval_file)
        dict_eval_file.close()
        if os.path.exists("eval_props_{}".format(entry.split("_")[1].replace(".json", ""))):
            os.remove("eval_props_{}".format(entry.split("_")[1].replace(".json", "")))
        eval_props_file = open("eval_props_{}".format(entry.split("_")[1].replace(".json", "")), "w")
        if os.path.exists("eval_avg_{}".format(entry.split("_")[1].replace(".json", ""))):
            os.remove("eval_avg_{}".format(entry.split("_")[1].replace(".json", "")))
        eval_avg_file = open("eval_avg_{}".format(entry.split("_")[1].replace(".json", "")), "w")
        for eval in dict_eval:
            eval_props_file.write(eval+"\n")
            eval_avg_file.write(eval+"\n")
            sorted_dict = remove_prefix(dict_eval[eval]["per_relation"])
            for prop in sorted_dict:
                    precision_recall = sorted_dict[prop]
                    eval_props_file.write("P{}: {}\n".format(prop, precision_recall))
            eval_props_file.write("\n")

            eval_avg_file.write("Recall (per_query): {}\n".format(dict_eval[eval]["per_query_avg_rec"]))
            eval_avg_file.write("Precision (per_query): {}\n\n".format(dict_eval[eval]["per_query_avg_prec"]))
        eval_props_file.close()
        eval_avg_file.close()

if __name__ == "__main__":
    main()
