import math
#import sys
#sys.path.insert(1, "/home/fichtel/KnowliBERT/kb_embeddings/RelAlign/")
#from thirdParty.OpenKE import models
#from embedding import Embedding

#benchmark_dir = "/data/ehler/benchmarks/wikidata-20181221TN-1k_2000_50"
#embedding_dir = "/data/ehler/embeddings/embeddings/wikidata-20181221TN-1k_2000_50_transe"
#embedding_dir = "/data/ehler/embeddings/embeddings/wikidata-20181221TN-1k_2000_50_hole"

#emb = Embedding(benchmark_dir, embedding_dir, models.HolE, embedding_dimensions=100)

#function to get the loss to a given tripel
def get_loss(emb, tripel, entity):
    if tripel[0] == "?":
        subject_id = emb.lookup_ent_id("<http://www.wikidata.org/entity/{}>".format(entity))
        prop_id = emb.lookup_rel_id("<http://www.wikidata.org/prop/direct/{}>".format(tripel[1]))
        object_id = emb.lookup_ent_id("<http://www.wikidata.org/entity/{}>".format(tripel[2]))
        if subject_id and object_id and prop_id:
            return emb.get_predict([subject_id], [object_id], [prop_id])[0], None
        else:
            return None, "[WARNING] emp.lookup failed, subject:{}-->{}, prop:{}-->{}, object:{}-->{}".format(entity, subject_id, tripel[1], prop_id, tripel[2], object_id)
    elif tripel[2] == "?":
        subject_id = emb.lookup_ent_id("<http://www.wikidata.org/entity/{}>".format(tripel[0]))
        prop_id = emb.lookup_rel_id("<http://www.wikidata.org/prop/direct/{}>".format(tripel[1]))
        object_id = emb.lookup_ent_id("<http://www.wikidata.org/entity/{}>".format(entity))
        #print(subject_id)
        #print(prop_id)
        #print(object_id)
        #print(emb.lookup_entity(subject_id))
        #print(emb.lookup_relation(prop_id))
        #print(emb.lookup_entity(object_id))
        if subject_id and object_id and prop_id:
            return emb.get_predict([subject_id], [object_id], [prop_id])[0], None
        else:
            return None, "[WARNING] emp.lookup failed, subject:{}-->{}, prop:{}-->{}, object:{}-->{}".format(tripel[0], subject_id, tripel[1], prop_id, entity, object_id)
    else:
        return None, "[WARNING] wrong format of tripel"

#function to merch the LM log-probability and the loss of the kb embeddings
def calculate_probability(chosen_entity, dictio_entity_loss, log_prob):
    #loss of hole embedding is between [-1, 0] --> to have probability, make abs
    positive_loss = abs(dictio_entity_loss[chosen_entity])
    #LM log-probability --> to have probability, make exp
    probability = math.exp(log_prob)
    avg_prop = (positive_loss + probability) / 2
    #return log of avg probability
    return math.log(avg_prop)

#print(get_loss(emb, ['Q654957', 'P1412', '?'], "Q7976"))


    