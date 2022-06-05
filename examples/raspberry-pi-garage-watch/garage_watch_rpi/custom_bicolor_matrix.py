from adafruit_ht16k33 import matrix

import logging

# logger for the script
_logger = logging.getLogger(__name__)


class CustomBicolorMatrix8x8(matrix.Matrix8x8x2):
	"""
	Extend the BiColorMatrix with extra method for printing a matrix
	and enable rotation
	"""
	rotation = 0
	
	def __init__(self, *args, **kwargs):
		self.set_rotation(kwargs.pop('rotation', 0))
		super().__init__(*args, **kwargs)
		
	def rotate_matrix(self, matrix, value):
		assert value in (0, 90, 180, 270)
		if value == 0:
			return matrix
		elif value == 90:
			return [
				[matrix[7-row][col] for row in range(0, 8)] for col in range(0, 8)
			]
		elif value == 180:
			return [
				[matrix[7-col][7-row] for row in range(0, 8)] for col in range(0, 8)
			]
		elif value == 270:
			return [
				[matrix[row][7-col] for row in range(0, 8)] for col in range(0, 8)
			]
	
	def set_rotation(self, rotation):
		assert rotation in (0, 90, 180, 270)
		self.rotation = rotation
		
	def set_matrix_image(self, matrix):
		self.fill(0)
		m = self.rotate_matrix(matrix, self.rotation)
		for y, row in enumerate(m):
			for x, val in enumerate(row):
				self[x, y] = val
		try:
			self.show()
		except:
			_logger.exception('Error writing to display')

