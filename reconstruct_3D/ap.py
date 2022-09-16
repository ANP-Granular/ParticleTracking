# taken from:
# https://stackoverflow.com/questions/60940781/solving-the-assignment-problem-for-3-groups-instead-of-2

###############################################################################
###############################################################################


# import modules
import copy
import itertools
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pulp

# number of people (or items) per group (or dimension)
dims = [8, 4, 12]

# dummy weight array
# (one weight for each combination of people, with one from each group)
np.random.seed(0)
weights = np.random.rand(*dims)

# implement and solve problem
def maximum_npartite_matching(weights):

    # get dimensions from weights array
    dims = weights.shape

    # prepare auxiliary variables
    grid = [range(dim) for dim in dims]
    varx = itertools.product(*grid)

    # initialize variables
    xxx = pulp.LpVariable.dicts('xxx', varx, cat=pulp.LpBinary)

    # initialize optimization problem
    problem = pulp.LpProblem('nD matching', pulp.LpMaximize)

    # set objective
    # sum_ijk... c_ijk... x_ijk...
    problem += pulp.lpSum([weights[iii] * xxx[iii] for iii in xxx])

    # set constraints
    # sum_i x_ijk... <= 1
    # sum_j x_ijk... <= 1
    # sum...
    for idi, dim in enumerate(dims):
        for idv in range(dim):
            gric = copy.deepcopy(grid)
            gric[idi] = [idv]
            vary = itertools.product(*gric)
            problem += pulp.lpSum(xxx[iii] for iii in vary) <= 1

    # solve problem
    problem.solve()

    # write binary variables to array
    rex = weights.copy() * 0
    for iii in xxx:
        rex[iii] = xxx[iii].value()

    # find optimal matching = path and path weights
    whr = np.where(rex)
    paths = np.array(whr).T
    pathw = weights[whr]

    # print paths (n columns) and corresponding weights (last column)
    result = np.vstack([paths.T, pathw]).T
    print(result)

    return whr

# run matching
whr = maximum_npartite_matching(weights)

# define function for plotting results as network
def plot_results(weights, whr):

    # create list of node positions for plotting and labeling
    pon = [(idi, idv) for idi, dim in enumerate(dims) for idv in range(dim)]
    # convert to dictionary
    pos = {tuple(poi): poi for poi in pon}

    # create empty graph
    graph = nx.empty_graph(len(pos))
    # rename labels according to plot position
    mapping = {idp: tuple(poi) for idp, poi in enumerate(pon)}
    graph = nx.relabel_nodes(graph, mapping)

    # set edges from maximum n-partite matching
    edges = []
    # loop over paths
    for whi in np.array(whr).T:
        weight = weights[tuple(np.array(whj) for whj in whi)]
        pairs = list(zip(whi[:-1], whi[1:]))
        # loop over consecutive node pairs along path
        for idp, (id0, id1) in enumerate(pairs):
            edges.append(((idp+0, id0), (idp+1, id1), {'weight': weight}))
    graph.add_edges_from(edges)

    # set path weights as edge widths for plotting
    width = np.array([edge['weight'] for id0, id1, edge in graph.edges(data=True)])
    width = 3.0*width/max(width)

    #plot network
    fig = plt.figure(figsize=(16, 9))
    obj = weights[whr].sum()
    plt.title('total matching weight = %.2f' % obj)
    nx.draw_networkx(graph, pos=pos, width=width, node_color='orange', node_size=700)
    plt.axis('off')

    return graph, pos

# run plotting
graph, pos = plot_results(weights, whr)