from .custom_bicolor_matrix import CustomBicolorMatrix8x8
from .led_matrix_helpers import Icon8x8, R, G, K, Y
from .parking_controller import ParkingController

from adafruit_ht16k33 import segments

import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)


GRAPHICS = {
	'm_arrow': (
		'00011000'
		'00111100'
		'01111110'
		'11111111'
		'00111100'
		'00111100'
		'00111100'
		'00111100'
	),
	'b_stop': (
		'00RRRR00'
		'0RRRRRR0'
		'RRRRRRRR'
		'RRYYYYRR'
		'RRYYYYRR'
		'RRRRRRRR'
		'0RRRRRR0'
		'00RRRR00'
	),
	'm_smiley': (
		'00111100'
		'01000010'
		'10100101'
		'10000001'
		'10100101'
		'10011001'
		'01000010'
		'00111100'
	),
	'm_frown': (
		'00111100'
		'01000010'
		'10100101'
		'10000001'
		'10011001'
		'10100101'
		'01000010'
		'00111100'
	),
	'm_heart': (
		'01101100'
		'11111110'
		'11111110'
		'11111110'
		'01111100'
		'00111000'
		'00010000'
		'00000000'
	)
}

class LEDParkingController(ParkingController):
	YELLOW_ARROW = Icon8x8(GRAPHICS['m_arrow'], Y).matrix
	GREEN_ARROW = Icon8x8(GRAPHICS['m_arrow'], G).matrix
	RED_ARROW = Icon8x8(GRAPHICS['m_arrow'], R).matrix
	RED_ARROW_180 = Icon8x8(GRAPHICS['m_arrow'], R).rotate(90).matrix
	YELLOW_ARROW_180 = Icon8x8(GRAPHICS['m_arrow'], Y).rotate(90).matrix
	STOP = Icon8x8(GRAPHICS['b_stop']).matrix
	GREEN_SMILEY = Icon8x8(GRAPHICS['m_smiley'], G).rotate(90).matrix
	RED_HEART = Icon8x8(GRAPHICS['m_heart'], R).matrix
	RED_FROWN = Icon8x8(GRAPHICS['m_frown'], R).matrix
	
	
	def __init__(self, rotation=None, i2c_address=None, i2c_busnum = None):
		super().__init__()
		
		display_kwargs = {}
		
		if rotation is not None:
			display_kwargs['rotation'] = rotation
		if i2c_address is not None:
			display_kwargs['address'] = i2c_address
		if i2c_busnum is not None:
			display_kwargs['busnum'] = i2c_busnum
			
		# Create display instance on default I2C address (0x70) and bus number.
		self.display = CustomBicolorMatrix8x8(i2c, **display_kwargs)

		# Initialize the display. Must be called once before using the display.
		self.display.fill(self.display.LED_OFF)
		self.display.show()

		self.seven_segment = segments.Seg7x4(i2c, address=0x71)
		self.seven_segment.show()


	def write_amount(self, value):
		assert isinstance(value, int)
		if not value:
			self.seven_segment.fill(0)
		else:
			self.seven_segment.print_number_str("{}".format(value))
		
		self.seven_segment.fill(0)

	def write_amounts(self, value1, value2):
		if value1 > 99:
			value1 = '-'
		if value2 > 99:
			value2 = '-'
			
		self.seven_segment.print_number_str("{:2}{:2}".format(value1, value2))
		self.seven_segment.show()
		
	def on_enter_hold(self):
		self.display.clear()
		self.seven_segment.fill(0)
		self.display.show()
		
	def on_enter_parking_start(self):
		self.display.set_matrix_image(self.GREEN_ARROW)

	def on_enter_parking_approach(self):
		self.display.set_matrix_image(self.YELLOW_ARROW)
	
	def on_enter_parking_parking(self):
		self.display.set_matrix_image(self.RED_ARROW)
		
	def on_enter_parking_inplace(self):
		self.display.set_matrix_image(self.GREEN_SMILEY)
	
	def on_enter_parking_toofar(self):
		self.display.set_matrix_image(self.RED_FROWN)

	def on_enter_exit_in_place(self):
		self.display.set_matrix_image(self.GREEN_SMILEY)

	def on_enter_exit_backup(self):
		self.display.set_matrix_image(self.YELLOW_ARROW_180)

	def on_enter_exit_complete(self):
		self.display.set_matrix_image(self.RED_HEART)
