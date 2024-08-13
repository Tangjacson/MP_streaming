import numpy as np


class Path:
    def __init__(self, id):
        self.id = id

    def setup(self, bw, rtt):
        self.rtt = rtt
        self.baåndwidth = bw
        self.stream_list = []
    
    def close(self):
        self.rtt = 9999

    def assign_stream(self, stream):
        self.stream_list.append(stream)



class stream:
    def __init__(self, id, time_stamp, length):
        self.id = id
        self.time_stamp = time_stamp
        self.length = length
        self.bit_rate
        self.msssim
        self.psnr