import sys, os, time, csv
from common import run_cmd, run_cmd_in_docker, check_cpu_count, fetch_works
from benchmark import generate_fuzzing_worklist

BASE_DIR = os.path.join(os.path.dirname(__file__), os.pardir)
IMAGE_NAME = "directed-benchmark-final"
SUPPORTED_TOOLS = \
  ["AFL", "AFLGo", "AFLPP", "Beacon", "WindRanger",
   "DAFL", "DAFL_noasan", "DAFL_select", "DAFL_schedule", "DAFL_poc", "DAFL_naive",
   "DAFL_line", "DAFL_line_noasan", "DAFL_line_select", "DAFL_line_schedule", "DAFL_line_poc",
   ## Semantic versions
   "DAFL_line_basic", "DAFL_line_wide", "DAFL_line_wider", "DAFL_line_multi_same", "DAFL_line_multi_diff", "DAFL_line_range", "DAFL_line_delicate", "DAFL_line_extreme",
   ## Semantic and select versions
    "DAFL_line_basic_select", "DAFL_line_wide_select", "DAFL_line_wider_select", "DAFL_line_multi_same_select", "DAFL_line_multi_diff_select", "DAFL_line_range_select", "DAFL_line_delicate_select", "DAFL_line_extreme_select",
   ]


def decide_outdir(exp_id, tool):
    prefix = exp_id + "-" + tool
    i = 0
    while True:
        i += 1
        outdir = os.path.join(BASE_DIR, "output", "%s-%d" % (prefix, i))
        if not os.path.exists(outdir):
            return outdir


def spawn_containers(works):
    for i in range(len(works)):
        targ_prog, _, _, iter_id = works[i]
        cmd = "docker run --tmpfs /box:exec --rm -m=4g --cpuset-cpus=%d -it -d --name %s-%s %s" \
                % (i, targ_prog, iter_id, IMAGE_NAME)
        run_cmd(cmd)


def run_fuzzing(works, tool, timelimit):
    for (targ_prog, cmdline, src, iter_id) in works:
        cmd = "/tool-script/run_%s.sh %s \"%s\" %s %d" % \
                (tool, targ_prog, cmdline, src, timelimit)
        run_cmd_in_docker("%s-%s" % (targ_prog, iter_id), cmd, True)


def wait_finish(works, timelimit):
    time.sleep(timelimit)
    total_count = len(works)
    elapsed_min = 0
    while True:
        if elapsed_min > 120:
            break
        time.sleep(60)
        elapsed_min += 1
        print("Waited for %d min" % elapsed_min)
        finished_count = 0
        for (targ_prog, _, _, iter_id) in works:
            container = "%s-%s" % (targ_prog, iter_id)
            stat_str = run_cmd_in_docker(container, "cat /STATUS", False)
            if "FINISHED" in stat_str:
                finished_count += 1
            else:
                print("%s-%s not finished" % (targ_prog, iter_id))
        if finished_count == total_count:
            print("All works finished!")
            break


def store_outputs(works, outdir):
    for (targ_prog, _, _, iter_id) in works:
        container = "%s-%s" % (targ_prog, iter_id)
        cmd = "docker cp %s:/output %s/%s" % (container, outdir, container)
        run_cmd(cmd)


def cleanup_containers(works):
    for (targ_prog, _, _, iter_id) in works:
        cmd = "docker kill %s-%s" % (targ_prog, iter_id)
        run_cmd(cmd)


def main():
    if len(sys.argv) != 5:
        print("Usage: %s <ID> <tool> <time> <iter>" % sys.argv[0])
        exit(1)

    exp_id = sys.argv[1]
    tool = sys.argv[2]
    timelimit = int(sys.argv[3])
    iteration = int(sys.argv[4])

    check_cpu_count()
    if tool not in SUPPORTED_TOOLS:
        print("Unsupported tool: %s" % tool)
        exit(1)

    worklist = generate_fuzzing_worklist(iteration)
    outdir = decide_outdir(exp_id, tool)
    os.makedirs(outdir)
    while len(worklist) > 0:
        targ_prog, _, _, _ = worklist[0]
        timelimit=int(sys.argv[3])
        works = fetch_works(worklist)
        spawn_containers(works)
        run_fuzzing(works, tool, timelimit)
        wait_finish(works, timelimit)
        store_outputs(works, outdir)
        cleanup_containers(works)


if __name__ == "__main__":
    main()
