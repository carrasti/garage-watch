import re

K = BLACK = 0
G = GREEN = 1
R = RED = 2
Y = YELLOW = 3

class Icon8x8(object):
	COLOR_TYPE_MONOCHROME = 0
	COLOR_TYPE_TRI = 1
	
	def __init__(self, iconstr, color=None):
		
		if len(iconstr) != 8 * 8:
			raise Exception("Invalid length")
		
		# extract the type and validate
		if re.match(r'^[0RGY]+$', iconstr):
			self.color_type = Icon8x8.COLOR_TYPE_TRI
		elif re.match(r'^[01]+$', iconstr):
			self.color_type = Icon8x8.COLOR_TYPE_MONOCHROME
		else:
			raise Exception("Invalid color scheme")
		
		self.matrix = self.extract_matrix(iconstr, color)
		
	def get_pixel_color(self, character, color=None):
		if character == '0':
			return 0
			
		if self.color_type == Icon8x8.COLOR_TYPE_MONOCHROME and character == '1':
			return color if color else 1
		elif character == 'R':
			return R
		elif character == 'G':
			return G
		elif character == 'Y':
			return Y
	
	def rotate(self, value):
		"""
		rotates the matrix and returns itself
		"""
		assert value in (0, 90, 180, 270)
		if value == 90:
			self.matrix = [
				[self.matrix[7-row][col] for row in range(0, 8)] for col in range(0, 8)
			]
		elif value == 180:
			self.matrix = [
				[self.matrix[7-col][7-row] for row in range(0, 8)] for col in range(0, 8)
			]
		elif value == 270:
			self.matrix = [
				[self.matrix[row][7-col] for row in range(0, 8)] for col in range(0, 8)
			]
		return self
	
	def extract_matrix(self, iconstr, color=None):
		return [
			[self.get_pixel_color(iconstr[row * 8 + col], color) for col in range(0, 8)] for row in range(0, 8)
		]
