import json
import graph
import pdb

topo = dict()
topo["PortToVeth"] = []

fat_tree_graph = graph.Graph(15)
fat_tree_graph.construct_fattree_3()
pdb.set_trace()
total_cnt = 0
for i in range(15):
    for j in fat_tree_graph.edge[i]:
        if i < j:
            topo["PortToVeth"].append({"device_port": fat_tree_graph.lookup_global_id(i, j), "veth1": total_cnt * 2, "veth2": total_cnt * 2 + 1})
            topo["PortToVeth"].append({"device_port": fat_tree_graph.lookup_global_id(j, i), "veth1": total_cnt * 2 + 1, "veth2": total_cnt * 2})
            total_cnt += 1


topo["PortToVeth"].append({
    "device_port":64,
    "veth1":250,
    "veth2":251
})

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

json.dump(topo, open("topo.json", "w"), indent=4)

