import os,sys
import struct
import hashlib



class Cert:
    def __init__(self, buff:bytes) -> None:
        self.size1 = struct.unpack("<Q",buff[:8])
        (self.size2,self.magic) = struct.unpack("<Q16s", buff[-24:])
        self.ptr = 8
        max_size = len(buff) - 24

        while(self.ptr < max_size):
            (id_seq_size, _id) = struct.unpack("<QI", buff[self.ptr: self.ptr + 12])
            self._ptr_add(12)
            



    def _ptr_add(self, offset) -> None:
        '''
        self.ptr 增加offset，同时保证4字节对齐
        '''
        self.ptr += offset
        while self.ptr % 4 != 0:
            self.ptr += 1