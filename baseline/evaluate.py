import os
import sys
import json

import numpy as np
import matplotlib.pyplot as plt

from argparse import ArgumentParser


def get_entity_ids(entity_uris):
    # trim wikidata entity uri prefix
    # from each entity in list
    # and return as set
    entity_ids = set(map(
        lambda entity_uri:
        entity_uri.lstrip("http://www.wikidata.org/entity/"),
        entity_uris
        ))
    return entity_ids


def load_query_results(fn):
    # load query results
    sys.stdout.write("INFO: Reading query results {0} ...".format(fn))
    sys.stdout.flush()
    with open(fn, "r") as f:
        query_results = json.load(f)
        query_results = {
                int(k): get_entity_ids(v)
                for k, v in query_results.items()
                }
    print(" results for {0} queries read".format(len(query_results)))

    # done
    return query_results


def load_query_results_map(results_files):
    query_results_map = {}
    for results_file in results_files:
        # load results file
        query_results = load_query_results(results_file)

        # get basename without extension as dataset description for dict
        dataset = os.path.splitext(
                os.path.basename(results_file)
                )[0]

        # add to map
        query_results_map[dataset] = query_results

    # done
    return query_results_map


def load_query_propmap(fn):
    # load query property map for evaluation_per_relation
    with open(fn, "r") as f:
        query_propmap = json.load(f)
    return query_propmap


def load_query_groups(fn):
    # load query groups
    with open(fn, "r") as f:
        query_groups = json.load(f)
    return query_groups


def prec(gold, test, missing):
    # subtract gold and test with missing
    gold_m = gold.difference(missing)
    test_m = test.difference(missing)

    # get precision
    return (
            float(len(gold_m.intersection(test_m))) /
            float(len(test_m))
            ) if len(test_m) > 0 else 1.0


def rec(gold, test, missing):
    # subtract gold and test with missing
    gold_m = gold.difference(missing)
    test_m = test.difference(missing)

    # get recall
    return (
            float(len(gold_m.intersection(test_m))) /
            float(len(gold_m))
            ) if len(gold_m) > 0 else 1.0


def evaluation_per_query(
        gold_dataset,
        query_results,
        missing_data=None
        ):
    # assert
    assert missing_data is None or len(gold_dataset) == len(missing_data)
    assert len(gold_dataset) == len(query_results)

    # evaluate precision & recall per query
    # combine each query result with its corresponding missing_data result
    # if missing_data is given
    per_query = {}
    avg_prec = 0.0
    avg_rec = 0.0
    num_nonempty_query_results = 0
    for query_result in gold_dataset:
        # subtract results with missing_data results if given
        test = set.difference(
                query_results[query_result],
                missing_data[query_result]
                if missing_data is not None else set()
                )

        # get precision & recall values ONLY for non-empty
        # difference of results and missing_data
        per_query[query_result] = {}
        if len(test) > 0:
            num_nonempty_query_results += 1

            # calculate if non-empty result set
            per_query[query_result]["precision"] = prec(
                    gold_dataset[query_result],
                    test,
                    missing_data[query_result]
                    if missing_data is not None else set()
                    )
            per_query[query_result]["recall"] = rec(
                    gold_dataset[query_result],
                    test,
                    missing_data[query_result]
                    if missing_data is not None else set()
                    )

            # sum up precision & recall values to get the average later
            avg_prec += per_query[query_result]["precision"]
            avg_rec += per_query[query_result]["recall"]
        else:
            # set both to 0 if empty result
            per_query[query_result]["precision"] = 0.0
            per_query[query_result]["recall"] = 0.0

    # get average precision (weighted by #non-empty queries)
    # and recall (weighted by total queries)
    avg_prec /= num_nonempty_query_results
    avg_rec /= len(per_query.keys())

    # done
    return per_query, avg_prec, avg_rec


def evaluation_per_relation(
        gold_dataset,
        query_propmap,
        query_results,
        missing_data=None
        ):
    # assert
    assert missing_data is None or len(gold_dataset) == len(missing_data)
    assert len(gold_dataset) == len(query_results)

    # evaluate AVERAGE precision & recall per relation in query_propmap
    # combine each query result with its corresponding missing_data result
    # if missing_data is given
    per_relation = {}
    avg_prec = 0.0
    avg_rec = 0.0
    for prop in query_propmap:
        # sum up values for each query result
        num_queries = 0
        num_nonempty_query_results = 0
        for query_result in query_propmap[prop]:
            # skip this result if it is not in results
            # (could happen with query groups)
            # just assume that every dataset should have
            # or not have a specific query result all together
            if (
                    query_result not in gold_dataset and
                    query_result not in missing_data and
                    query_result not in query_results
                    ):
                continue
            else:
                num_queries += 1

            # initialize if not done yet
            if prop not in per_relation:
                per_relation[prop] = {}
                per_relation[prop]["precision"] = 0.0
                per_relation[prop]["recall"] = 0.0

            # subtract results with missing_data results if given
            test = set.difference(
                    query_results[query_result],
                    missing_data[query_result]
                    if missing_data is not None else set()
                    )

            # sum up precision & recall values ONLY for non-empty
            # difference of results and missing_data
            if len(test) > 0:
                num_nonempty_query_results += 1

                # calculate if non-empty result set
                per_relation[prop]["precision"] += prec(
                        gold_dataset[query_result],
                        test,
                        missing_data[query_result]
                        if missing_data is not None else set()
                        )
                per_relation[prop]["recall"] += rec(
                        gold_dataset[query_result],
                        test,
                        missing_data[query_result]
                        if missing_data is not None else set()
                        )

        # only when there were precision / recall values
        if prop in per_relation:
            # divide by number of query results for current property
            # to get the AVERAGE precision & recall
            if num_nonempty_query_results > 0:
                per_relation[prop]["precision"] /= num_nonempty_query_results
            per_relation[prop]["recall"] /= num_queries

            # sum up precision & recall values to get the average later
            avg_prec += per_relation[prop]["precision"]
            avg_rec += per_relation[prop]["recall"]

    # get average precision & recall
    if len(per_relation.keys()) > 0:
        avg_prec /= len(per_relation.keys())
        avg_rec /= len(per_relation.keys())

    # done
    return per_relation, avg_prec, avg_rec


