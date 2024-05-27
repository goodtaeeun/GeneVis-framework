import sys, os
import pandas as pd
import csv
from benchmark import check_targeted_crash
from benchmark import FUZZ_TARGETS
SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))

REPLAY_LOG_FILE = "replay_log.txt"
REPLAY_SEED_FILE = "seed_log.txt"
FUZZ_LOG_FILE = "fuzzer_stats"
REPLAY_ITEM_SIG = "Replaying crash - "
ADDITIONAL_INFO_SIG = " is located "
FOUND_TIME_SIG = "found at "
CSV_COLUMNS = ["Target", "TTE", "Total Seeds", "TTF", "Seeds to Func", "TTL", "Seeds to Line", "Crash Found Time", "Line Reached Time", "Avg Diff Time"]

VAR_DICT_SEED = {
    "objdump-2.31.1-2018-17360": {
        "edt.eat_addr": set(),
        "edt.num_functions": set(),
        "index": set(),
    },
    "xmllint-2017-9048": {
        "len": set()
    },
    "cjpeg-2.0.4-2020-13790": {
       "*bufferptr": set()
    }
}

VAR_DICT_CRASH = {
    "objdump-2.31.1-2018-17360": {
        "edt.eat_addr": set(),
        "edt.num_functions": set(),
        "index": set(),
    },
    "xmllint-2017-9048": {
        "len": set()
    },
    "cjpeg-2.0.4-2020-13790": {
       "*bufferptr": set()
    }
}

def replace_none(tte_list, timeout):
    list_to_return = []
    for tte in tte_list:
        if tte is not None:
            list_to_return.append(tte)
        elif timeout != -1:
            list_to_return.append(timeout)
        else:
            print("[ERROR] Should provide valid T/O sec for this result.")
            exit(1)
    return list_to_return


def average_tte(tte_list, timeout):
    has_timeout = None in tte_list
    tte_list = replace_none(tte_list, timeout)
    if len(tte_list) == 0:
        return 0
    avg_val = sum(tte_list) / len(tte_list)
    prefix = "> " if has_timeout else ""
    return "%s%d" % (prefix, avg_val)


def median_tte(tte_list, timeout):
    tte_list = replace_none(tte_list, timeout)
    tte_list.sort()
    found_time = len(tte_list) - tte_list.count(timeout)
    n = len(tte_list)
    if n % 2 == 0: # When n = 2k, use k-th and (k+1)-th elements.
        i = int(n / 2) - 1
        j = int(n / 2)
        med_val = (tte_list[i] + tte_list[j]) / 2
        half_timeout = (tte_list[j] == timeout)
    else: # When n = 2k + 1, use (k+1)-th element.
        i = int((n - 1) / 2)
        med_val = tte_list[i]
        half_timeout = (tte_list[i] == timeout)
    prefix = "> " if half_timeout else ""
    if half_timeout:
        return "N.A. (%d)" % found_time
    else:
        return "%d" % med_val


def min_max_tte(tte_list, timeout):
    has_timeout = None in tte_list
    tte_list = replace_none(tte_list, timeout)
    max_val = max(tte_list)
    min_val = min(tte_list)
    prefix = "> " if has_timeout else ""
    return ("%d" % min_val, "%s%d" % (prefix, max_val))


def get_experiment_info(outdir):
    targ_list = []
    max_iter_id = 0
    for d in os.listdir(outdir):
        if d.endswith("-iter-0"):
            targ = d[:-len("-iter-0")]
            targ_list.append(targ)
        iter_id = int(d.split("-")[-1])
        if iter_id > max_iter_id:
            max_iter_id = iter_id
    iter_cnt = max_iter_id + 1
    return (targ_list, iter_cnt)


