import pyodbc
import json
import os

if __name__ == '__main__':
    file_label_ID = open("/home/kalo/conferences/iswc2020/data/dictio_label_id_multi_token.json", "r")
    dictio_label_id = json.load(file_label_ID)
    file_label_ID.close()

    dictio_label_id_cleaned = {}
    for label in dictio_label_id:
        ids = dictio_label_id[label]
        ids_cleaned = []
        for id in ids:
            if id.split('/')[-1] not in ids_cleaned:
                ids_cleaned.append(id.split('/')[-1])
        dictio_label_id_cleaned[label] = ids_cleaned

    #open a json-file to save the data
    print("open file...")
    if os.path.exists("dictio_label_id_multi_token.json"):
       os.remove("dictio_label_id_multi_token.json")
    file = open("dictio_label_id_multi_token.json", "w")
    json.dump(dictio_label_id_cleaned, file)
    file.close()
    print("...result written to json :)")

