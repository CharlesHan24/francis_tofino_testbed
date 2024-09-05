import scapy
import pdb
from bfrt_grpc import client as gc
import math
import sys
import os
import pdb

from utils import *
from graph import Graph
verstr="3.5"
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/'))
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/bfrt_grpc/'))
"""
const bit<8> TYPE_SYNC = 0x00; // synchronization messages and ping_for_failure messages
const bit<8> TYPE_ACK = 0x01; // ACK messages
const bit<8> TYPE_PING_DETECTION = 0x02; // pkt_generator for failure detection
const bit<8> TYPE_RECIRC = 0x03; // recirculation messages in sync
const bit<8> TYPE_ALGO_SYNC = 0x04; // ALGO_SYNC
const bit<8> TYPE_ALGO_FAST = 0x05; // fast recovery
const bit<8> TYPE_ALGO_SLOW_RECONS = 0x06; // slow reconstruction
const bit<8> TYPE_PING_ALGO = 0x07;
"""

TYPE_SYNC = 0x00
TYPE_ACK = 0x01
TYPE_PING_DETECTION = 0x02
TYPE_RECIRC = 0x03
TYPE_ALGO_SYNC = 0x04
TYPE_ALGO_FAST = 0x05
TYPE_ALGO_SLOW_RECONS = 0x06
TYPE_PING_ALGO = 0x07

PKTGEN_PORT = 68
RECIRC_PORT = 54
MINUS_ONE_PORT = 0xf

NUM_PHYSICAL_PORTS = 64
CPU_PORT = 64

SIMULATION_TIME_MULTIPLIER = 40000

def get_slow_treeroots(n):
    # slow_treeroots = [1, 7, 5, 12] # [1, 9, 5, 12] for failed link == (3, 10)
    slow_treeroots = [1, 9, 6, 14]
    # slow_treeroots = [1, 4, 6, 12]
    random.shuffle(slow_treeroots)
    return slow_treeroots

