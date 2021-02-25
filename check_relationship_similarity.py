#!/usr/bin/env python3
import sys
import math
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

def get_distance(source, sink, adj_list):
    if source == sink:
        return 0

    # early stopping bfs
    visited_nodes = set()

    queue = deque([source])
    dist = 0
    found = False

    while len(queue) > 0 and not found:
        queue_len = len(queue)
        dist += 1

        for _ in range(queue_len):
            this_node = queue.popleft()
            
            if this_node not in visited_nodes:
                visited_nodes.add(this_node)

                for adj in adj_list[this_node]:
                    if adj == sink:
                        found = True
                        break
                    queue.append(adj)
            
            if found:
                break
         
    if not found:
        raise Exception("get_distance problem - sink not found")

    return dist

def build_distance_matrix(component, mesh_graph, lem_mesh_map, lem_mesh, lem_mesh_bigrams):
    intersect = list(get_intersect(component.keys(), lem_mesh))
    intersect.extend(list(get_intersect(component.keys(), lem_mesh_bigrams)))
    intersect = list(dict.fromkeys(intersect))

    hier_dists = []
    mesh_dists = []

    for node_0 in intersect:
        corresponding_mesh_0 = lem_mesh_map[node_0]
        for node_1 in intersect:
            corresponding_mesh_1 = lem_mesh_map[node_1]
            hier_dist = get_distance(node_0, node_1, component)
            mesh_dist = get_distance(corresponding_mesh_0, corresponding_mesh_1, mesh_graph)
            
            hier_dists.append(hier_dist)
            mesh_dists.append(mesh_dist)

    return (hier_dists, mesh_dists)

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


def get_component_subset(adj_list, lem_mesh, lem_mesh_bigrams, lem_mesh_map):
    logger = logging.getLogger(__name__)

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
        
        intersect = list(get_intersect(component.keys(), lem_mesh))
        intersect.extend(list(get_intersect(component.keys(), lem_mesh_bigrams)))
        intersect = list(dict.fromkeys(intersect))
        
        corresponding_mesh = list(dict.fromkeys([lem_mesh_map[it] for it in intersect]))

        if len(corresponding_mesh) > 1:
            components.append(component)

            if len(intersect) > max_intersect_len:
                max_intersect_len = len(intersect)
                max_component = component
    

    logger.info(f"Max intersect length: {max_intersect_len}")
    
    return components

# dist matrices are just lists of values here
def get_rmsd(dist_matrix_0, dist_matrix_1):
    if len(dist_matrix_0) != len(dist_matrix_1):
        raise Exception("rmsd - dist matrices do not have same dims")

    dim = math.sqrt(len(dist_matrix_0))

    rolling_sum = 0

    for idx, val_0 in enumerate(dist_matrix_0):
        val_1 = dist_matrix_1[idx]
        rolling_sum += math.pow((val_0 - val_1), 2)

    # don't want the diagonal values to count against us, there are no
    # self loops
    N = len(dist_matrix_0) - dim

    # dist matrix is redundant, divide rolling sum by 2
    rolling_sum = rolling_sum / 2.0

    return math.sqrt(rolling_sum / N)
    

# this is used to convert lemmatized mesh into a suitable set for 'in' checking
# millions of times for bigrams. for each item in mesh, if the item
# consists of 2 or more words, then all 2-length permutations are added
# to the set
#
# adds items to map as well
def get_bigram_set(mesh, lem_mesh_map):
    mesh_out = set()

    for element in mesh:
        original = element
        element = element.split()

        if len(element) > 1:
            # dedup
            element = list(dict.fromkeys(element))

            for permutation in permutations(element, 2):
                p = " ".join(permutation)
                mesh_out.add(p)
                lem_mesh_map[p] = lem_mesh_map[original]

            for permutation in permutations(element, 3):
                p = " ".join(permutation)
                mesh_out.add(p)
                lem_mesh_map[p] = lem_mesh_map[original]

            for permutation in permutations(element, 4):
                p = " ".join(permutation)
                mesh_out.add(p)
                lem_mesh_map[p] = lem_mesh_map[original]



    return (mesh_out, lem_mesh_map)

