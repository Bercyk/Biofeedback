import webiopi
import time
import spidev
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(5,GPIO.OUT)
GPIO.output(5, GPIO.HIGH)
GPIO.setup(21, GPIO.OUT)
SERVO_INSTANCE = GPIO.PWM(21, 50)
IMPULSE = 97
SERVO_INSTANCE.start(IMPULSE)
time.sleep(1)
SERVO_INSTANCE.start(100)
GPIO.output(5, GPIO.LOW)
TASK = 0
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz = 500000
spi.bits_per_word = 8
spi.mode = 0b00

class ADC:
    def __init__(self, current, adc, voltage):
        self.current = current
        self.adc = adc
        self.voltage = voltage
        self.resistance = 0
        self.error = ['0']
        self.offset_resistance = 0

    def init_ADC(self):
        self.reset()
        id = self.read_ID()
        if id != 75:
            self.error.append("ID_error")
        self.write_Default_Config()
        self.write_Io_Register_ADC(0)

    def read_ID(self):
        spi.writebytes([0x60])
        time.sleep(0.01)
        id = spi.readbytes(1).pop()
        return id

    def read_Io_Register(self):
        spi.writebytes([0x68])
        time.sleep(0.01)
        current_config = spi.readbytes(1).pop()
        if current_config == 0:
            self.current = 0
        else:
            if current_config == 1:
                self.current = 0.01
            else:
                if current_config == 2:
                    self.current = 0.21
                else:
                    if current_config == 3:
                        self.current = 1.0
                    else:
                        if current_config == 9:
                            self.current = 0.02
                        else:
                            if current_config == 10:
                                self.current = 0.42
                            else:
                                self.error.append("wrong_current_get_value")
        return

    def reset(self):
        spi.writebytes([0xFF])
        spi.writebytes([0xFF])
        spi.writebytes([0xFF])
        time.sleep(1)
        return

    def read_ADC(self):
        temp = 0
        for i in range(0,5):
            spi.writebytes([0x58])
            result = spi.readbytes(3)
            self.adc = (result[0] << 16) + (result[1] << 8) + result[2]
            self.calc_voltage()
            temp = temp + self.voltage
        self.voltage = temp / 5
        return

    def calc_voltage(self):
        self.voltage = (self.adc * 4.096) / 0xFFFFFF
        self.calc_resistance()
        return

    def calc_resistance(self):
        if self.current != 0:
            self.resistance = (self.voltage / self.current) - self.offset_resistance
        return

    #value:
    # 0- no current, 1 - 10uA, 2 - 20uA, 3 - 210uA, 4 - 420 uA, 5 - 1 mA
    def write_Io_Register_ADC(self, value):
        if value == 0:
          id = 0x00
        else: 
            if value == 1:
                id = 0x01
            else:
                if value == 2:
                    id = 0x09
                else:
                    if value == 3:
                        id = 0x02
                    else:
                        if value == 4:
                            id = 0x0A
                        else:
                            if value == 5:
                                id = 0x03
                            else:
                                self.error.append("wrong_current_set_value")
                                return
        spi.writebytes([0x28])
        spi.writebytes([id])
        spi.writebytes([0x68])
        anwser = spi.readbytes(1).pop()
        if anwser != id:
            self.error.append("current_set_error")
        else:
            self.read_Io_Register()
        return

    def read_Config(self):
        spi.writebytes([0x50])
        config = spi.readbytes(2)
        return config

    def write_Default_Config(self):
        config = [0x10, 0x10]
        spi.writebytes([0x10])
        spi.writebytes(config)
        spi.writebytes([0x50])
        config_set = spi.readbytes(2)
        if config_set != config:
            self.error.append("default_config_set_error")
        return


ADC_INSTANCE = ADC(0,0,0)


def setup():
    ADC_INSTANCE.init_ADC()

def loop():
    if TASK == 0:
        time.sleep(0.5)
    if TASK == 1:
        auto_measure_resistance()
    if TASK == 2:
        manual_measure_resistance()


def destroy():
    SERVO_INSTANCE.stop()
    GPIO.cleanup()
    spi.close()
    time.sleep(1)


def manual_measure_resistance():
    ADC_INSTANCE.write_Io_Register_ADC(1)
    while TASK == 2:
        ADC_INSTANCE.read_ADC()
        time.sleep(0.5)
    ADC_INSTANCE.write_Io_Register_ADC(0)
    ADC_INSTANCE.resistance = 0
    ADC_INSTANCE.voltage = 0
    return


def auto_measure_resistance():
    i = 1
    ADC_INSTANCE.write_Io_Register_ADC(i)
    while TASK == 1:
        ADC_INSTANCE.write_Io_Register_ADC(i)
        time.sleep(0.1)
        ADC_INSTANCE.read_ADC()
        if ADC_INSTANCE.current == 0.01:
            if ADC_INSTANCE.voltage < 1.9:
                i = i + 1
        if ADC_INSTANCE.current == 0.02:
            if ADC_INSTANCE.voltage > 4.0:
                i = i - 1
            else:
                if ADC_INSTANCE.voltage < 0.36:
                    i = i + 1
        if ADC_INSTANCE.current == 0.21:
            if ADC_INSTANCE.voltage > 4.0:
                i = i - 1
            else:
                if ADC_INSTANCE.voltage < 1.68:
                    i = i + 1
        if ADC_INSTANCE.current == 0.42:
            if ADC_INSTANCE.voltage > 4.0:
                i = i - 1
            else:
                if ADC_INSTANCE.voltage < 1.59:
                    i = i + 1
        if ADC_INSTANCE.current == 1.0:
            if ADC_INSTANCE.voltage > 4.0:
                i = i - 1
        time.sleep(0.1)
        IMPULSE = 97-((ADC_INSTANCE.resistance*180)/409)*0.05
        SERVO_INSTANCE.ChangeDutyCycle(IMPULSE)
    IMPULSE = 97
    SERVO_INSTANCE.ChangeDutyCycle(IMPULSE)
    time.sleep(1)
    SERVO_INSTANCE.ChangeDutyCycle(100)
    ADC_INSTANCE.write_Io_Register_ADC(0)
    ADC_INSTANCE.resistance = 0
    ADC_INSTANCE.voltage = 0
    return

@webiopi.macro
def setTask(task_number):
    global TASK
    TASK = int(task_number)
    return getValues()

@webiopi.macro
def getValues():
    return "%d;%.3f;%.3f;%.6f" % (TASK, ADC_INSTANCE.current, ADC_INSTANCE.voltage, ADC_INSTANCE.resistance)

@webiopi.macro
def setCurrent(current):
    ADC_INSTANCE.write_Io_Register_ADC(int(current))
    return getValues()

@webiopi.macro
def setAngle(angle):
    global IMPULSE
    IMPULSE = 97-(int(angle)*0.05)
    SERVO_INSTANCE.ChangeDutyCycle(IMPULSE)
    time.sleep(2)
    SERVO_INSTANCE.ChangeDutyCycle(100)
    return

@webiopi.macro
def getErrors():
    return