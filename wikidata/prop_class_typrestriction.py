from SPARQLWrapper import SPARQLWrapper, JSON
import json
import os
import time
import pyodbc
import numpy as np
#endpoit of server with database on it
sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
# Specifying the ODBC driver, server name, database, etc. directly
cnxn_current = pyodbc.connect('DSN=MyVirtuoso;UID=dba;PWD=F4B656JXqBG')
cnxn_current.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
cnxn_current.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')

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
    with cnxn_current:
        # Create a cursor from the connection
        cursor_current = cnxn_current.cursor()
        for p in props:
            print(p)
            if p == "P1376":
                prop = "P36"
                constraint_id = ["Q21510865", "Q21503250"]
            else:
                prop = p
                constraint_id = ["Q21503250", "Q21510865"]
            #QP? 
            sparql.setQuery("""SELECT ?class_
                            WHERE {{
                                <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/P2302> ?constraint_statement .
                                ?constraint_statement <http://www.wikidata.org/prop/statement/P2302> <http://www.wikidata.org/entity/{}> .
                                OPTIONAL {{?constraint_statement <http://www.wikidata.org/prop/qualifier/P2308> ?class_ .}}
                            }}""".format(prop, constraint_id[1]))
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            list_object = {}
            for r in results["results"]["bindings"]:
                res = r["class_"]["value"]
                query = """SELECT ?s
                            WHERE {{
                                ?s <http://www.wikidata.org/prop/direct/P279>+ <{}>.
                            }}""".format(res)
                cursor_current.execute("SPARQL "+query)
                while True:
                    row = cursor_current.fetchone()
                    if not row:
                        break
                    list_object[row.s] = res
            #?PQ
            sparql.setQuery("""SELECT ?class_
                            WHERE {{
                                <http://www.wikidata.org/entity/{}> <http://www.wikidata.org/prop/P2302> ?constraint_statement .
                                ?constraint_statement <http://www.wikidata.org/prop/statement/P2302> <http://www.wikidata.org/entity/{}> .
                                OPTIONAL {{?constraint_statement <http://www.wikidata.org/prop/qualifier/P2308> ?class_ .}}
                            }}""".format(prop, constraint_id[0]))
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            list_subject = {}
            for r in results["results"]["bindings"]:
                res = r["class_"]["value"]
                query = """SELECT ?s
                            WHERE {{
                                ?s <http://www.wikidata.org/prop/direct/P279>+ <{}>.
                            }}""".format(res)
                cursor_current.execute("SPARQL "+query)
                while True:
                    row = cursor_current.fetchone()
                    if not row:
                        break
                    list_subject[row.s] = res

            temp = {}
            temp["?PQ"] = list_subject
            temp["QP?"] = list_object
            dictio_classes[p] = temp
        #open a txt-file to save the data
        print("open file...")
        if os.path.exists("dictio_prop_class.json"):
            os.remove("dictio_prop_class.json")
        file = open("dictio_prop_class.json", "w")
        for prop in dictio_classes:
            temp = {}
            temp[prop] = dictio_classes[prop]
            json.dump(temp, file)
            file.write("\n")
        file.close()
        print("...result written to txt :)")

if __name__ == '__main__':
    main()