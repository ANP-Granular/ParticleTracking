# PARTITIONED GRAPH CLASS

import numpy as np
import itertools as it
import scipy.optimize as op
# for plotting
import networkx as nx
import matplotlib.pyplot as plt
import pylab
from math import cos, sin, pi



class PGraph:

    # P = number of partitions, N = number of vertices
    # fill with values 0,...,rand_max-1
    def __init__(self, P, N, rand_max = None, weights = None, wf = None):

        self.P, self.N = P, N
        self.w = [[0]*P for i in range(P)]  # zero list of weights

        # choose random weights
        for i,j in it.combinations(range(P), 2):

            if wf is not None:

                self.w[i][j] = wf(size=(N,N))

            elif weights is not None:

                self.w[i][j] = weights[(i, j)]


            elif rand_max == None:
                self.w[i][j] = np.zeros(shape=(N, N))
            elif isinstance(rand_max,tuple):
                self.w[i][j] = np.random.randint(low=rand_max[0], high=(rand_max[1]+1), size=(N, N))
            else:
                self.w[i][j] = np.random.randint(rand_max, size=(N, N))

            self.w[j][i] = self.w[i][j].transpose()

    # returns either weights of tuple c or list of weights from partition c
    # self[(i,j)] = weights from partition i to partition j
    def __getitem__(self, c):
        if isinstance(c, tuple):
            return self.w[c[0]][c[1]]  # return weights
        else:
            return self.w[c]  # return list of weights

    # cost of weights between partitions c = (i,j) obtained by permutation p,
    # alternatively one can past a list of (parititon, perm) pairs for c
    def cost(self, c, p = None):
        if p is not None:
            return self[c][range(self.N), p].sum()
        else:
            return sum([self.cost(*x) for x in c])

    # flatten partitions c = (i,j) using permutation p
    def flatten(self, c, p):
       # if self.P <= 2: return None
        # new renumeration of parititons
        c0, c1 = sorted(c)
        ren = list(range(c1)) + [c0] + list(range(c1,self.P-1))

        # new empty graph
        g = PGraph(P=self.P - 1, N=self.N)  # zero graph

        # place the unaffected partitions to new graph (w/o copying values)
        for i, j in it.combinations(range(self.P), 2):
            if i not in c and j not in c:
                g.w[ren[i]][ren[j]] = self.w[i][j]
                g.w[ren[j]][ren[i]] = self.w[j][i]

        # place the affected partitions to new graph
        for i in range(self.P):
            if i not in c:
                g.w[ren[i]][c0] = self.w[i][c[0]] + self.w[c[1]][i][p].transpose()
                g.w[c0][ren[i]] = g.w[ren[i]][c0].transpose()

        return g#, ren #, self.cost(c,p)

    # perform hungarian method on partitions c[0] and c[1]
    def hungarian(self, c, maximize = True):
        row, col = op.linear_sum_assignment([1.0,-1.0][maximize]* self[c])
        return col

    def weight_range(self):
        m, M  = 10000,-10000
        for c in it.combinations(range(self.P),2):
            m = min(m, np.min(self[c]))
            M = max(m, np.max(self[c]))
        return m,M

    # returns "best" flattening with permutation and cost
    def hungarian_flatten(self, c, maximize = True):
        p = self.hungarian(c, maximize=maximize)
        return self.flatten(c, p), p, self.cost(c, p)

    # draw graph with partitions c & permutation p emphasized
    def draw(self, c = [], p = None):
        G = nx.Graph()
        edge_colors = []
        print(c)
        for i, j,(p0,p1) in it.product(range(self.N),range(self.N),it.combinations(range(self.P), 2)):
            b = ((((p0,p1) == c) and (p[i] == j))) or (((p1,p0) == c) and (p[j] == i))
            G.add_edge(i+p0*self.N,j+p1*self.N,label=self.w[p0][p1][i][j], color = ['darkcyan','black'][b], weight=[1,2][b])
       # print(G.edges)
        #edge_colors.reverse()
        sp = 0.5  # space
        pos = {i: (cos(((i//self.N)*(self.N+sp)+(i % self.N)) * 2.0 * pi / (self.P * (self.N + sp))),
                   sin(((i//self.N)*(self.N+sp)+(i % self.N)) * 2.0 * pi / (self.P * (self.N + sp))))
               for i in range(self.N*self.P)}
        edge_labels = dict([((u, v,), d['label']) for u, v, d in G.edges(data=True)])
        edge_colors = [G[u][v]['color'] for u,v in G.edges()]
        edge_weights = [G[u][v]['weight'] for u,v in G.edges()]
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        nx.draw_networkx_labels(G,pos,labels={i:i for i in range(self.N*self.P)})
        nx.draw(G, pos, node_color='red', node_size=120, edge_color=edge_colors, width = edge_weights)
        pylab.show()

    def __repr__(self):

        s = 'Graph ' + str(self.P) + ' partitions ' + str(self.N) + ' nodes.\n'
        for c in it.combinations(range(self.P), 2):
            s += str(c)+ ": "
            for row in self[c]:
                s += str(row) + "\n        "
            s = s[:-8] + "\n"
        return s


# restore permutation c if graph previously flattened by c_flat
def restore_partition_pair(c_flat, c):
    c_new = [i if i < max(c_flat) else i+1 for i in c]
    if c_new[0] == min(c_flat): c_new[0] = c_flat[0]
    if c_new[1] == min(c_flat): c_new[1] = c_flat[0]
    return c_new[0], c_new[1]


def invert_permutation(permutation):
    return [i for i, j in sorted(enumerate(permutation), key=lambda x: x[1])]


def order_partition_pair(cp):
    return cp if cp[0][0] < cp[0][1] else ((cp[0][1], cp[0][0]), invert_permutation(cp[1]))


# from a list of permutations compute all permutations
# so that the list forms a n-dimensional assignment problem
# input: [ (partition pair), permutation, ... ]
def reconstruct_permutations(cps):

    # sort cp-pairs
    cps0 = [order_partition_pair(cp) for cp in cps]
    cps0.sort(key=lambda x:x[0])
    used_comb = set([c for c,p in cps0])
    P = max([max(i, j) for i, j in used_comb])+1  # get number of partitions # TODO: should incude as parameter?

    while len(used_comb) < P * (P-1) // 2:

        for (c0,p0), (c1,p1) in it.combinations(cps0, 2):

            # combine permutations
            if c0[1] == c1[0]:
                c = (c0[0], c1[1])
                if c in used_comb: continue
                p = [p1[j] for j in p0]

            elif c0[0] == c1[0]:
                c = (c0[1], c1[1])
                if c in used_comb: continue
                p = [p1[j] for j in invert_permutation(p0)]

            elif c0[1] == c1[1]:
                c = (c0[0], c1[0])
                if c in used_comb: continue
                p1i = invert_permutation(p1)
                p = [p1i[j] for j in p0]

            else:
                continue

            used_comb |= set([c]) # add to combinations
            cps0.append((c,p)) # add to permutation set
            cps0.sort(key=lambda x: x[0])

    return cps0



def load_pgraph(s):
    file = open('data/'+s+'.txt', 'r')
    l = file.readlines()
    P, N, l = int(l[0]), int(l[1]), l[2:]
    data = [int(x) for x in (' '.join([i.strip() for i in l])).split()]
    weights = {}
    for i, c in enumerate(it.combinations(range(P), 2)):
        weights[c] = np.array([data[i*N*N:(i+1)*N*N]]).reshape((N, N))
    file.close()

    # get solution
    file = open('data/SOL' + s + '.txt', 'r')
    best = 0
    for l in file.readlines():
        if l.find('Total') >= 0:
        #    print(l)
            best = int(l.strip().split()[-1])
    file.close()

    return P, N, PGraph(P, N, weights=weights), best




