#!/usr/bin/env python3
import argparse
from random import choice

def check_keyword_intersection(keywords, mesh_path):
    with open(mesh_path, encoding="ISO-8859-1", mode="r") as handle:
        mesh = [line.strip("\n") for line in handle]
    
    result = {word for word in keywords if word in mesh}
    #print(result)
    return len(result)

def get_random_keywords(corpus_fp, number):
    # going to have keywords be a set to ease deduping
    keywords = set()
    corpus = []

    with open(corpus_fp, "r") as handle: 
        for line in handle:
            line = line.strip("\n")
            if line:
                corpus.append(line)
    
    if len(corpus) < number:
        raise Exception("Corpus is smaller than required number of keywords for evaluation")

    # add a random keyword until there are the required number
    # keywords is a set so there will be no duplicates
    while len(keywords) < number:
        keywords.add(choice(corpus))
    
    return keywords

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", help="Path to input corpus file", required=True)
    parser.add_argument("-n", "--intersection", help="Number of keywords/bigrams found by " \
            "our method that intersect with actual MeSH terms ('true positives')", type=int)
    parser.add_argument("-t", "--total", help="Total number of keywords found by our " \
            "method", type=int)
    parser.add_argument("-m", "--mesh", help="Path to lemmatized MeSH file")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    
    keywords = get_random_keywords(args.input, args.total)
    # print(keywords) 
    intersect_len = check_keyword_intersection(keywords, args.mesh)

    print(f"intersect len: {intersect_len}")
