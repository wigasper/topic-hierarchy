#!/usr/bin/env python3
import sys
import math
import logging
import argparse
from random import choice

from scipy.stats import normaltest
from scipy.special import ndtr

def check_keyword_intersection(keywords, mesh):
    # use set to avoid duplicates
    result = {word for word in keywords if word in mesh}
    
    return len(result)

def get_random_keywords(corpus, number):
    if len(corpus) < number:
        raise Exception("Corpus is smaller than required number of keywords for evaluation")

    keywords = set()

    # add a random keyword until there are the required number
    # keywords is a set so there will be no duplicates
    while len(keywords) < number:
        keywords.add(choice(corpus))

    return keywords

def run_trials(corpus, mesh, num_keywords, num_trials):
    random_intersect_results = []
    
    for _ in range(num_trials):
        keywords = get_random_keywords(corpus, num_keywords) 
        random_intersect_results.append(check_keyword_intersection(keywords, mesh))

    return random_intersect_results
    
def compute_p_val(method_intersect_len, random_intersect_results):
    logger = logging.getLogger(__name__)

    # check for normality of random_intersect_results
    k2, p = normaltest(random_intersect_results)
    logger.info(f"normaltest p-val: {p}")
   
    x_bar = sum(random_intersect_results) / len(random_intersect_results)
    
    numer = sum([(x - x_bar) ** 2 for x in random_intersect_results])
    std_dev = math.sqrt(numer / (len(random_intersect_results) - 1))

    z = (method_intersect_len - x_bar) / std_dev
        
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
    parser.add_argument("-t", "--trials", help="Number of random trials to run",
            type=int, default=100000)
    
    args = parser.parse_args()
   
    # log delimiter
    logger.info("###############################")
    logger.info(f"corpus: {args.corpus}")
    logger.info(f"method results: {args.result}")
    logger.info(f"mesh file: {args.mesh}")
    logger.info(f"num trials: {args.trials}")

    return parser.parse_args()

if __name__ == "__main__":
    logger = initialize_logger()

    args = get_args()

    # load in things
    corpus = load_list(args.corpus)
    method_results = load_list(args.result)
    mesh = load_mesh(args.mesh)
    
    # get relevant metrics for our method
    method_results_len = len(method_results)
    method_intersect_len = check_keyword_intersection(method_results, mesh)
    
    # run trials
    random_intersect_results = run_trials(corpus, mesh, method_results_len, args.trials)

    p = compute_p_val(method_intersect_len, random_intersect_results)

    logger.info(f"p: {p}") 
