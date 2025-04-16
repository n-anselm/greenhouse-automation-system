# Author: nanselm
# Updated on: 2025-04-16

import machine
import dht
import time
from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

# VARIABLES
OPEN_TEMP = 28            # Default temps to open/close windows
CLOSE_TEMP = 22
WINDOW_OPEN = False       # Track window open/closed status
ACTUATOR_TIME = 50        # Time it takes to open/close the actuator (seconds) | OG: 35 | SET TO: 45
ACTUATOR_ACTIVE = False   # Status of actuator
START_TIME = 0            # Start time of actuator
MANUAL_MODE = False       # Auto/manual mode switch
WINDOW_TEXT = ""          # Text to show while opening/closing windows

# PINS
PIN_SDA = 0                          #              (yellow)
PIN_SCL = 1                          #              (blue)
PIN_TEMP_SENSOR = machine.Pin(2)     #              (black)
PIN_LOWTEMP_UP = machine.Pin(10)     #              (cyan) 
PIN_LOWTEMP_DOWN = machine.Pin(11)   #              (cyan) 
PIN_HIGHTEMP_UP = machine.Pin(12)    #              (purple)
PIN_HIGHTEMP_DOWN = machine.Pin(13)  #              (purple)
PIN_MANUAL_RETRACT = machine.Pin(14) #              (brown)
PIN_MANUAL_EXTEND = machine.Pin(15)  #              (brown)
PIN_MODE_SWITCH = machine.Pin(28)    #              (gray)
PIN_MOTOR_ENABLE = machine.Pin(3)    # R_EN, L_EN   (gray)
PIN_RIGHT_PWM = machine.Pin(4)       # RPWM         (yellow)
PIN_LEFT_PWM = machine.Pin(5)        # LPWM         (blue)

# Sensor
dht_sensor = dht.DHT22(PIN_TEMP_SENSOR)

