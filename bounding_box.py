def bounding_box( box1 , box2, overlap_thresh=0.5 ):
	"""
	box = [top_left_x,top_left_y, bottom_right_x, bottom_right_y]
	overlap_thresh :threshhold for considering box1 in box2
	return  1 : box1 in box2
	return  0 : box2 in box1
	return -1 : no overlap
	"""

	if (box1[2] > box2[0]) & (box1[3] > box2[1]) & (box2[2] > box1[0]) & (box2[3] > box1[1]):
		xtemp1 = max( box1[0] , box2[0] )
		ytemp1 = max( box1[1] , box2[1] )
		xtemp2 = min( box1[2] , box2[2] )
		ytemp2 = min( box1[3] , box2[3] )
		x_overlap = xtemp2 - xtemp1
		y_overlap = ytemp2 - ytemp1
		overlap_area = x_overlap*y_overlap
		box1_area= (box1[2]-box1[0])*(box1[3]-box1[1])
		box2_area= (box2[2]-box2[0])*(box2[3]-box2[1])
		percent_overlap_box1 = float(overlap_area)/float(box1_area)
		percent_overlap_box2 = float(overlap_area)/float(box2_area)

		if (percent_overlap_box1 > overlap_thresh):
			return 1
		if (percent_overlap_box2 > overlap_thresh):
			return 0

	return -1