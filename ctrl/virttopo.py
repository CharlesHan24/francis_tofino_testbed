import json
import graph
import pdb

mode = "sim"
mode = "hw"

topo = dict()
topo["PortToVeth"] = []

fat_tree_graph = graph.Graph(15)
fat_tree_graph.construct_fattree_3()
pdb.set_trace()
total_cnt = 0
for i in range(15):
    for j in fat_tree_graph.edge[i]:
        if i < j:
            veth1 = total_cnt * 2 if mode == "sim" else (total_cnt * 4)
            veth2 = total_cnt * 2 + 1 if mode == "sim" else (total_cnt * 4 + 1)
            topo["PortToVeth"].append({"device_port": fat_tree_graph.lookup_global_id_self(i, j), "veth1": veth1, "veth2": veth2})
            veth1 = total_cnt * 2 + 1 if mode == "sim" else (total_cnt * 4 + 2)
            veth2 = total_cnt * 2 if mode == "sim" else (total_cnt * 4 + 3)
            topo["PortToVeth"].append({"device_port": fat_tree_graph.lookup_global_id_self(j, i), "veth1": veth1, "veth2": veth2})
            total_cnt += 1


topo["PortToVeth"].append({
    "device_port":64,
    "veth1":250,
    "veth2":251
})

if mode == "sim":
    topo["PortToVeth"].append({
    "device_port":54,
    "veth1":54,
    "veth2":55
    })
    topo["PortToVeth"].append({
        "device_port":55,
        "veth1":55,
        "veth2":54
    })
else:
    topo["PortToVeth"].append({
    "device_port":54,
    "veth1":54 * 2,
    "veth2":54 * 2 + 1
    })
    topo["PortToVeth"].append({
        "device_port":55,
        "veth1":55 * 2,
        "veth2":55 * 2 + 1
    })

if mode == "hw":
    json.dump(topo, open("topo_hw.json", "w"), indent=4)
else:
    json.dump(topo, open("topo.json", "w"), indent=4)

