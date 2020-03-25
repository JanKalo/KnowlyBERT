import pyodbc
import json
import os

if __name__ == '__main__':
    file_label_ID = open("dictio_label_id_multi_token.json", "r")
    dictio_label_id = json.load(file_label_ID)
    file_label_ID.close()

    dictio_id_label = {}
    for label in dictio_label_id:
        ids = dictio_label_id[label]
        for id in ids:
            if id in dictio_id_label:
                print("ERROR label:{}, id:{}, zweitesLabel:{}".format(label, id, dictio_id_label[id]))
            else:
                dictio_id_label[id] = label

    #open a json-file to save the data
    print("open file...")
    if os.path.exists("dictio_id_label_multi_token.json"):
       os.remove("dictio_id_label_multi_token.json")
    file = open("dictio_id_label_multi_token.json", "w")
    json.dump(dictio_id_label, file)
    file.close()
    print("...result written to json :)")

