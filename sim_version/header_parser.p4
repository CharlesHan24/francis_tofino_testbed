#ifndef _HEADER_PARSER_P4
#define _HEADER_PARSER_P4

#include <core.p4>
#if __TARGET_TOFINO__ == 3
#include <t3na.p4>
#elif __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif


const bit<16> ETH_TYPE_IPV4 = 0x0800;
const bit<8> TYPE_SYNC = 0x00; // synchronization messages and ping_for_failure messages
const bit<8> TYPE_ACK = 0x01; // ACK messages
const bit<8> TYPE_PING_DETECTION = 0x02; // pkt_generator for failure detection
const bit<8> TYPE_RECIRC = 0x03; // recirculation messages in sync
const bit<8> TYPE_ALGO_SYNC = 0x04; // ALGO_SYNC
const bit<8> TYPE_ALGO_FAST = 0x05; // fast recovery
const bit<8> TYPE_ALGO_SLOW_RECONS = 0x06; // slow reconstruction
const bit<8> TYPE_PING_ALGO = 0x07;

#define SIMULATION_TS_MULTIPLIER 1000
#define NUM_TREES 4
#define TOTAL_SLOT 6        // the number of trees being built
#define DEBUG_MODE

#define CHANNEL_BITRATE_TS_INTERVAL (2500000) // 1us per 64-byte message = 0.2Gbps = 0.2% bandwidth
// #define CHANNEL_BITRATE_TS_INTERVAL (2500) // 1us per 64-byte message = 0.2Gbps = 0.2% bandwidth
#define MINUS_ONE 0xf // broadcast
#define BIT_8_MINUS_ONE 0xff

#define PHASE_1 5 // depth <= 5
#define PHASE_2 10 // depth <= 5
#define PHASE_3 16 // depth = 4 (drop when round_id == 15)
#define NUM_PORTS 4 // 4 ports maximum per virtual switch
#define NUM_VIRT_SWITCH 20 // number of virtual switches
#define NUM_PHYSICAL_PORTS (64)

typedef bit<48> mac_addr_t;
typedef bit<32> ipv4_addr_t;

header ethernet_t {
    mac_addr_t dst_addr;
    mac_addr_t src_addr;
    bit<16>   ethertype;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<6>    dscp;
    bit<2>    ecn;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ipv4_addr_t src;
    ipv4_addr_t dst;
}

header message_type_t {
    bit<8> type;
}

// header sync_msg_t {
//     bit<8> tree_id;
//     bit<8> sync_or_fail_ping; // true: sync, false: fail_ping
//     bit<16> msg_id;
// }

// header ack_msg_t {
//     bit<8> tree_id;
// }

// header algo_fast_t {
//     bit<8> tree_id;
// }

// header ping_detection_t {
//     bit<32> ping_id;
// }

// header algo_sync_t {
//     bit<8> round_id;
// }

// header algo_slow_recons_t {
//     bit<8> tree_id;
//     bit<8> tree_depth;
//     bit<8> max_depth;
//     bit<8> _pad1;
//     bit<32> argmax;
// }

// header pktgen_timer_header_t {
//     @padding bit<3> _pad1;
//     bit<2> pipe_id;                     // Pipe id
//     bit<3> app_id;                      // Application id
//     @padding bit<8> _pad2;

//     bit<16> batch_id;                   // Start at 0 and increment to a
//                                         // programmed number

//     bit<16> packet_id;                  // Start at 0 and increment to a
//                                         // programmed number
// }

header payload_t {
    bit<8> tree_id;
    bit<8> sync_or_fail_ping; // true: sync, false: fail_ping
    bit<8> tree_depth;
    bit<8> round_id;
    bit<8> argmin;
    bit<8> self_id;
    bit<16> msg_id;
    bit<8> ping_id;
}

header recirc_t {
    bit<8> recirc_idx; // for i = 0:4
}

// header ig_eg_info_t {
//     bit<1> is_algo_sync;
//     bit<7> _pad;
// }

struct ig_headers {
    // mirror_bridged bridge;
    recirc_t recirc_msg;
    pktgen_timer_header_t ping;
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    message_type_t msg_type;
    payload_t pld;
}




// parser TofinoIngressParser(
//         packet_in pkt,
//         out ingress_intrinsic_metadata_t ig_intr_md) {
//     state start {
//         pkt.extract(ig_intr_md);


//         transition select(ig_intr_md.resubmit_flag) {
//             1 : parse_resubmit;
//             0 : parse_non_resubmit;
//         }
//     }

//     state parse_resubmit {
//         // Parse resubmitted packet here.
//         //pkt.advance(64); 
//         pkt.extract(hdr.recirc_msg);
//         transition accept;
//     }

//     state parse_non_resubmit {
//         pkt.advance(64);  //tofino 1
//         transition select(ig_intr_md.ingress_port) {
//             68: parse_pktgen;
//             default: accept;
//         }
//     }

//     state parse_pktgen {
//         pkt.extract(ping);
//         transition accept;
//     }
// }




struct ig_metadata_t {
    bit<32> ig_port_pow_2; // 1 << ingress intrinsic port
    bit<32> mcast_bitmap;
    bit<1> to_recirc;
    bit<16> msg_id;
    bit<16> comb_ignore_is_root;
    bit<8> to_ack;
    bit<8> port;
    bit<8> depth;
    bit<8> version;
    bit<16> diff_msg_id;
    bit<8> slow_recons_root;
    bit<32> neighbor_cnt;
    bit<32> total_cnt;
    bit<8> last_depth;
    bit<8> is_incoming_smaller;
    bit<8> unicast_port;
    bit<1> is_algo_sync;
    bit<8> index;
    bit<8> last_depth_plus_round_id;
    bit<8> recirc_tree_id;
    bit<8> algo_sync_index;
}




