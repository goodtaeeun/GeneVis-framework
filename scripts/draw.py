import os
import sys
import re
import difflib
import json
import shutil
from parse_result import *

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

ID_RE = r'id:(\d{6})'
PARENT_RE = r'src:([^,]+)'
SEC_RE = r'(\d+)\s+sec'
REP_RE = r'rep:(\d+)'
SEED_FULL_RE = r'Seed - (.*) \(found at'

seeds = {}
crashes = {}

def read_and_parse_seeds(indir):
    
    log_txt = open(os.path.join(indir,"seed_log.txt"), 'r')
    seed_list = []
    found_time_list = []
    for line in log_txt.readlines():
        mutation_string = ""
        if "Seed - " in line:
            full_name = re.search(SEED_FULL_RE, line).group(1)
            seed_id = int(re.search(ID_RE, line).group(1))
            found_time = int(re.search(SEC_RE, line).group(1))
            
            if "src:" not in line:
                # This is an initial seed
                parents =[]
            else:
                parents = re.search(PARENT_RE, line).group(1)
                if "+" in parents:
                    parents = parents.split("+")
                else:
                    parents = [parents]

                parents = [int(parent) for parent in parents]

                reps = re.search(REP_RE, line).group(1)
                mutation_string = f'{reps} operations overlapped'
                if "cov+" in line:
                    mutation_string += ", new branch edge covered"
                

            seeds[seed_id] = {
                "full_name": full_name,
                "parents": parents,
                "mutation": mutation_string
                }
            seed_list.append((seed_id, found_time))
            found_time_list.append(found_time)
    
    seed_list.reverse()
    max_time = max(found_time_list)
    
    # initialize the last seed with the largest time value (just in case)
    seed_id, _ = seed_list[0]
    seed_list[0] = seed_id, max_time
    
    prev_time = max_time
    for seed in seed_list:
        seed_id, found_time = seed
        if found_time > prev_time:
            seed_list[seed_list.index(seed)] = seed_id, prev_time
        else:
            prev_time = found_time
    
    seed_list.reverse()
    
    for seed in seed_list:
        seed_id, found_time = seed
        seeds[seed_id]["found_time"] = found_time

def read_and_parse_crashes(indir,target):
    imported_crashes = identify_crashes(target,indir)
    for crash in imported_crashes:
        crashes[crash] = imported_crashes[crash]

    


def calculate_found_time_delta():
    for seed in seeds:
        seed_id = seed
        found_time = seeds[seed]["found_time"]
        parents = seeds[seed]["parents"]
        if len(parents) == 0:
            seeds[seed]["time_delta"] = 0
        elif len(parents) == 1:
            parent_id = parents[0]
            parent_time = seeds[parent_id]["found_time"]
            delta = found_time - parent_time
            seeds[seed]["time_delta"] = delta
        elif len(parents) == 2:
            parent1_id = parents[0]
            parent2_id = parents[1]
            parent1_time = seeds[parent1_id]["found_time"]
            parent2_time = seeds[parent2_id]["found_time"]
            delta1 = found_time - parent1_time
            delta2 = found_time - parent2_time
            seeds[seed]["time_delta"] = min(delta1, delta2)
        else:
            print("Seed %d has more than 2 parents" % seed_id)
            seeds[seed]["time_delta"] = -1

    for crash in crashes:
        crash_id = crash
        found_time = crashes[crash]["found_time"]
        parents = crashes[crash]["parents"]
        if len(parents) == 0:
            crashes[crash]["time_delta"] = 0
        elif len(parents) == 1:
            parent_id = parents[0]
            parent_time = seeds[parent_id]["found_time"]
            delta = found_time - parent_time
            crashes[crash]["time_delta"] = delta
        elif len(parents) == 2:
            parent1_id = parents[0]
            parent2_id = parents[1]
            parent1_time = seeds[parent1_id]["found_time"]
            parent2_time = seeds[parent2_id]["found_time"]
            delta1 = found_time - parent1_time
            delta2 = found_time - parent2_time
            crashes[crash]["time_delta"] = min(delta1, delta2)
        else:
            print("Crash %d has more than 2 parents" % crash_id)
            crashes[crash]["time_delta"] = -1

