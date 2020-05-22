import os
import sys
import json
import pickle

import numpy as np

from argparse import ArgumentParser
from tqdm import tqdm
from multiprocessing import Pool

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
            rel_format.format(rel): {
                position: set(map(
                    lambda x: ent_format.format(x),
                    classes.keys()
                    ))
                for position, classes in positions.items()
                }
            for line in lines
            for rel, positions in line.items()
            }

    # done
    return ents_classes, rels_classes


# unused, too slow
def satisfies_classes_idx_range_p(
        ents_classes_p, rel_classes,
        ent_uri_range, offset_p
        ):
    # checks if entities satisfy the expected classes
    # for the head ("?PQ") or tail ("QP?") position
    # of a relation and return the indexes of these
    # entities for a specific entity range

    # determine satisfaction by set intersection
    return [
            idx + offset_p for idx, ent_uri in enumerate(ent_uri_range)
            if (
                ent_uri in ents_classes_p and
                len(ents_classes_p[ent_uri].intersection(rel_classes)) != 0
                )
            ]


# unused, too slow
def satisfies_classes_idx_range_multiprocessed(
        ents_classes, rels_classes,
        ent_uri_range, rel_uri, position, processes
        ):
    # checks if entities satisfy the expected classes
    # for the head ("?PQ") or tail ("QP?") position
    # of a relation and return the indexes of these
    # entities multiprocessed

    # if there are no classes defined for the
    # relation provided, just return nothing
    if rel_uri not in rels_classes:
        return []

    # init sampling pool
    rel_classes = rels_classes[rel_uri][position]
    range_size_p = -(-len(ent_uri_range) // processes)
    ent_uri_range_p = [
            ent_uri_range[i:i + range_size_p]
            for i in range(0, len(ent_uri_range), range_size_p)
            ]
    results_p = []
    pool = Pool(processes=processes)
    for p in range(0, len(ent_uri_range_p)):
        ents_classes_p = {
                ent_uri: ents_classes[ent_uri]
                for ent_uri in ent_uri_range_p[p]
                if ent_uri in ents_classes
                }
        offset_p = p * range_size_p
        results_p.append(pool.apply_async(
            satisfies_classes_idx_range_p,
            [
                ents_classes_p, rel_classes,
                ent_uri_range_p[p], offset_p
                ]
            ))
    pool.close()
    pool.join()

    # get flattened results
    return [x for results in results_p for x in results.get()]


def satisfies_classes_idx_range(
        ents_classes, rels_classes,
        ent_uri_range, rel_uri, position
        ):
    # checks if entities satisfy the expected classes
    # for the head ("?PQ") or tail ("QP?") position
    # of a relation and return the indexes of these
    # entities

    # if there are no classes defined for the
    # relation provided, just return nothing
    if rel_uri not in rels_classes:
        return []

    # determine satisfaction by set intersection
    rel_classes = rels_classes[rel_uri][position]
    return [
            idx for idx, ent_uri in enumerate(ent_uri_range)
            if (
                ent_uri in ents_classes and
                len(ents_classes[ent_uri].intersection(rel_classes)) != 0
                )
            ]


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
        classes_available = False
        print(
                "WARN: No valid entity_class, subclass "
                "or relation class dictionaries "
                "specified, continuing without type constraints"
                )

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

    # get entity ranges
    sys.stdout.write("INFO: Getting entity ranges ...")
    sys.stdout.flush()
    ent_id_range = list(range(0, emb.con.get_ent_total()))
    ent_uri_range = list(map(
        lambda x: emb.lookup_entity(x).lstrip("<").rstrip(">"), ent_id_range
        ))
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
            if classes_available:
                # filter entity range to predict by the relations
                # expected classes
                # also keep track of the filtered indexes
                # to be able to assign the predicted values
                # correctly later
                predict_ent_range = satisfies_classes_idx_range(
                        ents_classes, rels_classes,
                        ent_uri_range, rel_uri,
                        "QP?" if test_atom == "s" else "?PQ"
                        )
                lookup_orig_idx = {
                        filtered_idx: orig_idx
                        for filtered_idx, orig_idx
                        in enumerate(predict_ent_range)
                        }
            else:
                predict_ent_range = ent_id_range

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

            # argsort predictions
            def argsort_thresh(x):
                idx = np.arange(x.size)[x <= args.max_threshold]
                return idx[np.argsort(x[idx])]
            topk_argsort = argsort_thresh(predictions.reshape(-1))[:args.top_k]

            # if it was filtered by types, get the original indexes
            if classes_available:
                topk_argsort = list(map(
                    lambda x: lookup_orig_idx[x], topk_argsort
                    ))

            # get topk entity result set
            topk_entities = list(map(
                lambda x: emb.lookup_entity(x).lstrip("<").rstrip(">"),
                topk_argsort
                ))
            query_results[query] = topk_entities

            # print #predictions #empty_queries in postfix just for more info
            if len(topk_entities) > 0:
                num_predictions += len(topk_entities)
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
