import os
import struct
from typing import List



class ResChunkHeader:
    res_type:int = None
    header_size:int = 0
    size:int = 0

    def __init__(self, buff:bytes) -> None:
        (self.res_type,
        self.header_size,
        self.size) = struct.unpack("<HHI", buff)
    
class StringPool:
    header = None
    string_offsets:List[int] = []
    style_offsets:List[int] = []
    
    # 会有故意使用错误字符对抗分析的情况，所以用二进制存储
    # 使用时可自行转换为字符串
    strings:List[bytes] = []
    styles:List[bytes] = []


