#parsing the label-ID-dictionary
entities = {}
dicto = open("dictio_label_id.txt", "r")
lines = dicto.read().split("']\n")
for line in lines:
    key_value = line.split(" ['")
    if(key_value != ['']):
        values = key_value[1].split("', '")
        list_values = []
        for v in values:
            if "http://www.wikidata.org/entity/Q" in v:
                list_values.append(v)
                entities[key_value[0]] = list_values
dicto.close()

test_label = "English"
#if test_label in entities:
#    print(entities[test_label])
#else:
#    print("label does not exist")

dictio = {}
dictio["haus"] = 7
dictio["daniel"] = 3
for k in dictio:
    print(k)
    print(dictio[k])