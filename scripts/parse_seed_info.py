#!/usr/bin/env python3

import os
import sys
from parse_result import *

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_DIR = os.path.join(BASE_DIR, "output", "seed_graph")
CRASH_TOK = 'Replaying crash - '
SEED_TOK = 'Seed - '
TIME_START_TOK = ' (found at '
TIME_END_TOK = ' sec.'

SEED_DICT = {}

def read_file(filename):
    f = open(filename, "r")
    buf = f.readlines()
    f.close()
    return buf

def pick(line, start, end):
    return line.split(start)[1].split(end)[0].strip()



def run(indir, target):

    ex_id = indir.split("/")[-1]
    print(indir)
    print(ex_id)
    
    os.makedirs(os.path.join(OUT_DIR,ex_id,target), exist_ok=True)

    # Parse the seed info
    for iter_dir in os.listdir(indir):
        if target not in iter_dir:
            continue     
        iter = iter_dir.split("-iter-")[1]
        # 1. Read queue names and the inheritance info to form a node and edges, ans the timestamp too
        # 1-2. read form seed log to obtain this

        seed_file_string = read_file(os.path.join(indir, iter_dir, "seed_log.txt"))
        for line in seed_file_string:
            if SEED_TOK in line:
                seed_info = pick(line, SEED_TOK, TIME_START_TOK)
                seed_id = str(int(pick(seed_info, "id:", ",")))
                if "src:" in seed_info:
                    seed_source = [ str(int(x)) for x in pick(seed_info, "src:", ",op:").split("+")]
                else:
                    seed_source = []
                seed_time = pick(line, TIME_START_TOK, TIME_END_TOK)
                
                if iter in SEED_DICT:
                    SEED_DICT[iter][seed_id] = {
                        "source": seed_source,
                        "time": seed_time
                    }
                else:
                    SEED_DICT[iter] = {
                        seed_id: {
                            "source": seed_source,
                            "time": seed_time
                        }
                    }

        # 2. Obtain crash information using parse-result
        # 2-1. what is the target crash among the crashes and what are its parents

        ## find out what is crash
        found_time = parse_tte(target, os.path.join(indir, iter_dir))

        if found_time == None:
            continue
        else:
            ## get its info
            crash_file_string = read_file(os.path.join(indir, iter_dir, "replay_log.txt"))
            for line in crash_file_string:
                if CRASH_TOK in line:
                    crash_info = pick(line, CRASH_TOK, TIME_START_TOK)
                    crash_source = [ str(int(x)) for x in pick(crash_info, "src:", ",op:").split("+")]
                    crash_time = pick(line, TIME_START_TOK, TIME_END_TOK)


                    if int(found_time) == int(crash_time):
                        if iter in SEED_DICT:
                            SEED_DICT[iter]["crash"] = {
                                "source": crash_source,
                                "time": crash_time
                            }
                        else:
                            SEED_DICT[iter] = {
                                "crash": {
                                    "source": crash_source,
                                    "time": crash_time
                                }
                            }


    # 3. Convert the info into dot format. add crash id and the timestamp for the node lables.

    for iter in SEED_DICT:
        out_string = "digraph G {\n{\nnode [shape=box]\n"
        node_list = []
        edge_list = []

        for seed_id in SEED_DICT[iter]:
            label = seed_id + " " + SEED_DICT[iter][seed_id]["time"] + " sec"
            if seed_id == "crash":
                node_list.append("crash [label=\"" + label + "\" style=\"filled\" color=\"red\"]")
            else:
                node_list.append(seed_id+ "[label=\""+label+"\"]")
            
            for source in SEED_DICT[iter][seed_id]["source"]:
                edge_list.append(source + " -> " + seed_id)
        for node in node_list:
            out_string += (node + "\n")
        out_string += "}\n"
        for edge in edge_list:
            out_string += (edge + "\n")
        out_string += "}"

    # 4. if possible, add the coverage information for the nodes (optional)

    # 5. make output directory, containing one file for each iterations.
        f = open(os.path.join(OUT_DIR,ex_id,target,iter+"-seed_graph.dot"), "w")
        f.write(out_string)
        f.close()

    # 6. run dot to generate the graph image
        intput_file_path = os.path.join(OUT_DIR,ex_id,target,iter+"-seed_graph.dot")
        output_file_path = os.path.join(OUT_DIR,ex_id,target,iter+"-seed_graph.svg")

        os.system("dot -Tsvg -o" + output_file_path + " " + intput_file_path)


def main():

    if len(sys.argv) != 2:
        print("Usage: %s <outdir>" % sys.argv[0])
        exit(1)
    
    indir = sys.argv[1]
    # target = sys.argv[2]
    
    for target in ["swftophp-4.7-2016-9829", "swftophp-4.7-2017-9988"]:
        run(indir, target)




if __name__ == '__main__':
    main()
