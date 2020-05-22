# /baseline/

This directory contains all code to create our baseline datasets and to evaluate the performance of a given systems' result.

To create our baseline datasets, we considered [the **T-REx** Natural Language Alignment with Knowledge Base Triples][1] and [Context-Aware Representations for Knowledge Base Relation Extraction][3].
See the links to get the data necessary for this code to run.

## Preparing data

### **TREx** data

We need the **full** **TREx** data containing all processed Wikipedia abstracts in **JSON** format.
The data is available [here][2].

### Context-Aware Representations code

Furthermore, we need [this][3] code to create our `ContextWeighted2017` dataset.
We assume that everything is set up in a folder called `emnlp2017-relation-extraction`.

## Sample `ContextWeighted2017` Triples

We have two scripts provided to create our ContextWeighted2017.nt.
`TREx/sample_contextweighted_parallel.py` will compute batches in parallel but will consume a lot of memory for better performance.
`TREx/sample_contextweighted_batched.py` is more balanced w.r.t. memory consumption and performance.

**IMPORTANT**: Please insert the path to the `emnlp2017-relation-extraction` folder and to the GloVe embeddings and the keras model at the beginning of the script! (Lines **9**, **18**, **23**)

```shell
$ python3 TREx/sample_contextweighted_batched.py --batch-count 16 re-nlg_*.json
```

## Evaluating queries on previously created .nt baselines

The script `query_eval.py` will create query results and query maps in JSON format for an input .nt file and input queries.
Evaluate our `gold_dataset.nt`, `missing_data.nt` and the previously created .nt baselines.

```shell
$ python3 query_eval.py gold_dataset.nt < queries.new.41
$ python3 query_eval.py missing_data.nt < queries.new.41
$ python3 query_eval.py ContextWeighted.nt < queries.new.41
```

This will create the query results as JSON files and also `query_map.json` and `query_propmap.json` which describe the queries and which are necessary for the final evaluation.
Note that for other .nt datasets it is important to use the same queries for evaluation.

## Evaluating queries on our **HolE** Knowledge Embedding

To get the query results from a knowledge embedding, we provide the script `query_eval_embedding.py`.
To get our baseline query results from our **HolE** embedding, run the following command:

```shell
$ python3 query_eval_embedding.py --embedding-dimensions 50 --batch-count 20 wikidata_iswc2020/ wikidata_iswc2020_hole/ HolE < queries.new.41
```

## Evaluating Precision & Recall for previously created .json query results

The script `evaluate.py` needs a few parameters to evaluate precision and recall and to plot diagrams:

- `query_propmap.json`: Will be created by `query_eval.py`.
- `gold_dataset.json`: Query results of the Gold-Dataset.
- `result1.json`, `result2.json`, ...: Query result(s) of datasets to evaluate.
- `missing_data.json`: Query results of the dataset containing missing data.
- `query_groups.json` (optional): Defines query groups for which to perform evaluation separately.

See `python3 evaluate.py -h` for more details.

[1]: https://hadyelsahar.github.io/t-rex/
[2]: https://hadyelsahar.github.io/t-rex/downloads/
[3]: https://github.com/UKPLab/emnlp2017-relation-extraction

