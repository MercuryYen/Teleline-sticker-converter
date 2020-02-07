import numpy as np
from PIL import Image
from numba import jit
from numba import types
from numba.typed import Dict,List

@jit(nopython=True)
def dis(a,b):
	return (a[0]-b[0])**2+(a[1]-b[1])**2+(a[2]-b[2])**2+(a[3]-b[3])**2

@jit(nopython=True)
def handle(arr,mag,new_arr):
	new_y = round(len(arr)*mag-0.5)
	new_x = round(len(arr[0])*mag-0.5)
	for i in range(new_y):
		for j in range(new_x):
			new_i = round(i/mag-0.5)
			new_j = round(j/mag-0.5)

			if new_i>=new_y:
				new_i=new_y-1
			if new_j>=new_x:
				new_j=new_x-1
			t = arr[new_i][new_j]

			new_arr[i][j][0] = t[0]
			new_arr[i][j][1] = t[1]
			new_arr[i][j][2] = t[2]
			new_arr[i][j][3] = t[3]
	return new_arr


def handle_image(mag,image_array):
	new_y = round(len(image_array)*mag)
	new_x = round(len(image_array[0])*mag)
	new_arr = np.zeros([new_y,new_x,4])
	return handle(image_array,mag,new_arr).astype(np.uint8)

