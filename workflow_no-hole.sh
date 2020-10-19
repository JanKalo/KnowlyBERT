#!/bin/bash

# download and extract data
#wget data.tar.bz2.aa
#wget ...
#wget data.tar.bz2.am
echo "1/5: DOWNLOADING DATA"
wget https://cloudstorage.tu-braunschweig.de/dl/fiJb1YCX2EAuQ7FfozPjKQ1W/data.tar.bz2.aa
wget https://cloudstorage.tu-braunschweig.de/dl/fi4UWwcCupm5nxPkZnQ5W4gg/data.tar.bz2.ab
wget https://cloudstorage.tu-braunschweig.de/dl/fiQnuKhQF4WvTQXwMuUbKEVj/data.tar.bz2.ac
wget https://cloudstorage.tu-braunschweig.de/dl/fiKBGdUsbBbM2SUG6iPFGhQE/data.tar.bz2.ad
wget https://cloudstorage.tu-braunschweig.de/dl/fiUPw5utqpqatgXAPRXK96b1/data.tar.bz2.ae
wget https://cloudstorage.tu-braunschweig.de/dl/fi5t8AYdGFm3GpTWXRkuja3n/data.tar.bz2.af
wget https://cloudstorage.tu-braunschweig.de/dl/fiFCg2EvBmJiepWoAsgBGoTb/data.tar.bz2.ag
wget https://cloudstorage.tu-braunschweig.de/dl/fiGXu3AjFTdL8eEC48GGDJ94/data.tar.bz2.ah
wget https://cloudstorage.tu-braunschweig.de/dl/fiXfjsXGVVUZo2XjziqHYDZS/data.tar.bz2.ai
wget https://cloudstorage.tu-braunschweig.de/dl/fiMTA6AvCyFjui95xvXKetmE/data.tar.bz2.aj
wget https://cloudstorage.tu-braunschweig.de/dl/fi6qiSeTdPTVbzKSFkdzd2Lq/data.tar.bz2.ak
wget https://cloudstorage.tu-braunschweig.de/dl/fiJs8ZoGKMMFbfSvKaN4npMx/data.tar.bz2.al
wget https://cloudstorage.tu-braunschweig.de/dl/fiKamu9vDKnxLBFKFb5zbp8Z/data.tar.bz2.am
cat data.tar.bz2.* | tar -xjvf -
rm data.tar.bz2.*

# evaluate queries on gold data, missing data and baselines
echo "2/5: EVALUATING ON GOLD DATA, MISSING DATA, BASELINES"
cd evaluation/
python3 ../baseline/query_eval.py ../data/gold_dataset.nt < ../data/queries.new.41
python3 ../baseline/query_eval.py ../data/missing_data.new.nt < ../data/queries.new.41
python3 ../baseline/query_eval.py ../data/ContextWeighted2017.nt < ../data/queries.new.41

# get results from KnowlyBERT
echo "3/5: GETTING RESULTS FROM KNOWLYBERT"
cd ../
python3 get_results.py

# evaluate results
echo "4/5: EVALUATING RESULTS"
cd evaluation/*/
python3 ../../baseline/evaluate.py --missing-data ../missing_data.new.json --query-groups *query_groups.json ../query_propmap.json ../gold_dataset.json ../ContextWeighted2017.json data/

# get precision-recall values
echo "5/5: GETTING PRECISION RECALL VALUES"
python3 ../../baseline/get_precision_recall.py evaluation_all.json evaluation_object.json evaluation_subject.json evaluation_single.json evaluation_multi.json evaluation_1-1.json evaluation_1-n.json evaluation_n-m.json evaluation_cardinality-1.json evaluation_cardinality-1-10.json evaluation_cardinality-10-100.json evaluation_cardinality-100-inf.json

# done
echo "DONE REPRODUCTION"
cd ../../