def config_timer_pktgen(ctrl_manager, fat_tree_graph: Graph, cfgs): # cfgs parsed arguments
    pdb.set_trace()
    bfrt_info = ctrl_manager.bfrt_info

    src_port = PKTGEN_PORT # source port for the packet generator is 6 for the Tofino 2 model
    batch_count = 1
    n = fat_tree_graph.n
    packets_per_batch = n # n switches
    
    target = gc.Target(device_id=0, pipe_id=0xffff)
    pkt_buffer = simple_ipv4ip_packet()
    pktlen = len(pkt_buffer)
    buff_offset = 0

    pktgen_app_cfg_table = bfrt_info.table_get("app_cfg")
    pktgen_pkt_buffer_table = bfrt_info.table_get("pkt_buffer")
    pktgen_port_cfg_table = bfrt_info.table_get("port_cfg")

    # enble packet generation on the port
    pktgen_port_cfg_table.entry_mod(
                target,
                [pktgen_port_cfg_table.make_key([gc.KeyTuple('dev_port', src_port)])],
                [pktgen_port_cfg_table.make_data([gc.DataTuple('pktgen_enable', bool_val=True)])])

    # shared buffer across apps
    pktgen_pkt_buffer_table.entry_mod(
                target,
                [pktgen_pkt_buffer_table.make_key([gc.KeyTuple('pkt_buffer_offset', buff_offset),
                                                   gc.KeyTuple('pkt_buffer_size', (pktlen))])],
                [pktgen_pkt_buffer_table.make_data([gc.DataTuple('buffer', bytearray(bytes(pkt_buffer)))])])  # p[6:]))])

    # app 7
    period = 2520 * 10 * SIMULATION_TIME_MULTIPLIER # 1260 ns
    data = pktgen_app_cfg_table.make_data([gc.DataTuple('timer_nanosec', period),
                                            gc.DataTuple('app_enable', bool_val=False),
                                            gc.DataTuple('pkt_len', (pktlen)),
                                            gc.DataTuple('pkt_buffer_offset', buff_offset),
                                            gc.DataTuple('pipe_local_source_port', src_port),
                                            gc.DataTuple('increment_source_port', bool_val=False),
                                            gc.DataTuple('batch_count_cfg', batch_count - 1),
                                            gc.DataTuple('packets_per_batch_cfg', 1 - 1), # multicasted to all ports for all logical switches
                                            gc.DataTuple('ibg', 1),
                                            gc.DataTuple('ibg_jitter', 0),
                                            gc.DataTuple('ipg', 1000),
                                            gc.DataTuple('ipg_jitter', 500),
                                            gc.DataTuple('batch_counter', 0),
                                            gc.DataTuple('pkt_counter', 0),
                                            gc.DataTuple('trigger_counter', 0)],
                                            # "trigger_timer_one_shot")
                                            'trigger_timer_periodic')
    pktgen_app_cfg_table.entry_mod(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 7)])],
                [data])
    

    # app 2
    period = 50000 * SIMULATION_TIME_MULTIPLIER # 50000 ns
    data = pktgen_app_cfg_table.make_data([gc.DataTuple('timer_nanosec', period),
                                            gc.DataTuple('app_enable', bool_val=False),
                                            gc.DataTuple('pkt_len', (pktlen)),
                                            gc.DataTuple('pkt_buffer_offset', buff_offset),
                                            gc.DataTuple('pipe_local_source_port', src_port),
                                            gc.DataTuple('increment_source_port', bool_val=False),
                                            gc.DataTuple('batch_count_cfg', batch_count - 1),
                                            gc.DataTuple('packets_per_batch_cfg', packets_per_batch - 1),
                                            # gc.DataTuple('packets_per_batch_cfg', 0), # debug
                                            gc.DataTuple('ibg', 1),
                                            gc.DataTuple('ibg_jitter', 0),
                                            gc.DataTuple('ipg', 1000),
                                            gc.DataTuple('ipg_jitter', 500),
                                            gc.DataTuple('batch_counter', 0),
                                            gc.DataTuple('pkt_counter', 0),
                                            gc.DataTuple('trigger_counter', 0)],
                                            # "trigger_timer_one_shot")
                                            'trigger_timer_periodic')

    pktgen_app_cfg_table.entry_mod(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 2)])],
                [data])

    def pktgen_launch_handle(pktgen_app_cfg_table, target, cfgs):
        if cfgs.test_phase > 1:
            pktgen_app_cfg_table.entry_mod(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 7)])],
                [pktgen_app_cfg_table.make_data([gc.DataTuple('app_enable', bool_val=True)],
                                                'trigger_timer_periodic')]
            )
        
        pktgen_app_cfg_table.entry_mod(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 2)])],
                [pktgen_app_cfg_table.make_data([gc.DataTuple('app_enable', bool_val=True)],
                                                'trigger_timer_periodic')]
            )
        print(time.time())

    def pktgen_teardown_handle_wait(pktgen_app_cfg_table, target):
        cur_time = time.time()
        print(cur_time)
        while time.time() - cur_time < 100: # wait until 100s or until the trigger_counter reaches 100
            resp = pktgen_app_cfg_table.entry_get(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 2)])],
                #{"from_hw": True}
            )
            data_dict = next(resp)[0].to_dict()
            tri_value = data_dict["trigger_counter"]
            if tri_value >= 5:
                break
            time.sleep(0.1)
        print(time.time() - cur_time)

        pktgen_app_cfg_table.entry_mod(
            target,
            [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 2)])],
            [pktgen_app_cfg_table.make_data([gc.DataTuple('app_enable', bool_val=False)],
                                            'trigger_timer_periodic')]
        )

        while time.time() - cur_time < 100:
            resp = pktgen_app_cfg_table.entry_get(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 7)])],
                #{"from_hw": True}
            )
            data_dict = next(resp)[0].to_dict()
            tri_value = data_dict["trigger_counter"]
            if tri_value >= 55:
                break
            time.sleep(0.1)

        pktgen_app_cfg_table.entry_mod(
                target,
                [pktgen_app_cfg_table.make_key([gc.KeyTuple('app_id', 7)])],
                [pktgen_app_cfg_table.make_data([gc.DataTuple('app_enable', bool_val=False)],
                                                'trigger_timer_periodic')]
            )
        
        print(time.time() - cur_time)
        time.sleep(1)
        os.system("killall tcpdump")
        pdb.set_trace()

    return [Func_wrapper(pktgen_launch_handle, pktgen_app_cfg_table, target, cfgs)], Func_wrapper(pktgen_teardown_handle_wait, pktgen_app_cfg_table, target) # # launch pktgen after cunfigurations

def bincount(x):
    count = 0
    while x > 0:
        x &= x - 1
        count += 1
    return count

"""
ingress
"""

