// @compiler 9.9.1
#ifndef _FRANCIS_CLOCK_INGRESS_P4
#define _FRANCIS_CLOCK_INGRESS_P4

#include <core.p4>
#if __TARGET_TOFINO__ == 3
#include <t3na.p4>
#elif __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif
#include "header_parser.p4"

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/


// TODO: support emulation of multiple switches.

struct tree_info_t{
    bit<32> bitmap;
    bit<32> one_cnt;
}

struct glb_max_dep_t {
    bit<32> depth;
    bit<32> argmax;
}

control SwitchIngress(inout ig_headers hdr,
                inout ig_metadata_t ig_md,
                in ingress_intrinsic_metadata_t ig_intr_md,
                in ingress_intrinsic_metadata_from_parser_t ig_intr_prsr_md,
                inout ingress_intrinsic_metadata_for_deparser_t ig_intr_dprsr_md,
                inout ingress_intrinsic_metadata_for_tm_t ig_intr_tm_md) {

    Register<bit<8>, bit<8> >(NUM_VIRT_SWITCH) tree_ver;
    RegisterAction<bit<8>, bit<8>, bit<8> >(tree_ver) tree_ver_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value){
            read_value = value;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> >(tree_ver) tree_ver_write_action = {
        void apply(inout bit<8> value, out bit<8> read_value){
            value = ig_md.version;
            read_value = value;
        }
    };

    Register<bit<16>, bit<8> >(NUM_VIRT_SWITCH << 2) msg_id_info;
    RegisterAction<bit<16>, bit<8>, bit<16> >(msg_id_info) msgid_read_action = {
        void apply(inout bit<16> value, out bit<16> read_value){
            read_value = hdr.pld.msg_id - value;
        }
    };
    RegisterAction<bit<16>, bit<8>, bit<16> >(msg_id_info) msgid_write_action = {
        void apply(inout bit<16> value){
            value = hdr.pld.msg_id;
        }
    };

    Register<bit<16>, bit<8> > (NUM_VIRT_SWITCH << 2) msg_id_ping_info;
    RegisterAction<bit<16>, bit<8>, bit<16> >(msg_id_ping_info) msgid_ping_read_update_action = {
        void apply(inout bit<16> value, out bit<16> read_value){
            read_value = value + 1;
            value = value + 1;
        }
    };
    RegisterAction<bit<16>, bit<8>, bit<16> >(msg_id_ping_info) msgid_ping_read_action = {
        void apply(inout bit<16> value, out bit<16> read_value){
            read_value = hdr.pld.msg_id - value;
        }
    };

    Register<bit<16>, bit<8> >(NUM_VIRT_SWITCH) comb_ignore_is_root; // is_root << 1 | comb_ignore

    RegisterAction<bit<16>, bit<8>, bit<16> >(comb_ignore_is_root) comb_ignore_is_root_read_update_action = {
        void apply(inout bit<16> value, out bit<16> read_value){
            read_value = value;
            if (ig_md.diff_msg_id == 3) {
                value = 3; // is_root
            }
        }
    };

    RegisterAction<bit<16>, bit<8>, bit<16> >(comb_ignore_is_root) comb_ignore_is_root_write_action = {
        void apply(inout bit<16> value){
            value = ig_md.comb_ignore_is_root;
        }
    };

    Register<bit<32>, bit<8> >(TOTAL_SLOT * NUM_VIRT_SWITCH) treeson_port; // the bitmap is of its local port ids rather than global ones
    RegisterAction<bit<32>, bit<8>, bit<32> >(treeson_port) treeson_port_read_action = {
        void apply(inout bit<32> value, out bit<32> read_value){
            read_value = value;
        }
    };

    RegisterAction<bit<32>, bit<8>, bit<32> >(treeson_port) treeson_port_write_action = {
        void apply(inout bit<32> value, out bit<32> read_value){
            read_value = value;
            
            value = value | ig_md.ig_port_pow_2;
        }
    };

    action treeson_port_read_action_wrap(bit<8> index) {
        ig_md.mcast_bitmap = treeson_port_read_action.execute(index);
    }

    table treeson_port_read_newtree_tab {
        key = {
            hdr.pld.tree_id: exact; // < 6
            hdr.pld.self_id: exact; // < 20
        }
        actions = {
            treeson_port_read_action_wrap;
            NoAction();
        }
        size = 128;
        default_action = NoAction();
    }


    action mark_to_drop(){
        ig_intr_dprsr_md.drop_ctl = 1;
        exit;
    }

    // #define UNICAST(id) \
    // action unicast## id ##(bit<9> port){ \
    //     ig_intr_tm_md.ucast_egress_port = port; \
    // }
    // UNICAST(1)
    // UNICAST(2)
    // UNICAST(3)


    // action ing_to_bitmap_action(bit<32> port_bitmap) {
    //     ig_md.port_bitmap = port_bitmap;
    // }
    // table ing_to_bitmap_tab {
    //     key = {
    //         ig_intr_md.ingress_port: exact;
    //     }
    //     actions = {
    //         ing_to_bitmap_action;
    //         NoAction;
    //     }
    //     size = 33;
    //     default_action = NoAction();
    // }
    
    // #define BLANK_TAB(id) \
    // table ig_blank_tab## id ## { \
    //     key = { \
    //         hdr.ethernet.ethertype: exact; \
    //     } \
    //     actions = { \
    //         NoAction; \
    //     } \
    //     default_action = NoAction(); \
    // }
    
    // BLANK_TAB(1)

    Register<bit<8>, bit<8> > (TOTAL_SLOT * NUM_VIRT_SWITCH) depth;
    RegisterAction<bit<8>, bit<8>, bit<8> > (depth) depth_up_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
            if (value == 0){
                value = ig_md.depth;
            }
        }
    };

    RegisterAction<bit<8>, bit<8>, bit<8> > (depth) depth_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
        }
    };

    Register<bit<8>, bit<8> > (TOTAL_SLOT * NUM_VIRT_SWITCH) father; // recording the emulated global port id (ig_intr_md.ingress_port) rather than local port id
    RegisterAction<bit<8>, bit<8>, bit<8> > (father) father_write_action = {
        void apply(inout bit<8> value) {
            value = (bit<8>)ig_intr_md.ingress_port;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (father) father_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
        }
    };

    Register<bit<8>, bit<8> > (TOTAL_SLOT * NUM_VIRT_SWITCH) max_depth;
    RegisterAction<bit<8>, bit<8>, bit<8> > (max_depth) max_depth_update_action = {
        void apply(inout bit<8> value) {
            value = max(value, hdr.pld.tree_depth);
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (max_depth) max_depth_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value + 1; // return current max_depth + 1 for the next hop
        }
    };

    // Register<glb_max_dep_t, bit<8> > (1) global_max_depth;
    // RegisterAction<glb_max_dep_t, bit<8>, bit<32> > (global_max_depth) global_max_depth_update_action = {
    //     void apply(inout glb_max_dep_t value, out bit<32> read_value) {
    //         if (value.depth < hdr.pld.max_depth) {
    //             value.depth = hdr.pld.max_depth;
    //             value.argmax = hdr.pld.argmax;
    //         }
    //         read_value = value.argmax;
    //     }
    // };
    Register<bit<8>, bit<8> > (NUM_VIRT_SWITCH) global_min_depth;
    RegisterAction<bit<8>, bit<8>, bit<8> > (global_min_depth) global_min_depth_update_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            if (value > hdr.pld.tree_depth) {
                value = hdr.pld.tree_depth;
                read_value = 2;
            }
            else if (value == hdr.pld.tree_depth) {
                read_value = 1;
            }
            else {
                read_value = 0;
            }
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (global_min_depth) global_min_depth_updatemax_action = {
        void apply(inout bit<8> value) {
            if (value < hdr.pld.tree_depth) {
                value = hdr.pld.tree_depth;
            }
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (global_min_depth) global_min_depth_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
        }
    };
    Register<bit<8>, bit<8> > (NUM_VIRT_SWITCH) global_argmin_depth;
    RegisterAction<bit<8>, bit<8>, bit<8> > (global_argmin_depth) global_argmin_update_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            if (ig_md.is_incoming_smaller == 2) {
                value = hdr.pld.argmin;
            }
            else if (ig_md.is_incoming_smaller == 1) {
                value = min(value, hdr.pld.argmin);
            }
            read_value = value;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (global_argmin_depth) global_argmin_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
        }
    };

    Register<bit<32>, bit<8> > (256) algo_sync_msg_cnt;
    RegisterAction<bit<32>, bit<8>, bit<32> > (algo_sync_msg_cnt) algo_sync_msg_cnt_update_action = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            if (value + 1 == ig_md.neighbor_cnt) {
                value = 0;
            }
            else {
                value = value + 1;
            }
            read_value = value;
        }
    };

    
    

    action init_basic_info_action(bit<8> self_id, bit<8> slow_recons_root, bit<32> neighbor_cnt, bit<32> ig_port_pow_2, bit<8> index) {
        ig_md.ig_port_pow_2 = ig_port_pow_2;
        hdr.pld.self_id = self_id; // the logical switch id of itself. 
        /* the logical switch_id is assigned by the following rule:
        if (hdr.msg_type.type == TYPE_ALGO_PING || TYPE_PING_DETECTION || TYPE_RECIRC) then the switch id is carried by the message itself. Otherwise the switch_id = ingress_port / NUM_PORTS (per virt switch)
        */
        ig_md.index = index;
        ig_md.slow_recons_root = slow_recons_root; // 0: not a root. 2~5: roots
        ig_md.neighbor_cnt = neighbor_cnt; // how many packets expected to be received from 1) neighbors 2) itself indicating that the current node has finished sending out all the packets for this round
        ig_md.depth = hdr.pld.round_id + 1;
        ig_md.algo_sync_index[4:0] = self_id[4:0];
        ig_md.algo_sync_index[7:5] = hdr.pld.round_id[2:0];

        ig_intr_tm_md.copy_to_cpu = 1; 
    }

    action init_ping_info_action(bit<8> slow_recons_root, bit<32> neighbor_cnt, bit<32> ig_port_pow_2, bit<8> index) {
        ig_md.ig_port_pow_2 = ig_port_pow_2;
        ig_md.index = index;
        ig_md.slow_recons_root = slow_recons_root; // 0: not a root. 2~5: roots
        ig_md.neighbor_cnt = neighbor_cnt;
        ig_md.depth = hdr.pld.round_id + 1;
        ig_intr_tm_md.copy_to_cpu = 1; 
    }

    table init_basic_info_tab {
        key = {
            hdr.msg_type.type: exact;
            // ig_intr_md.ingress_port[7:0]: exact;
            ig_intr_md.ingress_port: ternary;
            hdr.pld.tree_id: exact;
            hdr.pld.self_id: ternary;
        }
        actions = {
            init_basic_info_action;
            init_ping_info_action;
            NoAction;
        }
        size = 5000;
        default_action = NoAction();
    }

    // recirc_idx range from 2 to 5
    // is_algo_sync = 1 for hdr.msg_type.type == TYPE_ALGO_SYNC or 0 for RECIRC messages; for the third phase, there won't be any recirc messages
    #define phase_launch_next_round_def(id) \
    action phase_## id ##_launch_next_round_action(bit<1> to_recirc, bit<8> recirc_idx, bit<8> recirc_tree_id, bit<1> to_ack) { \
        ig_md.to_recirc = to_recirc; \
        hdr.recirc_msg.recirc_idx = recirc_idx; \
        hdr.msg_type.type = TYPE_ALGO_SLOW_RECONS; \
        ig_md.is_algo_sync = to_ack; \
        ig_md.recirc_tree_id = recirc_tree_id; \
    } \
    table phase_## id ##_launch_next_round_tab { \
        key = { \
            hdr.msg_type.type: exact; \
            hdr.recirc_msg.recirc_idx: exact; \
            hdr.pld.self_id: exact; \
            hdr.pld.round_id: range; \
        } \
        actions = { \
            phase_## id ##_launch_next_round_action; \
        } \
        size = 256; \
        default_action = phase_## id ##_launch_next_round_action(0, 0, 0, 0); \
    }
    
    phase_launch_next_round_def(12)

   //action mcast_action(MulticastGroupId_t mgrp1, MulticastGroupId_t mgrp2) {
   action mcast_action(MulticastGroupId_t mgrp1) {
        ig_intr_tm_md.mcast_grp_a = mgrp1;
        // for monitoring
        //ig_intr_tm_md.mcast_grp_b = mgrp2;
    }

    table mcast_lookup_tab {
        key = {
            hdr.pld.self_id: exact; // switch id
            ig_md.mcast_bitmap: exact;
            ig_md.is_algo_sync: exact; // 1: sync.
            ig_md.unicast_port: exact; // initialized to -1 which means that we do not unicast
            ig_md.to_recirc: exact; // 1 to recirc and 0 to not recirc
            ig_md.to_ack: exact; // 1 to ack
            hdr.msg_type.type: exact;
        }
        actions = {
            mcast_action;
            mark_to_drop();
        }
        size = 4096;
        default_action = mark_to_drop();
    }

    // action dif_msg_id_comp_action() {
    //     ig_md.diff_msg_id = hdr.pld.msg_id - ig_md.msg_id;
    // }

    // table dif_msg_id_comp_tab {
    //     key = {
    //         hdr.msg_type.type: exact; // must be TYPE_PING_DETECTION
    //     }
    //     actions = {
    //         dif_msg_id_comp_action;
    //     }
    //     size = 1;
    //     default_action = dif_msg_id_comp_action();
    // }

    action algo_fast_non_root_action() {
        ig_md.to_ack = 1;
        ig_md.is_algo_sync = 1;
        ig_md.mcast_bitmap = MINUS_ONE; // broadcast
        ig_md.unicast_port = ig_intr_md.ingress_port[7:0];
    }

    table algo_fast_non_root_tab {
        key = {
            hdr.msg_type.type: exact; // must be TYPE_PING_DETECTION
        }
        actions = {
            algo_fast_non_root_action;
        }
        size = 1;
        default_action = algo_fast_non_root_action();
    }

    // action argmax_init_action(){
    //     hdr.pld.argmax = hdr.pld.self_id;
    // }

    // table argmax_init_tab {
    //     key = {
    //         hdr.msg_type.type: exact;
    //     }
    //     actions = {
    //         argmax_init_action;
    //         NoAction;
    //     }
    //     size = 1;
    //     default_action = NoAction();
    // }

    action last_depth_plus_round_id_action() {
        ig_md.last_depth_plus_round_id = ig_md.last_depth + hdr.pld.round_id;
    }
    table last_depth_plus_round_id_tab {
        key = {
            
        }
        actions = {
            last_depth_plus_round_id_action;
        }
        size = 1;
        default_action = last_depth_plus_round_id_action();
    }

    Register<bit<8>, bit<8> > (1) ping_algo_counter;
    RegisterAction<bit<8>, bit<8>, bit<8> > (ping_algo_counter) ping_algo_counter_update_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value + 1;
            value = value + 1;
        }
    };

    apply {
        @stage(0){
            init_basic_info_tab.apply();
        }
        // TODO: notice that for general algorithms, there's a potential bug regarding read/write conflict. For a round, if a write operation generated from processing a neighboring packet happens before a read operation for ALGO_SYNC + sending the SLOW_RECONS packet, then we could be reading the wrong value since the value was updated upon the write operation.
        // In our example, however, we don't have such concern since every read operation is robust to the write operation: at stage i we only process nodes of depth#i. Thus the write operation for nodes of depths #i+1 will not affect the read operation for nodes of depth #i.
        if ((hdr.msg_type.type == TYPE_RECIRC) || (hdr.msg_type.type == TYPE_ALGO_SYNC)) { // TYPE_RECIRC or TYPE_ALGO_SYNC
            if (hdr.msg_type.type == TYPE_ALGO_SYNC) {
                @stage(1){
                    ig_md.total_cnt = algo_sync_msg_cnt_update_action.execute(ig_md.algo_sync_index);
                }
            }
            if ((ig_md.total_cnt == 0) || (hdr.msg_type.type == TYPE_RECIRC)) {
                if (hdr.msg_type.type == TYPE_ALGO_SYNC) {
                    @stage(2){
                        hdr.pld.round_id = hdr.pld.round_id + 1;
                        hdr.recirc_msg.setValid(); // to be consistent with hdr.pld.round_id <= PHASE_2 cases
                        hdr.recirc_msg.recirc_idx = 0;
                    }
                }
                
                @stage(3){
                    phase_12_launch_next_round_tab.apply();
                }
                
                
                if (hdr.pld.round_id <= PHASE_2) { // PHASE_1 and PHASE_2. NOTE: let one extra round in case max_depth is not fully propagated
                    @stage(4){
                        ig_md.last_depth = depth_read_action.execute(ig_md.recirc_tree_id);
                    }

                    last_depth_plus_round_id_tab.apply();
                    
                    if (ig_md.last_depth_plus_round_id == PHASE_2 + 2) {
                        @stage(8){
                            hdr.pld.tree_depth = max_depth_read_action.execute(ig_md.recirc_tree_id);
                        }

                        @stage(10){
                            ig_md.unicast_port = father_read_action.execute(ig_md.recirc_tree_id);
                        }
                    }

                    else if (ig_md.last_depth == hdr.pld.round_id) {
                        ig_md.mcast_bitmap = MINUS_ONE;
                    }

                    // if (hdr.msg_type.type == TYPE_RECIRC) {
                    //     hdr.recirc_msg.recirc_idx += 1;
                    //     if (hdr.recirc_msg.recirc_idx < 4) {
                    //         ig_md.to_recirc = 1;
                    //     }
                    // }
                    // else {
                    //     hdr.recirc_msg.recirc_idx = 1;
                    //     ig_md.to_recirc = 1;
                    // }

                    // hdr.msg_type.type = TYPE_ALGO_SLOW_RECONS;
                    // ig_md.is_algo_sync = 1;
                    
                    
                }

                else if (hdr.pld.round_id <= PHASE_3) { // no recirculation at phase 3, so hdr.msg_type.type == TYPE_ALGO_SYNC
                    
                    @stage(4){
                        hdr.pld.tree_depth = global_min_depth_read_action.execute(hdr.pld.self_id);
                    }
                    
                    @stage(5){
                        hdr.pld.argmin = global_argmin_read_action.execute(hdr.pld.self_id);
                    }
                    

                    
                    hdr.msg_type.type = TYPE_ALGO_SLOW_RECONS;
                    ig_md.is_algo_sync = 1;
                    // ig_md.to_ack = 1;
                    ig_md.mcast_bitmap = MINUS_ONE;
                }
                
                else {
                    mark_to_drop(); // hdr.pld.round_id == PHASE_3 means that all 3 phases have been completed
                }
            }
            // else if (ig_md.total_cnt == 0) {
            //     ig_md.to_ack = 1;
            // }
            // mcast_lookup_tab will default the "else" branch to mark_to_drop()
            // else {
            //     mark_to_drop();
            // }
        }

        else if (hdr.msg_type.type == TYPE_ALGO_SLOW_RECONS) {
            if (hdr.pld.round_id <= PHASE_1) { // broadcast
                @stage(4){
                    ig_md.last_depth = depth_up_action.execute(ig_md.index);
                }
                
                if (ig_md.last_depth == 0) {
                    // ig_md.to_ack = 1; // NOTE: done in the second phase. see line 510: treeson_port_write_action.execute(ig_md.index);
                    // hdr.msg_type.type = TYPE_ACK;
                    // @stage(7){
                    //     comb_ignore_is_root_write_action.execute(hdr.pld.self_id);
                    // }
                    @stage(10){
                        father_write_action.execute(ig_md.index);
                    }
                }
            }
            else if (hdr.pld.round_id <= PHASE_2) {
                
                if (hdr.pld.tree_id == ig_md.slow_recons_root){
                    @stage(4){
                        global_min_depth_updatemax_action.execute(hdr.pld.self_id);
                    }
                }
                // global_argmax_update_action.execute(hdr.pld.self_id); No need to update argmax for now since it'll be initialized to self_id. TODO in the control plane.

                @stage(8){
                    max_depth_update_action.execute(ig_md.index);
                }

                @stage(9){
                    treeson_port_write_action.execute(ig_md.index);
                }
            }
            else {
                @stage(4){
                    ig_md.is_incoming_smaller = (bit<8>) global_min_depth_update_action.execute(hdr.pld.self_id);
                }
                bit<8> argmin;
                @stage(5){
                    argmin = global_argmin_update_action.execute(hdr.pld.self_id);
                }
                if (hdr.pld.round_id == PHASE_3) {
                    if (argmin == hdr.pld.self_id) {
                        ig_md.comb_ignore_is_root = 3;
                        ig_md.version = ig_md.slow_recons_root;
                    }
                    else {
                        ig_md.comb_ignore_is_root = 1;
                        ig_md.version = ig_md.slow_recons_root;
                    }
                    
                    // ig_md.version = ig_md.slow_recons_root;
                    @stage(7){
                        comb_ignore_is_root_write_action.execute(hdr.pld.self_id); // TODO: combine comb_ignore_is_root and tree_ver
                    }
                    
                    if (argmin == hdr.pld.self_id){
                        @stage(8){
                            tree_ver_write_action.execute(hdr.pld.self_id);
                        }
                    }
                }
            }

            mark_to_drop(); // drop anyway
        }

        else if (hdr.msg_type.type == TYPE_ALGO_FAST) {
            // ig_md.comb_ignore_is_root = 1;
            
            bit<8> last_depth;
            
            @stage(4){
                last_depth = depth_up_action.execute(ig_md.index); // here we don't actually care about the depth value itself, but whether it's >= 1 or not. Within the function, ig_md.depth will always be 0
            }
            @stage(5){
                msgid_write_action.execute(hdr.pld.self_id);
            }
            
            if (last_depth == 0) {
                @stage(7){
                    comb_ignore_is_root_write_action.execute(hdr.pld.self_id); // ig_md.comb_ignore_is_root is defaulted to be 1;
                }
                @stage(8){
                    algo_fast_non_root_tab.apply();
                }
                // ig_md.to_ack = 1;
                // ig_md.is_algo_sync = 1;
                // ig_md.mcast_bitmap = MINUS_ONE; // broadcast
                
                @stage(10) {
                    father_write_action.execute(ig_md.index);
                }
            }
        }
        
        else if (hdr.msg_type.type == TYPE_PING_DETECTION) {
            
            @stage(4){
                hdr.pld.msg_id = msgid_ping_read_update_action.execute(hdr.pld.self_id);
            }
            @stage(5){
                 ig_md.diff_msg_id = msgid_read_action.execute(hdr.pld.self_id); // included hdr.pld.msg_id - ig_md.msg_id;
            }

            @stage(7){
                ig_md.comb_ignore_is_root = comb_ignore_is_root_read_update_action.execute(hdr.pld.self_id);
            }

            if ((ig_md.comb_ignore_is_root == 0) || (ig_md.comb_ignore_is_root == 2)) {
                mark_to_drop();
            }
            else {
                if ((ig_md.comb_ignore_is_root == 3) || (ig_md.diff_msg_id == 2)) {
                    @stage(8){
                        hdr.pld.tree_id = tree_ver_read_action.execute(hdr.pld.self_id);
                    }
                    // ig_md.mcast_bitmap = treeson_port_read_action.execute(hdr.pld.tree_id);

                    @stage(9){
                        treeson_port_read_newtree_tab.apply();
                    }

                    hdr.msg_type.type = TYPE_SYNC;

                    if (ig_md.comb_ignore_is_root != 3) { // meaning that ig_md.diff_msg_id == 2
                        hdr.pld.sync_or_fail_ping = 1; // fail ping
                    }
                    else {
                        hdr.pld.sync_or_fail_ping = 0; // sync;
                    }
                    // ig_md.mcast_bitmap = treeson_port_read_action.execute(hdr.pld.self_id); // only considering for tree #0
                    
                }
                else if ((ig_md.comb_ignore_is_root == 1) && (ig_md.diff_msg_id == 3)) {
                    @stage(8) {
                        tree_ver_write_action.execute(hdr.pld.self_id);
                    }
                    // TODO: update ig_md.comb_ignore_is_root to 3
                    @stage(9){
                        hdr.msg_type.type = TYPE_ALGO_FAST;
                        hdr.pld.tree_id = 1; // 1 for fast recovery
                        ig_md.mcast_bitmap = MINUS_ONE; // broadcast
                        ig_md.is_algo_sync = 1; // algo sync broadcast
                        // ig_md.version = 1;
                    }
                }
                else {
                    mark_to_drop();
                }
                
            }
        }

        else if (hdr.msg_type.type == TYPE_SYNC) {
            @stage(4){
                ig_md.diff_msg_id = msgid_ping_read_action.execute(hdr.pld.self_id); // write to the next slot
            }

            @stage(5){
                msgid_write_action.execute(hdr.pld.self_id);
            }

            if ((hdr.pld.sync_or_fail_ping == 0) || (ig_md.diff_msg_id != 0)) {
                @stage(9){
                    ig_md.mcast_bitmap = treeson_port_read_action.execute(ig_md.index);
                }
            }
            // lastly lookup the mcast table for multicast & add one packet for resubmission
        }

        else if (hdr.msg_type.type == TYPE_PING_ALGO) {
            @stage(6){
                hdr.pld.ping_id = ping_algo_counter_update_action.execute(0);
            }
            @stage(10){
                ig_md.mcast_bitmap = MINUS_ONE; // transmission at egress
            }
        }

        else if (hdr.msg_type.type == TYPE_ACK) {
            // ing_to_bitmap_tab.apply();
            // ig_md.comb_ignore_is_root = 0; // resetting comb_ignore_is_root to 0 for the node that launches the fast recovery 
            // comb_ignore_is_root_write_action.execute(hdr.pld.self_id);

            @stage(9){
                treeson_port_write_action.execute(ig_md.index);
            }
            mark_to_drop();
        }

        
        
        

        mcast_lookup_tab.apply();
    }
}


control SwitchIngressDeparser(
    packet_out pkt,
    inout ig_headers hdr,
    in ig_metadata_t ig_md,
    in ingress_intrinsic_metadata_for_deparser_t ig_intr_md_for_dprsr) {

    // IngressMirror() mirror;

    apply {
        // mirror.apply(hdr, ig_md, ig_intr_md_for_dprsr);
        // pkt.emit(hdr.bridge);
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.msg_type);
        pkt.emit(hdr.pld);
        pkt.emit(hdr.recirc_msg);
        
    }
}

#endif