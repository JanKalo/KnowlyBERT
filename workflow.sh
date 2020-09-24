#!/bin/bash

# evaluate queries on gold data, missing data and baselines
echo "1/4: EVALUATING ON GOLD DATA, MISSING DATA, BASELINES"
cd evaluation/
python3 ../baseline/query_eval.py ../data/gold_dataset.nt < ../data/queries.new.41
python3 ../baseline/query_eval.py ../data/missing_data.new.nt < ../data/queries.new.41
python3 ../baseline/query_eval.py ../data/ContextWeighted2017.nt < ../data/queries.new.41
python3 ../baseline/query_eval_embedding.py --embedding-dimensions 50 --batch-count 20 ../data/wikidata_iswc2020/ ../data/wikidata_iswc2020_hole/ HolE < ../data/queries.new.41

# get results from KnowlyBERT
echo "2/4: GETTING RESULTS FROM KNOWLYBERT"
cd ../
python3 get_results.py

# evaluate results
echo "3/4: EVALUATING RESULTS"
cd evaluation/*/
python3 ../../baseline/evaluate.py --missing-data ../missing_data.new.json --query-groups *query_groups.json ../query_propmap.json ../gold_dataset.json ../ContextWeighted2017.json ../wikidata_iswc2020*.json data/

# get precision-recall values
echo "4/4: GETTING PRECISION RECALL VALUES"
python3 ../../baseline/get_precision_recall.py evaluation_all.json evaluation_object.json evaluation_subject.json evaluation_single.json evaluation_multi.json evaluation_1-1.json evaluation_1-n.json evaluation_n-m.json evaluation_cardinality-1.json evaluation_cardinality-1-10.json evaluation_cardinality-10-100.json evaluation_cardinality-100-inf.json

# done
echo "DONE REPRODUCTION"
cd ../../