def config_init_tree(ctrl_manager: Ctrl_Manager, fat_tree_graph: Graph):
    bfrt_info = ctrl_manager.bfrt_info

    parent, children = fat_tree_graph.parent, fat_tree_graph.children
    n = fat_tree_graph.n

    # setup the tree_ver register, initialized to 0 for all
    ctrl_manager.reset_register("tree_ver")

    # setup the treeson register
    ctrl_manager.reset_register("treeson_port")
    for i in range(n): # for the 0th tree
        ctrl_manager.insert_entry("treeson_port", i, "f1", children[i])

    # setup the father register
    ctrl_manager.reset_register("father")
    for i in range(n):
        ctrl_manager.insert_entry("father", i, "f1", parent[i])
    for i in range(n, n * 6):
        ctrl_manager.insert_entry("father", i, "f1", -1)

    # configure the treeson_port_read_newtree_tab
    for i in range(6):
        for j in range(fat_tree_graph.n):
            ctrl_manager.table_add("treeson_port_read_newtree_tab", ["hdr.pld.tree_id", "hdr.pld.self_id"], [i, j], "treeson_port_read_action_wrap", ["index"], [i * fat_tree_graph.n + j])

    # configure comb_ignore_is_root
    ctrl_manager.reset_register("comb_ignore_is_root")
    for i in range(n): # for the 0th tree; for the j >= 1th tree, comb_ignore_is_root is 0
        ctrl_manager.insert_entry("comb_ignore_is_root", i, "f1", 3 if i == 0 else 1)

    return []


def config_other_register_tables(ctrl_manager: Ctrl_Manager, slow_treeroots, failed_node, fat_tree_graph: Graph):
    bfrt_info = ctrl_manager.bfrt_info

    # Configure msg_id_info
    ctrl_manager.reset_register("msg_id_info")
    msgid_entries = 2 ** (int(math.log2(20)) + 2)

    # batch_count = 500
    n = fat_tree_graph.n

    ctrl_manager.reset_register("msg_id_info")
    ctrl_manager.reset_register("msg_id_ping_info")
    # for i in range(msgid_entries):
    #     ctrl_manager.insert_entry("msg_id_info", i, "SwitchIngress.msg_id_info.f1", batch_count) # last message id to be infinity

    # configure depth
    ctrl_manager.reset_register("depth") # reset to 0 for all
    ctrl_manager.insert_entry("depth", 1 * n + failed_node, "SwitchIngress.depth.f1", 1)
    
    for i in range(4): # set the depth of the roots for each slow tree to 1
        ctrl_manager.insert_entry("depth", (i + 2) * n + slow_treeroots[i], "SwitchIngress.depth.f1", 1)

    # configure max_depth, initialized to 0
    ctrl_manager.reset_register("max_depth")

    # configure global_min_depth, initialized to 0x00.
    ctrl_manager.reset_register("global_min_depth")
    for i in range(n):
        if i not in slow_treeroots[0:4]:
            ctrl_manager.insert_entry("global_min_depth", i, "SwitchIngress.global_min_depth.f1", 0x70)

    # configure global_argmin_depth, initialized to self_id
    ctrl_manager.reset_register("global_argmin_depth")
    for i in range(n):
        ctrl_manager.insert_entry("global_argmin_depth", i, "SwitchIngress.global_argmin_depth.f1", i)

    # configure algo_sync_msg_cnt, initialized to 0
    ctrl_manager.reset_register("algo_sync_msg_cnt")

    return []