def plot_evaluation(
        evaluation,
        output_fn_prefix,
        eval_type,
        metric,
        diff_data=None
        ):
    # prepare
    plt.clf()
    plt.xlim([-0.1, 1.1])
    plt.xticks(np.arange(0.0, 1.1, 0.1))
    if metric == "precision":
        plt.xlabel("PRECISION")
    elif metric == "recall":
        plt.xlabel("RECALL")
    else:
        raise ValueError(
                "ERROR: Invalid metric value "
                "(use one of {\"precision\", \"recall\"})"
                )
    if eval_type == "per_query":
        if diff_data is None:
            plt.ylabel("QUERIES")
        else:
            plt.ylabel("QUERIES-DIFF")
    elif eval_type == "per_relation":
        if diff_data is None:
            plt.ylabel("RELATIONS")
        else:
            plt.ylabel("RELATIONS-DIFF")
    else:
        raise ValueError(
                "ERROR: Invalid eval_type value "
                "(use one of {\"per_query\", \"per_relation\"})"
                )

    # get values for each dataset
    datasets = {
            k: list(map(
                lambda x: v[eval_type][x][metric],
                v[eval_type]
                ))
            for k, v in evaluation.items()
            }
    labels = []
    colors = [
            "#000000",
            "#505050",
            "#A0A0A0",
            "#FFA0A0",
            "#FF5050",
            "#FF0000",
            "#A0A0FF",
            "#5050FF",
            "#0000FF",
            "#FFA0FF",
            "#FF50FF",
            "#FF00FF"
            ]
    values = []
    for dataset in datasets:
        labels.append(dataset)
        values.append(datasets[dataset])

    # prepare diff_data if specified
    if diff_data is not None:
        diff_data_idx = labels.index(diff_data)
        diff_data_values = values[diff_data_idx]
        labels = labels[:diff_data_idx] + values[diff_data_idx + 1:]
        values = values[:diff_data_idx] + values[diff_data_idx + 1:]
        diff_data_hgram_y, _ = np.histogram(
                diff_data_values,
                bins=np.arange(0.0, 1.2, 0.1),
                range=(0.0, 1.0)
                )

    # calculate histograms for each dataset
    bar_width = 0.08
    subbar_width = bar_width / len(labels)
    hgrams = []
    for i in range(0, len(labels)):
        hgram_y, hgram_x = np.histogram(
                values[i],
                bins=np.arange(0.0, 1.2, 0.1),
                range=(0.0, 1.0)
                )

        # subtract by diff_data if specified
        if diff_data is not None:
            hgram_y -= diff_data_hgram_y

        # shift succeeding bars and center all to ticks
        hgram_x += subbar_width * i
        hgram_x -= bar_width / 2.0

        # add
        hgrams.append((hgram_y, hgram_x))

    # plot
    for i, (hgram_y, hgram_x) in enumerate(hgrams):
        plt.bar(
                hgram_x[:-1],
                hgram_y,
                width=subbar_width,
                align="edge",
                edgecolor="black",
                color=colors[i],
                label=labels[i],
                zorder=3
                )

    # legend
    plt.axhline(color="black")
    plt.grid(zorder=0)
    plt.legend()
    plt.savefig("{0}_{1}_{2}.pdf".format(output_fn_prefix, eval_type, metric))


