# stats for APn algorithm

from statistics import mean, pstdev
from time import time
import csv

timer_data = {}

def start_timer(i):
    global timer_data
    timer_data[i] = time()

def timer_value(i):
    global timer_data
    return time() - timer_data[i]

# print stats, input: method name strings, times, costs
def print_stats(ss, times, costs):

    for i, s in enumerate(ss):
        print(s, round(mean(times[i]),4), round(mean([1.0*c for c in costs[i]]),1))


def fmeansd(a):
    fa = [1.0*x for x in a]
    return mean(fa), pstdev(fa)

def fmean(a):
    fa = [1.0*x for x in a]
    return mean(fa)
# write csv

def csv_write(name, data):
    with open(name, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(data)