def load_lem_mesh(mesh_fp):
    lem_uid_map = {}
    lem_mesh = []

    with open(mesh_fp, "r") as handle:
        for line in handle:
            line = line.strip("\n").split(",")

            lem_mesh.append(line[1])
            lem_uid_map[line[1]] = line[0]
    # mesh should be a set because later there are millions of checks to see
    # if an element is in the data structure
    return (set(lem_mesh), lem_uid_map)

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

def analyze_component(component, lem_mesh, lem_mesh_bigrams, lem_mesh_map, 
        desc_data, adj_list, mesh_graph):
    result = []

    intersect = list(get_intersect(component, lem_mesh))
    intersect.extend(list(get_intersect(component, lem_mesh_bigrams)))
    intersect = list(dict.fromkeys(intersect))

    result.append("Intersection w/ MeSH (terms from our method that have "
                "corresponding MeSH terms):")
    result.append("; ".join(intersect))

    corresponding = list(dict.fromkeys([desc_data[lem_mesh_map[t]]['name'] for t in intersect]))
    result.append("Corresponding MeSH terms:")
    result.append("; ".join(corresponding))
    
    result.append("Dists")
    for term_0_idx in range(len(intersect)):
        for term_1_idx in range(term_0_idx + 1, len(intersect)):
            term_0 = intersect[term_0_idx]
            term_1 = intersect[term_1_idx]
            term_dist = get_distance(term_0, term_1, adj_list)
            corr_mesh_0 = lem_mesh_map[term_0]
            corr_mesh_1 = lem_mesh_map[term_1]
            mesh_dist = get_distance(corr_mesh_0, corr_mesh_1, mesh_graph)
            
            mesh_term_0 = desc_data[corr_mesh_0]['name']
            mesh_term_1 = desc_data[corr_mesh_1]['name']
            result.append(f"{term_0} - {term_1} dist: {term_dist}")
            result.append(f"{mesh_term_0} - {mesh_term_1} dist: {mesh_dist}")
    return result

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
    parser.add_argument("-i", "--input", help="Path to edge list from our method", 
            default="data/edge_list")
    parser.add_argument("-m", "--mesh", help="Path to MeSH edge list", 
            default="data/mesh_edge_list")
    parser.add_argument("-l", "--lem", help="Path to lemmatized MeSH file with term UIDs", 
            default="data/lem_mesh_map")
    parser.add_argument("-d", "--desc", help="Path to MeSH descriptor file", 
            default="data/desc2020")

    args = parser.parse_args()

    # log delimiter
    logger.info("###############################")

    return parser.parse_args()

if __name__ == "__main__":
    logger = initialize_logger()
    args = get_args()

    adj_list = load_from_edge_list(args.input)
    
    (desc_data, _) = parse_mesh(args.desc)

    # these need to be lists
    (lem_mesh, lem_uid_map) = load_lem_mesh(args.lem)
    (lem_mesh_bigrams, lem_uid_map) = get_bigram_set(lem_mesh, lem_uid_map)

    components = get_components(adj_list)
    components_subset = get_component_subset(adj_list, lem_mesh, lem_mesh_bigrams, lem_uid_map)

    logger.info(f"total number of components: {len(components)}")
    logger.info(f"num components w/ multiple mesh terms: {len(components_subset)}")

    mesh_graph = load_from_edge_list(args.mesh)

    rmsds = []
    results = []

    for component in components_subset:
        (h_d, m_d) = build_distance_matrix(component, mesh_graph, lem_uid_map, 
                                            lem_mesh, lem_mesh_bigrams)
        rmsd = get_rmsd(h_d, m_d)
        if rmsd < 2.0:
            results.append("####")
            results.append(f"RMSD: {rmsd}")
            result = analyze_component(component, lem_mesh, lem_mesh_bigrams, 
                    lem_uid_map, desc_data, adj_list, mesh_graph)
            
            results.extend(result)
        rmsds.append(rmsd)

    #logger.info(rmsds)
    mean_rmsd = sum(rmsds) / len(rmsds)
    logger.info(f"Mean RMSD: {mean_rmsd}")

    with open("comparison_results", "w") as out:
        for res in results:
            out.write(f"{res}\n")


