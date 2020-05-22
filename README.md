# KnowlyBERT - Hybrid Query Processing over Language Models and Knowledge Graphs

This repository contains the code which allows to reproduce our results in the paper.

## System Requirements
- Linux
- 128GB RAM recommended
- a CUDA-enabled GPU with at least 11GB memory (the software runs also on CPU, but it is extremely slow :/)

## Dependencies
- Python3
- PyPi Packages
    - matplotlib==3.1.2
    - cython==0.29.2
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
    - tensorflow==1.14.0rc0 (select GPU support in `requirements.txt` manually!)

## FIRST STEPS

### Install Python requirements

```shell
$ python3 -m pip install -r requirements.txt
```

### Clone RelAlign Repository

```shell
$ cd kb_embeddings/
$ git clone https://github.com/JanKalo/RelAlign.git
$ cd ..
```

### Install LAMA
Do not clone the LAMA repository again. Only install it as an editable package.

```shell
$ cd LAMA/
$ pip install --editable .
$ cd ..
```

## Repository Structure

### /LAMA/

This is mainly the repository of Petroni et al. (https://github.com/facebookresearch/LAMA) but there are also some scripts added and edited to enable this hybrid system: 1) multi token results of the language model 2) automatically extracted templates

### /baseline/

This directory includes the script to evaluate the results of the Laguage Model to a specific query file. It is also possible to evaluate the two baselines as a comaprison to the language model: 1) relation extraction model 2) knowledge base embedding. For more information, see the README.md file located in the directory `baseline/`.

### /kb\_embeddings/

This directory includes the script for the integration of the knowledge base embedding *HolE* to get the loss of a given tripel.

### /threshold\_method/

This directory includes the script for calculating the threshold of the language model probabilities.

## Python Files

This section only contains the files which are needed to reproduce the results.

### 1) get\_results.py

This script saves the results of the language model to given queries and parameters of the hybrid system. The parameters can be changed in *get\_results.py* starting from line 343. For each evaluation and the given parameters a result directory (e.g. `<chosen_result_directory>` = 21.05.\_03:18:34\_tmc\_tprank2\_ts5\_trmmax\_ps1\_kbe-1\_cpTrue\_mmd0.6) is saved to `evaluation/`. 

```shell
$ python3 get_results.py
$ cd evaluation/<chosen_result_directory>/
```
### 2) baseline/evaluate.py

This script evaluates the results of the language model by reading the result files in `evaluation/<chosen_result_directory>/`.
It returns the following eight files:
- evaluation\_all.json --> all given queries
- evaluation\_object.json --> only queries based on the tripel (s, p, ?x)
- evaluation\_subject.json --> only queries based on the tripel (?x, p, o)
- evaluation\_single.json --> only queries with only one-token results
- evaluation\_multi.json --> only queries with one-token AND multi-token results
- evaluation\_1-1.json --> only queries with 1-1 properties
- evaluation\_1-n.json --> only queries with 1-n properties
- evaluation\_n-m.json --> only queries with n-m properties

```shell
$ python3 ../../baseline/evaluate.py --missing-data ../../baseline/missing_data.json --query-groups query_groups.json ../../baseline/query_propmap.json ../../baseline/gold_dataset.json ../../baseline/ContextWeighted2017.json data/
```
### 3) baseline/get\_precision\_recall.py

This script saves files with precision and recall values by reading the output files of `baseline/evaluate.py`.
For each evaluation.json, it returns a file with the averaged precision and recall over all queries and a file with the precision and recall averaged over all the containing queries per property.

```shell
$ python3 ../../baseline/get_precision_recall.py evaluation_all.json evaluation_object.json evaluation_subject.json evaluation_single.json evaluation_multi.json evaluation_1-1.json evaluation_1-n.json evaluation_n-m.json
```
