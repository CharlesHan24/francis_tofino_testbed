import copy
class Graph(object):
    def __init__(self, n=20):
        self.n = n
        self.m = 0
        self.edge = []
        for i in range(n):
            self.edge.append([]) # ordered list
        self.mode = "sim"
        self.is_deformed = False
    
    def set_hw_mode(self):
        self.mode = "hw"
    
    def set_orig_mode(self):
        self.mode = "orig"

    def add_edge(self, u, v):
        self.edge[u].append(v)
        self.edge[v].append(u)
        self.m += 2 # total number of ports that take into account the failed link (two ports)

    def delete_edge(self, u, v):
        # self.m -= 2
        if self.lookup_global_id(u, v) == self.parent[u]:
            self.children[v] ^= (1 << self.lookup_id(v, u))
        else:
            self.children[u] ^= (1 << self.lookup_id(u, v))
        
        self.edge[u].pop(self.lookup_id(u, v))
        self.edge[v].pop(self.lookup_id(v, u))

        # delete the children relationship between u and v
        
            

    def lookup_id(self, u, v):
        for i in range(len(self.original_edges[u])):
            if self.original_edges[u][i] == v:
                return i

    def lookup_global_id_self(self, u, v): # looking up the port number according to the simulation-based port numbering scheme of its LOCAL PORTS: incrementally assigning ports looping over the nodes from 0 to n - 1. For hardware mode, we need to use the lookup_global_id interface for ingress/egress port translation. The egress port number should be the ingress port number of its peer so as to allow transmitting the packet through loopback, i.e. lookup_global_id(u, v) = lookup_global_id_self(v, u). In this case, packet to be delivered at the egress pipeline appear exactly at the its peer's ports, and later on emerges at its peer's ingress pipeline after loopback.
        if self.n == 20:
            base = u * 4 if u < 12 else 12 * 4 + (u - 12) * 2
        elif self.is_deformed == False:
            if u < 3:
                base = u * 3
            elif u < 9:
                base = 9 + 7 * ((u - 3) >> 1) + (4 if ((u & 1) == 0) else 0)
            else:
                base = 30 + 2 * (u - 9)
        else:
            if u < 3:
                base = u * 3
            elif u < 9:
                base = 9 + 7 * ((u - 3) >> 1) + (3 if ((u & 1) == 0) else 0)
            else:
                base = 30 + 2 * (u - 9)
        
        return base + self.lookup_id(u, v)

    def lookup_global_id(self, u, v): # looking up the port id of its egress pipeline which, in case of the hardware mode being set, should be the peer's port id for later loopback && appearing at the peer's ingress pipeline.
        print(self.mode)
        if self.mode == "hw":
            return self.lookup_global_id_self(v, u)
        else:
            return self.lookup_global_id_self(u, v)
    
    def igport_egport_translation(self, u, global_id):
        if self.mode == "sim":
            return global_id
        else:
            for neighbor in self.edge[u]:
                if self.lookup_global_id_self(u, neighbor) == global_id:
                    return self.lookup_global_id_self(neighbor, u)

    def construct_fattree_4(self):
        for i in range(4):
            for j in range(4):
                self.add_edge(i, 4 + j * 2 + (i >= 2))

        for j in range(4):
            for k in range(2):
                for l in range(2):
                    self.add_edge(4 + j * 2 + k, 12 + j * 2 + l)
        
        self.edge[13][1], self.edge[13][0] = self.edge[13][0], self.edge[13][1] # make sure that (4, 13) is the failed link and the edge is the last edge in the list for node 4 and 13
        self.original_edges = copy.deepcopy(self.edge)

    def construct_fattree_3(self):
        for i in range(3):
            for j in range(3):
                self.add_edge(i, 3 + j * 2 + (i >= 2))
        
        for j in range(3):
            for k in range(2):
                for l in range(2):
                    self.add_edge(3 + j * 2 + k, 9 + j * 2 + l)

        if self.mode != "orig":
            self.edge[2][2], self.edge[2][0] = self.edge[2][0], self.edge[2][2]
            self.edge[4][2], self.edge[4][0] = self.edge[4][0], self.edge[4][2]
        # self.edge[10][1], self.edge[10][0] = self.edge[10][0], self.edge[10][1] # make sure that (3, 10) is the failed link and the edge is the last edge in the list for node 3 and 10
        self.original_edges = copy.deepcopy(self.edge)

    def construct_fattree_3_deformed(self):
        self.is_deformed = True
        for i in range(3):
            for j in range(3):
                self.add_edge(i, 3 + j * 2 + (i >= 1))
        
        for j in range(3):
            for k in range(2):
                for l in range(2):
                    self.add_edge(3 + j * 2 + k, 9 + j * 2 + l)
        
        if self.mode != "orig": # cutting down an edge between 0, and 7
            self.edge[7][0], self.edge[7][2] = self.edge[7][2], self.edge[7][0]
        self.original_edges = copy.deepcopy(self.edge)

    
    def spanning_tree(self, root=0):
        self.parent = [-1] * self.n
        self.children = [0 for i in range(self.n)]
        visited = [False] * self.n
        queue = []
        queue.append(root)
        visited[root] = True
        while queue:
            u = queue.pop(0)
            for i, v in enumerate(self.edge[u]):
                if not visited[v]:
                    visited[v] = True
                    # print("father {} is {}".format(v, u))
                    self.parent[v] = self.lookup_global_id_self(v, u) # parent is defined as the ingress port so as to be consistent with the data plane implementation!
                    self.children[u] |= (1 << i)
                    queue.append(v)

    def calc_neighbors(self, u):
        return len(self.edge[u])
    