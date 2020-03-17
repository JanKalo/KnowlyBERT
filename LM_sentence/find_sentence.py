import json

def find(dictio, prop, structure_string):
    if prop in dictio:
        sentence = dictio[prop][structure_string]
        if sentence == "":
            return -1
        else:
            return sentence
    return -1