def config_ma_tables(ctrl_manager: Ctrl_Manager, slow_treeroots, fat_tree_graph: Graph):
    
    bfrt_info = ctrl_manager.bfrt_info
    target = gc.Target(device_id=0, pipe_id=0xffff)

    n = fat_tree_graph.n

    
    cur_root_map = [0 for i in range(n)]
    nslow_roots = 4
    ntrees = 6

    for i in range(nslow_roots): # 2~5
        cur_root_map[slow_treeroots[i]] = i + 2

    # initializing init_basic_info_tab
    # For ping messages
    total_entries = 0
    msg_types = [2, 7]
    for msg_type in msg_types:
        port = PKTGEN_PORT

        for i in range(ntrees): # number of trees
            
        
            for k in range(n):
                ctrl_manager.table_add("init_basic_info_tab", ["hdr.msg_type.type", "ig_intr_md.ingress_port", "hdr.pld.tree_id", "hdr.pld.self_id"], [msg_type, port, i, k], "init_ping_info_action", ["slow_recons_root", "neighbor_cnt", "ig_port_pow_2", "index"], [cur_root_map[k], fat_tree_graph.calc_neighbors(k) + 1, 0, i * n + k], is_ternary=True, ternary_mask_list=[-1, 255, -1, 255]) # 8 bts for self_id. msg_index = (cur_round (msg_id) % 2) << 5 + k.
                total_entries += 1

    # For recirc messages
    msg_type = 3 # TYPE_RECIRC
    for i in range(ntrees):
        
        port = RECIRC_PORT ^ 1 # ingress port for recirc messages is 55, and egress port for recirc messages is 54
        # (bit<32> self_id, bit<8> slow_recons_root, bit<32> neighbor_cnt, bit<32> ig_port_pow_2, bit<8> index)
    
        for k in range(n): # self_id

            ctrl_manager.table_add("init_basic_info_tab", ["hdr.msg_type.type", "ig_intr_md.ingress_port", "hdr.pld.tree_id", "hdr.pld.self_id"], [msg_type, port, i, k], "init_basic_info_action", ["self_id", "slow_recons_root", "neighbor_cnt", "ig_port_pow_2", "index"], [k, cur_root_map[k], fat_tree_graph.calc_neighbors(k) + 1, 0, i * n + k], is_ternary=True, ternary_mask_list=[-1, 255, -1, 255])
            total_entries += 1

    # For other messages
    msg_types = [0, 1, 4, 5, 6]
    for msg_type in msg_types:
        for self_id in range(n):
            for port_delta in range(len(fat_tree_graph.edge[self_id])):
                port = fat_tree_graph.lookup_global_id_self(self_id, fat_tree_graph.edge[self_id][port_delta]) # lookup the ingress port number of itself
                fake_redund_self_id_match = 0
                # if self_id < 12:
                #     port = port_delta + self_id * 4
                # else:
                #     port = 48 + (self_id - 12) * 2 + port_delta

                for k in range(ntrees):
                    ctrl_manager.table_add("init_basic_info_tab", ["hdr.msg_type.type", "ig_intr_md.ingress_port", "hdr.pld.tree_id", "hdr.pld.self_id"], [msg_type, port, k, fake_redund_self_id_match], "init_basic_info_action", ["self_id", "slow_recons_root", "neighbor_cnt", "ig_port_pow_2", "index"], [self_id, cur_root_map[self_id], fat_tree_graph.calc_neighbors(self_id) + 1, 1 << port_delta, k * n + self_id], is_ternary=True, ternary_mask_list=[-1, 255, -1, 0])
                    total_entries += 1
    # pdb.set_trace()

    # initializing algo_fast_non_root_tab
    ctrl_manager.table_add("algo_fast_non_root_tab", ["hdr.msg_type.type"], [2], "algo_fast_non_root_action", [], [])

    # initializing phase_12_launch_next_round_tab
    msg_type = 4 # TYPE_ALGO_SYNC
    recirc_idx = 0
    for self_id in range(n):
        ctrl_manager.table_add("phase_12_launch_next_round_tab", ["hdr.msg_type.type", "hdr.recirc_msg.recirc_idx", "hdr.pld.self_id", "hdr.pld.round_id"], [msg_type, recirc_idx, self_id, [0, 10]], "phase_12_launch_next_round_action", ["to_recirc", "recirc_idx", "recirc_tree_id", "to_ack"], [1, recirc_idx, (recirc_idx + 2) * n + self_id, 0]) # 
    
    msg_type = 3 # TYPE_PING_RECIRC
    for recirc_idx in range(3): # NOTE: 10 is the number of phase 1 + phase 2 rounds
        for self_id in range(n):
            ctrl_manager.table_add("phase_12_launch_next_round_tab", ["hdr.msg_type.type", "hdr.recirc_msg.recirc_idx", "hdr.pld.self_id", "hdr.pld.round_id"], [msg_type, recirc_idx, self_id, [0, 10]], "phase_12_launch_next_round_action", ["to_recirc", "recirc_idx", "recirc_tree_id", "to_ack"], [1 if recirc_idx <= 1 else 0, recirc_idx + 1, (recirc_idx + 3) * n + self_id, 1 if recirc_idx == 2 else 0])


    return []

"""
action mcast_action(MulticastGroupId_t mgrp1) {
    ig_intr_tm_md.mcast_grp_a = mgrp1;
}

table mcast_lookup_tab {
    key = {
        hdr.pld.self_id: exact; // switch id
        ig_md.mcast_bitmap: exact;
        ig_md.is_algo_sync: exact; // 1: sync.
        ig_md.unicast_port: exact; // initialized to -1 which means that we do not unicast
        ig_md.to_recirc: exact; // 1 to recirc and 0 to not recirc
        ig_md.to_ack: exact; // 1 to ack
    }
    actions = {
        mcast_action;
        NoAction;
    }
    size = 32768;
    default_action = NoAction();
}
"""

def calc_mcast_global_port_ids(fat_tree_graph: Graph, mcast_bitmap, self_id):
    i = 0
    ret_ports = []
    while mcast_bitmap > 0:
        if mcast_bitmap & 1:
            ret_ports.append(i)
        mcast_bitmap >>= 1
        i += 1
    return ret_ports

def calc_mcast_port_ids(fat_tree_graph: Graph, mcast_bitmap, self_id):
    # base_port = (4 * self_id if self_id < 12 else 48 + 2 * (self_id - 12))
    ret_ports = []
    for i in range(4):
        if mcast_bitmap & (1 << i):
            ret_ports.append(fat_tree_graph.lookup_global_id(self_id, fat_tree_graph.edge[self_id][i])) # egress port
    return ret_ports

