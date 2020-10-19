import dill
import os
import json
#from LAMA.lama.modules import build_model_by_name
#import LAMA.lama.options as options

def read_config_file():
    #parsing the config file
    config_file = open("config.json", "r")
    dictio_config = json.load(config_file)
    config_file.close()
    return dictio_config

def build(lm_name):
    dictio_config = read_config_file()
    path = dictio_config["lm_build_path_template"].replace("<name>", lm_name)
    if os.path.exists(path):
        with open(path, 'rb') as lm_build_file:
            lm_build = dill.load(lm_build_file)
    else:
        #TODO
        #if lm == "roberta":
        #   path = "/data/fichtel/roberta.large/"
        #   result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--rmd", path, "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
        #   #print(result)
        #elif lm == "bert":
        #    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--bmn", "bert-large-cased", "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
        #else:
        #    result = subprocess.Popen(["python", "LAMA/lama/eval_generation.py", "--lm", lm, "--t", query_LM], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
        lm_build = None
    return lm_build
