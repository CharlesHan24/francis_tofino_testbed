from scapy.all import *
import pdb
import sys
sys.path.insert(0, "../")
from ctrl import graph


ANNOUNCE_MESSAGE = 0xB

class PortIdentityField(XStrFixedLenField):
    encoding = "!BBBBBBBBh"

    @classmethod
    def from_mac(cls, mac, port):
        mac_bytes = mac.split(":")
        if len(mac_bytes) != 6:
            raise ValueError("Invalid MAC Address")

        return struct.pack(
            cls.encoding,
            int(mac_bytes[0], 16),
            int(mac_bytes[1], 16),
            int(mac_bytes[2], 16),
            0xFF,
            0xFE,
            int(mac_bytes[3], 16),
            int(mac_bytes[4], 16),
            int(mac_bytes[5], 16),
            port
        )

    def __init__(self, name, default):
        XStrFixedLenField.__init__(self, name, default, length=10)

    def i2h(self, pkt, val):
        if val is None:
            return "None"
        p = struct.unpack(self.encoding, val)
        return (int.from_bytes(val[:3] + b'\xff' + b'\xfe' + val[5:8], byteorder="big"), p[8])
        # return f"{p[0]:02x}:{p[1]:02x}:{p[2]:02x}:{p[5]:02x}:{p[6]:02x}:{p[7]:02x}/{p[8]}"

    def i2repr(self, pkt, x):
        return self.i2h(pkt, x)

class PTPv2(Packet):
    name = "PTPv2"

    MSG_TYPES = {
        0x0: "Sync",
        0x2: "PdelayReqest",
        0x3: "PdelayResponse",
        0x8: "FollowUp",
        0xA: "PdelayResponseFollowUp",
        0xB: "Announce",
    }

    FLAGS = [
        "LI61", "LI59", "UTC_REASONABLE", "TIMESCALE",
        "TIME_TRACEABLE", "FREQUENCY_TRACEABLE", "?", "?",
        "ALTERNATE_MASTER", "TWO_STEP", "UNICAST", "?",
        "?", "profileSpecific1", "profileSpecific2", "SECURITY",
    ]


    fields_desc = [
        BitField("majorSdoId", 1, 4),
        BitEnumField("messageType", 0, 4, MSG_TYPES),
        XBitField("minorVersionPTP", 0, 4),
        BitField("versionPTP", 0x2, 4),
        ShortField("messageLength", 34),
        ByteField("domainNumber", 0),
        XByteField("minorSdoId", 0),
        FlagsField("flags", 0, 16, FLAGS),
        LongField("correctionField", 0),
        XIntField("messageTypeSpecific", 0),
        PortIdentityField("sourcePortIdentity", 0),
        ShortField("sequenceId", 0),
        XByteField("controlField", 0),
        SignedByteField("logMessageInterval", -3),
    ]

class Announce(Packet):
    name = "Announce"
    fields_desc = [
        XShortField("originTimestamp1", 0),
        XLongField("originTimestamp2", 0),
        ShortField("currentUtcOffset", 0),
        ByteField("reserved", 0),
        ByteField("grandmasterPriority1", 0),
        XIntField("grandmasterClockQuality", 0),
        ByteField("grandmasterPriority2", 0),
        LongField("grandmasterIdentity", 0),
        ShortField("stepsRemoved", 0),
        ByteField("timeSource", 0),
    ]

def eth2ptp(pkt):
    return PTPv2(raw(pkt["Ether"].payload))

def parse_packets(pkts, start_ts=0):
    res_pkts = []
    cnt = 0
    for pkt in pkts:
        ts = pkt.time
        if ts < start_ts:
            continue
        cnt += 1
        try:
            src, dst = pkt["Ether"].src, pkt["Ether"].dst
            pkt = eth2ptp(pkt)
            if pkt.messageType == ANNOUNCE_MESSAGE:
                res_pkts.append((ts, pkt, Announce(raw(pkt["Raw"])), src, dst, cnt))
        except:
            continue
    
    return res_pkts

def get_eventual_depth(pkts):
    # simple approach that waits until convergence
    if len(pkts) == 0:
        return 1000000
    self_identity = pkts[-1][1].sourcePortIdentity[0]
    gm_identity = pkts[-1][2].grandmasterIdentity
    return -1 if self_identity == gm_identity else pkts[-1][2].stepsRemoved

def cmp_pkts(pkt1, pkt2):
    if pkt1.stepsRemoved != pkt2.stepsRemoved:
        return 0
    if pkt1.grandmasterIdentity != pkt2.grandmasterIdentity:
        return 0
    if pkt1.grandmasterPriority1 != pkt2.grandmasterPriority1:
        return 0
    if pkt1.grandmasterPriority2 != pkt2.grandmasterPriority2:
        return 0
    if pkt1.grandmasterClockQuality != pkt2.grandmasterClockQuality:
        return 0
    return 1

