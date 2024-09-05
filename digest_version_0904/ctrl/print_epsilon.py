import graph
import analysis_tools
import random
from scapy.all import *

import sys
verstr="3.9"
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/'))
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/bfrt_grpc/'))


veths = ["veth{}".format(i) for i in range(42)]
n = 15
all_pkts = [[] for i in range(n)]

fat_tree_graph = graph.Graph(15)
fat_tree_graph.construct_fattree_3_deformed()

for i in range(n):
    for v in fat_tree_graph.edge[i]:
        veth = "veth{}".format(fat_tree_graph.lookup_global_id_self(i, v))
        captured_packets = rdpcap("/home/wenchen_han_22/results_hardcases/tcpdump_newalgo_hard/{}.pcap".format(veth))
        for captured_packet in captured_packets:
            all_pkts[i].append([float(captured_packet.time), veth, analysis_tools.extract_pkt(captured_packet)])

    all_pkts[i] = sorted(all_pkts[i], key=lambda x: x[0])

from controller_init import *
depth_original = [0, 4, 4, 1, 3, 1, 3, 1, 3, 2, 2, 2, 2, 2, 2]
depth_fast = [7, 3, 3, 6, 4, 6, 4, 0, 2, 5, 5, 5, 5, 1, 1]

depth_slow = [4, 0, 2, 3, 1, 3, 1, 3, 1, 2, 2, 2, 2, 2, 2]

start_ts = -0.05 / 2 * 50000

delays = []

for i in range(n):
    delays.append(0)
    for pkt in all_pkts[i]:
        if pkt[2].type == TYPE_SYNC:
            delays[i] = (pkt[0] - all_pkts[0][0][0]) / 2 * 50000
            if delays[i] > 2000:
                delays[i] = 0
            break

first_algo_sync_time = []
for i in range(n):
    first_algo_sync_time.append(0)
    for pkt in all_pkts[i]:
        if pkt[2].type == TYPE_ALGO_FAST:
            first_algo_sync_time[i] = (pkt[0] - all_pkts[0][0][0] - 4) / 2 * 50000 + (100000 - start_ts)
            break

print(first_algo_sync_time, "123")
import numpy as np
print(list((np.array(first_algo_sync_time) - 100000) * 4 + 100000))
y = (np.array(first_algo_sync_time) - 100000) * 4 + 100000
print(y.var() ** 0.5)

max_cons_time = []
for i in range(n):
    max_cons_time.append(0)
    for j in range(len(all_pkts[i]) - 1, -1, -1):
        pkt = all_pkts[i][j]
        if pkt[2].type == TYPE_ALGO_SLOW_RECONS:
            # pdb.set_trace()
            max_cons_time[i] = (pkt[0] - all_pkts[0][0][0] - 4) / 1.008 * 51200 + (100000 - start_ts)
            break

print(max_cons_time)
print(list(np.array(max_cons_time) + 25000))
y = np.array(max_cons_time) + 25000
print(y.var() ** 0.5)

last_sync_time = [-1000000 for i in range(n)]
cur_ts = -500000

pdb.set_trace()
fout = open("epsilon2.txt", "w")
while cur_ts < 2500000:
    cur_ts += 10000 * (0.95 + random.random() * 0.1)

    if cur_ts < start_ts:
        for i in range(n):
            if cur_ts - last_sync_time[i] - delays[i] > 50000:
                last_sync_time[i] = cur_ts

        epsilon = (cur_ts - min(last_sync_time)) * 0.0002 + 20
    
    elif cur_ts < max(max_cons_time):
        for i in range(n):
            if cur_ts > first_algo_sync_time[i] and cur_ts - last_sync_time[i] - delays[i] > 50000:
                last_sync_time[i] = cur_ts
        epsilon = 0
        for i in range(n):
            if cur_ts > first_algo_sync_time[i]:
                epsilon = max(epsilon, (cur_ts - last_sync_time[i]) * 0.0002 + depth_fast[i] * 5)
            else:
                epsilon = max(epsilon, (cur_ts - last_sync_time[i]) * 0.0002 + 20)
    
    else:
        for i in range(n):
            if cur_ts - last_sync_time[i] > 50000:
                last_sync_time[i] = cur_ts
        epsilon = 0
        for i in range(n):
            epsilon = max(epsilon, (cur_ts - last_sync_time[i]) * 0.0002 + depth_slow[i] * 5)
    
    fout.write("{} {}\n".format(cur_ts + start_ts, epsilon))

