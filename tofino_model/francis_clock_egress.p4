// @compiler 9.9.1
#ifndef _FRANCIS_CLOCK_EGRESS_P4
#define _FRANCIS_CLOCK_EGRESS_P4

#include <core.p4>
#if __TARGET_TOFINO__ == 3
#include <t3na.p4>
#elif __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif
#include "header_parser.p4"


// TODO: NOTICE: we ignore the concept of virtual_switch_id at egress and handle independently the transmission for each egress port regardless of the corresponding virtual_switch_id

control SwitchEgress(
                inout eg_headers hdr,
                inout eg_metadata_t eg_md,
                /* Intrinsic */    
                in    egress_intrinsic_metadata_t                  eg_intr_md,
                in    egress_intrinsic_metadata_from_parser_t      eg_intr_md_from_prsr,
                inout egress_intrinsic_metadata_for_deparser_t     eg_intr_md_for_dprsr,
                inout egress_intrinsic_metadata_for_output_port_t  eg_intr_md_for_oport){
    
    action eg_mark_to_drop(){
        eg_intr_md_for_dprsr.drop_ctl = 1;
    }

    Register<bit<8>, bit<8> > (NUM_PHYSICAL_PORTS) store_sync_round_id;
    RegisterAction<bit<8>, bit<8>, bit<8> > (store_sync_round_id) store_sync_round_id_write_action = {
        void apply(inout bit<8> value) {
            value = hdr.pld.round_id + 1;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (store_sync_round_id) store_sync_round_id_read_action = { // read and then reset
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value - 1;
            if (value != 0) {
                value = 0;
            }
        }
    };

    Register<bit<32>, bit<8> > (NUM_PHYSICAL_PORTS) last_transmitted_time; // timestamp % (2^32 ns) + CHANNEL_BITRATE_TS_INTERVAL
    RegisterAction<bit<32>, bit<8>, bit<32> > (last_transmitted_time) last_transmitted_time_write_action = {
        void apply(inout bit<32> value) {
            if ((int<32>)eg_intr_md_from_prsr.global_tstamp[31:0] - (int<32>)value > 0) { // value = max(value + 1000, cur_timestamp). Rate limit control
                value = eg_intr_md_from_prsr.global_tstamp[31:0];
            }
            else {
                value = value + CHANNEL_BITRATE_TS_INTERVAL;
            }
        }
    };
    RegisterAction<bit<32>, bit<8>, bit<32> > (last_transmitted_time) last_transmitted_time_read_update_action = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            read_value = value;
            if ((int<32>)eg_intr_md_from_prsr.global_tstamp[31:0] - (int<32>)value > CHANNEL_BITRATE_TS_INTERVAL) {
                value = eg_intr_md_from_prsr.global_tstamp[31:0];
            }
            else if ((int<32>)eg_intr_md_from_prsr.global_tstamp[31:0] - (int<32>)value > 0) {
                value = value + CHANNEL_BITRATE_TS_INTERVAL;
            }
        }
    };

    Register<bit<8>, bit<8> > (NUM_PHYSICAL_PORTS) queue_list1; // initialized into ALL_ONE
    RegisterAction<bit<8>, bit<8>, bit<8> > (queue_list1) queue_list1_add_action = {
        void apply(inout bit<8> value) {
            value = value + eg_md.pow2_result;
            // if (eg_md.pow2_result == 1) {
            //     value = value ^ 1;
            // }
            // else if (eg_md.pow2_result == 2) {
            //     value = value ^ 2;
            // }
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (queue_list1) queue_list1_extract_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
            if (value >= 2) { // highest bit
                value = value ^ 2;
            }
            else if (value >= 1) {
                value = 0;
            }
        }
    };

    Register<bit<8>, bit<8> > (NUM_PHYSICAL_PORTS) queue_list2; // initialized into 0
    RegisterAction<bit<8>, bit<8>, bit<8> > (queue_list2) queue_list2_add_action = {
        void apply(inout bit<8> value) {
            value = value + eg_md.pow2_result;
            // if (eg_md.pow2_result == 4) {
            //     value = value ^ 4;
            // }
            // else if (eg_md.pow2_result == 8) {
            //     value = value ^ 8;
            // }
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (queue_list2) queue_list2_extract_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
            if (value >= 8) { // highest bit
                value = value ^ 8;
            }
            else if (value >= 4) {
                value = 0;
            }
        }
    };

    Register<bit<32>, bit<8> > (256) algo_store_lower;
    RegisterAction<bit<32>, bit<8>, bit<32> > (algo_store_lower) algo_store_lower_write_action = {
        void apply(inout bit<32> value) {
            value = eg_md.store_content_lower;
        }
    };
    RegisterAction<bit<32>, bit<8>, bit<32> > (algo_store_lower) algo_store_lower_read_action = {
        void apply(inout bit<32> value, out bit<32> read_value) {
            read_value = value;
        }
    };

    Register<bit<8>, bit<8> > (NUM_VIRT_SWITCH) waited_algo_msg_cnt;
    RegisterAction<bit<8>, bit<8>, bit<8> > (waited_algo_msg_cnt) waited_algo_msg_cnt_increment = {
        void apply(inout bit<8> value) {
            value = value + 1;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (waited_algo_msg_cnt) waited_algo_msg_cnt_decrement = {
        void apply(inout bit<8> value) {
            value = value - 1;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (waited_algo_msg_cnt) waited_algo_msg_cnt_read = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            read_value = value;
        }
    };

    Register<bit<8>, bit<8> > (NUM_VIRT_SWITCH) waited_last_id;
    RegisterAction<bit<8>, bit<8>, bit<8> > (waited_last_id) waited_last_id_write_action = {
        void apply(inout bit<8> value) {
            value = hdr.pld.ping_id;
        }
    };
    RegisterAction<bit<8>, bit<8>, bit<8> > (waited_last_id) waited_last_id_read_action = {
        void apply(inout bit<8> value, out bit<8> read_value) {
            if (hdr.pld.ping_id - value >= 1) {
                read_value = 0;
            }
            else {
                read_value = 1;
            }
        }
    };



    action lookup_pow2_recirc_idx_action(bit<8> pow2_result, bit<2> recirc_idx) {
        eg_md.pow2_result = pow2_result;
        eg_md.store_content_lower[7:0] = hdr.pld.argmin;
        eg_md.recirc_idx[1:0] = recirc_idx;
        eg_md.recirc_idx[7:2] = (bit<6>) eg_md.egress_port;
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

    action lookup_lowbit_action(bit<8> lowbit) {
        eg_md.index[1:0] = lowbit[1:0];
        eg_md.index[7:2] = eg_md.egress_port[5:0];
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

    action retrans_slow_recons_msg_action(bit<8> tree_id) {
        hdr.msg_type.type = TYPE_ALGO_SLOW_RECONS;
        // do not extract the recirc_idx?
        hdr.pld.tree_id = tree_id; // recirc_idx + 2
        hdr.pld.argmin = eg_md.store_content_lower[7:0];
        hdr.pld.tree_depth = eg_md.store_content_lower[15:8];
        hdr.pld.round_id = eg_md.store_content_lower[23:16];
        
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
        size = 8;
        default_action = NoAction();
    }

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

    action egress_self_id_get_action(bit<8> self_id) {
        hdr.pld.self_id = self_id;
    }
    action eg_self_id_mark_to_drop() {
        eg_intr_md_for_dprsr.drop_ctl = 1;
        hdr.msg_type.type = 0x9;
    }

    table egress_self_id_tab {
        key = {
            eg_intr_md.egress_port: exact;
        }
        actions = {
            egress_self_id_get_action;
            eg_self_id_mark_to_drop;
        }
        size = 64;
        default_action = eg_self_id_mark_to_drop();
    }
    
    apply {
        if (hdr.msg_type.type == TYPE_SYNC) { // send synchronization messages in a non-blocking way and don't count it towards our dist algo packets (so does not consider them for rate limit)
            // hdr.recirc_msg.setInvalid(); // we assert that recirc_msg does not exist 
        }
        else if (hdr.msg_type.type == TYPE_PING_ALGO) {
            egress_self_id_tab.apply();
            @stage(1){
                eg_md.last_timestamp = last_transmitted_time_read_update_action.execute((bit<8>)eg_md.egress_port);
            }

            @stage(2){
                comp_last_timestamp_tab.apply(); // if eg_intr_md_from_prsr.global_tstamp[31:0] - eg_md.last_timestamp > 0?
            }

            #ifndef DEBUG_MODE
                if (eg_md.comp_last_timestamp_flag != 0) {
            #else
                if (1 != 0) {
            #endif
                
                @stage(3){
                    eg_md.waiting_list = queue_list1_extract_action.execute((bit<8>)eg_md.egress_port);
                }
                if (eg_md.waiting_list == 0) {
                    @stage(5){
                        eg_md.waiting_list = queue_list2_extract_action.execute((bit<8>)eg_md.egress_port);
                    }
                }

                if (eg_md.waiting_list != 0) {
                    @stage(6){
                        lookup_lowbit_tab.apply();
                    }

                    @stage(7){
                        eg_md.store_content_lower = algo_store_lower_read_action.execute(eg_md.index);
                    }

                    @stage(8) {
                        waited_algo_msg_cnt_decrement.execute(hdr.pld.self_id);
                    }
                    @stage(9) {
                        waited_last_id_write_action.execute(hdr.pld.self_id);
                    }

                    @stage(11){
                        retrans_slow_recons_msg_tab.apply();
                    }
                }

                else {
                    bit<8> cnt;
                    bit<8> is_this_id;
                    @stage(8){
                        cnt = waited_algo_msg_cnt_read.execute(hdr.pld.self_id);
                    }
                    @stage(9) {
                        is_this_id = waited_last_id_read_action.execute(hdr.pld.self_id);
                    }
                    if ((cnt == 0) && (is_this_id == 0)){ // cnt == 0 and (hdr.pld.sync_or_fail_ping - last_id >= 1)
                        @stage(10){
                            eg_md.round_id = store_sync_round_id_read_action.execute((bit<8>)eg_md.egress_port);
                        }
                        @stage(11){
                            if (eg_md.round_id != BIT_8_MINUS_ONE) {
                                hdr.msg_type.type = TYPE_ALGO_SYNC;
                                hdr.pld.round_id = eg_md.round_id;
                            }
                            else {
                                eg_mark_to_drop();
                            }
                        }
                    }
                    else {
                        eg_mark_to_drop();
                    }
                }
            }
            else {
                eg_mark_to_drop();
            }
        }

        else if (eg_intr_md.egress_rid == 2) { // ack
            // @stage(1){
            //     last_transmitted_time_write_action.execute((bit<8>)eg_md.egress_port);
            // }
            if (hdr.msg_type.type == TYPE_ALGO_FAST){
                hdr.msg_type.type = TYPE_ACK; // pld.tree_id has already been set up
            }
            else {
                hdr.msg_type.type = TYPE_ALGO_SYNC;
                hdr.pld.sync_or_fail_ping = 1;
                hdr.recirc_msg.setInvalid();
            }
        }
        else if ((hdr.msg_type.type == TYPE_ALGO_FAST) || (hdr.msg_type.type == TYPE_ALGO_SLOW_RECONS)) {
            if (eg_md.egress_port == 54) { // recirculation packet, non blocking
                hdr.msg_type.type = TYPE_RECIRC;
            }
            else if (eg_intr_md.egress_rid == 0) { // egress_rid == 0: sending packets of the type itself; egress_rid == 1: sending TYPE_ALGO_SYNC packets. egress_rid == 2: ack
                if (hdr.msg_type.type == TYPE_ALGO_FAST) {
                    // hdr.recirc_msg.setInvalid();
                    @stage(1){
                        last_transmitted_time_write_action.execute((bit<8>)eg_md.egress_port);
                    }
                }
                else { // ALGO_SLOW_RECONS. Store 
                    @stage(1){
                        lookup_pow2_recirc_idx.apply();
                    }
                    
                    // @stage(2){
                    //     // eg_md.store_content_lower[7:0] = eg_md.recirc_idx;
                    //     eg_md.store_content_lower[7:0] = hdr.pld.argmin;
                    // }
                    @stage(2){
                        eg_md.store_content_lower[15:8] = hdr.pld.tree_depth;
                        eg_md.store_content_lower[23:16] = hdr.pld.round_id;
                    }

                    if (eg_md.pow2_result < 4) { // low
                        @stage(3){
                            queue_list1_add_action.execute((bit<8>)eg_md.egress_port); // in each epoch, 
                        }
                    }
                    else {
                        @stage(5){
                            queue_list2_add_action.execute((bit<8>)eg_md.egress_port); // in each epoch, 
                        }
                    }
                    @stage(7){
                        algo_store_lower_write_action.execute(eg_md.recirc_idx);
                    }
                    @stage(8){
                        waited_algo_msg_cnt_increment.execute(hdr.pld.self_id);
                    }
                    
                    eg_mark_to_drop();
                }
            }
            else if (eg_intr_md.egress_rid == 1) { // egress_rid == 1
                @stage(10){
                    store_sync_round_id_write_action.execute((bit<8>)eg_md.egress_port);
                }
                eg_mark_to_drop();
            }
            // else { // ack
            //     @stage(1){
            //         last_transmitted_time_write_action.execute((bit<8>)eg_md.egress_port);
            //     }
            //     hdr.msg_type.type = TYPE_ACK; // pld.tree_id has already been set up
            // }
        }
        else if (hdr.msg_type.type == TYPE_RECIRC) {

        }
        else {
            eg_mark_to_drop();
        }
    }
}



control SwitchEgressDeparser(packet_out pkt,
            inout eg_headers hdr,
            in eg_metadata_t eg_md,
            /* Intrinsic */
            in    egress_intrinsic_metadata_for_deparser_t  eg_dprsr_md){
    apply {
        pkt.emit(hdr.recirc_msg);
        pkt.emit(hdr.ethernet);
        pkt.emit(hdr.ipv4);
        pkt.emit(hdr.msg_type);
        pkt.emit(hdr.pld);
    }
}

#endif

