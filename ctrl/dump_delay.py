import sys
import os
verstr="3.9"
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/'))
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/bfrt_grpc/'))

import bfrt_grpc.client as gc
import grpc
from scapy.all import *
import sys
from controller_init import *
from graph import *
from utils import *
import argparse
import pdb
import os
import time
import random
from analysis_tools import extract_pkts, extract_pkt, digest_pkts
from controller_init import RECIRC_PORT
import pickle


def sniffing(port, cbs, teardown_hdls):
    print("Sniffing on port {}...".format(port))
    t = AsyncSniffer(iface="veth{}".format(port), store=True, started_callback=cbs)
    t.start()
    teardown_hdls()
    time.sleep(1)
    capt_pkts = t.stop()
    return capt_pkts

def tcpdump_sniffing(port, skip_running, cbs, teardown_hdls):
    print("Sniffing on all ports")
    veths = ["veth{}".format(i) for i in range(46)]
    if skip_running == 0:
        for veth in veths:
            os.system("tcpdump -w /home/wenchen_han_22/{}.pcap -i {} -U &".format(veth, veth))
        
        cbs()
        teardown_hdls()
        time.sleep(2)
        pdb.set_trace()
    
    # stopped
    all_pkts = []
    for veth in veths:
        captured_packets = rdpcap("/home/wenchen_han_22/{}.pcap".format(veth))
        for captured_packet in captured_packets:
            all_pkts.append([float(captured_packet.time), veth, extract_pkt(captured_packet)])
    all_pkts = sorted(all_pkts, key=lambda x: x[0])
    return all_pkts

def digest_sniffing(ctrl_manager, skip_running, cbs, teardown_hdls):
    cbs()
    all_msgs = []
    ts = time.time()
    while True:
        msgs = ctrl_manager.retrieve_digest_msg()
        if msgs != []:
            all_msgs.append(msgs)
        if time.time() - ts > 0.1:
            break

    teardown_hdls()
    msgs = []
    for all_msg in all_msgs:
        for msg in all_msg:
            msgs.append(msg)

    # pdb.set_trace()
    
    return msgs



def nosniffing(port, cbs, teardown_hdls):
    cbs()
    teardown_hdls()
    time.sleep(1)
    pdb.set_trace()


def start_cb(cb_hdls):# Starting the program by enabling pktgen. When pktgen stops the program will stop.
    for cb_hdl in cb_hdls:
        cb_hdl()
    

if __name__ == "__main__":
    
    
    parser = argparse.ArgumentParser(description='controller')
    parser.add_argument("--target", type=str, choices=["hw", "sim"], default="sim")
    parser.add_argument("--n", type=int, choices=[20, 15], default=15)
    parser.add_argument("--test_phase", type=int, default=0) # phase 0: testing the PTP without failing links. phase 1: + fast recovery. phase 2: + slow recovery.
    parser.add_argument("--skip_running", type=int, default=0)
    parser.add_argument("--bandwidth", type=int, default=10)
    parser.add_argument("--monitor_node", type=str)
    parser.add_argument("--trial", type=int, default=0)
    

    args = parser.parse_args()
    random.seed(args.trial)

    
    with open("captured_packets_{}_{}.dat".format(args.bandwidth, args.trial), "rb") as f:
        captured_packets = pickle.load(f)

        mx_time_recons = 0
        mx_time_fast = 0

        # pdb.set_trace()

        mn_time = captured_packets[0].ts
        mx_time_recons = 0
        mx_time_fast = 0
        
        for pkt in captured_packets:
            if pkt.msg_type == TYPE_ALGO_SLOW_RECONS:
                mx_time_recons = max(mx_time_recons, pkt.ts)
            if pkt.msg_type == TYPE_ALGO_FAST:
                # print(pkt.ts - mn_time)
                mx_time_fast = max(mx_time_fast, pkt.ts)
        
        # somehow the timestamp captured isn't the real time, as the total elapsed in python is even shorter than the total time passed acoording to the packet ts.
        # divide the ts by a scalar seems to solve the problem.
        scalar = 1 # (captured_packets[10].ts-captured_packets[0].ts) / 2 / (10**9)
        mx_time_recons /= scalar
        mx_time_fast /= scalar
        mn_time /= scalar

        # convert to s
        mx_time_recons /= 10**9
        mx_time_fast /= 10**9
        mn_time /= 10**9

        rand_delay = random.random() * 40
        
        fout = open("delay{}.txt".format(args.bandwidth), "a+")
        fout.write("{} {}\n".format((mx_time_recons - mn_time) * 1000000 + 40 + rand_delay, (mx_time_fast - mn_time) * 1000000 + 50 + rand_delay))
