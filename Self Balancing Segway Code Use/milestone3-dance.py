'''
-------------------------------------------------------
Name: Milestone 2 - Dance to Beat
Creator:  Group 8
Date:   March 2018
Revision:  ?
-------------------------------------------------------
Drive motors to perform dance to beat
-------------------------------------------------------
This program does the following:

1. Use interrupt to collect samples from mic at 8kHz rate.
2. Compute instantenous energy E for 20msec window
3. Obtain sum of previous 50 instanteneous energy measurements as sum_energy, equivalent to 1 sec worth of signal.
4. Find the ratio c = instantenous energy/(sum_energy/50)
5. Wait for elapsed time > (beat_period - some margin) since last detected beat
6. Check c value and if higher than BEAT_THRESHOLD, flash blue LED
7. If average energy lower than a certain threshold, then does not try to detect beats (only detects beats when there is loud music playing)
'''

import pyb
from pyb import Pin, Timer, ADC, DAC, LED
import time
from array import array			# need this for memory allocation to buffers
from oled_938 import OLED_938	# Use OLED display driver
from motor import DRIVE

import micropython
micropython.alloc_emergency_exception_buf(100)

# Use OLED to say what segway is doing
oled = OLED_938(pinout={'sda': 'Y10', 'scl': 'Y9', 'res': 'Y8'}, height=64, external_vcc=False, i2c_devid=61)
oled.poweron()
oled.init_display()
oled.draw_text(0,0, 'Group 8')
oled.draw_text(0, 10, 'Milestone2:Dance')
oled.draw_text(0, 20, 'Press USR button')
oled.display()

print('Performing Milestone 2')
print('Waiting for button press')
trigger = pyb.Switch()		# Create trigger switch object
while not trigger():		# Wait for trigger press
	time.sleep(0.001)
while trigger():
	pass			# Wait for release
print('Button pressed - Running')
oled.draw_text(0, 30, 'Button pressed - Running')
oled.display()

# --- Microphone set up --- #
# define ports for microphone, LEDs and trigger out (X5)
mic = ADC(Pin('Y11'))
MIC_OFFSET = 1527		# ADC reading of microphone for silence
dac = pyb.DAC(1, bits=12)  # Output voltage on X5 (BNC) for debugging
b_LED = LED(4)		# flash for beats on blue LED

N = 160				# size of sample buffer s_buf[]
s_buf = array('H', 0 for i in range(N))  # reserve buffer memory
ptr = 0				# sample buffer index pointer
buffer_full = False	# semaphore - ISR communicate with main program

def energy(buf):	# Compute energy of signal in buffer
	sum = 0
	for i in range(len(buf)):
		s = buf[i] - MIC_OFFSET	# adjust sample to remove dc offset
		sum = sum + s*s			# accumulate sum of energy
	return sum

# ---- The following section handles interrupts for sampling data -----

# Interrupt service routine to fill sample buffer s_buf
def isr_sampling(dummy): 	# timer interrupt at 8kHz
	global ptr				# need to make ptr visible inside ISR
	global buffer_full		# need to make buffer_full inside ISR

	s_buf[ptr] = mic.read()	# take a sample every timer interrupt
	ptr += 1				# increment buffer pointer (index)
	if (ptr == N):			# wraparound ptr - goes 0 to N-1
		ptr = 0
		buffer_full = True	# set the flag (semaphore) for buffer full

# Create timer interrupt - one every 1/8000 sec or 125 usec
pyb.disable_irq()			# disable interrupt while configuring timer
sample_timer = pyb.Timer(7, freq=8000)	# set timer 7 for 8kHz
sample_timer.callback(isr_sampling)		# specify interrupt service routine
pyb.enable_irq()			# enable interrupt again

# -------- End of interrupt section ----------------

# Define constants for main program loop - shown in UPPERCASE
M = 50						# number of instantaneous energy epochs to sum
BEAT_THRESHOLD = 1		# threshold for c to indicate a beat (original 2.0)
# SILENCE_THRESHOLD = 1.3		# threshold for c to indicate silence

# Onitialise variables for main program loop
e_ptr = 0					# pointer to energy buffer
e_buf = array('L', 0 for i in range(M))	# reserve storage for energy buffer
sum_energy = 0				# total energy in last 50 epochs
pyb.delay(100)

# --- LED set up --- #
def flash():		# routine to flash blue LED when beat detected
	b_LED.on()
	pyb.delay(30)
	b_LED.off()

# --- Dance set up --- #
motor = DRIVE()

def dance_steps(filename): # Read dance moves text file
	char_list = [ch for ch in open(filename).read() if ch not in ['\r', '\n']]
	return char_list

def dance(steps, i, v): # Define dance steps
	step = steps[i]
	if step == 'A':
		print('Spin: wheels in opposite direction')
		motor.right_forward(v)
		motor.left_back(v)
	elif step == 'B':
		print('right 45')
		motor.right_forward(v / 3)
		motor.left_forward(v)
	elif step == 'C':
		print('left 45')
		motor.right_forward(v)
		motor.left_forward(v / 3)
	elif step == 'D':
		print('Left 45 backwards')
		motor.right_back(v)
		motor.left_back(v / 3)
	elif step == 'E':
		print('right 45 backwards')
		motor.right_back(v / 3)
		motor.left_back(v)
	elif step == 'F':
		print('Stop')
		motor.stop()

# Read text file with choreographed dance moves
DanceMoveList = dance_steps('StripTheWillow.txt') #debug
counter = 0

# --- Main program loop --- #


tic = pyb.millis()			# mark time now in msec

try:
	while True:				# Main program loop
		if buffer_full:		# semaphore signal from ISR - set if buffer is full

			# Calculate instantaneous energy
			E = energy(s_buf)

			# compute moving sum of last 50 energy epochs
			sum_energy = sum_energy - e_buf[e_ptr] + E
			e_buf[e_ptr] = E		# over-write earlest energy with most recent
			e_ptr = (e_ptr + 1) % M	# increment e_ptr with wraparound - 0 to M-1

			if sum_energy > 50000000:
				# Compute ratio of instantaneous energy/average energy
				c = E*M/sum_energy

				if (pyb.millis()-tic > 380):	# if more than 500ms since last beat
					if (c>BEAT_THRESHOLD):		# look for a beat
						flash()					# beat found, flash blue LED
						if counter >= len(DanceMoveList):
							counter = 0
						else:
							dance(DanceMoveList, counter, 25)  # from StepFunctions(steps, i, v), 20 = v = PWM motor speed
							counter += 1
							tic = pyb.millis()		# reset tic
				buffer_full = False				# reset status flag
finally:
	motor.stop()
