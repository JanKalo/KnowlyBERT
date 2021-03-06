import os
import sys
import json

from argparse import ArgumentParser


# insert path to emnlp2017-relation-extraction repository code here
sys.path.insert(0, "emnlp2017-relation-extraction/")


from relation_extraction.core import keras_models
from relation_extraction.core.parser import RelParser


# init keras_models and relparser
keras_models.model_params['wordembeddings'] = (
        "/data/ehler/emnlp2017-relation-extraction/glove/glove.6B.50d.txt"
        )
relparser = RelParser(
        "model_ContextWeighted",
        models_folder=(
            "/data/ehler/emnlp2017-relation-extraction/trainedmodels/"
            )
        )


def tokenize(sentence):
    # remove some symbols and split by whitespace
    # (as simple as possible)
    tokens = sentence.replace(".", "")
    tokens = tokens.replace(",", "")
    tokens = tokens.replace("-", "")
    tokens = tokens.replace(":", "")
    tokens = tokens.replace(";", "")
    tokens = tokens.replace("?", "")
    tokens = tokens.replace("!", "")
    tokens = tokens.replace("\"", "")
    tokens = tokens.replace("'", "")
    tokens = tokens.replace("(", "")
    tokens = tokens.replace(")", "")
    tokens = tokens.replace("=", "")
    tokens = tokens.replace("{", "")
    tokens = tokens.replace("}", "")
    tokens = tokens.replace("<", "")
    tokens = tokens.replace(">", "")
    tokens = tokens.replace("/", "")
    tokens = tokens.replace("\\", "")
    tokens = tokens.split(" ")
    return tokens


def generate_contextweighted_input(tokens, entity_uri_mask):
    # generate edgeSet's by combining every possible entity pair,
    # contextweighted2017 style
    edges = []

    # left side loop
    for i, e1 in enumerate(entity_uri_mask):
        # skip token that we had in an iteration before
        # because we already handled multitoken entites
        # at this point
        if i > 0 and e1 == entity_uri_mask[i - 1]:
            continue

        # skip non-masked token
        if e1 is None:
            continue

        # right side loop
        left = [i]
        left_complete = False
        last_right = 0
        for j, e2 in enumerate(entity_uri_mask[i + 1:]):
            # build left side and check if current right is the same
            # which means it is a multitoken entity and belongs to left side
            if not left_complete and e1 == e2:
                left.append(j + i + 1)
                continue
            left_complete = True

            # skip non-masked token and reset left side
            if e2 is None:
                continue

            # skip if we have an already processed multitoken in right side
            if last_right > j + i + 1:
                continue

            # build right side in the same way
            right = [j + i + 1]
            last_right = j + i + 1 + 1
            while (
                    last_right < len(entity_uri_mask) and
                    e2 == entity_uri_mask[last_right]
                    ):
                right.append(last_right)
                last_right += 1

            # append edge
            edges.append({
                "left": left,
                "right": right
                })

    # return input for contextweighted2017 code
    return {
            "tokens": tokens,
            "edgeSet": edges
            }


def classify_inputs(relparser, contextweighted_inputs):
    return relparser.classify_graph_relations(contextweighted_inputs)


def get_triples(contextweighted_outputs, entity_uri_masks):
    # process every edge and get wikidata uris
    # with the help of entity_uri_mask
    triples = []
    for i, contextweighted_output in enumerate(contextweighted_outputs):
        for edge in contextweighted_output["edgeSet"]:
            # check if edge is not P0 (placeholder)
            p = edge["kbID"]
            if p == "P0":
                continue

            # get atoms
            p = "http://www.wikidata.org/prop/direct/" + p
            s = entity_uri_masks[i][edge["left"][0]]
            o = entity_uri_masks[i][edge["right"][0]]

            # add triple
            triples.append({"s": s, "p": p, "o": o})

    # done
    return triples