parser TofinoIngressParser(
        packet_in pkt,
        out ingress_intrinsic_metadata_t ig_intr_md,
        out ig_headers hdr) {
    state start {
        pkt.extract(ig_intr_md);
        pkt.advance(64); 

        transition accept;
    }
}

parser SwitchIngressParser(
        packet_in pkt,
        out ig_headers hdr,
        out ig_metadata_t ig_md,
        out ingress_intrinsic_metadata_t ig_intr_md) {

    TofinoIngressParser() tofino_parser;

    state start {
        tofino_parser.apply(pkt, ig_intr_md, hdr);
        // do some initialization
        ig_md.port = 0;
        ig_md.index = 0;
        ig_md.comb_ignore_is_root = 1;

        ig_md.ig_port_pow_2 = 0; // 1 << ingress intrinsic port
        ig_md.mcast_bitmap = 0;
        ig_md.to_recirc = 0;
        ig_md.msg_id = 0;
        

        ig_md.to_ack = 0;
        ig_md.last_depth_plus_round_id = 0;
        ig_md.depth = 0;
        ig_md.version = 1;
        ig_md.diff_msg_id = 0;
        ig_md.slow_recons_root = 0;
        ig_md.neighbor_cnt = 0;
        ig_md.total_cnt = 0xff;
        ig_md.last_depth = 0;
        ig_md.is_incoming_smaller = 0;
        ig_md.unicast_port = 0xff;
        ig_md.is_algo_sync = 0;
        ig_md.recirc_tree_id = 0;
        ig_md.algo_sync_index = 0;

        transition parse_meta;
    }

    state parse_meta {
        transition select(ig_intr_md.ingress_port) { // ports: 54out and 55in, 68 for resubmit and packet generators
            55: parse_resubmit;
            68: parse_ping;
            default: parse_eth1;
        }
    }

    state parse_resubmit {   
        pkt.extract(hdr.recirc_msg);
        transition parse_eth1;
    }

    state parse_ping {
        pkt.extract(hdr.ping);
        hdr.msg_type.setValid();
        hdr.pld.setValid();
        // hdr.msg_type.type[3:0] = hdr.ping.app_id;
        hdr.pld.self_id = (bit<8>)hdr.ping.packet_id; // the timer repeats for hdr.ping.batch_id batches, and for each batch the packet generator fires hdr.ping.packet_id packets. For emulation, we regard the hdr.ping.packet_id th packet as the generated packet for the hdr.ping.batch_id th logical switch.
        

        transition select (hdr.ping.app_id) {
            2: parse_ping_2;
            7: parse_ping_7;
            default: reject;
        }
    }

    state parse_ping_2 {
        hdr.msg_type.type = 2;
        transition parse_eth2;
    }

    state parse_ping_7 {
        hdr.msg_type.type = 7;
        transition parse_eth2;
    }
    
    state parse_eth1 {
        
        pkt.extract(hdr.ethernet);
        transition select (hdr.ethernet.ethertype) {
            ETH_TYPE_IPV4: parse_ip1;
            default : reject;
        }
    }

    state parse_eth2 {
        
        pkt.extract(hdr.ethernet);
        transition select (hdr.ethernet.ethertype) {
            ETH_TYPE_IPV4: parse_ip2;
            default : reject;
        }
    }

    state parse_ip1 {
        pkt.extract(hdr.ipv4);
        pkt.extract(hdr.msg_type);
        pkt.extract(hdr.pld);
        transition accept;
    }

    state parse_ip2 {
        pkt.extract(hdr.ipv4);
        transition accept;
    }
}

struct eg_headers {
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    message_type_t msg_type;
    payload_t pld;
    recirc_t recirc_msg;
    
}


struct eg_metadata_t {
    bit<8> waiting_list;
    bit<8> round_id;
    bit<32> store_content_lower;
    bit<8> recirc_idx;
    bit<8> pow2_result;
    bit<8> index;
    bit<8> comp_last_timestamp_flag;
    bit<32> last_timestamp;
    bit<8> egress_port;

}


parser SwitchEgressParser(packet_in pkt,
        out eg_headers hdr,
        out eg_metadata_t eg_md,
        out egress_intrinsic_metadata_t eg_intr_md) {
    
    state start {
        pkt.extract(eg_intr_md);
        // initialize variables
        eg_md.waiting_list = 0;
        eg_md.round_id = 0;
        eg_md.store_content_lower = 0;
        eg_md.recirc_idx = 0;
        eg_md.pow2_result = 0;
        eg_md.index = 0;
        eg_md.comp_last_timestamp_flag = 0;
        eg_md.last_timestamp = 0;
        eg_md.egress_port = eg_intr_md.egress_port[7:0];

        transition parse_ethernet;
        
    }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        pkt.extract(hdr.ipv4);
        pkt.extract(hdr.msg_type);
        pkt.extract(hdr.pld);
        transition select(hdr.msg_type.type) {
            TYPE_ALGO_SLOW_RECONS: parse_resubmit;
            default: accept;
        }
    }
    state parse_resubmit {
        pkt.extract(hdr.recirc_msg);
        transition accept;
    }
}

#endif