def config_mcast_rules(ctrl_manager: Ctrl_Manager, fat_tree_graph: Graph):
    # initializing mcast_lookup_tab and tm rules for mcast
    
    bfrt_info = ctrl_manager.bfrt_info
    n = fat_tree_graph.n
    mcast_grp_id = -1

    for self_id in range(n): # for each switch
        msg_type = TYPE_ALGO_FAST

        for is_algo_sync in [0, 1]:
            to_recirc = 0
            num_neighbors = fat_tree_graph.calc_neighbors(self_id)
            unicast_port_list = [-1]
            for neighbor in fat_tree_graph.edge[self_id]:
                unicast_port_list.append(fat_tree_graph.lookup_global_id_self(self_id, neighbor)) # port number as appeared in the ingress pipeline should be "global_id_self"

            for unicast_port in unicast_port_list:

                for to_ack in [0, 1]:
                    
                    for mcast_bitmap in [0, (1 << num_neighbors) - 1]:

                        mcast_grp_id += 1
                        
                        mcast_port_ids = calc_mcast_port_ids(fat_tree_graph, mcast_bitmap, self_id)
                        rids = [0]
                        dpids = [mcast_port_ids]
                        if is_algo_sync == 1:
                            dpids.append(calc_mcast_port_ids(fat_tree_graph, (1 << num_neighbors) - 1, self_id))
                            rids.append(1)

                        if to_ack == 1 and unicast_port != -1:
                            eg_unicast_port = fat_tree_graph.igport_egport_translation(self_id, unicast_port)
                            dpids.append([eg_unicast_port])
                            rids.append(2)
                        

                        if mcast_bitmap != 0:
                            mcast_bitmap = MINUS_ONE_PORT
                        
                        ctrl_manager.add_multinode_mc_grp(mcast_grp_id, [dpids, rids])
                        ctrl_manager.table_add("mcast_lookup_tab", ["hdr.pld.self_id", "ig_md.mcast_bitmap", "ig_md.is_algo_sync", "ig_md.unicast_port", "ig_md.to_recirc", "ig_md.to_ack", "hdr.msg_type.type"], [self_id, mcast_bitmap, is_algo_sync, unicast_port, to_recirc, to_ack, msg_type], "mcast_action", ["mgrp1"], [mcast_grp_id])

        msg_types = [TYPE_ALGO_SLOW_RECONS]
        for msg_type in msg_types:
            for is_algo_sync in [0, 1]:
                for to_recirc in [0, 1]:
                    num_neighbors = fat_tree_graph.calc_neighbors(self_id)
                    to_ack = 0
                    
                    unicast_port_list = [-1]
                    for neighbor in fat_tree_graph.edge[self_id]:
                        unicast_port_list.append(fat_tree_graph.lookup_global_id_self(self_id, neighbor)) # port number as appeared in the ingress pipeline should be "global_id_self"

                    for unicast_port in unicast_port_list:
    
                        for mcast_bitmap in [0, (1 << num_neighbors) - 1]: # mcast groups will only be 0 or ALL, and if unicast_port_base != -1 then mcast_bitmap will be 0
                            if mcast_bitmap != 0 and unicast_port != -1:
                                continue
                            mcast_grp_id += 1
                            if unicast_port == -1:
                                mcast_port_ids = calc_mcast_port_ids(fat_tree_graph, mcast_bitmap, self_id)
                            else:
                                eg_unicast_port = fat_tree_graph.igport_egport_translation(self_id, unicast_port)
                                mcast_port_ids = [eg_unicast_port]
                            rids = []
                            dpids = []
                            if unicast_port != -1 or mcast_bitmap != 0:
                                rids.append(0)
                                dpids.append(mcast_port_ids)

                            if is_algo_sync == 1:
                                dpids.append(calc_mcast_port_ids(fat_tree_graph, (1 << num_neighbors) - 1, self_id))
                                rids.append(1)
                            

                            if to_recirc == 1:
                                if fat_tree_graph.mode == "sim": # carefully handle the case for recirculation port translation
                                    dpids.append([RECIRC_PORT])
                                else:
                                    dpids.append([RECIRC_PORT ^ 1])
                                rids.append(3)
                            
                            if mcast_bitmap != 0:
                                mcast_bitmap = MINUS_ONE_PORT

                            ctrl_manager.add_multinode_mc_grp(mcast_grp_id, [dpids, rids])
                            
                            
                            ctrl_manager.table_add("mcast_lookup_tab", ["hdr.pld.self_id", "ig_md.mcast_bitmap", "ig_md.is_algo_sync", "ig_md.unicast_port", "ig_md.to_recirc", "ig_md.to_ack", "hdr.msg_type.type"], [self_id, mcast_bitmap, is_algo_sync, unicast_port, to_recirc, to_ack, msg_type], "mcast_action", ["mgrp1"], [mcast_grp_id])
                                

        msg_type = TYPE_RECIRC # TYPE_RECIRC messages won't appear in the ingress pipeline
        msg_type = TYPE_ACK # ACK messages are dropped at the ingress pipeline

        msg_type = TYPE_PING_DETECTION # TYPE_PING_DETECTION messages are either dropped or converted to other message types

        # msg_type = TYPE_ALGO_SYNC # TYPE_ALGO_SYNC messages are all defaulted to be converted to other messages
        # is_algo_sync = 0
        # to_recirc = 0
        # num_neighbors = fat_tree_graph.calc_neighbors(self_id)
        # unicast_port_list = []
        # for neighbor in fat_tree_graph.edge[self_id]:
        #     unicast_port_list.append(fat_tree_graph.lookup_global_id(self_id, neighbor))
        
        # to_ack = 1
        # for ingress_port in unicast_port_list:
        #     dpids = []
        #     rids = []
        #     dpids.append([ingress_port])
        #     rids.append(2)
        #     mcast_grp_id += 1
        #     ctrl_manager.add_multinode_mc_grp(mcast_grp_id, [dpids, rids])

        #     ctrl_manager.table_add("mcast_lookup_tab", ["hdr.pld.self_id", "ig_md.mcast_bitmap", "ig_md.is_algo_sync", "ig_md.unicast_port", "ig_md.to_recirc", "ig_md.to_ack", "hdr.msg_type.type", "ig_intr_md.ingress_port"], [self_id, 0, is_algo_sync, -1, to_recirc, to_ack, msg_type, ingress_port], "mcast_action", ["mgrp1"], [mcast_grp_id], is_ternary=True, ternary_mask_list=[-1, -1, -1, -1, -1, -1, -1, 255])



        msg_type = TYPE_PING_ALGO # always broadcasted
        num_neighbors = fat_tree_graph.calc_neighbors(self_id)
        unicast_port = -1
        to_recirc = 0
        to_ack = 0
        mcast_bitmap = (1 << fat_tree_graph.m) - 1
        is_algo_sync = 0

        mcast_grp_id += 1 # Assuming that the multicast packets appear exactly in the same order as those that are specified in mcast_port_ids! This way, we guarantee that pinged sync packets for each logical switch are sent "atomically": sync packets of other switches are pinged after the current switch finishes.
        rids = []
        dpids = []
        for i in range(n):
            rids.append(i)
            dpid = []
            for neighbor in fat_tree_graph.edge[i]:
                dpid.append(fat_tree_graph.lookup_global_id(i, neighbor))
            dpids.append(dpid)
        # mcast_port_ids = calc_mcast_global_port_ids(fat_tree_graph, mcast_bitmap, self_id)
        # rids = [0]
        # dpids = [mcast_port_ids]

        mcast_port_ids = []
        for i in range(fat_tree_graph.n):
            y = fat_tree_graph.edge[i][0]
            mcast_port_ids.append(fat_tree_graph.lookup_global_id(y, i)) # pinging to itself
        rids.append(16)
        dpids.append(mcast_port_ids)

        ctrl_manager.add_multinode_mc_grp(mcast_grp_id, [dpids, rids])
        ctrl_manager.table_add("mcast_lookup_tab", ["hdr.pld.self_id", "ig_md.mcast_bitmap", "ig_md.is_algo_sync", "ig_md.unicast_port", "ig_md.to_recirc", "ig_md.to_ack", "hdr.msg_type.type"], [self_id, MINUS_ONE_PORT, is_algo_sync, unicast_port, to_recirc, to_ack, msg_type], "mcast_action", ["mgrp1"], [mcast_grp_id])

        msg_type = TYPE_SYNC # user packets
        unicast_port = -1
        to_recirc = 0
        to_ack = 0
        is_algo_sync = 0

        num_neighbors = fat_tree_graph.calc_neighbors(self_id)
        for mcast_bitmap in range(1 << num_neighbors):
            mcast_grp_id += 1
            mcast_port_ids = calc_mcast_port_ids(fat_tree_graph, mcast_bitmap, self_id)
            rids = [0]
            dpids = [mcast_port_ids]
            ctrl_manager.add_multinode_mc_grp(mcast_grp_id, [dpids, rids])
            ctrl_manager.table_add("mcast_lookup_tab", ["hdr.pld.self_id", "ig_md.mcast_bitmap", "ig_md.is_algo_sync", "ig_md.unicast_port", "ig_md.to_recirc", "ig_md.to_ack", "hdr.msg_type.type"], [self_id, mcast_bitmap, is_algo_sync, unicast_port, to_recirc, to_ack, msg_type], "mcast_action", ["mgrp1"], [mcast_grp_id])

    return []

    
    

