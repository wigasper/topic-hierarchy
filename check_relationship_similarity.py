#!/usr/bin/env python3
import sys
import logging
import argparse
from itertools import permutations
from collections import deque

from parse_mesh import parse_mesh

# returns the bfs result starting at node. used to get the component
# of the node
def bfs(node, adj_list):
    component = []
    visited_nodes = set()

    queue = deque([node])

    while len(queue) > 0:
        this_node = queue.popleft()
        
        if this_node not in visited_nodes:
            visited_nodes.add(this_node)
            component.append(this_node)

            for adj in adj_list[this_node]:
                queue.append(adj)
    
    return {n: adj_list[n] for n in component}

def get_intersect(elements, mesh):
    return {ele for ele in elements if ele in mesh}

def get_components(adj_list):
    unvisited_nodes = set(adj_list.keys())
    
    components = []

    while len(unvisited_nodes) > 0:
        node = unvisited_nodes.pop()
        component = bfs(node, adj_list)

        for n in component.keys():
            if n != node:
                 unvisited_nodes.remove(n)
        
        components.append(component)

    return components


def get_component_subset(adj_list, lem_mesh, lem_mesh_bigrams):
    logger = logging.getLogger()

    unvisited_nodes = set(adj_list.keys())    
    components = []

    max_intersect_len = 0
    max_component = {}

    while len(unvisited_nodes) > 0:
        node = unvisited_nodes.pop()
        component = bfs(node, adj_list)

        for n in component.keys():
            if n != node:
                 unvisited_nodes.remove(n)
        
        intersect_len = len(get_intersect(component.keys(), lem_mesh))
        intersect_len += len(get_intersect(component.keys(), lem_mesh_bigrams))

        if intersect_len > 1:
            components.append(component)

            if intersect_len > max_intersect_len:
                max_intersect_len = intersect_len
                max_component = component
    

    print(f"max intersect len: {max_intersect_len}")
    print(max_component.keys())
    return components

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

def load_mesh(mesh_fp):
    with open(mesh_fp, encoding="ISO-8859-1", mode="r") as handle:
        mesh = [line.strip("\n") for line in handle]

    # mesh should be a set because later there are millions of checks to see
    # if an element is in the data structure
    return set(mesh)

def load_from_edge_list(fp):
    adj_list = {}

    with open(fp, "r") as handle:
        for line in handle:
            line = line.strip("\n").split("\t")
            line = [it.strip() for it in line]

            if line[0] in adj_list.keys():
                adj_list[line[0]].append(line[1])
            else:
                adj_list[line[0]] = [line[1]]

            if line[1] in adj_list.keys():
                adj_list[line[1]].append(line[0])
            else:
                adj_list[line[1]] = [line[0]]

    for key in adj_list:
        adj_list[key] = list(dict.fromkeys(adj_list[key]))
    return adj_list

def initialize_logger(debug=False, quiet=False):
    level = logging.INFO
    if debug:
        level = logging.DEBUG

    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.FileHandler("relationships.log")
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
    parser.add_argument("-i", "--input", help="Path to edge list from our method", required=True)
    parser.add_argument("-m", "--mesh", help="Path to MeSH descriptor file", required=True)
    parser.add_argument("-l", "--lem", help="Path to lemmatized MeSH file", required=True)

    args = parser.parse_args()

    # log delimiter
    logger.info("###############################")
    #logger.info(f"Corpus: {args.corpus}")
    #logger.info(f"Method results: {args.result}")
    #logger.info(f"MeSH file: {args.mesh}")
    #logger.info(f"Num. trials: {args.trials}")

    return parser.parse_args()

if __name__ == "__main__":
    logger = initialize_logger()
    args = get_args()

    adj_list = load_from_edge_list(args.input)

    lem_mesh = load_mesh(args.lem)
    lem_mesh_bigrams = get_bigram_set(lem_mesh)

    components = get_components(adj_list)
    components_subset = get_component_subset(adj_list, lem_mesh, lem_mesh_bigrams)

    logger.info(f"total number of components: {len(components)}")
    logger.info(f"num components w/ multiple mesh terms: {len(components_subset)}")
