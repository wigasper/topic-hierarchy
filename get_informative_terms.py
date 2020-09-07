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
    
    out = []

    # Return empty list for terms (like 'D005260' - 'Female') that aren't
    # actually part of any trees
    
    if uid in term_trees.keys() and len(term_trees[uid][0]) > 0:
        children = []

        # NOTE: this is really inefficient
        for tree in term_trees[uid]:
            parent_depth = len(tree.split("."))
            for key, vals in term_trees.items():
                for val in vals:
                    child_depth = len(val.split("."))
                    if tree in val and uid != key and child_depth == parent_depth + 1:
                        children.append(key)
        
        # dedup
        out = list(dict.fromkeys(children))
    
    return out

def get_informative_terms(term_freqs, term_trees, cutoff):
    informative_terms = []
    
    candidate_terms = [uid for uid, freq in term_freqs.items() if freq > cutoff]

    for uid in candidate_terms:
        children = get_children(uid, term_trees)
        
        all_children_below_cutoff = len([c for c in children if term_freqs[c] < cutoff]) == 0
        if len(children) > 0 and all_children_below_cutoff:
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

def load_specialized_term_set(fp):
    terms = []
    with open(fp, "r") as handle:
        for line in handle:
            line = line.strip("\n").split("\t")
            
            terms.extend([it for it in line[1:] if it])

    return set(terms)

def write_output(terms_out, out_fp, desc_data):
    with open(out_fp, "w") as out:
        for term in terms_out:
            out.write(f"{desc_data[term]['name']}\n")

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
            default="data/desc2020")
    parser.add_argument("-c", "--counts", help="Path to term counts csv", 
            default="data/pm_doc_term_counts.csv")
    parser.add_argument("-a", "--articles", help="Path to term counts for articles subset",
            default="data/specialized_3yrs_solutions_uids.tsv")
    parser.add_argument("-o", "--output", help="Output file path",
            default="data/seed_topics")
    parser.add_argument("-t", "--threshold", help="Cutoff value", type=int, required=True)
    args = parser.parse_args()

    logger.info("###############################")
    logger.info(f"MeSH descriptor: {args.mesh}")
    logger.info(f"Term counts file: {args.counts}")
    logger.info(f"Articles subset: {args.articles}")
    logger.info(f"Cutoff value: {args.threshold}")

    return args

if __name__ == "__main__":
    logger = initialize_logger()

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
    
    logger.info(f"Found {len(informative_terms)} informative terms")

    target_subset = load_specialized_term_set(args.articles)

    terms_out = [term for term in informative_terms if term in target_subset]
    logger.info(f"{len(terms_out)} informative terms are in the subset")

    write_output(terms_out, args.output, desc_data)
