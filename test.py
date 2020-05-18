import simplejson as json

def read_config_file():
    #parsing the config file
    config_file = open("config.json", "r")
    dictio_config = json.load(config_file)
    config_file.close()
    return dictio_config

def read_template_file(path):
    #read json file for templates
    dictio_prop_templates = {}
    file_prop_sentence = open(path, "r", encoding="utf8")
    dictio_prop_templates = json.load(file_prop_sentence)
    file_prop_sentence.close()
    return dictio_prop_templates

dictio_config = read_config_file()
print(dictio_config["template_path"]["LPQAQ_paraphrase"])
temps = read_template_file(dictio_config["template_path"]["LPQAQ_paraphrase"])