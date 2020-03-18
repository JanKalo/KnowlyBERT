import pyodbc
import json
import os

# Specifying the ODBC driver, server name, database, etc. directly
cnxn = pyodbc.connect('DRIVER={/home/fichtel/virtodbc_r.so};HOST=134.169.32.169:1112;DATABASE=Virtuoso;UID=dba;PWD=F4B656JXqBG')
cnxn.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
cnxn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
# Create a cursor from the connection
cursor = cnxn.cursor()

def main():
    props = ["P31", "P279", "P361"]
    entities = {}
    for p in props:
        try:
            print(p)
            query = """SELECT DISTINCT ?item ?itemLabel
                    WHERE {{
                        ?item <http://www.wikidata.org/prop/direct/{}> ?id
                        OPTIONAL {{
                            ?item <http://www.w3.org/2000/01/rdf-schema#label> ?itemLabel.
                            FILTER(LANG(?itemLabel) = "en").
                        }}
                    }}""".format(p)
            cursor.execute("SPARQL "+query)
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                if row.itemLabel != None:
                    item_label = row.itemLabel
                    if len(item_label.split(" ")) == 1:
                        item_id = row.item
                        if item_label not in entities:
                            item_id_list = [item_id]
                            entities[item_label] = item_id_list
                        else:
                            item_id_list = entities[item_label]
                            if item_id not in item_id_list:
                                item_id_list.append(item_id)
        except Exception as e:
            print(e)
            continue
    #open a txt-file to save the data
    print("open file...")
    if os.path.exists("dictio_label_id.json"):
       os.remove("dictio_label_id.json")
    file = open("dictio_label_id.json", "w")
    for label in entities:
        temp = {}
        temp[label] = entities[label]
        json.dump(temp, file)
        file.write("\n")
    file.close()
    print("...result written to txt :)")

if __name__ == '__main__':
    main()