def format_hexdump(hex_str, width=16):
    hex_lines = []
    for i in range(0, len(hex_str), width * 2):  # width * 2 because each byte is represented by two hex characters
        chunk = hex_str[i:i + width * 2]
        hex_chunk = ' '.join(chunk[j:j+2] for j in range(0, len(chunk), 2))
        hex_lines.append(hex_chunk)
    return hex_lines

# def format_diff(diff):
#     formatted_lines = []
#     for line in diff:
#         if line.startswith('---') or line.startswith('+++'):
#             formatted_lines.append(line)
#         elif line.startswith('@@'):
#             formatted_lines.append(line)
#         else:
#             # For context and change lines, format hex pairs with spaces for readability
#             prefix = line[0]
#             hex_pairs = ' '.join(line[1:][i:i+2] for i in range(0, len(line[1:]), 2))
#             formatted_lines.append(f'{prefix} {hex_pairs}')
#     return '\n'.join(formatted_lines)

def format_diff(diff):
    formatted_lines = []
    current_addition = []
    current_deletion = []

    for line in diff:
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            if current_addition:
                formatted_lines.append('+' + ' '.join(current_addition))
                current_addition = []
            if current_deletion:
                formatted_lines.append('-' + ' '.join(current_deletion))
                current_deletion = []
            formatted_lines.append(line)
        elif line.startswith('+'):
            if current_deletion:
                formatted_lines.append('-' + ' '.join(current_deletion))
                current_deletion = []
            current_addition.append(line[1:])
        elif line.startswith('-'):
            if current_addition:
                formatted_lines.append('+' + ' '.join(current_addition))
                current_addition = []
            current_deletion.append(line[1:])
        else:
            if current_addition:
                formatted_lines.append('+' + ' '.join(current_addition))
                current_addition = []
            if current_deletion:
                formatted_lines.append('-' + ' '.join(current_deletion))
                current_deletion = []
            formatted_lines.append(' ' + line)
    
    if current_addition:
        formatted_lines.append('+' + ' '.join(current_addition))
    if current_deletion:
        formatted_lines.append('-' + ' '.join(current_deletion))

    return '\n'.join(formatted_lines)


def calculate_mutation_delta(indir):
    for seed in seeds:
        parents = seeds[seed]["parents"]

        if parents == [] or len(parents) == 2:
            seeds[seed]["mutation_delta"] = ""
            continue
        
        parent_id = parents[0]
        
        f_name = seeds[seed]["full_name"]
        f_path = os.path.join(indir, "queue", f_name)
        f = open(f_path, "rb")
        seed_hex = f.read().hex()

        p_f_name = seeds[parent_id]["full_name"]
        p_f_path = os.path.join(indir, "queue", p_f_name)
        f = open(p_f_path, "rb")
        parent_hex = f.read().hex()

        diff = difflib.unified_diff(
        [seed_hex[i:i+2] for i in range(0, len(seed_hex), 2)],
        [parent_hex[i:i+2] for i in range(0, len(parent_hex), 2)],
        lineterm=''
        )
        
        formatted_diff = format_diff(diff)
        print("====================================")
        print(seed)
        print(formatted_diff)
        seeds[seed]["mutation_delta"] = formatted_diff

    for crash in crashes:
        parents = crashes[crash]["parents"]

        if parents == [] or len(parents) == 2:
            crashes[crash]["mutation_delta"] = ""
            continue
        
        parent_id = parents[0]
        
        f_name = crashes[crash]["full_name"]
        f_path = os.path.join(indir, "crashes", f_name)
        f = open(f_path, "rb")
        crash_hex = f.read().hex()

        p_f_name = seeds[parent_id]["full_name"]
        p_f_path = os.path.join(indir, "queue", p_f_name)
        f = open(p_f_path, "rb")
        parent_hex = f.read().hex()

        diff = difflib.unified_diff(
        [crash_hex[i:i+2] for i in range(0, len(crash_hex), 2)],
        [parent_hex[i:i+2] for i in range(0, len(parent_hex), 2)],
        lineterm=''
        )
                
        formatted_diff = format_diff(diff)
        # print(formatted_diff)
        crashes[crash]["mutation_delta"] = formatted_diff

        
