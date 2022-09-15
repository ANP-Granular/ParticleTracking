# assignment problem solver

from pgraph import *
import itertools as it
from random import choice, shuffle
from copy import deepcopy


# basic "single" hungarian method
def basic_hungarian(g, maximize = True):
    g0, cost, c = g, 0, (0, 1)
    while g0.P > 1:
        g0, p0, cost0 = g0.hungarian_flatten((0,1), maximize=maximize)  # False if minimizing
        cost += cost0
    return cost


# returns optimal solution for partitions (0,1)
def bipartite_hungarian(g, maximize=True):
    p0 = g.hungarian((0,1), maximize=maximize)  # False if minimizing
    return g.cost((0,1), p0), [((0,1), p0)]



# recursively check all hungarian possibilities and select best
# if use_c is (i,j) do not loop through all partition pairs
def greedy_hungarian(g, use_c = None, maximize=True):

    sgn = [-1, 1][bool(maximize)]

    # two partitions
    if g.P == 2:
        return bipartite_hungarian(g, maximize= maximize)[0]

    best = None

    c_set = it.combinations(range(g.P), 2) if use_c is None else [use_c]

    best_c, best_cost = None, None

#    print(list(c_set))
    for c in c_set:
        g0, p0, cost0 = g.hungarian_flatten(c, maximize=maximize)
        #print(g0,p0,cost0)
        if best_c is None or sgn*cost0 > sgn*best_cost:
            best_cost = cost0
            best_c = deepcopy(c)

        #cost1, perms = multiple_hungarian(g0, maximize=maximize)
        # perms are inner permutations

        '''
        if best is None or sgn*(cost0+cost1) > sgn*best[0]:
            new_perms = [(restore_partition_pair(c, cx), p) for (cx, p) in perms]
            best = (cost0+cost1, new_perms + [(tuple(c), p0)])
        '''

    g0, p0, cost0 = g.hungarian_flatten(best_c, maximize=maximize)
    sub_cost = greedy_hungarian(g0, maximize=maximize)#[0]
    return best_cost + sub_cost

#    return best[0], reconstruct_permutations(best[1])


# recursively check all hungarian possibilities and select best
# if use_c is (i,j) do not loop through all partition pairs
def multiple_hungarian(g, use_c = None, maximize=True):

    sgn = [-1, 1][bool(maximize)]

    # two partitions
    if g.P == 2:
        return bipartite_hungarian(g, maximize= maximize)

    best = None

    c_set = it.combinations(range(g.P), 2) if use_c is None else [use_c]

    for c in c_set:
        g0, p0, cost0 = g.hungarian_flatten(c, maximize=maximize)

        cost1, perms = multiple_hungarian(g0, maximize=maximize)
        # perms are inner permutations

        if best is None or sgn*(cost0+cost1) > sgn*best[0]:
            new_perms = [(restore_partition_pair(c, cx), p) for (cx, p) in perms]
            best = (cost0+cost1, new_perms + [(tuple(c), p0)])

    return best[0], reconstruct_permutations(best[1])


# perform contractions on all possible permutations and with steepest descent keep on performing contractions
def iterative_hungarian_old(g, maximize=True):
    sgn = [-1, 1][bool(maximize)]

    if g.P == 2:
        return bipartite_hungarian(g, maximize=maximize)

    # get initial solution
    best_cost, cps = multiple_hungarian(g, maximize=maximize)

    while True:

        best = None
        # loop through all possible partition pairs
   #     print("cps",cps)
        for c, p in cps:

            cost0, g0 = g.cost(c, p), g.flatten(c, p)

            cost1, cps1 = multiple_hungarian(g0, maximize=maximize)

            # replace best if better solution
            if best is None or sgn*best[0] < sgn*(cost0+cost1): #
                cps2 = [(restore_partition_pair(c, cx), p) for (cx, p) in cps1]
                best = (cost0+cost1, cps2)

        if sgn*best[0] <= sgn*best_cost:

            break
        else:

    #            best_cost, cps = best

            best_cost = best[0]
            cps = reconstruct_permutations(best[1])
    return best

