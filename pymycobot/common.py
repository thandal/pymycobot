# coding=utf-8

from __future__ import division
import struct
import time


class ProtocolCode(object):
    # BASIC
    HEADER = 0xFE
    FOOTER = 0xFA

    # System status
    VERSION = 0x00

    # Overall status
    POWER_ON = 0x10
    POWER_OFF = 0x11
    IS_POWER_ON = 0x12
    RELEASE_ALL_SERVOS = 0x13
    IS_CONTROLLER_CONNECTED = 0x14
    READ_NEXT_ERROR = 0x15
    SET_FREE_MODE = 0x1A
    IS_FREE_MODE = 0x1B

    # MDI MODE AND OPERATION
    GET_ANGLES = 0x20
    SEND_ANGLE = 0x21
    SEND_ANGLES = 0x22
    GET_COORDS = 0x23
    SEND_COORD = 0x24
    SEND_COORDS = 0x25
    PAUSE = 0x26
    IS_PAUSED = 0x27
    RESUME = 0x28
    STOP = 0x29
    IS_IN_POSITION = 0x2A
    IS_MOVING = 0x2B

    # JOG MODE AND OPERATION
    JOG_ANGLE = 0x30
    JOG_COORD = 0x32
    JOG_STOP = 0x34
    SET_ENCODER = 0x3A
    GET_ENCODER = 0x3B
    SET_ENCODERS = 0x3C
    GET_ENCODERS = 0x3D

    # RUNNING STATUS AND SETTINGS
    GET_SPEED = 0x40
    SET_SPEED = 0x41
    GET_FEED_OVERRIDE = 0x42
    GET_ACCELERATION = 0x44
    GET_JOINT_MIN_ANGLE = 0x4A
    GET_JOINT_MAX_ANGLE = 0x4B

    # SERVO CONTROL
    IS_SERVO_ENABLE = 0x50
    IS_ALL_SERVO_ENABLE = 0x51
    SET_SERVO_DATA = 0x52
    GET_SERVO_DATA = 0x53
    SET_SERVO_CALIBRATION = 0x54
    RELEASE_SERVO = 0x56
    FOCUS_SERVO = 0x57

    # ATOM IO
    SET_PIN_MODE = 0x60
    SET_DIGITAL_OUTPUT = 0x61
    GET_DIGITAL_INPUT = 0x62
    SET_PWM_MODE = 0x63
    SET_PWM_OUTPUT = 0x64
    GET_GRIPPER_VALUE = 0x65
    SET_GRIPPER_STATE = 0x66
    SET_GRIPPER_VALUE = 0x67
    SET_GRIPPER_INI = 0x68
    IS_GRIPPER_MOVING = 0x69
    SET_COLOR = 0x6A

    # Basic
    SET_BASIC_OUTPUT = 0xA0
    GET_BASIC_INPUT = 0xA1


class DataProcessor(object):
    # Functional approach
    def _encode_int8(self, data):
        return struct.pack("b", data)

    def _encode_int16(self, data):
        return list(struct.pack(">h", data))

    def _decode_int8(self, data):
        return struct.unpack("b", data)[0]

    def _decode_int16(self, data):
        return struct.unpack(">h", data)[0]

    def _angle2int(self, angle):
        return int(angle * 100)

    def _coord2int(self, coord):
        return int(coord * 10)

    def _int2angle(self, _int):
        return round(_int / 100.0, 3)

    def _int2coord(self, _int):
        return round(_int / 10.0, 2)

    def _flatten(self, _list):
        return sum(
            ([x] if not isinstance(x, list) else self._flatten(x)
             for x in _list), []
        )

    def _process_data_command(self, args):
        if not args:
            return []

        return self._flatten(
            [
                [self._encode_int16(int(i))
                 for i in x] if isinstance(x, list) else x
                for x in args
            ]
        )

    def _is_frame_header(self, data, pos):
        return data[pos] == ProtocolCode.HEADER and data[pos + 1] == ProtocolCode.HEADER

    def _process_received(self, data, genre):
        if not data:
            return []

        data = bytearray(data)
        body_len = 0
        # Get valid header: 0xfe0xfe
        for idx in range(len(data) - 2):
            if self._is_frame_header(data, idx):
                body_len = data[idx + 2] - 2
                if body_len > 0:
                    break
        else:
            return []

        # compare send header and received header
        cmd_id = data[idx + 3]
        if cmd_id != genre:
            return []
        data_pos = idx + 4
        body = data[data_pos:(data_pos + body_len)]

        # check the footer: 0xfa

        # process valid data
        res = []
        if body_len == 12 or body_len == 8:
            for idx in range(0, len(body), 2):
                one = body[idx: idx + 2]
                res.append(self._decode_int16(one))
        elif body_len == 2:
            if genre in [ProtocolCode.IS_SERVO_ENABLE]:
                return [self._decode_int8(body[1:2])]
            res.append(self._decode_int16(body))
        else:
            res.append(self._decode_int8(body))
        return res

    def _process_single(self, data):
        return data[0] if data else -1


def write(self, command):
    self.log.debug("_write: {}".format(command))
    self._serial_port.write(command)
    # Default Windows flush is really inefficient: it sleeps for 0.05s.
    #self._serial_port.flush()
    while self._serial_port.out_waiting:
        time.sleep(0.005)

# Aggressively pre-read the mystery messages so that we get straight to the real message.
# NOTE: this only works with an efficient transponder on the Basic, like SimpleTransponder.
FAST_READ = False
FAST_READ_SIZE = 96

def read(self):
    if FAST_READ: 
        self._serial_port.read(FAST_READ_SIZE)
    mystery_size = 0
    while True:
        header = self._serial_port.read(3)
        if (len(header) == 3) and (header[0] == 0xFF) and (header[1] == 0xFF):
            # Read the undocumented messages that precede every read. They have the format:
            # Header: 0xFF 0xFF
            # Instruction?: 0xXX
            # Length: 0xXX
            # Body: (Length bytes)
#            self.log.debug(f"_read: mystery header {header}")
            length = self._serial_port.read(1)
#            self.log.debug(f"_read: mystery instruction {header[2]} length {length[0]}")
            body = self._serial_port.read(length[0])
#            self.log.debug(f"_read: mystery body {body}")
            mystery_size += 3 * length[0]
        elif (len(header) == 3) and (header[0] == ProtocolCode.HEADER) and (header[1] == ProtocolCode.HEADER):
            self.log.debug(f"_read: mystery_size={mystery_size}")
            # Read the actual messages we want.
            length = header[2]
            body = self._serial_port.read(length)
            if len(body) < length:
                self.log.debug("_read: could not read body")
                return None
            data = header + body
            self.log.debug("_read: {}".format(data))
            return data
        else:
            self.log.error(f"_read: bad header {header}")
