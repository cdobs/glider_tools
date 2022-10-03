#!/bin/bash
PROJECT_PATH="/Users/cdobson/Documents/Github/glider_tools/metadata_mining/"
AM_PATH="/Users/cdobson/Documents/Github/ooicgsn-asset-management"

GLIDER="379"
MAX_DEPLOYMENT=16

for ((i=1;i<=MAX_DEPLOYMENT;i++)); do
    DNUM=`printf D%05d $i`
    AM_CSV="$AM_PATH/deployment/CP05MOAS-GL${GLIDER}_Deploy.csv"
    AM_CSV_DIR="$PROJECT_PATH/input/CP05MOAS-GL${GLIDER}/"
    TO_DIR="$PROJECT_PATH/input/CP05MOAS-GL$GLIDER/$DNUM/dockserver_logs"

    echo $TO_DIR

    if [ -d $TO_DIR ]
    then
        echo "Directory exists."
    else
        mkdir -p $TO_DIR
    fi

    rsync -aP ooiuser@ooi-omsds1.whoi.net:/home/ooiuser/DS/CP05MOAS-GL$GLIDER/$DNUM/logs/*.log $TO_DIR
    rsync -aP $AM_CSV $AM_CSV_DIR


    python3 process_glider_metadata.py -g "CP05MOAS-GL${GLIDER}" -d $i -t meta -s $PROJECT_PATH

done
