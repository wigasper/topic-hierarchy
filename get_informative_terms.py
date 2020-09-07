#!/usr/bin/env python3
import sys
import logging
import argparse

from parse_mesh import parse_mesh

def get_children(uid, term_trees):
    ''' Gets a list of children for a term. Because there isn't actually a graph
        to traverse, it's done by searching according to position (described by a string)
        on the graph
    params
        uid - the UID of the term
        term_trees - a dict giving the position(s) on the graph for each UID
    returns
        a list of the children of the UID
    '''
    
    # Return empty list for terms (like 'D005260' - 'Female') that aren't
    # actually part of any trees
    if len(term_trees[uid][0]) == 0:
        return []

    children = []

    for tree in term_trees[uid]:
        parent_depth = len(tree.split("."))
        for key, vals in term_trees.items():
            for val in vals:
                child_depth = len(val.split("."))
                if tree in val and uid != key and child_depth == parent_depth + 1:
                    children.append(key)
    
    return list(dict.fromkeys(children))

def get_informative_terms(term_freqs, term_trees, cutoff):
    informative_terms = []
    
    candidate_terms = [uid for uid, freq in term_freqs.items() if freq > cutoff]

    for uid in candidate_terms:
        children = get_children(uid, term_trees)
        
        if len([child for child in children if term_freqs[child] < cutoff]) == 0:
            informative_terms.append(uid)

    return informative_terms

def load_term_freqs(desc_uids, counts_fp):
    term_freqs = {uid: 0 for uid in desc_uids}

    with open(counts_fp, "r") as handle:
        for line in handle:
            line = line.strip("\n").split(",")[1:]
            
            for uid in line:
                if uid in term_freqs.keys():
                    term_freqs[uid] += 1
                else:
                    term_freqs[uid] = 1

    return term_freqs

def initialize_logger(debug=False, quiet=False):
    level = logging.INFO
    if debug:
        level = logging.DEBUG

    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.FileHandler("get_informative_terms.log")
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
    parser.add_argument("-m", "--mesh", help="Path to MeSH descriptor file", 
            default="desc2020")
    parser.add_argument("-c", "--counts", help="Path to term counts csv", 
            default="pm_doc_term_counts.csv")
    parser.add_argument("-t", "--threshold", help="Cutoff value", type=int, required=True)
    args = parser.parse_args()

    logger.info("###############################")

    return args

if __name__ == "__main__":
    
    args = get_args()

    desc_data, desc_uids = parse_mesh(args.mesh)

    term_trees = {}
    term_trees_rev = {}

    for uid in desc_data:
        term_trees[uid] = desc_data[uid]["graph_positions"].split("|")
        
        for graph_position in desc_data[uid]["graph_positions"].split("|"):
            term_trees_rev[graph_position] = uid
            
    term_freqs = load_term_freqs(desc_uids, args.counts)

    informative_terms = get_informative_terms(term_freqs, term_trees, args.threshold)
    
    print(f"{informative_terms}")