# perform contractions on all possible permutations and with steepest descent keep on performing contractions
def iterative_hungarian(g, maximize=True):
    sgn = [-1, 1][bool(maximize)]

    if g.P == 2:
        return bipartite_hungarian(g, maximize=maximize)

    # get initial solution
    best_cost, cps = multiple_hungarian(g, maximize=maximize)

    while True:

        best = None

        for c, p in cps:

            cost0, g0 = g.cost(c, p), g.flatten(c, p)  # flatten g by matching p

            cost1, cps1 = multiple_hungarian(g0, maximize=maximize)  # compute new solution of g/p

            # replace best if better solution
            if best is None or sgn*best[0] < sgn*(cost0+cost1): #

                cps2 = [(restore_partition_pair(c, cx), p) for (cx, p) in cps1]

                best = (cost0+cost1, cps2 + [(tuple(c),np.array(p))])  # store as best, add contracted solution

        if sgn*best[0] <= sgn*best_cost:  # solution is not better than previous solution
            break

        else:
             best_cost, cps = best[0], reconstruct_permutations(best[1])  # reconstruct the entire new k-matching

    return best

'''
def iterative_hungarian_random(g, maximize=True):
  t = [iterative_hungarian_random_one(g, maximize=maximize) for i in range(10)]
  tc = [(x[0],i) for i,x in enumerate(t)]
  m,i = min(tc)
  return t[i]
'''

# perform contractions on all possible permutations and with steepest descent keep on performing contractions

# E
def iterative_hungarian_random_one(g, maximize=True):
    sgn = [-1, 1][bool(maximize)]

    if g.P == 2:
        return bipartite_hungarian(g, maximize=maximize)

    # get initial solution
    best_cost, cps = multiple_hungarian(g, maximize=maximize)
    best = [best_cost, cps]

    while True:


        found_new = False

        #print(cps)

        shuffle(cps)

        for c, p in cps:

            cost0, g0 = g.cost(c, p), g.flatten(c, p)  # flatten g by matching p

            cost1, cps1 = multiple_hungarian(g0, maximize=maximize)  # compute new solution of g/p

            # replace best if better solution
            if sgn*best[0] < sgn*(cost0+cost1): #

                #print(best, "vs", cost0+cost1)

                cps2 = [(restore_partition_pair(c, cx), p) for (cx, p) in cps1]

                best = (cost0+cost1, cps2 + [(tuple(c),np.array(p))])  # store as best, add contracted solution

                found_new = True

                break

        if not found_new:
            break
        else:
             best_cost, cps = best[0], reconstruct_permutations(best[1])  # reconstruct the entire new k-matching

    return best



def iterative_hungarian_random_one_best_of_n(g, n, maximize=True):

    results = []
    for i in range(n):

        cost, cps = iterative_hungarian_random_one(g, maximize=maximize)
        results.append(cost)

    if maximize:
        return max(results)
    else:
        return min(results)



# perform contractions on all possible permutations and with steepest descent keep on performing contractions
def iterative_hungarian_random_two(g, maximize=True):
    sgn = [-1, 1][bool(maximize)]

    if g.P == 2:
        return bipartite_hungarian(g, maximize=maximize)

    # get initial solution
    best_cost, cps = multiple_hungarian(g, maximize=maximize)
    best = [best_cost, cps]

    for x in range(100):


        found_new = False

        #print(cps)

        shuffle(cps)

        equals = []

        for c, p in cps:

            cost0, g0 = g.cost(c, p), g.flatten(c, p)  # flatten g by matching p

            cost1, cps1 = multiple_hungarian(g0, maximize=maximize)  # compute new solution of g/p


            # replace best if better solution
            if sgn*best[0] < sgn*(cost0+cost1): #

                #print(best, "vs", cost0+cost1)

                cps2 = [(restore_partition_pair(c, cx), p) for (cx, p) in cps1]

                best = (cost0+cost1, cps2 + [(tuple(c),np.array(p))])  # store as best, add contracted solution

                found_new = True

                break

            elif sgn*best[0] == sgn*(cost0+cost1):
                cps2 = [(restore_partition_pair(c, cx), p) for (cx, p) in cps1]
                equals.append( (cost0+cost1, cps2 + [(tuple(c),np.array(p))]))

        if not found_new:
            if len(equals) <= 1:
                break
            best_cost, bestcps1 = choice(equals)
            cps = reconstruct_permutations(bestcps1)
        else:
             best_cost, cps = best[0], reconstruct_permutations(best[1])  # reconstruct the entire new k-matching

    return best