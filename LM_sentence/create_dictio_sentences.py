import os
import argparse
import json
import pyodbc

def main(file_path):
    #open a json-file to save the data
    if os.path.exists("prop_sentence.json"):
        os.remove("prop_sentence.json")
    file_dictio = open("prop_sentence.json", "w")
    dictio_prop_sentence = {}

    file_relations = open("relations.jsonl")
    line = file_relations.readline().split("\n")[0]
    while line != "":
        data = json.loads(line)
        prop = data["relation"]
        dictio_sentence = {}
        sentence = data["template"]
        dictio_sentence["?PQ"] = (sentence.replace("[X]", "[MASK]")).replace("[Y]", "Q")
        dictio_sentence["QP?"] = (sentence.replace("[Y]", "[MASK]")).replace("[X]", "Q")
        dictio_prop_sentence[prop] = dictio_sentence
        line = file_relations.readline().split("\n")[0]
        
    for prop in dictio_prop_sentence:
        temp = {}
        temp[prop] = dictio_prop_sentence[prop]
        json.dump(temp, file_dictio)
        file_dictio.write("\n")
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-path",default=None, help="Path to the possible examples")
    args = parser.parse_args()
    main(args.path)