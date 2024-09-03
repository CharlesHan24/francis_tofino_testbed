from scapy.all import *

"""
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
"""
class FRANCIS(Packet):
    name = "FRANCIS"
    fields_desc = [
        XByteField("type", 0),
        XByteField("tree_id", 0),
        XByteField("sync_or_fail_ping", 0),
        XByteField("tree_depth", 0),
        XByteField("round_id", 0),
        XByteField("argmax", 0),
        XByteField("self_id", 0),
        XShortField("msg_id", 0),
    ]

def extract_pkts(raw_pkts):
    pkts = []
    for raw_pkt in raw_pkts:
        ts = raw_pkt.time
        pkt = FRANCIS(raw(raw_pkt["IP"].payload))
        pkts.append([pkt, ts])
    return pkts

def extract_pkt(raw_pkt):
    return FRANCIS(raw(raw_pkt["IP"].payload))



"""
struct cpu_digest_t {
    bit<48> timestamp;
    bit<8> self_id;
    bit<8> msg_type;
    bit<8> round_id;
    bit<8> tree_id;
    bit<8> ingress_port;
}
"""
class digest_pkts(object):
    def __init__(self, ts, self_id, msg_type, round_id, tree_id, ingress_port):
        self.ts = ts
        self.self_id = self_id
        self.msg_type = msg_type
        self.round_id = round_id
        self.tree_id = tree_id
        self.ingress_port = ingress_port
    


if __name__ == "__main__":
    import pdb
    pkts = rdpcap("../../sender.pcap")
    pkts = extract_pkts(pkts)
    pdb.set_trace()
    for pkt in pkts:
        print(pkt[0].show())
        print(pkt[1])
        print("")