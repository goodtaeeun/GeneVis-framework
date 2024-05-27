import os
import sys

def reorder(base_dir):
    
    casedirs = os.listdir(os.path.join(base_dir))
    for casedir in casedirs:
        
        indirs = os.listdir(os.path.join(base_dir,casedir))
        for indir in indirs: ## this is reach iteration dirs
            
            log_txt = open(os.path.join(base_dir,casedir,indir,"seed_log.txt"), 'r')
            seed_list = []
            found_time_list = []
            for line in log_txt.readlines():
                if "Seed - " in line:
                    seed_id = line.split("id:")[1].split(" (found at")[0]
                    found_time = int(line.split("(found at ")[1].split(" sec.):")[0])
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

                
            out_txt = open(os.path.join(base_dir,casedir,indir,"reordered_seed_log.txt"), 'w')
            out_txt.write("Seed Replay log\n\n")
            
            for seed in seed_list:
                seed_id, found_time = seed
                out_txt.write("Seed - id:%s (found at %d sec.):\n\n" % (seed_id, found_time))
                    
            out_txt.close()



def main():
    if len(sys.argv) != 2:
        print("Usage: %s <input dir>" % sys.argv[0])
        exit(1)
    indir = sys.argv[1]

    reorder(indir)

if __name__ == '__main__':
    main()