def search_for_completion_time(pkts, start_ts):
    if len(pkts) < 2:
        return 0
    for i in range(len(pkts) - 2, -1, -1):
        if cmp_pkts(pkts[i][2], pkts[i + 1][2]) == 0:
            return pkts[i + 1][0] - start_ts
    return 0

def search_for_earliest_completion_time(pkts, start_ts):
    if len(pkts) < 2:
        return 0
    # pdb.set_trace()
    for i in range(len(pkts) - 1):
        if cmp_pkts(pkts[i][2], pkts[-1][2]) == 1:
            # return pkts[i][0] - start_ts
            # return pkts[i][0] - pkts[0][0]
            return pkts[i][0] - (pkts[0][0] + start_ts) / 2
    return 0

def build_ms_relation(list_of_pkts, list_of_macs, topo, n):
    depth = []
    for i in range(len(list_of_pkts)):
        depth.append(get_eventual_depth(list_of_pkts[i]))
    
    print(depth)

    node_depth = [0 for i in range(n)]

    n_packets = []
    for i in range(len(list_of_pkts)):
        if len(list_of_pkts[i]) > 0:
            n_packets.append([list_of_pkts[i][-1][5], i])
    
    n_packets = sorted(n_packets, key=lambda x: x[0])
    max_interval = 0
    argmax_interval = 0
    for i in range(1, len(n_packets)):
        if n_packets[i][0] - n_packets[i-1][0] > max_interval:
            max_interval = n_packets[i][0] - n_packets[i-1][0]
            argmax_interval = n_packets[i][0]
    
    
    # pdb.set_trace()

    for i in range(len(n_packets)):
        if len(list_of_pkts[i]) == 0:
            n_packets.append([0, i])
    
    n_packets = sorted(n_packets, key=lambda x: x[1]) # an edge could be the tree edge if and only if n_packets[i][0] >= argmax_interval
    

    for i in range(n):
        is_grandmaster = True
        for v in topo.edge[i]:
            global_id = topo.lookup_global_id_self(i, v)
            if (depth[global_id] >= 0 and len(list_of_pkts[global_id]) > 0) or i >= 1:# list_of_macs[global_id] != list_of_pkts[global_id][-1][3]:
                is_grandmaster = False
                break
        
        if is_grandmaster:
            node_depth[i] = 0
            grandmaster = i
            print("Node {} is grandmaster".format(i))
        
    for i in range(n):
        if i == grandmaster:
            continue
        
        depth_list = []
        for v in topo.edge[i]:
            
            global_id = topo.lookup_global_id_self(i, v)
            depth_list.append(depth[global_id])
            if v == grandmaster:
                print("Father({}) is {}".format(i, v))
                node_depth[i] = 1
            
        if (max(depth_list) - min(depth_list)) >= 1:
            for j, v in enumerate(topo.edge[i]):
                if depth_list[j] == max(depth_list):
                    node_depth[v] = depth_list[j] + 1
                    # print("Father({}) is {}".format(v, i))
    node_depth[grandmaster] = 0

    for i in range(n):
        for v in topo.edge[i]:
            if node_depth[i] == node_depth[v] + 1:
                global_id = topo.lookup_global_id_self(i, v)
                if n_packets[global_id][0] >= argmax_interval:
                    print("Tree edge: {} -> {}".format(i, v))
    

    return node_depth


def get_mac_addresses(topo):
    addresses = []
    for i in range(topo.m):
        addresses.append(conf.ifaces.dev_from_name("veth{}".format(i)).mac)
    return addresses

if __name__ == "__main__":
    list_of_pkts = []

    fin = open("down_ts.txt", "r")
    start_ts = float(fin.readline().strip())

    
    for i in range(42):
        pkts = rdpcap("/home/wenchen_han_22/veth{}.pcap".format(i))
    
        pkts = parse_packets(pkts, start_ts=start_ts)
        list_of_pkts.append(pkts)
    pdb.set_trace()
    n = 15
    topo = graph.Graph(n=15)
    topo.set_orig_mode()
    topo.construct_fattree_3_deformed()


    # node_depth = build_ms_relation(list_of_pkts, get_mac_addresses(topo), topo, n)
    node_depth = build_ms_relation(list_of_pkts, [], topo, n)
    print(node_depth)

    fout = open("conv_result.txt", "w")
    # log_announce_interval = 0.125
    log_announce_interval = 1 / (2 ** 13)
    fout.write("{}\n".format(log_announce_interval * 1000000))
    pdb.set_trace()
    for i in range(n):
        conv_time_node = 0
        for v in topo.edge[i]:
            global_id = topo.lookup_global_id_self(i, v)
            # conv_time_node = max(conv_time_node, search_for_completion_time(list_of_pkts[global_id], start_ts))
            conv_time_node = max(conv_time_node, search_for_earliest_completion_time(list_of_pkts[global_id], start_ts))
        print("Node {} converges in {}".format(i, conv_time_node))
        # fout.write("{} {}\n".format(conv_time_node, conv_time_node / log_announce_interval))
        fout.write("{} {}\n".format(conv_time_node / (2 ** 5) * 1000000, conv_time_node / (2 ** 5) / log_announce_interval))