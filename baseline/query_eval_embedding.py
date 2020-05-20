import os
import sys
import json

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
            "-t", "--max-threshold", type=float, default=0.0
            )
    parser.add_argument(
            "-f", "--batch-count", type=int, default=100
            )
    args = parser.parse_args()

    # check arguments
    if not os.path.isdir(args.BENCHMARK_DIR):
        sys.exit("ERROR: Specified benchmark directory does not exist")
    if not os.path.isdir(args.EMBEDDING_DIR):
        sys.exit("ERROR: Specified embedding directory does not exist")

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

            # get relevant ids in embedding
            test_atom = "s" if query_atoms[query]["s"] != "?" else "o"
            predict_ent_range = list(range(0, emb.con.get_ent_total()))
            predict_test_ent_range = [
                    emb.lookup_ent_id(query_atoms[query][test_atom])
                    ] * emb.con.get_ent_total()
            predict_test_rel_range = [
                    emb.lookup_rel_id(query_atoms[query]["p"])
                    ] * emb.con.get_ent_total()

            # skip if atoms are unknown to embedding
            if (
                    None in predict_test_ent_range or
                    None in predict_test_rel_range
                    ):
                continue

            # batched prediction
            batch_size = emb.con.get_ent_total() // args.batch_count
            for batch in tqdm(
                    range(0, emb.con.get_ent_total(), batch_size),
                    desc="INFO: Batch"
                    ):
                batch_end = batch + batch_size
                if test_atom == "s":
                    predictions = emb.get_predict(
                            predict_test_ent_range[batch:batch_end],
                            predict_ent_range[batch:batch_end],
                            predict_test_rel_range[batch:batch_end]
                            )
                else:
                    predictions = emb.get_predict(
                            predict_ent_range[batch:batch_end],
                            predict_test_ent_range[batch:batch_end],
                            predict_test_rel_range[batch:batch_end]
                            )

                # threshold "correct" triples
                query_empty = True
                for i, prediction in enumerate(predictions):
                    if prediction <= args.max_threshold:
                        query_results[query].append(
                                emb.lookup_entity(predict_ent_range[batch + i])
                                )
                        num_predictions += 1
                        query_empty = False
                if query_empty:
                    num_empty_queries += 1

            # print #predictions #empty_queries in postfix just for more info
            t.set_postfix_str(
                    "#Predictions: {0}, #Empty Queries: {1}"
                    .format(num_predictions, num_empty_queries)
                    )

    # save results
    sys.stdout.write("INFO: Saving results ...")
    sys.stdout.flush()
    results_fn = (
            os.path.basename(os.path.normpath(args.EMBEDDING_DIR))
            + "_max-t_{0:.4f}.json".format(args.max_threshold)
            )
    with open(results_fn, "w") as f:
        json.dump(query_results, f, indent=4)
    print(" done")


if __name__ == "__main__":
    main()
