
import graph
import analysis_tools
import random
import pickle

random.seed(19)

TYPE_SYNC = 0x00
TYPE_ACK = 0x01
TYPE_PING_DETECTION = 0x02
TYPE_RECIRC = 0x03
TYPE_ALGO_SYNC = 0x04
TYPE_ALGO_FAST = 0x05
TYPE_ALGO_SLOW_RECONS = 0x06
TYPE_PING_ALGO = 0x07


f = open("captured_packets_{}_{}.dat".format(100, 3), "rb")

n = 15

captured_packets = pickle.load(f)

start_ts = -10000 - 30000 * random.random()


last_sync_time = [-1000000 for i in range(n)]
cur_ts = -1000000


fout = open("epsilon2.txt", "w")

depth_original = [0, 4, 4, 1, 3, 1, 3, 1, 3, 2, 2, 2, 2, 2, 2]
depth_fast = [7, 3, 3, 6, 4, 6, 4, 0, 2, 5, 5, 5, 5, 1, 1]

depth_slow = [4, 0, 2, 3, 1, 3, 1, 3, 1, 2, 2, 2, 2, 2, 2]


delays = []

for i in range(n):
    delays.append(0)
    for pkt in captured_packets:
        if pkt.msg_type == TYPE_SYNC and pkt.self_id == i:
            delays[i] = (pkt.ts - captured_packets[0].ts)
            if delays[i] > 3532:
                delays[i] = 3532
            break

first_algo_sync_time = []
for i in range(n):
    first_algo_sync_time.append(0)
    for pkt in captured_packets:
        if pkt.msg_type == TYPE_ALGO_FAST and pkt.self_id == i:
            first_algo_sync_time[i] = (pkt.ts - captured_packets[0].ts)  + (50000) - start_ts
            break

max_cons_time = []
for i in range(n):
    max_cons_time.append(0)
    for j in range(len(captured_packets) - 1, -1, -1):
        pkt = captured_packets[j]
        if pkt.msg_type == TYPE_ALGO_SLOW_RECONS and pkt.self_id == i:
            # pdb.set_trace()
            max_cons_time[i] = (pkt.ts - captured_packets[0].ts)  + (40000) - start_ts
            break
import pdb
pdb.set_trace()

delays_now = [50000 * (0.95 + random.random() * 0.1) for i in range(1000)]
top = [0 for i in range(n)]

while cur_ts < 2500000:
    cur_ts += 10000 * (0.95 + random.random() * 0.1)

    if cur_ts < 0:
        for i in range(n):
            if cur_ts - last_sync_time[i] - delays[i] > 50000:
                last_sync_time[i] += delays_now[top[i]] # cur_ts
                top[i] += 1

        epsilon = (cur_ts - min(last_sync_time)) * 0.0002 + 20
    
    # if cur_ts > 0:
        
        # pdb.set_trace()
    
    elif cur_ts < max(max_cons_time):
        top = [500 for i in range(n)]
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
        if top[0] == 500:
            for i in range(n):
                last_sync_time[i] = cur_ts
            top = [501 for i in range(n)]
        for i in range(n):
            if cur_ts - last_sync_time[i] - delays[i] > 50000:
                last_sync_time[i] += delays_now[top[i]] # cur_ts
                top[i] += 1
                # last_sync_time[i] = cur_ts
        epsilon = 0
        for i in range(n):
            epsilon = max(epsilon, (cur_ts - last_sync_time[i]) * 0.0002 + 20)
    
    fout.write("{} {}\n".format(cur_ts, epsilon))

