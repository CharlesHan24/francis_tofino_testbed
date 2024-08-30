import sys
sys.path.insert(0, "../")
from ctrl import graph
import os
import pdb
import argparse
from scapy.all import *
import time
import random

def tcpdump(topo, n):
    for i in range(n):
        for v in topo.edge[i]:
            veth = "veth{}".format(topo.lookup_global_id_self(i, v))
            os.system("ip netns exec ns{} tcpdump -w /home/wenchen_han_22/{}.pcap -i {} -U &".format(i, veth, veth))

def ptp_trial(topo, n):
    os.system("ip netns exec ns0 ptp4l -f ./ptp4l_prio.conf -i veth0 -2 -S &")
    os.system("ip netns exec ns3 ptp4l -f ./ptp4l.conf -i veth9 -i veth10 -2 -S &")
    os.system("ip netns exec ns1 ptp4l -f ./ptp4l.conf -i veth3 -2 -S &")

def ptp_test(topo, n):
    for i in range(n):
        list_of_veths = []
        for v in topo.edge[i]:
            veth = "veth{}".format(topo.lookup_global_id_self(i, v))
            list_of_veths.append(veth)
        cmd = "ip netns exec ns{} ptp4l -2 -S ".format(i)
        if i == 0:
            cmd += "-f ./ptp4l_prio.conf"
        else:
            cmd += "-f ./ptp4l.conf"

        for veth in list_of_veths:
            cmd += " -i {}".format(veth)
        cmd += " &"
        os.system(cmd)
        time.sleep(0.01)

def ptp_link_fail_test(topo, n, log_announce_interval):
    for i in range(n):
        list_of_veths = []
        for v in topo.edge[i]:
            veth = "veth{}".format(topo.lookup_global_id_self(i, v))
            list_of_veths.append(veth)
        cmd = "ip netns exec ns{} ptp4l -2 -S ".format(i)
        if i == 0:
            cmd += "-f ./ptp4l_prio.conf"
        else:
            cmd += "-f ./ptp4l.conf"

        for veth in list_of_veths:
            cmd += " -i {}".format(veth)
        cmd += " &"
        os.system(cmd)
        time.sleep(0.05 * log_announce_interval)
    
    # sleeping for 15s for the network to converge
    print("Sleeping for 15s")
    time.sleep((15 + random.random()) * log_announce_interval)
    
    print("Link fail test. Cutting down a link between 0 and 3. Setting the loss rate to 100%")

    # os.system("ip netns exec ns0 tc qdisc change dev veth0 root netem loss 100%")
    os.system("ip netns exec ns0 ip link set dev veth0 down")
    os.system("ip netns exec ns3 ip link set dev veth9 down")
    # os.system("ip netns exec ns3 tc qdisc change dev veth9 root netem loss 100%")
    fout = open("down_ts.txt", "w")
    fout.write("{}\n".format(time.time()))
    print("time = {}".format(time.time()))

    time.sleep((40 + random.random()) * log_announce_interval)
    os.system("killall ptp4l")
    os.system("killall tcpdump")
    os.system("ip netns exec ns0 ip link set dev veth0 up")
    os.system("ip netns exec ns3 ip link set dev veth9 up")
    

def teardown(topo, n):
    for i in range(n):
        
        for j in range(topo.m):
            veth1 = "veth{}".format(j)
            os.system("ip netns exec ns{} ip link delete {} type veth".format(i, veth1))
        os.system("ip netns delete ns{}".format(i))

def analysis_sample():
    pass

# TODO: use pmc to dynamically change the identity of the grandmaster

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup network namespaces for ptp")

    parser.add_argument("--build", type=int, default=0)
    args = parser.parse_args()

    n = 15
    topo = graph.Graph(n=15)
    topo.set_orig_mode()
    topo.construct_fattree_3_deformed()

    log_announce_interval = 0.125

    if args.build == 2:
        teardown(topo, n)
        exit(0)

    if args.build == 1:
        for i in range(n): # setup network namespaces
            os.system("ip netns add ns{}".format(i))

        for i in range(n):
            for j in range(len(topo.edge[i])):
                v = topo.edge[i][j]
                if i > v:
                    continue
                veth1 = "veth{}".format(topo.lookup_global_id_self(i, v))
                veth2 = "veth{}".format(topo.lookup_global_id_self(v, i))
                
                os.system("ip link add {} type veth peer name {}".format(veth1, veth2))
                os.system("ip link set {} up".format(veth1))
                os.system("ip link set {} up".format(veth2))
                # pdb.set_trace()
                os.system("ip link set {} netns ns{}".format(veth1, i))
                os.system("ip link set {} netns ns{}".format(veth2, v))

                os.system("ip netns exec ns{} ip link set {} up".format(i, veth1))
                os.system("ip netns exec ns{} ip link set {} up".format(v, veth2))
                os.system("ip netns exec ns{} tc qdisc add dev {} root netem delay 0.6ms".format(i, veth1))
                os.system("ip netns exec ns{} tc qdisc add dev {} root netem delay 0.6ms".format(v, veth2))
                os.system("ip netns exec ns{} ip addr add 10.0.{}.{}/32 dev {}".format(i, i, j, veth1))
                os.system("ip netns exec ns{} ip addr add 10.0.{}.{}/32 dev {}".format(v, i, 254 - j, veth2))

    # launching ptp
    if args.build != 3:
        tcpdump(topo, n)
        ptp_link_fail_test(topo, n, log_announce_interval)
    
    # analysis
    analysis_sample()