# LCD setup
I2C_ADDR     = 0x27
I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16
i2c = I2C(0, sda=machine.Pin(PIN_SDA), scl=machine.Pin(PIN_SCL), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

# Define motor control pins
ENABLE_PIN = machine.Pin(PIN_MOTOR_ENABLE, machine.Pin.OUT) # Right and left enable
RIGHT_PWM_PIN = machine.Pin(PIN_RIGHT_PWM, machine.Pin.OUT) # Retract
LEFT_PWM_PIN = machine.Pin(PIN_LEFT_PWM, machine.Pin.OUT)   # Extend

# Define buttons
btn_lowtemp_up = machine.Pin(PIN_LOWTEMP_UP, machine.Pin.IN, machine.Pin.PULL_UP)
btn_lowtemp_down = machine.Pin(PIN_LOWTEMP_DOWN, machine.Pin.IN, machine.Pin.PULL_UP)
btn_hightemp_up = machine.Pin(PIN_HIGHTEMP_UP, machine.Pin.IN, machine.Pin.PULL_UP)
btn_hightemp_down = machine.Pin(PIN_HIGHTEMP_DOWN, machine.Pin.IN, machine.Pin.PULL_UP)
btn_manual_retract = machine.Pin(PIN_MANUAL_RETRACT, machine.Pin.IN, machine.Pin.PULL_UP)
btn_manual_extend = machine.Pin(PIN_MANUAL_EXTEND, machine.Pin.IN, machine.Pin.PULL_UP)

# Mode switch (auto/manual)
mode_switch = machine.Pin(PIN_MODE_SWITCH, machine.Pin.IN, machine.Pin.PULL_UP)

# Button flags
btn_lowtemp_up_pressed = False
btn_lowtemp_down_pressed = False
btn_hightemp_up_pressed = False
btn_hightemp_down_pressed = False
btn_manual_retract_pressed = False
btn_manual_extend_pressed = False

def button_pressed(pin):
    global btn_lowtemp_up_pressed, btn_lowtemp_down_pressed, btn_hightemp_up_pressed, btn_hightemp_down_pressed, btn_manual_retract_pressed, btn_manual_extend_pressed
    time.sleep_ms(50)
    if pin == btn_lowtemp_up and not MANUAL_MODE:
        btn_lowtemp_up_pressed = True
    elif pin == btn_lowtemp_down and not MANUAL_MODE:
        btn_lowtemp_down_pressed = True
    elif pin == btn_hightemp_up and not MANUAL_MODE:
        btn_hightemp_up_pressed = True
    elif pin == btn_hightemp_down and not MANUAL_MODE:
        btn_hightemp_down_pressed = True
    elif pin == btn_manual_retract and MANUAL_MODE and not ACTUATOR_ACTIVE:
        btn_manual_retract_pressed = True
    elif pin == btn_manual_extend and MANUAL_MODE and not ACTUATOR_ACTIVE:
        btn_manual_extend_pressed = True

# Attach interrupt function to buttons
btn_lowtemp_up.irq(trigger=machine.Pin.IRQ_RISING, handler=button_pressed)
btn_lowtemp_down.irq(trigger=machine.Pin.IRQ_RISING, handler=button_pressed)
btn_hightemp_up.irq(trigger=machine.Pin.IRQ_RISING, handler=button_pressed)
btn_hightemp_down.irq(trigger=machine.Pin.IRQ_RISING, handler=button_pressed)
btn_manual_retract.irq(trigger=machine.Pin.IRQ_RISING, handler=button_pressed)
btn_manual_extend.irq(trigger=machine.Pin.IRQ_RISING, handler=button_pressed)

def extend_actuator():
    print("Extend actuator function called") # DEBUG
    ENABLE_PIN.value(1)
    #RIGHT_PWM_PIN.value(0)
    LEFT_PWM_PIN.value(1)
    for _ in range(ACTUATOR_TIME):
        time.sleep(1)
    stop_actuator()

def retract_actuator():
    print("Retract actuator function called") # DEBUG
    ENABLE_PIN.value(1)
    #LEFT_PWM_PIN.value(0)
    RIGHT_PWM_PIN.value(1)
    for _ in range(ACTUATOR_TIME):
        time.sleep(1)
    stop_actuator()

def stop_actuator():
    LEFT_PWM_PIN.value(0)
    RIGHT_PWM_PIN.value(0)
    ENABLE_PIN.value(0)
    
def check_mode_switch():
    global MANUAL_MODE
    MANUAL_MODE = not mode_switch.value()  # Invert because PULL_UP means LOW = ON
    print("Mode: MANUAL" if MANUAL_MODE else "Mode: AUTO")

def open_window():
    global ACTUATOR_ACTIVE, START_TIME
    print("Open window function called") # DEBUG
    ENABLE_PIN.value(1)
    #RIGHT_PWM_PIN.value(0)
    LEFT_PWM_PIN.value(1)
    START_TIME = time.time()
    ACTUATOR_ACTIVE = True
    
def close_window():
    global ACTUATOR_ACTIVE, START_TIME
    print("Close window function called") # DEBUG
    ENABLE_PIN.value(1)
    #LEFT_PWM_PIN.value(0)
    RIGHT_PWM_PIN.value(1)
    START_TIME = time.time()
    ACTUATOR_ACTIVE = True

def update_actuator():
    global ACTUATOR_ACTIVE
    # If actuator is running
    if ACTUATOR_ACTIVE:
        lcd.move_to(0, 0)
        lcd.putstr("                ")
        lcd.move_to(0, 0)
        lcd.putstr(WINDOW_TEXT)
        # If time is greater than time length
        #print("Current time: " + str(time.time()) + " Start time: " + str(ACTUATOR_TIME)) # DEBUG
        #print("Elapsed time: " + str(time.time() - START_TIME)) # DEBUG
        if time.time() - START_TIME >= ACTUATOR_TIME:
            stop_actuator()
            ACTUATOR_ACTIVE = False


check_mode_switch() # Check if auto or manual mode

if not MANUAL_MODE:
    # Close windows on power-on to have a reference point
    lcd.move_to(0, 0)
    #lcd.putstr("CLOSING WINDOWS")
    WINDOW_TEXT = "CLOSING WINDOWS"
    close_window()

while True:
    
    update_actuator()
    check_mode_switch() # Check if auto or manual mode
    
    # Read temp
    try:
        dht_sensor.measure()
        temp = round(dht_sensor.temperature())
        humidity = round(dht_sensor.humidity())
        
    # If unable to read the temp sensor
    except Exception as e:
        if not ACTUATOR_ACTIVE:
            print("Error reading DHT22: ", str(e))
            lcd.clear()
            lcd.move_to(1, 0)
            lcd.putstr("ERROR READING")
            lcd.move_to(2, 1)
            lcd.putstr("TEMPERATURE")
        continue
    
    # Only in Auto mode
    if not MANUAL_MODE:
        # BUTTONS
        # Increase lowtemp
        if btn_lowtemp_up_pressed:
            btn_lowtemp_up_pressed = False
            if CLOSE_TEMP != (OPEN_TEMP - 1):
                CLOSE_TEMP += 1
                print("Close temp updated to " + str(CLOSE_TEMP) + " C")
            else:
                print("Close temp limit reached!")
        # Decrease lowtemp
        elif btn_lowtemp_down_pressed:
            btn_lowtemp_down_pressed = False
            CLOSE_TEMP -= 1
            print("Close temp updated to " + str(CLOSE_TEMP) + " C")
        # Increase hightemp
        elif btn_hightemp_up_pressed:
            btn_hightemp_up_pressed = False
            OPEN_TEMP += 1
            print("Open temp updated to " + str(OPEN_TEMP) + " C")
        # Decrease hightemp
        elif btn_hightemp_down_pressed:
            btn_hightemp_down_pressed = False
            if OPEN_TEMP != (CLOSE_TEMP + 1):
                OPEN_TEMP -= 1
                print("Open temp updated to " + str(OPEN_TEMP) + " C")
            else:
                print("Open temp limit reached!")
        
    # DEBUG
    #print("Temperature: {:.2f} ºC".format(temp))
    #print("Humidity: {:.2f} %".format(humidity))
    
    # --- AUTO MODE ---
    if not MANUAL_MODE:
        
        lcd.move_to(0, 1)
        lcd.putstr(str(CLOSE_TEMP))
        lcd.move_to(13, 1)
        lcd.putstr("   ")
        lcd.move_to(14, 1)
        lcd.putstr(str(OPEN_TEMP))
        
        lcd.move_to(2, 1)
        lcd.putstr("            ")
        lcd.move_to(4, 1)
        lcd.putstr("HUM: " + str(humidity) + "%")
        
        # --- Open window ---
        if temp >= OPEN_TEMP and not ACTUATOR_ACTIVE:
            if not WINDOW_OPEN:
                lcd.move_to(0, 0)
                WINDOW_TEXT = "OPENING WINDOWS"
                WINDOW_OPEN = True
                open_window()
            
            #if not ACTUATOR_ACTIVE:
            lcd.move_to(0, 0)
            lcd.putstr("                ")
            lcd.move_to(4, 0)
            lcd.putstr(str(temp) + "C OPEN")
        # --- Close window ---
        elif temp <= CLOSE_TEMP and not ACTUATOR_ACTIVE:
            if WINDOW_OPEN:
                lcd.move_to(0, 0)
                WINDOW_TEXT = "CLOSING WINDOWS"
                WINDOW_OPEN = False
                close_window()
                
            #if not ACTUATOR_ACTIVE:
            lcd.move_to(0, 0)
            lcd.putstr("                ")
            lcd.move_to(3, 0)
            lcd.putstr(str(temp) + "C CLOSED")
        else:
            if not ACTUATOR_ACTIVE:
                if WINDOW_OPEN:
                    lcd.move_to(0, 0)
                    lcd.putstr("                ")
                    lcd.move_to(4, 0)
                    lcd.putstr(str(temp) + "C OPEN")
                else:
                    lcd.move_to(0, 0)
                    lcd.putstr("                ")
                    lcd.move_to(3, 0)
                    lcd.putstr(str(temp) + "C CLOSED")

    # --- MANUAL MODE ---
    else:
        lcd.move_to(0, 1)
        lcd.putstr("            ")
        lcd.move_to(0, 1)
        lcd.putstr("HUM: " + str(humidity) + "%")
        lcd.move_to(10, 1)
        lcd.putstr("MANUAL")
        
        # --- Close window ---
        # Close button pressed
        if btn_manual_retract_pressed:
            btn_manual_retract_pressed = False
            WINDOW_TEXT = "CLOSING WINDOWS"
            WINDOW_OPEN = False
            close_window()
        # --- Open window ---
        # Open button pressed
        elif btn_manual_extend_pressed:
            btn_manual_extend_pressed = False
            WINDOW_TEXT = "OPENING WINDOWS"
            WINDOW_OPEN = True
            open_window()
        else:
            if not ACTUATOR_ACTIVE:
                if WINDOW_OPEN:
                    lcd.putstr("                ")
                    lcd.move_to(4, 0)
                    lcd.putstr(str(temp) + "C OPEN")
                else:
                    lcd.putstr("                ")
                    lcd.move_to(3, 0)
                    lcd.putstr(str(temp) + "C CLOSED")
    
    time.sleep(0.2)
