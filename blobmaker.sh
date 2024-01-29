#!/bin/bash

cubitpath='/opt/Coreform-Cubit-2023.8/bin'
filename='sample_blanket.json'
printinfo='false'
runprogram='false'

usage() {
    echo "Usage:"
    echo "Options:"
    echo " -h,       Display this message"
    echo " -i,       Print cubit IDs of volumes in materials and surfaces in boundaries"
    echo " -f,       FILE Specify an input file"
    echo " -p,       PATH Add cubit library to python path"
    echo " -c,       CLASS Get info on classes"
}

while getopts "hif:c:" opt; do
    case $opt in
        h)
            usage
            exit 0
            ;;
        i)
            printinfo='true'
            ;;
        f)
            filename=$OPTARG
            runprogram='true'
            ;;
        p)
            cubitpath=$OPTARG
            ;;
        c)
            python3 main.py -c $OPTARG
            exit 0
            ;;
        /?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            exit 1
            ;;
    esac
done

if [ $runprogram = 'true' ]; then
    PYTHONPATH=$PYTHONPATH:$cubitpath
    python3 main.py -i $printinfo -f $filename
    exit 0
fi

exit 0