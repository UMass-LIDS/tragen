from joint_dst import *
from constants import *
from collections import defaultdict
import datetime
import os
import time
import sys

class TraceGenerator():
    def __init__(self, trafficMixer, args):
        self.trafficMixer = trafficMixer
        self.args = args
        self.log_file = open("OUTPUT/logfile.txt" , "w")
        self.read_obj_size_dst()
        self.curr_iter = 0
        
    def generate(self):
        fd = self.trafficMixer.FD_mix

        ## object weight vector
        OWV = self.trafficMixer.weight_vector
        
        trafficClasses = self.trafficMixer.trafficClasses        
        
        fd.setupSampling(self.args.hitrate_type, 0, TB)

        MAX_SD = fd.sd_keys[-1]

        ## sample 70 million objects
        n_sizes = []
        sizes   = []
        i = -1
        for i in range(len(OWV)-1):
            SZ = self.sz_dsts[trafficClasses[i]]
            n_sizes.extend(SZ.sample_keys(int(70*MIL * OWV[i])))
        SZ = self.sz_dsts[trafficClasses[i+1]]
        n_sizes.extend(SZ.sample_keys(int(70*MIL) - len(n_sizes)))
        random.shuffle(n_sizes)
        sizes.extend(n_sizes)        

        ## Now fill the objects such that the stack is 10TB
        total_sz = 0
        total_objects = 0
        i = 0
        while total_sz < MAX_SD:
            total_sz += sizes[total_objects]
            total_objects += 1
            if total_objects % 10000 == 0:
                print("using ", total_objects, total_sz)

        ## debug file
        debug = open("OUTPUT/debug.txt", "w")

        ## build the LRU stack
        trace = range(total_objects)
        trace_list, ss = gen_leaves(trace, sizes)
        st_tree, lvl = generate_tree(trace_list)
        root = st_tree[lvl][0]
        root.is_root = True
        curr = st_tree[0][0]

        ## Initialize
        c_trace   = []
        tries     = 0
        i         = 0
        j         = 0
        k         = 0
        no_desc   = 0
        fail      = 0
        curr_max_seen = 0

        stack_samples = fd.sample(1000)

        sz_added   = 0
        sz_removed = 0
        evicted_   = 0

        sizes_seen  = []
        sds_seen    = []
        sampled_fds = []

        while curr != None and i <= int(self.args.length):
            if k >= 1000:
                stack_samples = fd.sample(1000)
                k = 0

            sd = stack_samples[k]
            k += 1

            end_object = False

            ## Introduce a new object
            if sd < 0:
                end_object = True
                sz_removed += curr.s
                evicted_ += 1
            else:
                sd = random.randint(sd, sd+200000)         

            if sd >= root.s:
                fail += 1
                continue
            
            n  = node(curr.obj_id, curr.s)        
            n.set_b()            
            c_trace.append(n.obj_id)        
            if curr.obj_id > curr_max_seen:
                curr_max_seen = curr.obj_id
            
            sampled_fds.append(sd)

            if end_object == False:

                try:
                    descrepency, land, o_id = root.insertAt(sd, n, 0, curr.id, debug)                            
                except:
                    print("sd : ", sd, root.s)
                
                local_uniq_bytes = 0

                debug.write("debugline : " + str(local_uniq_bytes) + " " + str(sd) + " " + str(root.s) + " " + str(descrepency) + "\n")

                if n.parent != None :
                    root = n.parent.rebalance(debug)

            else:
                while root.s < MAX_SD:

                    if (total_objects + 1) % (70*MIL) == 0:
                        sizes_n = sz_dst.sample_keys(70*MIL)
                        sizes.extend(sizes_n)
                
                    total_objects += 1
                    sz = sizes[total_objects]
                    sz_added += sz
                    n = node(total_objects, sz)
                    n.set_b()        
                    descrepency, x, y = root.insertAt(root.s - 1, n, 0, curr.id, debug)
            
                    if n.parent != None:
                        root = n.parent.rebalance(debug)

            next, success = curr.findNext()
            while (next != None and next.b == 0) or success == -1:
                next, success = next.findNext()

            del_nodes = curr.cleanUpAfterInsertion(sd, n, debug)        

            if i % 10001 == 0:
                self.log_file.write("Trace computed : " +  str(i) + " " +  str(datetime.datetime.now()) +  " " + str(root.s) + " " + str(total_objects) + " " + str(curr_max_seen) + " fail : " + str(fail) + " sz added : " + str(sz_added) + " sz_removed : " + str(sz_removed) + "\n")
                print("Trace computed : " +  str(i) + " " +  str(datetime.datetime.now()) +  " " + str(root.s) + " " + str(total_objects) + " " + str(curr_max_seen) + " fail : " + str(fail) + " sz added : " + str(sz_added) + " sz_removed : " + str(sz_removed) + " evicted : " +  str(evicted_))
                self.log_file.flush()
                self.curr_iter = i

            curr = next
            i += 1

        tm_now = int(time.time())
        os.mkdir("OUTPUT/" + str(tm_now))
        f = open("OUTPUT/" + str(tm_now) + "/gen_sequence.txt", "w")

        with open("OUTPUT/" + str(tm_now) + "/command.txt", 'w') as fp:
            fp.write('\n'.join(sys.argv[1:]))
        
        self.assign_timestamps(c_trace, sizes, fd.byte_rate, f)
        sys.exit(0)
            
    def assign_timestamps(self, c_trace, sizes, byte_rate, f):
        timestamp = 0
        KB_added = 0
        KB_rate = byte_rate/1000

        for c in c_trace:
            KB_added += sizes[c]
            f.write(str(timestamp) + "," + str(c) + "," + str(sizes[c]) + "\n")

            if KB_added >= KB_rate:
                timestamp += 1
                KB_added = 0
            
            
    def read_obj_size_dst(self):
        self.sz_dsts = defaultdict()

        for c in self.trafficMixer.trafficClasses:
            sz_dst = SZ_dst("FOOTPRINT_DESCRIPTORS/" + str(c) + "/iat_sz_all.txt", 0, TB)
            self.sz_dsts[c] = sz_dst

