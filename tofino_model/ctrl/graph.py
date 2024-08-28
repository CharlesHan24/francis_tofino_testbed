import copy
class Graph(object):
    def __init__(self, n=20):
        self.n = n
        self.m = 0
        self.edge = []
        for i in range(n):
            self.edge.append([]) # ordered list
        
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

    def lookup_global_id(self, u, v):
        if self.n == 20:
            base = u * 4 if u < 12 else 12 * 4 + (u - 12) * 2
        else:
            if u < 3:
                base = u * 3
            elif u < 9:
                base = 9 + 7 * ((u - 3) >> 1) + (4 if ((u & 1) == 0) else 0)
            else:
                base = 30 + 2 * (u - 9)
        
        return base + self.lookup_id(u, v)
    
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

        self.edge[2][2], self.edge[2][0] = self.edge[2][0], self.edge[2][2]
        self.edge[4][2], self.edge[4][0] = self.edge[4][0], self.edge[4][2]
        # self.edge[10][1], self.edge[10][0] = self.edge[10][0], self.edge[10][1] # make sure that (3, 10) is the failed link and the edge is the last edge in the list for node 3 and 10
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
                    print("father {} is {}".format(v, u))
                    self.parent[v] = self.lookup_global_id(v, u)
                    self.children[u] |= (1 << i)
                    queue.append(v)

    def calc_neighbors(self, u):
        return len(self.edge[u])
    