def parse_tte(targ, targ_dir):
    log_file = os.path.join(targ_dir, REPLAY_LOG_FILE)
    f = open(log_file, "r", encoding="latin-1")
    buf = f.read()
    f.close()
    while REPLAY_ITEM_SIG in buf:
        # Proceed to the next item.
        start_idx = buf.find(REPLAY_ITEM_SIG)
        buf = buf[start_idx + len(REPLAY_ITEM_SIG):]
        # Identify the end of this replay.
        if REPLAY_ITEM_SIG in buf:
            end_idx = buf.find(REPLAY_ITEM_SIG)
        else: # In case this is the last replay item.
            end_idx = len(buf)
        replay_buf = buf[:end_idx]
        # If there is trailing allocsite information, remove it.
        if ADDITIONAL_INFO_SIG in replay_buf:
            remove_idx = buf.find(ADDITIONAL_INFO_SIG)
            replay_buf = replay_buf[:remove_idx]
        if check_targeted_crash(targ, replay_buf):
            found_time = int(replay_buf.split(FOUND_TIME_SIG)[1].split()[0])
            return found_time
    # If not found, return a high value to indicate timeout. When computing the
    # median value, should confirm that such timeouts are not more than a half.
    return None

def read_sa_results():
    df = pd.read_csv(os.path.join(SCRIPT_PATH,'sa_overhead.csv'), delimiter='\t')
    targets= list(df['Target'])
    dafl = list(df['DAFL'])
    dafl_naive = list(df['DAFL_naive'])
    aflgo = list(df['AFLGo'])
    beacon = list(df['Beacon'])

    sa_dict={}
    for i in range(len(targets)):
        sa_dict[targets[i]] = { "DAFL" : dafl[i], 
                                "AFLGo" : aflgo[i],
                                "Beacon" : beacon[i],
                                "DAFL_naive" : dafl_naive[i]}
    return sa_dict

def read_log_file(log_file_path):
    if os.path.exists(log_file_path):    
        f = open(log_file_path, "r", encoding="latin-1")
        buf = f.readlines()
        f.close()
        return buf
    else:
        return []

def first_input_to_target(log_file, targ, VAR_DICT):
    input_to_func = ""
    input_to_line = ""
    total_count = 0
    func_count = 0
    line_count = 0
    is_target_reaching_line = False
    
    input_id = ""
    for line in log_file:
        
        if "Replaying input" in line:
            input_id = line.split("input - id:")[1].split(",")[0]
            total_count += 1
            # print("Input id %s is found" % input_id)
            is_target_reaching_line = False
        else:
            if "[TARGET]" in line :
                func_count += 1
                # print("TARGET is found in Input id %s" % input_id)
                if input_to_func == "":
                    input_to_func = input_id
            if "[LINE]" in line:
                line_count += 1
                is_target_reaching_line = True
                # print("LINE is found in Input id %s" % input_id)
                if input_to_line == "":
                    input_to_line = input_id
            if "@@@ " in line and is_target_reaching_line:
                var = line.split("@@@ ")[1].split(" ")[0]
                val = line.split("is ")[-1].strip().split("l")[0]

                if var in VAR_DICT[targ]:
                    VAR_DICT[targ][var].add(int(val))


                
        
        
    # print("Total count: %d, Func count: %d, Line count: %d" % (total_count, func_count, line_count))
    return input_to_func, input_to_line, func_count, line_count, total_count

