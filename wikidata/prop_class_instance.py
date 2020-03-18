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
                    <{}> <http://www.wikidata.org/prop/direct/P31> ?instance
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

def main():
    file_sentences = open("../LM_sentence/prop_sentence.json", "r")
    line = file_sentences.readline().split("\n")[0]
    props = []
    while line != "":
        data = json.loads(line)
        for prop in data:
            props.append(prop)
        line = file_sentences.readline().split("\n")[0]
    file_sentences.close()

    dictio_classes = {}
    for p in props:
        try:
            if p != "P31" and p != "P279":
                items = []
                values = []
                print(p)
                query = """SELECT DISTINCT ?item ?value
                        WHERE {{
                            ?item <http://www.wikidata.org/prop/direct/{}> ?value
                        }}""".format(p)
                cursor.execute("SPARQL "+query)
                while True:
                    row = cursor.fetchone()
                    if not row:
                        break
                    if row.item not in items:
                        items.append(row.item)
                    if row.value not in values:
                        values.append(row.value)
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