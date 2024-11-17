#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2024 Hiroaki Santo

import argparse
import os
import time

import numpy as np
import serial

DELAY = 0.5


class CS2000A:
    def __init__(self, com_port):
        self.ser = serial.Serial(
            port=com_port,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        if self.ser.is_open:
            print("CS-2000A is connected")
        else:
            print("Failed to connect to CS-2000A")

    def enable_remote_mode(self):
        self.ser.write(b'RMTS,1\r\n')
        time.sleep(DELAY)
        response = self.ser.readline().decode('utf-8').strip()
        if "OK00" in response:
            print("Remote mode enabled successfully")
        else:
            raise Exception(f"Failed to enable remote mode: {response}")

    def start_measurement(self):
        self.ser.write(b"MEAS,1\r\n")
        print("Starting measurement...")
        time.sleep(DELAY)
        response = self.ser.readline().decode('utf-8').strip()
        if "OK00" in response:
            _, measurement_time = response.split(",")
            measurement_time = int(measurement_time)
            print(f"Measurement started successfully: {measurement_time} seconds")
            time.sleep(measurement_time)
        else:
            raise Exception(f"Failed to start measurement: {response}")

    def read_measurement_data(self):
        while True:
            data = self.ser.readline().decode('utf-8').strip()
            if "OK00" == data:
                break
            else:
                time.sleep(1)

        measurement_result = []
        for i in ['01', '02', '03', '04']:
            self.ser.write(f'MEDR,1,0,{i}\r\n'.encode('utf-8'))
            time.sleep(DELAY)
            data = self.ser.readline().decode('utf-8').strip()
            if "OK00" in data:
                data = data.replace("OK00,", "")
                measurement_result.append(data)
            else:
                raise Exception(f"Failed to read data: {data}")

        measurement_result = ",".join(measurement_result).split(",")
        measurement_result = np.array(measurement_result, dtype=float)
        return measurement_result

    def close_connection(self):
        self.ser.write(b'RMTS,0\r\n')
        time.sleep(DELAY)
        self.ser.close()
        print("Connection closed")

    def measure(self):
        try:
            self.enable_remote_mode()
            self.start_measurement()
            spectral_data = self.read_measurement_data()
            assert spectral_data is not None
        finally:
            self.close_connection()
        return spectral_data


def save_measurement_data(output_dir_path: str, data: np.ndarray):
    os.makedirs(output_dir_path, exist_ok=True)
    wavelengths = np.arange(380, 781, 1)
    assert len(wavelengths) == len(data), (len(wavelengths), len(data))

    write_data = np.stack([wavelengths, data], axis=0)
    np.savetxt(os.path.join(output_dir_path, "spectral.csv"), write_data, delimiter=",")

    print(f"Data saved to {output_dir_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="CS2000A Spectroradiometer")
    parser.add_argument('--port', type=str, required=True)
    parser.add_argument('--output_dir_path', type=str, required=True)
    args = parser.parse_args()

    cs2000a = CS2000A(args.port)
    spectral_data = cs2000a.measure()
    save_measurement_data(args.output_dir_path, spectral_data)