"""
egress
"""

def config_egress_regs(ctrl_manager: Ctrl_Manager, fat_tree_graph: Graph):
    bfrt_info = ctrl_manager.bfrt_info

    # store_sync_round_id initialized to all-zeros
    ctrl_manager.reset_register("store_sync_round_id")
    for i in range(NUM_PHYSICAL_PORTS):
        ctrl_manager.insert_entry("store_sync_round_id", i, "SwitchEgress.store_sync_round_id.f1", 64)

    # last_transmitted_time initialized to all-zeros
    ctrl_manager.reset_register("last_transmitted_time")

    # queue_list1 set to all-zeros -- 2 bits
    ctrl_manager.reset_register("queue_list1")
    for i in range(NUM_PHYSICAL_PORTS):
        ctrl_manager.insert_entry("queue_list1", i, "SwitchEgress.queue_list1.f1", 0)

    # queue_list2 set to zero
    ctrl_manager.reset_register("queue_list2")
    for i in range(NUM_PHYSICAL_PORTS):
        ctrl_manager.insert_entry("queue_list2", i, "SwitchEgress.queue_list2.f1", 0)

    # algo_store_lower initialized to all-zeros
    ctrl_manager.reset_register("algo_store_lower")

    # algo_store_upper initialized to all-zeros
    # ctrl_manager.reset_register("algo_store_upper")

    return []


