import os
import sys
import json

from argparse import ArgumentParser
from tqdm import tqdm


def read_stdin_queries():
    # read from stdin and format queries
    sys.stdout.write("INFO: reading queries from STDIN ...")
    sys.stdout.flush()
    queries = sys.stdin.readlines()
    queries = list(map(lambda x: x[:-1], queries))
    queries = list(filter(lambda x: x != "", queries))
    query_map = {i: query for i, query in enumerate(queries)}
    query_atoms = list(map(
        lambda x: {
            {0: "s", 1: "p", 2: "o"}[i]: atom.lstrip("<").rstrip(">")
            for i, atom in enumerate(query_map[x].split()[:3])
            }, query_map
        ))
    query_atoms = {i: atoms for i, atoms in enumerate(query_atoms)}

    # build query property map (relevant for evaluation_per_relation)
    query_propmap = {}
    for query in query_map:
        if query_atoms[query]["p"] not in query_propmap:
            query_propmap[query_atoms[query]["p"]] = []
        query_propmap[query_atoms[query]["p"]].append(query)

    # query_map performs oid mapping for query strings
    # query_atoms maps query oids to the corresponding queries' atoms
    # query_propmap is a dict mapping properties to its queries
    print(" {0} queries".format(len(query_map)))

    # check if query_map & query_propmap already exist
    # compare the map with currently read queries
    # if they are NOT the same, STOP and inform user to delete existing files
    if (
            os.path.isfile("query_map.json") and
            os.path.isfile("query_propmap.json")
            ):
        same = True

        # check query_map
        with open("query_map.json", "r") as f:
            query_map_existing = json.load(f)
        query_map_existing = {
                int(k): v
                for k, v in query_map_existing.items()
                }
        same = query_map == query_map_existing

        # check query_propmap
        with open("query_propmap.json", "r") as f:
            query_propmap_existing = json.load(f)
        query_propmap_existing = {
                k: v
                for k, v in query_propmap_existing.items()
                }
        same = query_propmap == query_propmap_existing

        # stop if necessary
        if not same:
            sys.exit(
                    "ERROR: existing query_map.json or query_propmap.json "
                    "are NOT from the same queries as currently read in. "
                    "Please remove these files manually to continue."
                    )
    else:
        # not existing - create them
        with open("query_map.json", "w") as f:
            json.dump(query_map, f, indent=4)
        with open("query_propmap.json", "w") as f:
            json.dump(query_propmap, f, indent=4)

    # done
    return query_map, query_atoms, query_propmap


def load_nt(fn):
    # load triples list
    sys.stdout.write("INFO: reading triples from {0} ...".format(fn))
    sys.stdout.flush()
    with open(fn, "r") as f:
        triples = f.readlines()
        triples = list(map(
            lambda x: {
                {0: "s", 1: "p", 2: "o"}[i]: atom.lstrip("<").rstrip(">")
                for i, atom in enumerate(x.split()[:3])
                }, triples
            ))
    print(" {0} triples".format(len(triples)))

    # build index for properties
    sys.stdout.write("INFO: building index for properties ...")
    sys.stdout.flush()
    p_index = {}
    for i, triple in enumerate(triples):
        if triple["p"] not in p_index:
            p_index[triple["p"]] = []
        p_index[triple["p"]].append(i)
    print(" {0} properties".format(len(p_index)))

    # done
    return triples, p_index


def main():
    # parse arguments
    parser = ArgumentParser()
    parser.add_argument(
            "NT_FILE", type=str,
            help="The .nt file to ask queries to from STDIN"
            )
    args = parser.parse_args()

    # check arguments
    if not os.path.isfile(args.NT_FILE):
        sys.exit("ERROR: specified .nt file does not exist")

    # read queries
    query_map, query_atoms, query_propmap = read_stdin_queries()

    # load .nt file
    triples, p_index = load_nt(args.NT_FILE)

    # for each query, get answers from triples
    sys.stdout.write("INFO: answering queries ...")
    sys.stdout.flush()
    query_results = {}
    for query in tqdm(query_map, desc="answering queries"):
        # skip unknown properties
        query_results[query] = []
        if query_atoms[query]["p"] not in p_index:
            continue

        # some assertions
        assert query_atoms[query]["s"] == "?" or query_atoms[query]["o"] == "?"
        assert query_atoms[query]["s"] != "?" or query_atoms[query]["o"] != "?"

        # get answer
        test_atom = "s" if query_atoms[query]["s"] != "?" else "o"
        target_atom = "s" if test_atom == "o" else "o"
        for triple in p_index[query_atoms[query]["p"]]:
            assert query_atoms[query]["p"] == triples[triple]["p"]
            if query_atoms[query][test_atom] == triples[triple][test_atom]:
                query_results[query].append(triples[triple][target_atom])
    print(" done")

    # save results
    sys.stdout.write("INFO: saving results ...")
    sys.stdout.flush()
    results_fn = os.path.splitext(os.path.basename(args.NT_FILE))[0] + ".json"
    with open(results_fn, "w") as f:
        json.dump(query_results, f, indent=4)
    print(" done")


if __name__ == "__main__":
    main()
