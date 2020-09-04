#!/usr/bin/env python3
import argparse
from random import choice

from scipy.stats import normaltest

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
    # check for normality of random_intersect_results
    k2, p = normaltest(random_intersect_results)
    print(f"normaltest p-val: {p}")

    left_of = len([it for it in random_intersect_results if it < method_intersect_len])
    
    #print(f"method_int_len {method_intersect_len}, left_of {left_of}")
    return 1.0 - (left_of / len(random_intersect_results))

def load_mesh(mesh_fp):
    with open(mesh_fp, encoding="ISO-8859-1", mode="r") as handle:
        mesh = [line.strip("\n") for line in handle]
    
    return set(mesh)

def load_list(fp):
    items = []
    
    with open(fp, "r") as handle: 
        for line in handle:
            line = line.strip("\n")
            if line:
                items.append(line)
    
    return items

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--corpus", help="Path to input corpus file", 
            required=True)
    parser.add_argument("-r", "--result", help="Path to results from our method",
            required=True)
    #parser.add_argument("-k", "--keywords-total", help="Total number of keywords found by " \
    #        "our method", type=int)
    parser.add_argument("-m", "--mesh", help="Path to lemmatized MeSH file",
            required=True)
    parser.add_argument("-t", "--trials", help="Number of random trials to run",
            type=int, default=100000)
    
    return parser.parse_args()

if __name__ == "__main__":
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

    print(f"p: {p}") 