def parse_ttt(targ, outdir, redir, iter_cnt):
    # redir has text files named as iteration number (ex. from 0 to 39)
    # It lists the seeds generated in that iteration and writes [Function] or [Line] after the id of each seed
    # if the seed covers the target function or line

    ## Iterate over the iterations of the experiment.

    ttt_func_list = []
    ttt_line_list = []
    seed_to_func_cnt_list = []
    seed_to_line_cnt_list = []
    seed_total_cnt_list = []
    
    for iter_id in range(iter_cnt):
        seed_log_file = read_log_file(os.path.join(redir, str(iter_id) + "-seed.log"))
        crash_log_file = read_log_file(os.path.join(redir, str(iter_id) + "-crash.log"))


        seed_time_to_func = 86400
        seed_time_to_line = 86400
        crash_time_to_func = 86400
        crash_time_to_line = 86400
        
        seed_to_func, seed_to_line, seed_to_func_cnt, seed_to_line_cnt, total_count = first_input_to_target(seed_log_file,targ, VAR_DICT_SEED)
        crash_to_func, crash_to_line, _, _, _ = first_input_to_target(crash_log_file,targ, VAR_DICT_CRASH)
        
        # # now read the original replay log and find the time-to-target for the seed
        # targ_dir = os.path.join(outdir, "%s-iter-%d" % (targ, iter_id))
        # orig_seed_log_file = read_log_file(os.path.join(targ_dir, REPLAY_SEED_FILE))
        # orig_crash_log_file = read_log_file(os.path.join(targ_dir, REPLAY_LOG_FILE))

        # # print("Iter is %d" % iter_id)
        # # print all seed_to_func, seed_to_line and crash_to_func, crash_to_line 
        # # print("Seed to func: %s, Seed to line: %s, Crash to func: %s, Crash to line: %s" % (seed_to_func, seed_to_line, crash_to_func, crash_to_line))

        # for line in orig_seed_log_file:
        #     if "Seed -" in line:
        #         seed_id = line.split("- id:")[1].split(",")[0]

        #         if seed_id == seed_to_func:
        #             seed_time_to_func = int(line.split("found at ")[1].split(" sec")[0])
        #             # print("Seed time to func: %d" % seed_time_to_func)
        #         if seed_id == seed_to_line:
        #             seed_time_to_line = int(line.split("found at ")[1].split(" sec")[0])
        #             # print("Seed time to line: %d" % seed_time_to_line)

        # for line in orig_crash_log_file:
        #     if "Replaying crash" in line:
        #         crash_id = line.split("- id:")[1].split(" (found at")[0]
        #         # print("%s" % crash_id)
        #         if crash_id == crash_to_func:
        #             crash_time_to_func = int(line.split("found at ")[1].split(" sec")[0])
        #             # print("Crash time to func: %d" % crash_time_to_func)
        #         if crash_id == crash_to_line:
        #             crash_time_to_line = int(line.split("found at ")[1].split(" sec")[0])
        #             # print("Crash time to line: %d" % crash_time_to_line)

        # ttt_func_list.append(min(seed_time_to_func, crash_time_to_func))
        # ttt_line_list.append(min(seed_time_to_line, crash_time_to_line))
        # seed_to_func_cnt_list.append(seed_to_func_cnt)
        # seed_to_line_cnt_list.append(seed_to_line_cnt)
        # seed_total_cnt_list.append(total_count)
    
    return
    
    # return ttt_func_list, ttt_line_list, seed_to_func_cnt_list, seed_to_line_cnt_list, seed_total_cnt_list




