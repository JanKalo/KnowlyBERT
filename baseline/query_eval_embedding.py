import os
import sys
import json
import pickle

import numpy as np

from argparse import ArgumentParser
from tqdm import tqdm

import query_eval


# insert path to RelAlign repository code here
sys.path.insert(0, "/home/ehler/Documents/GitHub/RelAlign")


from thirdParty.OpenKE import models
from embedding import Embedding


embedding_models = {
        "TransE": models.TransE,
        "HolE": models.HolE
        }


def get_classes(
        entity_class_pickle,
        subclass_dict_pickle,
        prop_class_json
        ):
    # create a dictionary which contains the class
    # and its next superclass for each entity
    # and also a dictionary which contains the expected
    # classes for each relation
    # to perform a type constrained query evaluation
    # in the query evaluation loop
    # get entity classes dictionary
    ents_classes = {}
    with open(entity_class_pickle, "rb") as f:
        ec = pickle.load(f)
    with open(subclass_dict_pickle, "rb") as f:
        sc = pickle.load(f)
    ent_format = "http://www.wikidata.org/entity/{0}"
    for ent in ec:
        classes = set()
        for c in ec[ent]:
            classes.add(c)
            if c in sc:
                classes = classes.union(sc[c])
        classes = set(map(lambda x: ent_format.format(x), classes))
        ents_classes[ent_format.format(ent)] = classes

    # get relation classes dictionary
    with open(prop_class_json, "r") as f:
        lines = f.readlines()
    lines = list(map(lambda x: json.loads(x), lines))
    rel_format = "http://www.wikidata.org/prop/direct/{0}"
    rels_classes = {
            rel_format.format(rel): classes
            for line in lines
            for rel, classes in line.items()
            }

    # done
    return ents_classes, rels_classes


