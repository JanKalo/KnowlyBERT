import os
import argparse
import json
import pyodbc

def main(file_path):
    #open a json-file to save the data
    if os.path.exists("/home/fichtel/conferences/iswc2020/data/prop_sentence_LAMA.json"):
        os.remove("/home/fichtel/conferences/iswc2020/data/prop_sentence_LAMA.json")
    file_dictio = open("/home/fichtel/conferences/iswc2020/data/prop_sentence_LAMA.json", "w")
    dictio_prop_sentence = {}

    file_relations = open("relations.jsonl")
    line = file_relations.readline().split("\n")[0]
    while line != "":
        data = json.loads(line)
        prop = data["relation"]
        sentence = data["template"]
        template = (sentence.replace("[X]", "[S]")).replace("[Y]", "[O]")
        dictio_prop_sentence[prop] = {}
        dictio_prop_sentence[prop][template] = 7
        line = file_relations.readline().split("\n")[0]
        
    json.dump(dictio_prop_sentence, file_dictio)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-path",default=None, help="Path to the possible examples")
    args = parser.parse_args()
    main(args.path)
