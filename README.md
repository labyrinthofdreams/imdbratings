Install python2 or install anaconda and run:

conda create -n python2 python=2.7 anaconda
conda activate python2

Then cd into the directory with python files and run:

python ratings.py directory_with_csv_files out.csv --sort-by dmean --limit-voters-min 5

directory_with_csv_files should have all the ratings.csv files where each csv file should be called username.csv

Run python ratings.py --help to see all the options for sorting and filtering output