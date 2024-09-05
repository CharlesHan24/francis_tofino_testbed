import sys
import os
verstr="3.5"
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
    teardown_hdls()

    msgs = ctrl_manager.retrieve_digest_msg()
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
    
    random.seed(0)
    parser = argparse.ArgumentParser(description='controller')
    parser.add_argument("--target", type=str, choices=["hw", "sim"], default="sim")
    parser.add_argument("--n", type=int, choices=[20, 15], default=15)
    parser.add_argument("--test_phase", type=int, default=0) # phase 0: testing the PTP without failing links. phase 1: + fast recovery. phase 2: + slow recovery.
    parser.add_argument("--skip_running", type=int, default=0)
    parser.add_argument("--bandwidth", type=int, default=10)
    args = parser.parse_args()

    graph = Graph(args.n)
    if args.target == "hw":
        graph.set_hw_mode()

    if args.n == 15:
        graph.construct_fattree_3_deformed()
    else:
        graph.construct_fattree_4()
    graph.spanning_tree()

    if args.test_phase >= 1:
        # failed_edge = (3, 10) if args.n == 15 else (4, 13)
        # failed_edge = (4, 2) if args.n == 15 else (4, 13)
        failed_edge = (0, 7) if args.n == 15 else (4, 13)
        graph.delete_edge(failed_edge[0], failed_edge[1]) # failed edge
    else:
        failed_edge = (-1, -1)

    slow_treeroots = get_slow_treeroots(args.n)

    if args.skip_running == 0:
        grpc_addr = "localhost:50052"
        ctrl_manager = Ctrl_Manager(grpc_addr)
        

        print("Bringing up ports.")
        if args.target == "sim":
            loopback_mode = "BF_LPBK_NONE"
        else:
            loopback_mode = "BF_LPBK_MAC_NEAR"

        if args.target == "sim":
            for i in range(graph.m):
                os.system("tc qdisc add dev veth{} root netem delay {}ms".format(i, 20))
        
        for i in range(graph.m):
            port_up(ctrl_manager, i, loopback_mode)
        
        port_up(ctrl_manager, RECIRC_PORT, loopback_mode)
        port_up(ctrl_manager, RECIRC_PORT ^ 1, loopback_mode)
        
        if args.target == "hw":
            assert(args.n == 15)
            

        print("Intiaializing the controllers...")

        def concat(cb_hdls, hdls):
            for hdl in hdls:
                cb_hdls.append(hdl)

        cb_hdls = []
        hdls = config_init_tree(ctrl_manager, graph)
        concat(cb_hdls, hdls)

        hdls = config_ma_tables(ctrl_manager, slow_treeroots, graph)
        concat(cb_hdls, hdls)

        hdls = config_other_register_tables(ctrl_manager, slow_treeroots, failed_edge[1], graph)
        concat(cb_hdls, hdls)

        hdls = config_mcast_rules(ctrl_manager, graph)
        concat(cb_hdls, hdls)

        hdls = config_egress_regs(ctrl_manager, graph)
        concat(cb_hdls, hdls)

        hdls = config_egress_tables(ctrl_manager, graph)
        concat(cb_hdls, hdls)

        hdls, teardown_hdls = config_timer_pktgen(ctrl_manager, graph, args)
        concat(cb_hdls, hdls)

        func = lambda: start_cb(cb_hdls)
    else:
        func = None
        teardown_hdls = None
    # captured_packets = tcpdump_sniffing(24, args.skip_running, cbs=func, teardown_hdls=teardown_hdls)
    #    captured_packets = extract_pkts(captured_packets)
    
    
    
    if 0 == 1:
        mn_time = captured_packets[0][0]
        mx_time_recons = 0
        mx_time_fast = 0
        for pkt in captured_packets:
            if pkt[2].type == TYPE_ALGO_SLOW_RECONS:
                mx_time_recons = max(mx_time_recons, pkt[0])
            if pkt[2].type == TYPE_ALGO_FAST:
                print(pkt[0] - mn_time)
                mx_time_fast = max(mx_time_fast, pkt[0])
        
        print("time elapsed for slow_recons = {}, fast = {}".format(mx_time_recons - mn_time, mx_time_fast - mn_time))

        # for pkt in captured_packets:
        #     print(pkt[0], pkt[1], pkt[2])

        print("Program finished.")
    
    if args.skip_running == 0:
        captured_packets = digest_sniffing(ctrl_manager, args.skip_running, cbs=func, teardown_hdls=teardown_hdls)
        pdb.set_trace()
        print("start analyzing packets...")
        print(len(captured_packets))

        for i in range(len(captured_packets)):
            captured_packets[i] = digest_pkts(captured_packets[i][0], captured_packets[i][1], captured_packets[i][2], captured_packets[i][3], captured_packets[i][4], captured_packets[i][5])

        with open("captured_packets_{}.dat".format(args.bandwidth), "wb") as f:
            pickle.dump(captured_packets, f)
    else:
        with open("captured_packets_{}.dat".format(args.bandwidth), "rb") as f:
            captured_packets = pickle.load(f)

    mx_time_recons = 0
    mx_time_fast = 0

    mn_time = captured_packets[0].ts
    mx_time_recons = 0
    mx_time_fast = 0
    pdb.set_trace()
    for pkt in captured_packets:
        if pkt.msg_type == TYPE_ALGO_SLOW_RECONS:
            mx_time_recons = max(mx_time_recons, pkt.ts)
        if pkt.msg_type == TYPE_ALGO_FAST:
            print(pkt.ts - mn_time)
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

    
    print("time elapsed for slow_recons = {}, fast = {}".format(mx_time_recons - mn_time, mx_time_fast - mn_time))
