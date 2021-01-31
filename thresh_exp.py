import sys
import math
import logging
import argparse
from collections import Counter
from time import perf_counter

from multiprocessing import Pool

from evaluate import evaluate, load_mesh, load_list

from tqdm import tqdm

def load_data(gen_kw_path, special_kw_path, min_spec_freq):
    special_keywords = {}
    general_keywords = {}

    len_general = 0
    len_special = 0

    with open(gen_kw_path, "r") as handle:
        len_general = handle.readline().split()[4]
        for line in handle:
            line = line.strip("\n").split()
            general_keywords[line[0]] = int(line[1])

    with open(special_kw_path, "r") as handle:
        len_special = handle.readline().split()[4]
        for line in handle:
            line = line.strip("\n").split()
            line[1] = int(line[1])
            if line[1] > min_spec_freq:
                special_keywords[line[0]] = line[1]
    
    return (special_keywords, len_special, general_keywords, len_general)

# Attribution note: this select_keywords function is mostly Jiahao Ma's 
# original code
def select_keywords(spec_freq_dic, len_special, gen_freq_dic, len_general, min_thresh, max_thresh):
    
    freq_dic = gen_freq_dic

    kw_special = set()
    
    for key, val in spec_freq_dic.items():
        kw_special.add(key)

        if key in freq_dic.keys():
            freq_dic[key] += 1
        else:
            freq_dic[key] = 1

#    f_special = {}
#    f_general = {}
    weirdness = {}
    # number of tokens
    N_special_count = int(len_special)
    N_general_count = int(len_general)

    k = []
    for key in freq_dic:
        if key in spec_freq_dic:
            if key in gen_freq_dic:
                k.append(key)
                weirdness[key] = (spec_freq_dic[key] * N_general_count) / \
                    ((gen_freq_dic[key] + 1) * N_special_count)

    avg_f = 0.0
    f_count = 0
    for key, value in spec_freq_dic.items():
        f_count += value
    avg_f = f_count / N_special_count

    sd_f = 0.0
    sd_f_upper = 0.0
    for key, value in spec_freq_dic.items():
        sd_f_upper += math.pow((value - avg_f), 2)

    sd_f_lower = N_special_count * (N_special_count - 1)

    sd_f = sd_f_upper / sd_f_lower

    avg_weird = 0.0
    avg_weird_upper = 0.0
    for key, value in weirdness.items():
        avg_weird_upper += value

    avg_weird = avg_weird_upper / N_special_count

    sd_avg_weird = 0.0
    sd_avg_weird_upper = 0.0

    for key, value in weirdness.items():
        sd_avg_weird_upper += math.pow((value - avg_weird), 2)

    sd_avg_weird = sd_avg_weird_upper / sd_f_lower
    
    # step 3 starts here

    for thresh in tqdm(range(min_thresh, max_thresh)):
        keywords = []
        z_score_freq_dict = {}
        z_score_weird_dict = {}

        for key in freq_dic:
            try:
                if key in kw_special:
                    z_score_freq_dict[key] = (spec_freq_dic[key] - avg_f) / sd_f
                    z_score_weird_dict[key] = (weirdness[key] - avg_weird) / sd_avg_weird
                    # you can change the threshold value here
                    if z_score_freq_dict[key] > thresh and z_score_weird_dict[key] > thresh:
                        keywords.append(key)
            except:
                pass

        yield (keywords, thresh)

def experiment_routine(gen_kw_path, special_kw_path, special_corpus_path, mesh_path, min_spec_freq):
    logger = logging.getLogger(__name__)
    logger.info("Loading data")
    (spec_freq_dic, len_special, gen_freq_dic, len_general) = load_data(gen_kw_path, special_kw_path, min_spec_freq)
    
    mesh = load_mesh(mesh_path)
    special_corpus = load_list(special_corpus_path)

    results = []
    min_thresh = 50
    max_thresh = 60

    logger.info(f"Min thresh: {min_thresh}")
    logger.info(f"Max thresh: {max_thresh}")
    logger.info("Starting thresholding")
    result_gen = select_keywords(spec_freq_dic, len_special, gen_freq_dic, len_general, min_thresh, max_thresh)
    
    pool = Pool(processes=8)

    futures = [pool.apply_async(evaluate, (special_corpus, keywords, mesh, 1000, thresh, False)) for (keywords, thresh) in result_gen]
    
    results = []
    for res in futures:
        results.append(res.get())
    #for (keywords, thresh) in result_gen:
    #    (p_val, res_int_len, rand_int_mean, rand_int_max) = evaluate(special_corpus, keywords, 
    #            mesh, 1000, verbose=False)

    #    results.append((thresh, p_val, res_int_len, rand_int_mean, rand_int_max))
    pool.close()
    pool.join()
    logger.info("Writing results")

    results = sorted(results, key=lambda res: res[0])

    with open("thresh_exp_res", "w") as out:
        out.write("threshold\tpval\tresult_intersect_len\trand_inter_mean_len\trand_inter_max\n")
        for res in results:
            out.write(f"{res[0]}\t{res[1]}\t{res[2]}\t{res[3]}\t{res[4]}\n")

def get_args():
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--general", help="Path to general keywords counts input", required=True)
    parser.add_argument("-s", "--special", help="Path to special keywords counts input", required=True)
    parser.add_argument("-c", "--corpus", help="Path to special corpus", required=True)
    parser.add_argument("-m", "--mesh", help="Path to lemmatized MeSH file", required=True)
    parser.add_argument("-t", "--trials", help="Number of random trials to run, default=10000",
            type=int, default=10000)
    parser.add_argument("-f", "--freq", help="Minimum occurrence frequency for special keywords, default=100",
            type=int, default=100)
    
    args = parser.parse_args()
   
    # log delimiter
    logger.info("###############################")
    logger.info(f"General kw counts: {args.general}")
    logger.info(f"Special kw counts: {args.special}")
    logger.info(f"Special corpus: {args.corpus}")
    logger.info(f"MeSH file: {args.mesh}")
    logger.info(f"Num. trials: {args.trials}")
    logger.info(f"Min spec freq: {args.freq}")

    return parser.parse_args()

def initialize_logger(debug=False, quiet=False):
    level = logging.INFO
    if debug:
        level = logging.DEBUG

    # Set up logging
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    handler = logging.FileHandler("threshold_experiment.log")
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

if __name__ == "__main__":
    logger = initialize_logger()
    args = get_args()
    experiment_routine(args.general, args.special, args.corpus, args.mesh, args.freq)
