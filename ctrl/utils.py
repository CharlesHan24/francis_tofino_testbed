import sys
import os
from scapy.all import *
from thrift.protocol import TBinaryProtocol, TMultiplexedProtocol
from thrift.transport import TSocket, TTransport
import struct
verstr="3.5"
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/'))
sys.path.append(os.path.expandvars('$SDE/install/lib/python'+verstr+'/site-packages/tofino/bfrt_grpc/'))

from bfrt_grpc import client as gc
import mc_pd_rpc.mc as mc_client_module

def port_to_pipe(port): 
    return port >> 7
def port_to_pipe_local_id(port):
    return port & 0x7F

def port_to_bit_idx(port):
    pipe = port_to_pipe(port)
    index = port_to_pipe_local_id(port)
    return 72 * pipe + index

def bytes_to_string(byte_array):
  form = 'B' * len(byte_array)
  return struct.pack(form, *byte_array)

def set_port_or_lag_bitmap(bit_map_size, indices):
    bit_map = [0] * ((bit_map_size + 7) // 8)
    for i in indices:
        index = port_to_bit_idx(i)
        bit_map[index // 8] = (bit_map[index // 8] | (1 << (index%8))) & 0xFF
    return bytes_to_string(bit_map)

def hex_to_i16(h):
    x = int(h)
    if x > 0x7FFF:
        x -= 0x10000
    return x


class Ctrl_Manager(object):
    def __init__(self, grpc_addr):
        self.GRPC_CLIENT = gc.ClientInterface(grpc_addr=grpc_addr, client_id=0, device_id=0)
        self.bfrt_info = self.GRPC_CLIENT.bfrt_info_get(p4_name=None)
        self.GRPC_CLIENT.bind_pipeline_config(p4_name=self.bfrt_info.p4_name)

        self.transport = TTransport.TBufferedTransport(TSocket.TSocket('localhost', 9090))
        self.transport.open()
        bprotocol = TBinaryProtocol.TBinaryProtocol(self.transport)

        self.mc = mc_client_module.Client(TMultiplexedProtocol.TMultiplexedProtocol(bprotocol, "mc"))
        self.mc_sess_hdl = self.mc.mc_create_session()

    def retrieve_digest_msg(self):
        msgs = []
        while True:
            try:
                new_msg_pack = self.GRPC_CLIENT.digest_get()
            except:
                break
            if new_msg_pack == None:
                break
            
            
            for new_msg in new_msg_pack.data:
                msg = []
                for dfield in new_msg.fields:
                    msg.append(int.from_bytes(dfield.stream, byteorder='big'))
                msgs.append(msg)
        return msgs


    def table_add(self, table_name, match_key_names_list, match_key_values_list, action_name, action_data_names_list, action_data_values_list, is_ternary=False, ternary_mask_list=None):
        # simply a wrapper
        t = self.bfrt_info.table_get(table_name)
        
        def table_add_gen_kd(table_name, match_key_names_list, match_key_values_list, action_name, action_data_names_list, action_data_values_list, is_ternary, ternary_mask_list):
            # prepare to add a single match-action table rule
            t = self.bfrt_info.table_get(table_name)

            # prepare KeyTuple
            KeyTuple_list=[]
            for i, (keyName, keyValue) in enumerate(zip(match_key_names_list,match_key_values_list)):
                if is_ternary == True and ternary_mask_list[i] != -1:
                    KeyTuple_list.append(gc.KeyTuple(name=keyName, value=keyValue, mask=ternary_mask_list[i]))
                else:
                    KeyTuple_list.append(gc.KeyTuple(name=keyName, value=keyValue) if type(keyValue) != list else gc.KeyTuple(name=keyName, low=keyValue[0], high=keyValue[1]))
            tKey = t.make_key(KeyTuple_list)

            DataTuple_List=[]
            for dataName, dataValue in zip(action_data_names_list,action_data_values_list):
                DataTuple_List.append(gc.DataTuple(name=dataName,val=dataValue))
            tData=t.make_data(DataTuple_List, action_name=action_name)
            return tKey, tData
        
        tKey, tData = table_add_gen_kd(table_name, match_key_names_list, match_key_values_list, action_name, action_data_names_list, action_data_values_list, is_ternary, ternary_mask_list)
        
        target = gc.Target(device_id=0, pipe_id=0xffff)
        t.entry_add(target=target, key_list=[tKey], data_list=[tData])        
        
    def insert_entry(self, register_name, register_idx, register_field_name1, register_field_val1, register_field_name2=None, register_field_val2=None):
        register_table = self.bfrt_info.table_get(register_name)
        target = gc.Target(device_id=0, pipe_id=0xffff)

        reg_data = [gc.DataTuple(register_field_name1, register_field_val1)]
        if register_field_name2 != None:
            reg_data.append(gc.DataTuple(register_field_name2, register_field_val2))

        register_table.entry_add(target, [register_table.make_key([gc.KeyTuple('$REGISTER_INDEX', register_idx)])], [register_table.make_data(reg_data)])

    def add_multinode_mc_grp(self, mc_gid, dpids_and_rids):
        # create the mc group
        mc_grp_hdl = self.mc.mc_mgrp_create(self.mc_sess_hdl, 0, hex_to_i16(mc_gid))
        # add one node for each (dpid, rid) pair
        lag_map = set_port_or_lag_bitmap(256, [])
        mc_node_hdls = []
        dpids, rids = dpids_and_rids
        for (dpid, rid) in zip(dpids, rids): # dpid is a list of ports
            port_map = set_port_or_lag_bitmap(288, dpid)
            mc_node_hdl = self.mc.mc_node_create(self.mc_sess_hdl, 0, rid, port_map, lag_map)
            self.mc.mc_associate_node(self.mc_sess_hdl, 0, mc_grp_hdl, mc_node_hdl, 0, 0)
            mc_node_hdls.append(mc_node_hdl)
        
        self.mc.mc_complete_operations(self.mc_sess_hdl)
        return mc_node_hdls, mc_grp_hdl

    def reset_register(self, register_name):
        register_table = self.bfrt_info.table_get(register_name)
        target = gc.Target(device_id=0, pipe_id=0xffff)
        # register_table.default_entry_reset(target)

    def reset(self):
        self.GRPC_CLIENT.clear_all_tables()

    def close(self):
        self.GRPC_CLIENT.__del__()



def ip_make_tos(tos, ecn, dscp):
    if ecn is not None:
        tos = (tos & ~(0x3)) | ecn

    if dscp is not None:
        tos = (tos & ~(0xFC)) | (dscp << 2)

    return tos

MINSIZE = 64
def simple_ipv4ip_packet(
    pktlen=64,
    eth_dst="00:01:02:03:04:05",
    eth_src="00:06:07:08:09:0a",
    dl_vlan_enable=False,
    vlan_vid=0,
    vlan_pcp=0,
    dl_vlan_cfi=0,
    ip_src="192.168.0.1",
    ip_dst="192.168.0.2",
    ip_tos=0,
    ip_ecn=None,
    ip_dscp=None,
    ip_ttl=64,
    ip_id=0x0001,
    ip_flags=0x0,
    ip_ihl=None,
    ip_options=False,
    inner_frame=None,
):
    """
    Return a simple dataplane IPv4 encapsulated packet

    Supports a few parameters:
    @param len Length of packet in bytes w/o CRC
    @param eth_dst Destination MAC
    @param eth_src Source MAC
    @param dl_vlan_enable True if the packet is with vlan, False otherwise
    @param vlan_vid VLAN ID
    @param vlan_pcp VLAN priority
    @param ip_src IP source
    @param ip_dst IP destination
    @param ip_tos IP ToS
    @param ip_ecn IP ToS ECN
    @param ip_dscp IP ToS DSCP
    @param ip_ttl IP TTL
    @param ip_id IP ID
    @param ip_flags IP Flags
    @param inner_frame payload of the packet

    Generates a simple IPv4 encapsulated packet.
    """

    if MINSIZE > pktlen:
        pktlen = MINSIZE

    ip_tos = ip_make_tos(ip_tos, ip_ecn, ip_dscp)


    pkt = Ether(dst=eth_dst, src=eth_src) / IP(
        src=ip_src,
        dst=ip_dst,
        tos=ip_tos,
        ttl=ip_ttl,
        id=ip_id,
        flags=ip_flags,
        ihl=ip_ihl,
        proto=253, # experimental
    )

    if inner_frame:
        pkt = pkt / inner_frame
    else:
        pkt = pkt / ("D" * (pktlen - len(pkt)))

    return pkt


class Func_wrapper(object): # call a function later
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self):
        return self.func(*self.args, **self.kwargs)
