# -*-: coding utf-8 -*-
""" Leds service for handling visual feedback for various states of
    the system. """

import random
import time
import struct
import code

import usb.core
import usb.util
from singleton import Singleton

class HID:
    """
    This class provides basic functions to access
    a USB HID device to write an endpoint
    """

    def __init__(self):
        self.dev = None
        self.ep_in = None
        self.ep_out = None

    @staticmethod
    def find(vid=0x2886, pid=0x0007):
        dev = usb.core.find(idVendor=vid, idProduct=pid)
        if not dev:
            return

        # get active config
        config = dev.get_active_configuration()

        # iterate on all interfaces:
        #    - if we found a HID interface
        interface_number = None
        for interface in config:
            if interface.bInterfaceClass == 0x03:
                interface_number = interface.bInterfaceNumber
                break

        try:
            if dev.is_kernel_driver_active(interface_number):
                dev.detach_kernel_driver(interface_number)
        except Exception as e:
            print(e.message)

        ep_in, ep_out = None, None
        for ep in interface:
            if ep.bEndpointAddress & 0x80:
                ep_in = ep
            else:
                ep_out = ep

        if ep_in and ep_out:
            hid = HID()
            hid.dev = dev
            hid.ep_in = ep_in
            hid.ep_out = ep_out

            return hid

    def write(self, data):
        """
        write data on the OUT endpoint associated to the HID interface
        """
        self.ep_out.write(data)

    def read(self):
        return self.ep_in.read(self.ep_in.wMaxPacketSize, -1)

    def close(self):
        """
        close the interface
        """
        usb.util.dispose_resources(self.dev)


class LedsService:
    """ Leds service for handling visual feedback for various states of
        the system. """

    class State:
        """ Leds states.- """
        none, waking_up, standby, listening, loading, notify, intent_recognized, error = range(8)

    def __init__(self):
        led_device = HID.find()
        if led_device:
            self.animator = ReSpeakerAnimator()
        else:
            print('No USB device found')

    def start_animation(self, animation_id):
        if not self.animator:
            return
        (animation, identifier) = self.get_animation(animation_id)

       
        self.animator.run(identifier, animation, )

    def get_animation(self, animation):
        identifier = str(random.randint(1, 100000))
        return (Animation(identifier, animation), identifier)


class Animation(Singleton):

    def __init__(self, id, active=0):
        self.id = id
        self.active = active


