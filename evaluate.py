#!/usr/bin/env python3
import sys
import math
import logging
import argparse
from random import choice
from itertools import permutations

from scipy.stats import normaltest
from scipy.special import ndtr


def check_intersection(elements, mesh):
    return len({el for el in elements if el in mesh})

def get_random_elements(corpus, number):
    if len(corpus) < number:
        raise Exception("Corpus is smaller than required number of elements for evaluation")

    elements = set()

    # add a random keyword until there are the required number
    # keywords is a set so there will be no duplicates
    while len(elements) < number:
        elements.add(choice(corpus))

    return elements

# this is used to convert mesh into a suitable set for 'in' checking
# millions of times for bigrams. for each item in mesh, if the item 
# consists of 2 or more words, then all 2-length permutations are added 
# to the set
#
# NOTE: this is not memory efficient, but fine for now
def get_bigram_set(mesh):
    mesh_out = set()

    for element in mesh:
        element = element.split()
        
        if len(element) > 1:
            # dedup
            element = list(dict.fromkeys(element))
            
            for permutation in permutations(element, 2):
                mesh_out.add(" ".join(permutation))

    return mesh_out

# NOTE: currently this is just going to assume keywords/bigrams based 
# on the split length
def run_trials(corpus, mesh, num_elements, num_trials):
    logger = logging.getLogger(__name__)

    random_intersect_results = []
    
    for _ in range(num_trials):
        elements = get_random_elements(corpus, num_elements)
        random_intersect_results.append(check_intersection(elements, mesh))
    
    return random_intersect_results
    
def compute_p_val(method_intersect_len, random_intersect_results):
    logger = logging.getLogger(__name__)

    # check for normality of random_intersect_results
    k2, p = normaltest(random_intersect_results)
    logger.info(f"normaltest p-val: {p}")
   
    x_bar = sum(random_intersect_results) / len(random_intersect_results)
    
    numer = sum([(x - x_bar) ** 2 for x in random_intersect_results])
    std_dev = math.sqrt(numer / (len(random_intersect_results) - 1))
    
    if std_dev > 0:
        z = (method_intersect_len - x_bar) / std_dev
    else:
        z = 0

    return 1 - ndtr(z)

def load_mesh(mesh_fp):
    with open(mesh_fp, encoding="ISO-8859-1", mode="r") as handle:
        mesh = [line.strip("\n") for line in handle]
    
    # mesh should be a set because later there are millions of checks to see
    # if an element is in the data structure
    return set(mesh)

def load_list(fp):
    items = []
    
    with open(fp, "r") as handle: 
        for line in handle:
            line = line.strip("\n")
            if line:
                items.append(line)
    
    return items

def initialize_logger(debug=False, quiet=False):
    level = logging.INFO
    if debug:
        level = logging.DEBUG

    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.FileHandler("eval.log")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if not quiet:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def get_args():
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--corpus", help="Path to input corpus file", required=True)
    parser.add_argument("-r", "--result", help="Path to results from our method", required=True)
    parser.add_argument("-m", "--mesh", help="Path to lemmatized MeSH file", required=True)
    parser.add_argument("-t", "--trials", help="Number of random trials to run, default=100000",
            type=int, default=100000)
    
    args = parser.parse_args()
   
    # log delimiter
    logger.info("###############################")
    logger.info(f"Corpus: {args.corpus}")
    logger.info(f"Method results: {args.result}")
    logger.info(f"MeSH file: {args.mesh}")
    logger.info(f"Num. trials: {args.trials}")

    return parser.parse_args()

# thresh is just for the experiment!!!
def evaluate(corpus, method_result, mesh, n_trials, thresh, verbose=True):
    if verbose:
        logger = logging.getLogger(__name__)
    
    # bigram detection
    if len(corpus[0].split()) == 2:
        if verbose:
            logger.info("Bigrams detected")
        mesh = get_bigram_set(mesh)
    
    # get result metric for our method
    method_intersect_len = check_intersection(method_result, mesh)
    
    # run trials
    random_intersect_results = run_trials(corpus, mesh, len(method_result), n_trials)
    random_mean = sum(random_intersect_results) / len(random_intersect_results)

    p = compute_p_val(method_intersect_len, random_intersect_results)

    if verbose:
        logger.info(f"Method intersect length: {method_intersect_len}")
        logger.info(f"Random intersect mean: {random_mean}")
        logger.info(f"Random intersect max: {max(random_intersect_results)}")
        logger.info(f"p: {p}") 

    return (thresh, p, method_intersect_len, len(method_result), random_mean, max(random_intersect_results))

if __name__ == "__main__":
    logger = initialize_logger()

    args = get_args()

    # load in things
    corpus = load_list(args.corpus)
    method_results = load_list(args.result)
    mesh = load_mesh(args.mesh)
    
    _ = evaluate(corpus, method_result, mesh, args.trials)