def process_abstract(abstract):
    # process sentences
    text = abstract["text"]
    contextweighted_inputs = []
    entity_uri_masks = []
    for sent_b in abstract["sentences_boundaries"]:
        # prepare sentence and tokens with a entitymask
        # annotating entities in tokens
        # with the corresponding wikidata uris
        sentence = text[sent_b[0]:sent_b[1]]
        tokens = tokenize(sentence)
        entity_uri_mask = [None] * len(tokens)

        # fill in the entitymask with every entities' uri
        for entity in abstract["entities"]:
            # skip entities which are not wikidata entities
            if not entity["uri"].startswith("http://www.wikidata.org/entity/"):
                continue

            # skip also entities which are out of bounds
            if (
                    entity["boundaries"][0] < sent_b[0] or
                    entity["boundaries"][0] >= sent_b[1]
                    ):
                continue

            # get number of entity tokens (split by whitespace)
            num_entity_tokens = len(tokenize(text[
                entity["boundaries"][0]:entity["boundaries"][1]
                ]))

            # count tokens from beginning of sentence
            # to left entity boundary to determine where
            # the first entity token is located and mark
            # as many consecutive tokens as there are entity tokens
            idx_first_ent_token = len(tokenize(text[
                sent_b[0]:entity["boundaries"][0]
                ])) - 1

            # annotate entity tokens in entitymask using
            # the wikidata entity ids foreach entity token
            for i in range(0, num_entity_tokens):
                if idx_first_ent_token + i < len(entity_uri_mask):
                    entity_uri_mask[idx_first_ent_token + i] = entity["uri"]
                elif i > 0:
                    print(
                            "WARNING: Cannot properly mask "
                            "multitoken entity, skipping this one ... "
                            )
                else:
                    raise IndexError()

        # generate contextweighted2017 input and add it to inputs list
        # also add entity_uri_mask to masks list
        contextweighted_inputs.append(
                generate_contextweighted_input(tokens, entity_uri_mask)
                )
        entity_uri_masks.append(entity_uri_mask)

    # return contextweighted inputs and entity uri masks
    # (classify and get triples later)
    return contextweighted_inputs, entity_uri_masks


def sample_file(fn, sample):
    # parse file
    with open(fn, "r") as f:
        jsonf = json.load(f)

    # go through every abstract ...
    for abstract in jsonf:

        # ... and get contextweighted inputs and entity uri masks
        contextweighted_inputs, entity_uri_masks = process_abstract(abstract)

        # combine
        sample["contextweighted_inputs"] += contextweighted_inputs
        sample["entity_uri_masks"] += entity_uri_masks

    # done for file fn
    return sample


def sample_files_p(fns):
    sample = {}
    sample["contextweighted_inputs"] = []
    sample["entity_uri_masks"] = []

    # sample each file
    for fn in fns:
        print("INFO: Sampling {0} ...".format(fn))
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
            "-b", "--batch-count", type=int, default=4,
            help=(
                "The number of batches to use for sampling. "
                "(Default: 4)"
                )
            )
    args = parser.parse_args()

    # check arguments
    if (args.batch_count < 1):
        sys.exit("ERROR: Invalid value for --batch-count")

    # check files
    for fn in args.FILES:
        if not os.path.isfile(fn):
            sys.exit("ERROR: {0} is not a file".format(fn))

    # init batched sampling of contextweighted2017 inputs and entity uri masks
    triples = []
    for b in range(0, args.batch_count):
        fns_b = [
                args.FILES[i]
                for i in range(b, len(args.FILES), args.batch_count)
                ]

        # sample this batch
        sample = sample_files_p(fns_b)

        # classify with contextweighted2017 and get triples
        print("INFO: Contextweighted2017: Classifying ...")
        classify_inputs(relparser, sample["contextweighted_inputs"])
        print("INFO: Getting triples ...")
        triples += get_triples(
                sample["contextweighted_inputs"],
                sample["entity_uri_masks"]
                )

    # save triple .nt file with triples from sample
    output_fn = "ContextWeighted2017.nt"
    print("INFO: Saving triples to {0} ...".format(output_fn))
    with open(output_fn, "w") as f:
        for triple in triples:
            f.write("<{0}> <{1}> <{2}> .\n".format(
                triple["s"],
                triple["p"],
                triple["o"]
                ))


if __name__ == "__main__":
    main()
