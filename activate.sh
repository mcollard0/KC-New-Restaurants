#!/bin/bash
# Activation script for KC New Restaurants environment

source /home/michael/anaconda3/etc/profile.d/conda.sh
conda activate kc-restaurants

echo "KC New Restaurants environment activated!"
echo "Python: $( which python )"
echo "pymongo version: $( python -c 'import pymongo; print( pymongo.__version__ )' )"
echo ""
echo "Ready to run: python 'KC New Restaurants.py'"