def calculate_coverage(indir):
    for seed in seeds:
        f_name = seeds[seed]["full_name"]
        f_path = os.path.join(indir, "coverage", f_name)
        f = open(f_path, "r")
        covered_by_seed = f.read().splitlines()

        line_covered = False
        function_covered = False
        for line in covered_by_seed:
            if "[LINE]" in line:
                line_covered = True
            elif "[FUNCTION]" in line:
                function_covered = True
        cov_info = ""
        if function_covered:
            cov_info += "Covered target function"
        if line_covered:
            cov_info += ", Covered target line"
        
        seeds[seed]["coverage"] = cov_info


def generate_vis_dir(indir):
    # the base directory for the visualization files
    indir_name = os.path.basename(indir)

    # the output directory
    outdir = os.path.join(BASE_DIR, "output", indir_name + "-vis")
    

    if os.path.exists(outdir):
        shutil.rmtree(outdir)

    template_dir = os.path.join(BASE_DIR, "vis_template")
    shutil.copytree(template_dir, outdir)

    return outdir

def generate_json(outdir):
    ## First, generate the dictionary that defines the structure of the graph
    graph_dict = {
        "nodes": [],
        "edges": []
    }

    for seed in seeds:
        graph_dict["nodes"].append(str(seed))
        for parent in seeds[seed]["parents"]:
            graph_dict["edges"].append((str(parent), str(seed)))
    
    for crash in crashes:
        graph_dict["nodes"].append("Crash: " + crash)
        for parent in crashes[crash]["parents"]:
            graph_dict["edges"].append((str(parent), "Crash: " + crash))

    json_file = open(os.path.join(outdir, "seed_graph.json"), "w")
    json.dump(graph_dict, json_file)

    ## Second, generate the dictionary that defines the metadata of each node.

    metadata_dict = {
    }

    for seed in seeds:
        metadata_dict[str(seed)] = {
            "found_time": seeds[seed]["found_time"],
            "parents": seeds[seed]["parents"],
            "time_delta": seeds[seed]["time_delta"],
            "mutation": seeds[seed]["mutation"],
            "mutation_delta": seeds[seed]["mutation_delta"],
            "coverage": seeds[seed]["coverage"]
        }
    for crash in crashes:
        metadata_dict["Crash: " + crash] = {
            "found_time": crashes[crash]["found_time"],
            "parents": crashes[crash]["parents"],
            "time_delta": crashes[crash]["time_delta"],
            "mutation": crashes[crash]["mutation"],
            "mutation_delta": crashes[crash]["mutation_delta"],
            "coverage": ""
        }

    json_file = open(os.path.join(outdir, "metadata.json"), "w")
    json.dump(metadata_dict, json_file)

    ## Save mutation delta to a file
    mut_outdir = os.path.join(outdir, "mutation_delta")
    os.mkdir(mut_outdir)
    for seed in seeds:
        f = open(os.path.join(mut_outdir, str(seed) + ".txt"), "w")
        f.write(seeds[seed]["mutation_delta"])
        f.close()
    for crash in crashes:
        f = open(os.path.join(mut_outdir, "Crash: " + crash+ ".txt"), "w")
        f.write(crashes[crash]["mutation_delta"])
        f.close()

def export_outdir(outdir):
    export_dir = "/var/www/html/goodtaeeun/genevis/temp"
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    shutil.copytree(outdir, export_dir)

def main():
    if len(sys.argv) != 2:
        print("Usage: %s <input dir>" % sys.argv[0])
        exit(1)
    indir = sys.argv[1]
    target = os.path.basename(indir).split("-iter")[0]

    # Read and parse seeds
    read_and_parse_seeds(indir)
    # Read and parse crashes
    read_and_parse_crashes(indir,target)
    # Calculate delta between parent and the child
    calculate_found_time_delta()
    # Calculate mutation delta
    calculate_mutation_delta(indir)

    calculate_coverage(indir)
    
    outdir = generate_vis_dir(indir)
    generate_json(outdir)
    export_outdir(outdir)

    # just for now
    tmpdir = os.path.join(BASE_DIR, "output", "tmp")
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    shutil.copytree(outdir, tmpdir)


if __name__ == '__main__':
    main()