import os
import sys
import json

from argparse import ArgumentParser
from multiprocessing import Pool


def sample_file(fn, sample):
    # parse file
    with open(fn, "r") as f:
        jsonf = json.load(f)

    # go through every abstract ...
    for abstract in jsonf:

        # ... and add all its triples
        for triple in abstract["triples"]:
            annotator = triple["annotator"]
            s = triple["subject"]["uri"]
            p = triple["predicate"]["uri"]
            o = triple["object"]["uri"]
            triple = {"s": s, "p": p, "o": o}

            # add triple
            if annotator not in sample:
                sample[annotator] = []
            sample[annotator].append(triple)

    # done for file fn
    return sample


def sample_files_p(fns):
    sample = {}

    # sample each file
    for fn in fns:
        print("INFO: sampling {0} ...".format(fn))
        sample = sample_file(fn, sample)

    # done
    return sample


def main():
    # parse arguments
    parser = ArgumentParser()
    parser.add_argument(
            "FILES", nargs="+", type=str,
            help="The files to sample.")
    parser.add_argument(
            "-p", "--processes", type=int, default=4,
            help=(
                "The number of processes to use for sampling. "
                "(Default: 4)"
                )
            )
    args = parser.parse_args()

    # check arguments
    if (args.processes < 1):
        sys.exit("ERROR: invalid value for --processes")

    # check files
    for fn in args.FILES:
        if not os.path.isfile(fn):
            sys.exit("ERROR: {0} is not a file".format(fn))

    # init sampling pool
    pool = Pool(processes=args.processes)
    samples_p = []
    for p in range(0, args.processes):
        fns_p = [
                args.FILES[i]
                for i in range(p, len(args.FILES), args.processes)
                ]
        samples_p.append(pool.apply_async(sample_files_p, [fns_p]))
    pool.close()
    pool.join()

    # getting results
    print("INFO: getting results")
    samples_p = list(map(lambda x: x.get(), samples_p))
    annotators = list(map(lambda x: list(x.keys()), samples_p))
    annotators = set([ann for sublist in annotators for ann in sublist])

    # save triple .nt files for each annotator
    for ann in annotators:
        print("INFO: saving {0} triples ...".format(ann))
        with open(ann + ".nt", "w") as f:
            for sample in samples_p:
                for triple in sample[ann]:
                    f.write("<{0}> <{1}> <{2}> .\n".format(
                        triple["s"],
                        triple["p"],
                        triple["o"]
                        ))


if __name__ == "__main__":
    main()
