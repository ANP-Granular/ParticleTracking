# -*- coding: utf-8 -*-
"""
Created on Tue Mar 16 20:31:11 2021

@author: Dmitry Puzyrev
"""

import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d.axes3d as p3
import matplotlib.animation as animation

import matplotlib.image as mpimg

#import matplotlib.gridspec as gridspec

import pandas as pd

import trackpy as tp

import skimage

from scipy.io import loadmat

from scipy.signal import savgol_filter

from scipy.optimize import linear_sum_assignment

import seaborn as sns


#%%

# Turn interactive plotting off
plt.ioff()
    
color = 'blue'
    
df_col = pd.read_csv('in_csv/rods_df_{:s}.csv'.format(color))


#in_folder = 'D:/GAGa/2017_08_Fallturm/shot1/GP34/gp3/images/'
in_folder = 'in_images/'
out_folder = 'out_gp3_blue/'

for i_f in range(100,110):
#for i_f in range(frame_start+1,frame_end):
    
    #io.imread()
    
    img = mpimg.imread(in_folder+'{:04d}.jpg'.format(i_f))
    
    plt.figure(figsize=(12, 9), dpi = 200, tight_layout=True)
    plt.imshow(img)
    
    df_part = df_col[df_col['frame']==i_f].reset_index()
    
    for ind_rod in df_part['particle']:
        x1= df_part[df_part['particle']==ind_rod]['x1_gp3'].values[0]*10.0
        x2= df_part[df_part['particle']==ind_rod]['x2_gp3'].values[0]*10.0
        y1= df_part[df_part['particle']==ind_rod]['y1_gp3'].values[0]*10.0
        y2= df_part[df_part['particle']==ind_rod]['y2_gp3'].values[0]*10.0
        
        if df_part[df_part['particle']==ind_rod]['seen'].values[0]==1:
            plt.plot([x1,x2],[y1,y2],'b')
        else:
            plt.plot([x1,x2],[y1,y2],linestyle = 'dotted',color='b')
        
        plt.text((x1+x2)/2,(y1+y2)/2,'{:d}'.format(ind_rod))
    
    plt.savefig(out_folder+'blue_{:d}.png'.format(i_f), bbox_inches='tight')
    plt.clf()
    