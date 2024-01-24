#!/bin/bash

cubitpath='/opt/Coreform-Cubit-2023.8/bin'
filename='sample_blanket.json'
printinfo='false'
runprogram='true'

usage() {
    echo "Usage:"
    echo "Options:"
    echo " -h,       Display this message"
    echo " -i,       Print cubit IDs of volumes in materials and surfaces in boundaries"
    echo " -f,       FILE Specify an input file"
    echo " -c,       PATH Add cubit library to python path"
}

while getopts "hif:c:" opt; do
    case $opt in
        h)
            usage
            runprogram='false'
            ;;
        i)
            printinfo='true'
            ;;
        f)
            filename=$OPTARG
            ;;
        c)
            cubitpath=$OPTARG
            ;;
        /?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

PYTHONPATH=$PYTHONPATH:$cubitpath

if [ $runprogram = 'true' ]; then
    if [ $printinfo = 'true' ]; then
        python3 main.py -i -f $filename
    else
        python3 main.py -f $filename
    fi
fi