class ReSpeakerAnimator(object):

    def __init__(self):
        self.hid = HID.find()
        self.led_dict = {
            'LED_1': 3,
            'LED_2': 4,
            'LED_3': 4,
            'LED_4': 5,
            'LED_5': 6,
            'LED_6': 7,
            'LED_7': 8,
            'LED_8': 9,
            'LED_9': 10,
            'LED_10': 11,
            'LED_11': 12,
            'LED_12': 13,
            'LED_13': 14,
        }

        self.animation_none = [{value: 0 for value in self.led_dict.values()}]

        self.animation_waking_up = [{value: 2 * st for value in self.led_dict.values()} 
                                     for st in range(20) + list(reversed(range(15)))]
        
        self.animation_standby = [{value: st for value in self.led_dict.values()} 
                                   for st in list(range(31)) + list(reversed(range(31)))]

        # the matrix above:
        def value_blue(i, j, N):
            if i == j:
                return 0
            elif i == (j + 1) % N:
                return 0
            elif i == (j - 1) % N:
                return 64
            elif i == (j + 2) % N or i == (j - 2) % N:
                return 127
            else:
                return 255

        def value_red(i, j, N):
            if i == j:
                return 0
            elif i == (j + 1) % N:
                return 0
            elif i == (j - 1) % N:
                return int("400000", 16)
            elif i == (j + 2) % N or i == (j - 2) % N:
                return int("7f0000", 16) #middle
            else:
                return int("FF0000", 16) #darkest

        def value_green(i, j, N):
            if i == j:
                return 0
            elif i == (j + 1) % N:
                return 0
            elif i == (j - 1) % N:
                return int("004000", 16)
            elif i == (j + 2) % N or i == (j - 2) % N:
                return int("007f00", 16) #middle
            else:
                return int("00fe00", 16) #darkest

        self.animation_listening = []
        leds = range(3, 15)
        N = len(leds)
        for i in range(0, N):
            self.animation_listening.append({leds[j]: value_green(i, j, N) for j in range(0, N)})

        self.animation_loading = [{value: 16 * st for value in self.led_dict.values()}
                                  for st in list(range(15)) + list(reversed(range(15)))]


        self.animation_notify = []
        for frame in range(0, 2):
            self.animation_notify.append({value: int("0000ff", 16) for value in self.led_dict.values()})
            self.animation_notify.append({value: int("000000", 16) for value in self.led_dict.values()})

        print("\nNotify: " + str(self.animation_notify))

        self.animation_intent_recognized = []
        for frame in range(0, 2):
            self.animation_intent_recognized.append({value: int("00FF00", 16) for value in self.led_dict.values()})
            self.animation_intent_recognized.append({value: int("000000", 16) for value in self.led_dict.values()})

        self.animation_error = []
        for frame in range(0, 2):
            self.animation_error.append(
                {value: int("ff0000", 16) for value in self.led_dict.values()})
            self.animation_error.append(
                {value: int("000000", 16) for value in self.led_dict.values()})

        # Set the ReSpeaker in the right mode
        try:
            init_addr = 0  # 0x0
            init_data = 6  # 0x00000006

            self.write(init_addr, init_data)
        except Exception as e:
            print(e.message)

    def get_random_color(self):
        hex_color = hex(random.randint(0, 16777215))[2:]
        return int(hex_color, 16)

    def write(self, address, data):
        if data > 0xFFFF:
            data = struct.pack('<I', data)
        elif data > 0xFF:
            data = struct.pack('<H', data)

        data = self.to_bytearray(data)

        length = len(data)
        if self.hid:
            packet = bytearray([address & 0xFF, (address >> 8) & 0x7F, length & 0xFF, (length >> 8) & 0xFF]) + data
            packet = list(packet)
            self.hid.write(packet)

    def read(self, address, length):
        if self.hid:
            self.hid.write(list(bytearray(
                [address & 0xFF, (address >> 8) & 0xFF | 0x80, length & 0xFF, (length >> 8) & 0xFF])))
            for _ in range(6):
                data = self.hid.read()
                # skip VAD data
                if int(data[0]) != 0xFF and int(data[1]) != 0xFF:
                    return data[4:(4 + length)]

    @staticmethod
    def to_bytearray(data):
        if type(data) is int:
            array = bytearray([data & 0xFF])
        elif type(data) is bytearray:
            array = data
        elif type(data) is str:
            array = bytearray(data)
        elif type(data) is list:
            array = bytearray(data)
        else:
            raise TypeError('%s is not supported' % type(data))

        return array

    def run(self, id, animation):
        if animation.active == LedsService.State.none:
            for item in self.animation_none:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.5)
        elif animation.active == LedsService.State.waking_up:
            for item in self.animation_waking_up:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.02)
        elif animation.active == LedsService.State.standby:
            for item in self.animation_standby:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.05)
        elif animation.active == LedsService.State.listening:
            for item in self.animation_listening:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.01)
        elif animation.active == LedsService.State.loading:
            for item in self.animation_loading:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.01)
        elif animation.active == LedsService.State.notify:
            for item in self.animation_notify:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.1)
        elif animation.active == LedsService.State.intent_recognized:
            for item in self.animation_intent_recognized:
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.1)
        elif animation.active == LedsService.State.error:
            for item in self.animation_error:
                code.interact(local=dict(globals(), **locals()))
                if animation.id != id:
                    break
                for k, v in item.items():
                    self.write(k, v)
                time.sleep(0.2)
