# KnowlyBERT - Hybrid Query Processing over Language Models and Knowledge Graphs

This repository contains the code which allows to reproduce our results in the paper.

## System Requirements
- TODO

## Dependencies
- Python3
- PyPi Packages
    - matplotlib
    - **TODO**

## FIRST STEPS

### TODO

### Install Python requirements

```shell
$ python3 -m pip install -r requirements.py
```

## Repository Structure

### /LAMA/

This is mainly the repository of Petroni et al. (https://github.com/facebookresearch/LAMA) but there are also some scripts added and changed to enable this hybrid system: 1) multi token results of the language model 2) automatically extracted templates

### /baseline/

This directory includes the script to evaluate the results of the Laguage Model to a specific query file. It is also possible to evaluate the two baselines as a comaprison to the language model: 1) relation extraction model 2) knowledge base embedding. For more information, see the README.md file located in the directory baseline/.

### /kb\_embeddings/

This directory includes the script for deadling with the knowledge embedding HolE to get the loss of a given tripel and calculate an average probability respecting to the loss and the language model probability of a tripel.

### /threshold\_method/

This directory includes the script for calculating the threshold of the language model probabilities.

## Python Files

This section only covers the files which are needed to reproduce the results.

### 1) get\_results.py

This script saves the results of the language model to given queries and parameters of the hybrid system. The parameters can be changed in get_results.py from line 336. For each evaluation and the given parameters a result directory (e.g. <chosen_result_directory> = 21.05._12:34:18_tmc_tprank2_ts5_trmavg_ps1_kbe-1_cpTrue_mmd0.7) is saved to evaluation/. 

```shell
$ python3 get_results.py
$ cd evaluation/<chosen_result_directory>
```
### 2) baseline/evaluate.py

This script evaluates the results of the language model by reading the result files in evaluation/<chosen_result_directory>.
It returns tree (TODO five) files:
- evaluation_all.json --> all given queries
- evaluation_object.json --> only queries based on the tripel (s, p,?x)
- evaluation_subject.json --> only queries based on the tripel (?x, p,o)
- evaluation_onetoken.json --> TODO
- evaluation_multitoken.josn --> TODO

```shell
$ python3 ../baseline/evaluate.py --missing-data ..baseline/missing_data.json --query-groups query_groups.json ..baseline/query_propmap.json ..baseline/gold_dataset.json ..baseline/ContextWeighted2017.json data/
```
### 3) baseline/get_precision_recall.py

This script saves files with precision and recall values by reading the output files of baseline/evaluate.py.
For each evaluation.json, it returns a file with average precision and recall per query and a file with the precision and recall of the properties which are used in the queries.

```shell
$ python3 ../baseline/get_precision_recall.py evaluation_all.json evaluation_object.json evaluation_subject.json
```

## Experiments

TODO

### Datasets

TODO

### Evaluation 1

```shell
$ TODO
```

### Evaluation n

```shell
$ TODO
```
