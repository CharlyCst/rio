#!/usr/bin/env bash

if [ -z "$1" ]
then
    echo "Missing argument: program name"
    exit 1
else
    PROGRAM=$1
fi

if [ -z $2 ]
then
    echo "Missing argument: number of repetitions"
    exit 1
else
    N_LOOP=$2
fi

if [ -z $3 ]
then
    echo "Missing argument: output file"
    exit 1
else
    OUTPUT=$3
fi

for ((i=1; i<=$N_LOOP; i++))
do
    mutrace --frame=1 --hash-size=100000 --all $PROGRAM 2>&1 | awk '/\s*[0-9]+\s+[0-9]+/{count++; lock+=$2; cont+=$4}; END{print count, lock, cont}' >> $OUTPUT
done