def evaluate(
        query_results_map,
        query_propmap,
        gold_dataset,
        missing_data,
        output_fn_prefix
        ):
    # evaluate each results_file
    print("INFO: Running {0} ({1} queries) ...".format(
        output_fn_prefix, len(gold_dataset)
        ))
    evaluation = {}
    for dataset in query_results_map:
        # evaluate
        query_results = query_results_map[dataset]
        per_query, per_query_avg_prec, per_query_avg_rec = (
                evaluation_per_query(
                    gold_dataset,
                    query_results,
                    missing_data
                    )
                )
        per_relation, per_relation_avg_prec, per_relation_avg_rec = (
                evaluation_per_relation(
                    gold_dataset,
                    query_propmap,
                    query_results,
                    missing_data
                    )
                )
        evaluation[dataset] = {
                "per_query": per_query,
                "per_query_avg_prec": per_query_avg_prec,
                "per_query_avg_rec": per_query_avg_rec,
                "per_relation": per_relation,
                "per_relation_avg_prec": per_relation_avg_prec,
                "per_relation_avg_rec": per_relation_avg_rec
                }

    # save evaluation
    print("INFO: Saving {0} ...".format(output_fn_prefix))
    with open(output_fn_prefix + ".json", "w") as f:
        json.dump(evaluation, f, indent=4)
    #plot_evaluation(evaluation, output_fn_prefix, "per_query", "precision")
    #plot_evaluation(evaluation, output_fn_prefix, "per_query", "recall")
    #plot_evaluation(evaluation, output_fn_prefix, "per_relation", "precision")
    #plot_evaluation(evaluation, output_fn_prefix, "per_relation", "recall")


def main():
    # parse arguments
    parser = ArgumentParser()
    parser.add_argument(
            "QUERY_PROPMAP_FILE", type=str,
            help="The query_propmap JSON file for evaluation_per_relation."
            )
    parser.add_argument(
            "GOLD_DATASET_FILE", type=str,
            help="The gold_dataset query results JSON file."
            )
    parser.add_argument(
            "RESULTS_FILES", nargs="+", type=str,
            help=(
                "The query results JSON files to evaluate. "
                "We'll use the files basename without extension "
                "as dataset description."
                )
            )
    parser.add_argument(
            "-m", "--missing-data", type=str, default=None,
            help=(
                "The missing_data query results JSON file. "
                "This will union these results with every query result. "
                "(Default: None)."
                )
            )
    parser.add_argument(
            "-g", "--query-groups", type=str, default=None,
            help=(
                "The query_groups JSON file containing a dict "
                "with query group names as keys and index lists "
                "of queries as values. (Default: None)."
                )
            )
    args = parser.parse_args()

    # check arguments
    if not os.path.isfile(args.QUERY_PROPMAP_FILE):
        sys.exit(
                "ERROR: Specified query_propmap '{0}' does not exist"
                .format(args.QUERY_PROPMAP_FILE)
                )
    if not os.path.isfile(args.GOLD_DATASET_FILE):
        sys.exit(
                "ERROR: Specified gold_dataset results '{0}' do not exist"
                .format(args.GOLD_DATASET_FILE)
                )
    if args.missing_data is not None:
        if not os.path.isfile(args.missing_data):
            sys.exit(
                    "ERROR: Specified missing_data results '{0}' do not exist"
                    .format(args.missing_data)
                    )
    else:
        print("INFO: No missing_data results specified, continuing without.")
    if args.query_groups is not None:
        if not os.path.isfile(args.query_groups):
            sys.exit(
                    "ERROR: Specified query_groups '{0}' does not exist"
                    .format(args.query_groups)
                    )
    else:
        print("INFO: No query_groups specified, using all as one group.")
    for results_file in args.RESULTS_FILES:
        if not os.path.exists(results_file):
            sys.exit(
                    "ERROR: Specified query results '{0}' do not exist"
                    .format(results_file)
                    )

    # load query property map
    query_propmap = load_query_propmap(args.QUERY_PROPMAP_FILE)

    # load gold_dataset and missing_data query results
    # and check if both have the same number of queries
    gold_dataset = load_query_results(args.GOLD_DATASET_FILE)
    if args.missing_data is not None:
        missing_data = load_query_results(args.missing_data)
    else:
        missing_data = None
    assert missing_data is None or len(gold_dataset) == len(missing_data)

    # load all query results and assert #queries
    results_files = []
    for entry in args.RESULTS_FILES:
        # load results file
        if os.path.isfile(entry):
            results_files.append(entry)
        else:
            path = entry
            for file in sorted(os.listdir(path)):
                results_files.append("{}{}".format(path, file))
    query_results_map = load_query_results_map(results_files)
    #for dataset in query_results_map:
    #    assert len(gold_dataset) == len(query_results_map[dataset])

    # evaluate query groups
    # or evaluate all queries
    if args.query_groups is not None:
        # for each query group one evaluation
        query_groups = load_query_groups(args.query_groups)
        for query_group in query_groups:
            # prepare datasets
            qg_gold_dataset = {
                    k: gold_dataset[k]
                    for k in query_groups[query_group]
                    }
            qg_missing_data = {
                    k: missing_data[k]
                    for k in query_groups[query_group]
                    }
            qg_query_results_map = {
                    dataset: {
                        k: query_results_map[dataset][k]
                        for k in query_groups[query_group]
                        }
                    for dataset in query_results_map
                    }

            # evaluate current query group
            evaluate(
                    qg_query_results_map,
                    query_propmap,
                    qg_gold_dataset,
                    qg_missing_data,
                    "evaluation_{0}".format(query_group)
                    )
    else:
        evaluate(
                query_results_map,
                query_propmap,
                gold_dataset,
                missing_data,
                "evaluation_all"
                )


if __name__ == "__main__":
    main()
