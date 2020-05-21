# KnowlyBERT - Hybrid Query Processing over Language Models and Knowledge Graphs

This repository contains the code which allows to reproduce our results in the paper.

## System Requirements
- Linux
- minimum 32GB RAM
- a CUDA-enabled GPU with at least 11GB memory (the software runs also on CPU, but the training is extremely slow)

## Dependencies
- Python3
- PyPi Packages
    - matplotlib
    - Cython==0.29.2
    - numpy==1.15.1
    - torch==1.0.1
    - pytorch-pretrained-bert==0.6.1
    - allennlp==0.8.5
    - spacy==2.1.8
    - tqdm==4.26.0
    - termcolor==1.1.0
    - pandas==0.23.4
    - fairseq==0.8.0
    - colorama==0.4.1
    - tensorflow

## FIRST STEPS

### Install Python requirements

```shell
$ python3 -m pip install -r requirements.py
```

### Clone RelAlign Repository

```shell
$ cd kb_embeddings/
$ git clone https://github.com/JanKalo/RelAlign.git
$ cd ..
```

### Install LAMA
Do not clone the LAMA repo again. Only install it as an editable package.

```shell
$ cd LAMA/
$ pip install --editable .
$ cd ..
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

This script saves the results of the language model to given queries and parameters of the hybrid system. The parameters can be changed in get_results.py from line 343. For each evaluation and the given parameters a result directory (e.g. *<chosen_result_directory>* = 21.05._12:34:18_tmc_tprank2_ts5_trmavg_ps1_kbe-1_cpTrue_mmd0.7) is saved to evaluation/. 

```shell
$ python3 get_results.py
$ cd evaluation/<chosen_result_directory>/
```
### 2) baseline/evaluate.py

This script evaluates the results of the language model by reading the result files in *evaluation/<chosen_result_directory>/*.
It returns eight files:
- evaluation_all.json --> all given queries
- evaluation_object.json --> only queries based on the tripel (s, p,?x)
- evaluation_subject.json --> only queries based on the tripel (?x, p,o)
- evaluation_single.json --> only queries with only one token results
- evaluation_multi.json --> only queries with one AND multi token results
- evaluation_1-1.json --> only queries with 1-1 properties
- evaluation_1-n.json --> oonly queries with 1-n properties
- evaluation_n-m.json --> only queries with n-m properties

```shell
$ python3 ../baseline/evaluate.py --missing-data ..baseline/missing_data.json --query-groups query_groups.json ..baseline/query_propmap.json ..baseline/gold_dataset.json ..baseline/ContextWeighted2017.json data/
```
### 3) baseline/get_precision_recall.py

This script saves files with precision and recall values by reading the output files of *baseline/evaluate.py*.
For each evaluation.json, it returns a file with average precision and recall per query and a file with the precision and recall of the properties which are used in the queries.

```shell
$ python3 ../baseline/get_precision_recall.py evaluation_all.json evaluation_object.json evaluation_subject.json evaluation_single.json evaluation_multi.json evaluation_1-1.json evaluation_1-n.json evaluation_n-m.json
```