def main():
    # parse arguments
    parser = ArgumentParser()
    parser.add_argument(
            "BENCHMARK_DIR", type=str
            )
    parser.add_argument(
            "EMBEDDING_DIR", type=str
            )
    parser.add_argument(
            "MODEL", type=str, choices=embedding_models.keys()
            )
    parser.add_argument(
            "-d", "--embedding-dimensions", type=int, default=100
            )
    parser.add_argument(
            "-f", "--batch-count", type=int, default=100
            )
    parser.add_argument(
            "-k", "--top-k", type=int, default=100000
            )
    parser.add_argument(
            "-t", "--max-threshold", type=float, default=-1.0
            )
    parser.add_argument(
            "-c", "--entity-class-pickle", type=str, default=None
            )
    parser.add_argument(
            "-s", "--subclass-dict-pickle", type=str, default=None
            )
    parser.add_argument(
            "-p", "--prop-class-json", type=str, default=None
            )
    args = parser.parse_args()

    # check arguments
    if not os.path.isdir(args.BENCHMARK_DIR):
        sys.exit("ERROR: Specified benchmark directory does not exist")
    if not os.path.isdir(args.EMBEDDING_DIR):
        sys.exit("ERROR: Specified embedding directory does not exist")
    classes_available = True
    if (
            args.entity_class_pickle is None or
            args.subclass_dict_pickle is None or
            args.prop_class_json is None or
            not os.path.isfile(args.entity_class_pickle) or
            not os.path.isfile(args.subclass_dict_pickle) or
            not os.path.isfile(args.prop_class_json)
            ):
        print(
                "WARN: No valid entity_class, subclass "
                "or relation class dictionaries "
                "specified, continuing without type constraints"
                )
        classes_available = False

    # read queries
    query_map, query_propmap, query_atoms, _, _ = (
            query_eval.read_stdin_queries()
            )

    # load embedding
    emb = Embedding(
            args.BENCHMARK_DIR,
            args.EMBEDDING_DIR,
            embedding_models[args.MODEL],
            args.embedding_dimensions
            )

    # get the entity and relation classes
    # for type constraints in query evaluation
    # (if available)
    if classes_available:
        sys.stdout.write("INFO: Loading classes ...")
        sys.stdout.flush()
        ents_classes, rels_classes = get_classes(
                args.entity_class_pickle,
                args.subclass_dict_pickle,
                args.prop_class_json
                )
        print(" done")

    # for each query, get answers from embedding
    query_results = {}
    num_predictions = 0
    num_empty_queries = 0
    with tqdm(query_map, desc="INFO: Answering queries") as t:
        for query in t:
            query_results[query] = []

            # some assertions
            assert (
                    query_atoms[query]["s"] == "?" or
                    query_atoms[query]["o"] == "?"
                    )
            assert (
                    query_atoms[query]["s"] != "?" or
                    query_atoms[query]["o"] != "?"
                    )

            # get ids of all entities in embedding and in the query
            test_atom = "s" if query_atoms[query]["s"] != "?" else "o"
            rel_uri = query_atoms[query]["p"]
            rel_id = emb.lookup_rel_id(rel_uri)
            test_ent_uri = query_atoms[query][test_atom]
            test_ent_id = emb.lookup_ent_id(test_ent_uri)

            # skip if atoms are unknown to embedding
            if rel_id is None or test_ent_id is None:
                continue

            # filter entities to match only the expected classes of
            # the target relation (if classes available)
            predict_ent_range = list(range(0, emb.con.get_ent_total()))
            if classes_available:
                # checks if entities satisfy the expected classes
                # for the head ("?PQ") or tail ("QP?") position
                # of a relation
                def satisfies_classes(ent_uri, rel_uri, position):
                    # if there are no classes defined for the
                    # entity and relation provided, just return false
                    if (
                            ent_uri not in ents_classes or
                            rel_uri not in rels_classes
                            ):
                        return False

                    # determine satisfaction by set intersection
                    ent_classes = ents_classes[ent_uri]
                    rel_classes = set(
                            rels_classes[rel_uri][position].keys()
                            )
                    return len(ent_classes.intersection(rel_classes)) != 0

                # filter entity range to predict by the relations
                # expected classes
                predict_ent_range = list(filter(
                    lambda x: satisfies_classes(
                        emb.lookup_entity(x).lstrip("<").rstrip(">"),
                        rel_uri,
                        "QP?" if test_atom == "s" else "?PQ"
                        ),
                    predict_ent_range
                    ))

            # skip if there are no entities in range to predict
            if len(predict_ent_range) == 0:
                continue

            # create test ranges
            predict_test_rel_range = [rel_id] * len(predict_ent_range)
            predict_test_ent_range = [test_ent_id] * len(predict_ent_range)

            # batched prediction
            batch_size = -(-len(predict_ent_range) // args.batch_count)
            query_empty = True
            predictions = []
            for batch in tqdm(
                    range(0, len(predict_ent_range), batch_size),
                    desc="INFO: Batch"
                    ):
                batch_end = batch + batch_size
                if test_atom == "s":
                    predictions = np.concatenate([predictions, emb.get_predict(
                            predict_test_ent_range[batch:batch_end],
                            predict_ent_range[batch:batch_end],
                            predict_test_rel_range[batch:batch_end]
                            )])
                else:
                    predictions = np.concatenate([predictions, emb.get_predict(
                            predict_ent_range[batch:batch_end],
                            predict_test_ent_range[batch:batch_end],
                            predict_test_rel_range[batch:batch_end]
                            )])

            # if the predict_ent_range was filtered by type constraints,
            # reconstruct the original shape for later argsort
            # (this works because the range was sorted from 0 to #entities)
            if classes_available:
                predictions_orig = []
                predict_ent_range_set = set(predict_ent_range)
                predictions_idx = 0
                for i in range(0, emb.con.get_ent_total()):
                    # check if index is in the predict_ent_range
                    if i in predict_ent_range_set:
                        predictions_orig += [predictions[predictions_idx]]
                        predictions_idx += 1
                    else:
                        predictions_orig += [sys.maxsize]
            else:
                predictions_orig = predictions

            # get topk triples
            def argsort_thresh(x):
                idx = np.arange(x.size)[x <= args.max_threshold]
                return idx[np.argsort(x[idx])]
            topk_triples = list(map(
                lambda x: emb.lookup_entity(x).lstrip("<").rstrip(">"),
                argsort_thresh(predictions_orig.reshape(-1))[:args.top_k]
                ))
            query_results[query] = topk_triples

            # print #predictions #empty_queries in postfix just for more info
            if len(topk_triples) > 0:
                num_predictions += len(topk_triples)
                query_empty = False
            if query_empty:
                num_empty_queries += 1
            t.set_postfix_str(
                    "#Predictions: {0}, #Empty Queries: {1}"
                    .format(num_predictions, num_empty_queries)
                    )

    # save results
    sys.stdout.write("INFO: Saving results ...")
    sys.stdout.flush()
    results_fn = (
            os.path.basename(os.path.normpath(args.EMBEDDING_DIR))
            + "_top-k_{0}_max-t_{1:.4f}{2}.json".format(
                args.top_k,
                args.max_threshold,
                "_constrained" if classes_available else ""
                )
            )
    with open(results_fn, "w") as f:
        json.dump(query_results, f, indent=4)
    print(" done")


if __name__ == "__main__":
    main()
