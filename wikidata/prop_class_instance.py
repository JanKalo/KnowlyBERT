import pyodbc
import json
import os

# Specifying the ODBC driver, server name, database, etc. directly
cnxn = pyodbc.connect('DRIVER={/home/fichtel/virtodbc_r.so};HOST=134.169.32.169:1112;DATABASE=Virtuoso;UID=dba;PWD=F4B656JXqBG')
cnxn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
cnxn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
# Create a cursor from the connection
cursor = cnxn.cursor()

def find_class(entity_id_urls):
    classes = {}
    for url in entity_id_urls:
        #finding instance
        query = """SELECT ?instance 
                WHERE {{
                    <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/direct/P31> ?instance
                }}""".format(url)
        cursor.execute("SPARQL "+query)
        while True:
            row = cursor.fetchone()
            if not row:
                break
            if row.instance in classes:
                classes[row.instance] = classes[row.instance] + 1
            else:
                classes[row.instance] = 1
    sorted_classes = {k: v for k, v in sorted(classes.items(), reverse=True, key=lambda item: item[1])}    
    return sorted_classes

def get_most_common_classes(classes):
    most_common_classes = {}
    biggest_amount = -1
    for c in classes:
        if most_common_classes == {}:
            biggest_amount = classes[c]
            most_common_classes[c] = classes[c]
        else:
            if classes[c]/biggest_amount > 0.4:
                most_common_classes[c] = classes[c]
            else:
                break
    return most_common_classes

def read_config_file():
    #parsing the config file
    config_file = open("../config.json", "r")
    dictio_config = json.load(config_file)
    config_file.close()
    return dictio_config

def main():
    #dictio_config = read_config_file()
    #dataset = open(dictio_config["wikidata_missing_tripel_path"])
    dataset = open("../P1412_dictio_wikidata_objects.json", "r")
    dictio_wikidata_objects = json.load(dataset)
    dataset.close()
    #props = ['P19', 'P20', 'P279', 'P37', 'P413', 'P166', 'P449', 'P69', 'P47', 'P138', 'P364', 'P54', 'P463', 'P101', 'P1923', 'P106', 'P527', 'P102', 'P530', 'P176', 'P27', 'P407', 'P30', 'P178', 'P1376', 'P131', 'P1412', 'P108', 'P136', 'P17', 'P39', 'P264', 'P276', 'P937', 'P140', 'P1303', 'P127', 'P103', 'P190', 'P1001', 'P31', 'P495', 'P159', 'P36', 'P740', 'P361']
    props = ["P1412"]
    dictio_classes = {}
    for p in props:
        try:
            items = []
            values = []
            subjects = dictio_wikidata_objects[p]
            for subj in subjects:
                items.append(subj)
                objects = dictio_wikidata_objects[p][subj]["random_incomplete"]
                for obj in objects:
                    values.append(obj)
            item_classes = find_class(items)            
            values_classes = find_class(values)
            temp = {}
            temp["?PQ"] = get_most_common_classes(item_classes)
            temp["QP?"] = get_most_common_classes(values_classes)
            dictio_classes[p] = temp
        except Exception as e:
            print(p)
            print(e)
            continue
    #open a txt-file to save the data
    print("open file...")
    if os.path.exists("dictio_prop_class_instances.json"):
        os.remove("dictio_prop_class_instances.json")
    file = open("dictio_prop_class_instances.json", "w")
    for prop in dictio_classes:
        temp = {}
        temp[prop] = dictio_classes[prop]
        json.dump(temp, file)
        file.write("\n")
    file.close()
    print("...result written to txt :)")

if __name__ == '__main__':
    main()