def analyze_targ_result(outdir, redir, timeout, targ, iter_cnt, writer):

    # sa_dict = read_sa_results()
    tool = outdir.split("/")[-1]

    tte_list = []
    timeout_list=[]
    targ_redir = os.path.join(redir, targ)

    parse_ttt(targ, outdir, targ_redir, iter_cnt)

    # for iter_id in range(iter_cnt):
    #     targ_dir = os.path.join(outdir, "%s-iter-%d" % (targ, iter_id))
    #     tte = parse_tte(targ, targ_dir)
    #     tte_list.append(tte)

    #     if tte == None:
    #         timeout_list.append(iter_id)

    # # if tool in ["AFLGo", "Beacon", "DAFL"]:
    # #     tte_list = [sa_dict[targ][tool] + tte if tte is not None else tte for tte in tte_list]
    # #     tte_list = [ tte if tte is None or tte < timeout else None for tte in tte_list]

    # tte_list = [ tte if tte is not None and tte < timeout else timeout for tte in tte_list]
    # for i in range(iter_cnt):
    #     if tte_list[i] < ttt_func_list[i]:
    #         ttt_func_list[i] = tte_list[i]
    #     if tte_list[i] < ttt_line_list[i]:
    #         ttt_line_list[i] = tte_list[i]
    #     if ttt_line_list[i] < ttt_func_list[i]:
    #         ttt_func_list[i] = ttt_line_list[i]
    
    # diff_time = [tte_list[i] - ttt_line_list[i] for i in range(iter_cnt) if tte_list[i] < timeout]

    # avg_total_seeds = int(sum(seed_total_cnt_list) / len(seed_total_cnt_list))
    # avg_seeds_to_func = int(sum(seed_to_func_cnt_list) / len(seed_to_func_cnt_list))
    # avg_seeds_to_line = int(sum(seed_to_line_cnt_list) / len(seed_to_line_cnt_list))

    # if len(diff_time) > 0:
    #     avg_diff_time = int(sum(diff_time) / len(diff_time))
    # else:
    #     avg_diff_time = timeout

    # found_time = len([x for x in tte_list if x < timeout])
    # line_reached_time = len([x for x in ttt_line_list if x < timeout])
    # if found_time > line_reached_time:
    #     line_reached_time = found_time

    # print("(Result of %s)" % targ)
    # print("Time-to-error: %s" % tte_list)
    # print("Time-to-target (function): %s" % ttt_func_list)
    # print("Time-to-target (line): %s" % ttt_line_list)
    # # print("Avg: %s" % average_tte(tte_list, timeout))
    # print("Med tte (found %d times): %s" % ( len([x for x in tte_list if x < timeout]) , median_tte(tte_list, timeout)))
    # print("Med ttfunction (found %d times): %s" % (len([x for x in ttt_func_list if x < timeout]) ,median_tte(ttt_func_list, timeout)))
    # print("Med ttline (found %d times): %s" % (len([x for x in ttt_line_list if x < timeout]) ,median_tte(ttt_line_list, timeout)))
    # print("Avg total Seeds: %d" % avg_total_seeds)
    # print("Avg Seeds to function: %d" % avg_seeds_to_func)
    # print("Avg Seeds to line: %d" % avg_seeds_to_line)
    # print("Avg diff time: %s" % avg_diff_time)

    # # print("Min: %s\nMax: %s" % min_max_tte(tte_list, timeout))
    # # if None in tte_list:
    # #     print("Found %d times" % (40 - timeout_times))
    # # print("Found iters: %s" % [x for x in range(0,40) if x not in timeout_list])
    # # print("Timeout iterations: %s" % timeout_list)
    # print("------------------------------------------------------------------")

    # writer.writerow([targ, median_tte(tte_list, timeout), avg_total_seeds, median_tte(ttt_func_list, timeout), avg_seeds_to_func, median_tte(ttt_line_list, timeout), avg_seeds_to_line, found_time, line_reached_time, avg_diff_time])


def main():
    if len(sys.argv) not in [3, 4]:
        print("Usage: %s <output dir> <replay dir> (timeout of the exp.)" % sys.argv[0])
        exit(1)
    outdir = sys.argv[1]
    redir = sys.argv[2]
    timeout = int(sys.argv[3]) if len(sys.argv) == 4 else 86400
    targ_list, iter_cnt = get_experiment_info(outdir)
    targ_list.sort()
    fuzz_targs = [x for (x, y, z, w) in FUZZ_TARGETS]

    output_file_name = redir.split("/")[-1]
    if output_file_name == "":
        output_file_name = redir.split("/")[-2]

    output_file = open(output_file_name+".csv", 'w')
    writer = csv.writer(output_file)
    # writer.writerow(CSV_COLUMNS)
    for targ in fuzz_targs:
        if targ in targ_list:
            analyze_targ_result(outdir,redir, timeout, targ, iter_cnt, writer)
        # else:
        #     writer.writerow([targ])
    output_file.close()

    print("Seed dict")
    for targ in VAR_DICT_SEED:
        print ("\n[Target: %s]" % targ)
        for var in VAR_DICT_SEED[targ]:
            print("Var is %s" % var)
            print("Min val is %s" % min(VAR_DICT_SEED[targ][var]))
            print("Max val is %s" % max(VAR_DICT_SEED[targ][var]))
            print("Cardinality of vals is %d" % len(VAR_DICT_SEED[targ][var]))
            print("%s\n" % (sorted(VAR_DICT_SEED[targ][var])))

    print("\n\n\nCrash dict")
    for targ in VAR_DICT_CRASH:
        print ("\n[Target: %s]" % targ)
        for var in VAR_DICT_CRASH[targ]:
            print("Var is %s" % var)
            print("Min val is %s" % min(VAR_DICT_CRASH[targ][var]))
            print("Max val is %s" % max(VAR_DICT_CRASH[targ][var]))
            print("Cardinality of vals is %d" % len(VAR_DICT_CRASH[targ][var]))
            print("%s\n" % (sorted(VAR_DICT_CRASH[targ][var])))


if __name__ == "__main__":
    main()