def config_egress_tables(ctrl_manager: Ctrl_Manager, fat_tree_graph: Graph):
    bfrt_info = ctrl_manager.bfrt_info

    # configuring lookup_pow2_recirc_idx
    """
    action lookup_pow2_recirc_idx_action(bit<8> pow2_result, bit<2> recirc_idx) {
        eg_md.pow2_result = pow2_result;
        eg_md.recirc_idx[1:0] = recirc_idx; // minus it by 2 for later indexing in register arrays.
        eg_md.recirc_idx[7:2] = (bit<6>) eg_intr_md.egress_port;
    }

    table lookup_pow2_recirc_idx {
        key = {
            hdr.recirc_msg.recirc_idx: exact;
        }
        actions = {
            lookup_pow2_recirc_idx_action;
            NoAction;
        }
        size = 4;
        default_action = NoAction();
    }
    """
    for recirc_idx in range(4):
        ctrl_manager.table_add("lookup_pow2_recirc_idx", ["hdr.recirc_msg.recirc_idx"], [recirc_idx], "lookup_pow2_recirc_idx_action", ["pow2_result", "recirc_idx"], [1 << recirc_idx, recirc_idx])
    
    # configuring lookup_lowbit_tab
    """
    action lookup_lowbit_action(bit<8> lowbit) {
        eg_md.index[1:0] = lowbit[1:0];
        eg_md.index[7:2] = eg_intr_md.egress_port[5:0];
    }

    table lookup_lowbit_tab {
        key = {
            eg_md.waiting_list: exact; // 1111xxxx
        }
        actions = {
            lookup_lowbit_action;
            NoAction;
        }
        size = 16;
        default_action = NoAction();
    }
    """
    for waiting_list in range(1, 16):
        for i in range(3, -1, -1):
            if (waiting_list & (1 << i)) != 0:
                lowbit = i
                break
        ctrl_manager.table_add("lookup_lowbit_tab", ["eg_md.waiting_list"], [waiting_list], "lookup_lowbit_action", ["lowbit"], [lowbit])

    # configuring comp_last_timestamp_tab
    """
    action comp_last_timestamp_action(bit<8> comp_last_timestamp_flag) {
        eg_md.comp_last_timestamp_flag = comp_last_timestamp_flag;
    }

    table comp_last_timestamp_tab {
        key = {
            eg_md.last_timestamp: ternary;
            // eg_intr_md_from_prsr.global_tstamp[31:0]: ternary; 
            eg_intr_md_from_prsr.global_tstamp: ternary; // NOTE: only looking at bits [31:0]
        }
        actions = {
            comp_last_timestamp_action;
        }
        size = 32;
        default_action = comp_last_timestamp_action(0);
    }
    """
    for i in range(31, -1, -1):
        mask = 1 << i
        priority = i
        ctrl_manager.table_add("comp_last_timestamp_tab", ["eg_md.last_timestamp", "eg_intr_md_from_prsr.global_tstamp", "$MATCH_PRIORITY"], [0, mask, priority], "comp_last_timestamp_action", ["comp_last_timestamp_flag"], [1], is_ternary=True, ternary_mask_list=[mask, mask, -1])
        # only set the case for eg_intr_md_from_prsr.global_tstamp > eg_md.last_timestamp (where comp_last_timestamp_flag = 1). Otherwise go to the default action where comp_last_timestamp_flag = 0
    
    # configuring retrans_slow_recons_msg_tab
    """
    action retrans_slow_recons_msg_action(bit<8> tree_id) {
        hdr.msg_type.type = TYPE_ALGO_SLOW_RECONS;
        // do not extract the recirc_idx?
        hdr.pld.tree_id = tree_id; // recirc_idx + 2
        hdr.pld.tree_depth = eg_md.store_content_lower[15:8];
        hdr.pld.round_id = eg_md.store_content_lower[23:16];
        hdr.pld.argmax = eg_md.store_content_upper;
        
    }

    table retrans_slow_recons_msg_tab {
        key = {
            hdr.msg_type.type: exact; // must be TYPE_PING_ALGO
            // eg_md.index[1:0]: exact;
            eg_md.index: ternary; // only looking at bits [1:0]
        }
        actions = {
            retrans_slow_recons_msg_action;
            NoAction;
        }
        size = 1;
        default_action = NoAction();
    }
    """

    msg_type = TYPE_PING_ALGO
    for i in range(4):
        ctrl_manager.table_add("retrans_slow_recons_msg_tab", ["hdr.msg_type.type", "eg_md.index"], [msg_type, i], "retrans_slow_recons_msg_action", ["tree_id"], [i + 2], is_ternary=True, ternary_mask_list=[-1, 3])
    
    """
    action egress_self_id_get_action(bit<8> self_id) {
        hdr.pld.self_id = self_id;
    }

    table egress_self_id_tab {
        key = {
            eg_intr_md.egress_port: exact;
        }
        actions = {
            egress_self_id_get_action;
            NoAction;
        }
        size = 64;
        default_action = NoAction();
    }
    """
    if fat_tree_graph.mode == "hw":
        for self_id in range(fat_tree_graph.n): # TODO: not working on sim topology
            for j, neighbor_id in enumerate(fat_tree_graph.edge[self_id]):
                ctrl_manager.table_add("egress_self_id_tab", ["eg_md.egress_port"], [fat_tree_graph.lookup_global_id(self_id, neighbor_id)], "egress_self_id_get_action", ["self_id", "peer_id", "peer_port", "count_incre"], [self_id, neighbor_id, fat_tree_graph.lookup_global_id_self(self_id, neighbor_id), (fat_tree_graph.calc_neighbors(self_id) + 1) if j == 0 else 0]) # egress
    else:
        for self_id in range(fat_tree_graph.n): 
            for j, neighbor_id in enumerate(fat_tree_graph.edge[self_id]):
                ctrl_manager.table_add("egress_self_id_tab", ["eg_md.egress_port"], [fat_tree_graph.lookup_global_id(self_id, neighbor_id)], "egress_self_id_get_action", ["self_id", "peer_id", "peer_port", "count_incre"], [self_id, neighbor_id, fat_tree_graph.lookup_global_id_self(neighbor_id, self_id), (fat_tree_graph.calc_neighbors(self_id) + 1) if j == 0 else 0]) # egress

    ctrl_manager.table_add("egress_self_id_tab", ["eg_md.egress_port"], [RECIRC_PORT ^ 1], "NoAction", [], []) # egress
    ctrl_manager.table_add("egress_self_id_tab", ["eg_md.egress_port"], [RECIRC_PORT], "NoAction", [], []) # egress
    ctrl_manager.table_add("egress_self_id_tab", ["eg_md.egress_port"], [CPU_PORT], "NoAction", [], []) # egress

    return []

# end of all the table/register/packet generator configurations



def port_up(ctrl_manager: Ctrl_Manager, port, loopback_mode):
    speed = "BF_SPEED_10G"
    fec = "BF_FEC_TYP_NONE"

    port_table = ctrl_manager.bfrt_info.table_get("$PORT")
    target = gc.Target(device_id=0, pipe_id=0xffff)
    
    port_table.entry_add(
        target,
        [port_table.make_key([gc.KeyTuple("$DEV_PORT", port)])],
        [port_table.make_data([gc.DataTuple("$SPEED", str_val=speed),
                                    gc.DataTuple("$FEC", str_val=fec),
                                    gc.DataTuple("$PORT_ENABLE", bool_val=True),
                                    gc.DataTuple("$LOOPBACK_MODE", str_val=loopback_mode)])])
    