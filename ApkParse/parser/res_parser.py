import struct
from typing import Dict, List, Tuple, Union
from lxml import etree
from xml.etree.ElementTree import Element   #这个用于开启代码提示
import logging


from ApkParse.utils.public_res_ids import PUBLIC_RES_ID

logger = logging.getLogger("apk_parse")

# https://cs.android.com/android/platform/superproject/+/master:frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h


############ ResType
RES_NULL_TYPE                     = 0x0000
RES_STRING_POOL_TYPE              = 0x0001
RES_TABLE_TYPE                    = 0x0002
RES_XML_TYPE                      = 0x0003

# Chunk types in RES_XML_TYPE
RES_XML_FIRST_CHUNK_TYPE          = 0x0100
RES_XML_START_NAMESPACE_TYPE      = 0x0100
RES_XML_END_NAMESPACE_TYPE        = 0x0101
RES_XML_START_ELEMENT_TYPE        = 0x0102
RES_XML_END_ELEMENT_TYPE          = 0x0103
RES_XML_CDATA_TYPE                = 0x0104
RES_XML_LAST_CHUNK_TYPE           = 0x017f
# This contains a uint32_t array mapping strings in the string
# pool back to resource identifiers.  It is optional.
RES_XML_RESOURCE_MAP_TYPE         = 0x0180

# Chunk types in RES_TABLE_TYPE
RES_TABLE_PACKAGE_TYPE            = 0x0200
RES_TABLE_TYPE_TYPE               = 0x0201
RES_TABLE_TYPE_SPEC_TYPE          = 0x0202
RES_TABLE_LIBRARY_TYPE            = 0x0203
RES_TABLE_OVERLAYABLE_TYPE        = 0x0204
RES_TABLE_OVERLAYABLE_POLICY_TYPE = 0x0205
RES_TABLE_STAGED_ALIAS_TYPE       = 0x0206
############ ResType end

############ Res_value types
TYPE_NULL               = 0x00
TYPE_REFERENCE          = 0x01
TYPE_ATTRIBUTE          = 0x02
TYPE_STRING             = 0x03
TYPE_FLOAT              = 0x04
TYPE_DIMENSION          = 0x05
TYPE_FRACTION           = 0x06
TYPE_DYNAMIC_REFERENCE  = 0x07
TYPE_DYNAMIC_ATTRIBUTE  = 0x08
TYPE_FIRST_INT          = 0x10
TYPE_INT_DEC            = 0x10
TYPE_INT_HEX            = 0x11
TYPE_INT_BOOLEAN        = 0x12
TYPE_FIRST_COLOR_INT    = 0x1c
TYPE_INT_COLOR_ARGB8    = 0x1c
TYPE_INT_COLOR_RGB8     = 0x1d
TYPE_INT_COLOR_ARGB4    = 0x1e
TYPE_INT_COLOR_RGB4     = 0x1f
TYPE_LAST_COLOR_INT     = 0x1f
TYPE_LAST_INT           = 0x1f
############ Res_value types end

############ size of some struct
RES_CHUNK_HEADER_SIZE           = 8         # 只有这个chunkheader大小是固定的，其他的供参考
STRING_POOL_HEADER_SIZE         = 0x1C      # string pool 头部大小
START_NAMESPACE_SIZE            = 0x18      # namespace结构体的大小，start namespace和end namespace是一样的
RES_XML_TREE_ATTREXT_SIZE       = 0x14      # res xml tree中关于attribute的描述信息的大小
CDATA_SIZE                      = 0x1C      # CData结构的基本大小
RES_VALUE_SIZE                  = 0x08      # ResValue结构体的大小
RES_TABLE_PACKAGE_HEADER_SIZE   = 0x120     # ResTablePackage的头部大小
RES_TABLE_TYPE_SPEC_SIZE        = 0x10      # ResTypeSpec的基本大小
RES_TABLE_TYPE_SIZE             = 0x14      # ResTableType的基本大小
############ size end

############ android官方资源中的，各个types对应的数值，没用到，先放着
RES_TYPES = {  
    0x01: "attr",
    0x02: "id",
    0x03: "style",
    0x04: "string",
    0x05: "dimen",
    0x06: "color",
    0x07: "array",
    0x08: "drawable",
    0x09: "layout",
    0x0a: "anim",
    0x0e: "integer",
    0x0b: "animator",
    0x0c: "interpolator",
    0x0d: "mipmap",
    0x11: "bool",
    0x0f: "transition",
    0x10: "raw",
    # 0x1010: "attr",   # TODO 还不知道pkg id为0x10的是干啥的
    # 0x10c0: "interpolator",
}
############



class ResChunkHeader:

    def __init__(self, buff:bytes) -> None:
        '''
        读取资源头 (8 bytes)
        '''
        if len(buff) >= RES_CHUNK_HEADER_SIZE:
            (self.res_type,
            self.header_size,
            self.size) = struct.unpack("<HHI", buff[:RES_CHUNK_HEADER_SIZE])

            if len(buff) < self.size:
                raise Exception(f"Chunk length error, except {self.size}, got {len(buff)}")

            self.buff = buff
            
            # self.ptr 作为一个虚拟的指针，用于定位当前数据读取的位置，由于android的资源文件都是4字节对齐的，
            # 读取完数据后需要有对齐操作，因此增加此指针和相关方法，方便数据读取
            self.ptr = RES_CHUNK_HEADER_SIZE
        else:
            raise Exception(f"Chunk header length error: {len(buff)}")

    def _ptr_add(self, offset) -> None:
        '''
        self.ptr 增加offset，同时保证4字节对齐
        '''
        self.ptr += offset
        while self.ptr % 4 != 0:
            self.ptr += 1
    
    def _ptr_reset(self, offset) -> None:
        '''
        self.ptr 重置位置，同时保证4字节对齐
        '''
        self.ptr = offset
        while self.ptr % 4 != 0:
            self.ptr += 1

# string chunk header flag
SORTED_FLAG = 1 << 0
UTF8_FLAG = 1 << 8

class StringPool(ResChunkHeader):
    def __init__(self, buff: bytes, pre_decode:bool = True) -> None:
        '''
        解析字符串池

        Args:
            buff: bytes buffer
            pre_decode: 在__init__函数中解析全部的字符串, 默认开启, 
                有特殊需求时(如只需要提取apk中某个已知id的字符串时)关闭可以提升一点效率
        '''
        super().__init__(buff)
        if self.header_size != STRING_POOL_HEADER_SIZE:
            # raise Exception("AXML: String pool header length error")
            logger.error("AXML: String pool header length error")
            pass
        
        header_buff = self.buff[RES_CHUNK_HEADER_SIZE: STRING_POOL_HEADER_SIZE]

        (self.string_cnt,
        self.style_cnt,
        self.flag,
        self.string_offset,
        self.style_offset) = struct.unpack("<5I", header_buff)
        self.is_utf8 = ((self.flag & UTF8_FLAG) != 0)
        logger.debug(f"StringPool: cnt--{self.string_cnt}, is utf-8? {self.is_utf8}")

        self.string_offsets:List[int] = []
        self.style_offsets:List[int] = []
        if self.string_cnt > 0:
            self.string_offsets:List[int] = list(struct.unpack(f"<{self.string_cnt}I", 
                        self.buff[self.header_size: self.header_size + 4*self.string_cnt]))
        if self.style_cnt > 0:
            self.style_offsets:List[int] = list(struct.unpack(f"<{self.style_cnt}I", 
                        self.buff[self.header_size + 4*self.string_cnt: self.header_size + 4*self.string_cnt + 4*self.style_cnt]))
        
        self.strings:Dict[int, str] = {}
        self.styles:Dict[int, str] = {}

        if pre_decode:
            for i in range(self.string_cnt):
                self.strings[i] = self.string_at(self.string_offset + self.string_offsets[i])
            for i in range(self.style_cnt):
                self.styles[i] = self.string_at(self.style_offset + self.style_offsets[i])

    def get_string(self, num:int) -> str:
        '''
        通过字符串序号(id)获取字符串, 传入值必须大于0
        '''
        if num > self.string_cnt or num < 0:
            logger.warning(f"AXML: Invalid String id number, {hex(num)}")
            return ""
        try:
            return self.strings[num]
        except:
            pass

        index = self.string_offset + self.string_offsets[num]
        self.strings[num] = self.string_at(index)
        return self.strings[num]

    def get_style(self, num:int) -> str:
        '''
        通过style序号(id)获取style字符串, 传入值必须大于0
        '''
        if num > self.style_cnt or num < 0:
            raise Exception(f"AXML: Invalid Style id number, {num}")
        try:
            return self.styles[num]
        except:
            pass

        index = self.style_offset + self.style_offsets[num]
        self.styles[num] = self.string_at(index)
        return self.styles[num]

    def string_at(self, index:int) -> str:
        '''
        从index开始解析一个字符串

        如果出错，返回空字符串

        出错一般是apk进行了对抗, 插入了错误字符串, 而实际上在app运行过程中不会使用此错误字符串
        '''
        if self.is_utf8:
            try:
                return self._decode_utf8(index)
            except:
                logger.warning("decode utf-8 string error")
                return ""
        else:
            try:
                return self._decode_utf16(index)
            except:
                logger.warning("decode utf-16 string error")
                return ""

    def _decode_utf8(self, offset:int) -> str:
        """
        Check bytes length, return bytes

        :param offset: offset of the string inside the data
        :return: bytes
        """
        # UTF-8 Strings contain two lengths, as they might differ:
        # 1) the UTF-16 length
        str_len, skip = self._decode_length(offset, 1)
        offset += skip

        # 2) the utf-8 string length
        encoded_bytes, skip = self._decode_length(offset, 1)
        offset += skip

        data_b = self.buff[offset: offset + encoded_bytes]
        # TODO. 解码失败时，不要直接报错或者返回空，把解码出来的unicode代号拼在一起，再次尝试u16be解码
        # 这样就不能用python自己的decode，需要自己写解码逻辑
        # 示例sha1：4bf11f72edaf8e23055991e565baa86d1370dbd2，此apk的app_name
        data = data_b.decode("utf-8", "replace")
        return data

    def _decode_utf16(self, offset:int) -> str:
        """
        Check bytes length, return bytes

        :param offset: offset of the string inside the data
        :return: bytes
        """
        str_len, skip = self._decode_length(offset, 2)
        offset += skip

        # The len is the string len in utf-16 units
        encoded_bytes = str_len * 2

        data_b = self.buff[offset: offset + encoded_bytes]
        data = data_b.decode("utf-16")
        return data

    def _decode_length(self, offset, sizeof_char):
        """
        Generic Length Decoding at offset of string

        The method works for both 8 and 16 bit Strings.
        Length checks are enforced:
        * 8 bit strings: maximum of 0x7FFF bytes (See
        http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/ResourceTypes.cpp#692)
        * 16 bit strings: maximum of 0x7FFFFFF bytes (See
        http://androidxref.com/9.0.0_r3/xref/frameworks/base/libs/androidfw/ResourceTypes.cpp#670)

        :param offset: offset into the string data section of the beginning of
        the string
        :param sizeof_char: number of bytes per char (1 = 8bit, 2 = 16bit)
        :returns: tuple of (length, read bytes)
        """
        sizeof_2chars = sizeof_char << 1
        fmt = "<2{}".format('B' if sizeof_char == 1 else 'H')
        highbit = 0x80 << (8 * (sizeof_char - 1))

        length1, length2 = struct.unpack(fmt, self.buff[offset:(offset + sizeof_2chars)])

        if (length1 & highbit) != 0:
            length = ((length1 & ~highbit) << (8 * sizeof_char)) | length2
            size = sizeof_2chars
        else:
            length = length1
            size = sizeof_char

        # These are true asserts, as the size should never be less than the values
        if sizeof_char == 1:
            assert length <= 0x7FFF, "length of UTF-8 string is too large! At offset={}".format(offset)
        else:
            assert length <= 0x7FFFFFFF, "length of UTF-16 string is too large!  At offset={}".format(offset)

        return length, size


class ResMap(ResChunkHeader):
    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)

        # headersize of this chunk is 8
        res_ids_buff = self.buff[self.header_size: self.size]
        self.num_res_ids:int = int(len(res_ids_buff) / 4)
        self.res_ids:tuple = struct.unpack("<{}I".format(str(self.num_res_ids)), res_ids_buff)
        
        self.res_id_str:List[str] = []
        for idx in self.res_ids:
            self.res_id_str.append(PUBLIC_RES_ID.get(idx, ""))


class StartNS(ResChunkHeader): # start namespace chunck
    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)

        if self.size != START_NAMESPACE_SIZE:
            pass    # TODO add log: "StartNamespace size is not equal to 0x18"

        (self.line_num,
        self.comment) = struct.unpack("<2I", self.buff[RES_CHUNK_HEADER_SIZE: RES_CHUNK_HEADER_SIZE + 8])

        (self.prefix,
        self.uri) = struct.unpack("<2I", self.buff[self.header_size: self.header_size + 8])


class EndNS(ResChunkHeader):
    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)

        if self.size != START_NAMESPACE_SIZE:
            logger.warning(f"EndNamespace size is not equal to 0x18, size={self.size}") 

        (self.line_num,
        self.comment) = struct.unpack("<2I", self.buff[RES_CHUNK_HEADER_SIZE: RES_CHUNK_HEADER_SIZE + 8])

        (self.prefix,
        self.uri) = struct.unpack("<2I", self.buff[self.header_size: self.header_size + 8])


class StartElement(ResChunkHeader):
    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)

        (self.line_num,
        self.comment) = struct.unpack("<2I", self.buff[RES_CHUNK_HEADER_SIZE: RES_CHUNK_HEADER_SIZE + 8])

        (self.ns,
        self.name,
        self.attribute_start,
        self.attribute_size,
        self.attribute_count,
        self.id_index,
        self.class_index,
        self.style_index) = struct.unpack("<2I6H", self.buff[self.header_size: self.header_size + RES_XML_TREE_ATTREXT_SIZE])

        self.attributes:List[AxmlAttribute] = []

        index = self.header_size + self.attribute_start
        for i in range(self.attribute_count):
            tmp = AxmlAttribute(self.buff[index: index + self.attribute_size])
            self.attributes.append(tmp)
            index += self.attribute_size


class EndElement(ResChunkHeader):
    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)

        (self.line_num,
        self.comment) = struct.unpack("<2I", self.buff[RES_CHUNK_HEADER_SIZE: RES_CHUNK_HEADER_SIZE + 8])

        (self.ns,
        self.name) = struct.unpack("<2I", self.buff[self.header_size: self.header_size + 8])


class CData(ResChunkHeader):
    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)
        if len(buff) < CDATA_SIZE:
            pass # TODO add log

        (self.line_num,
        self.comment) = struct.unpack("<2I", self.buff[RES_CHUNK_HEADER_SIZE: RES_CHUNK_HEADER_SIZE + 8])

        self.raw_data = struct.unpack("<I", self.buff[RES_CHUNK_HEADER_SIZE + 8: RES_CHUNK_HEADER_SIZE + 12])

        self.typed_data = ResValue(self.buff[RES_CHUNK_HEADER_SIZE + 12: RES_CHUNK_HEADER_SIZE + 20])


class AxmlAttribute:
    def __init__(self, buff: bytes) -> None:
        (self.ns,
        self.name,
        self.raw_value) = struct.unpack("<3I", buff[:12])
        
        # res_value 的结构体固定长8字节
        self.value:ResValue = ResValue(buff[12:20])


class ResValue:
    def __init__(self, buff: bytes) -> None:
        if len(buff) != RES_VALUE_SIZE:
            pass # TODO add log: res value length error

        (self.size,
        self.res0,
        self.data_type,
        self.data) = struct.unpack("<H2BI", buff)

        self.data_bin:bytes = buff[4:]    # 二进制的data

        if self.data_type > 0x1f:
            logger.error(f"res value type error,type:{self.data_type}") 
    
    def parse_data(self, string_pool:StringPool):
        '''
        使用指定的字符串池解析当前的value
        '''
        self.string_pool = string_pool

        # Type of the data value.
        decode_methods = {       
            0x00:self._type_null,       # TYPE_NULL
            0x01:self._type_reference,  # TYPE_REFERENCE
            0x02:self._type_tmp,        # TYPE_ATTRIBUTE
            0x03:self._type_string,     # TYPE_STRING
            0x04:self._type_float,      # TYPE_FLOAT
            0x05:self._type_tmp,        # TYPE_DIMENSION
            0x06:self._type_tmp,        # TYPE_FRACTION
            0x07:self._type_tmp,        # TYPE_DYNAMIC_REFERENCE
            0x08:self._type_tmp,        # TYPE_DYNAMIC_ATTRIBUTE
            0x10:self._type_int_dec,    # TYPE_INT_DEC
            0x11:self._type_int_hex,    # TYPE_INT_HEX
            0x12:self._type_int_bool,   # TYPE_INT_BOOLEAN
            0x1c:self._type_int_hex,    # TYPE_INT_COLOR_ARGB8  # 颜色没必要解析，就用十六进制表示
            0x1d:self._type_int_hex,    # TYPE_INT_COLOR_RGB8
            0x1e:self._type_int_hex,    # TYPE_INT_COLOR_ARGB4
            0x1f:self._type_int_hex,    # TYPE_INT_COLOR_RGB4
        }

        try:
            return decode_methods[self.data_type]()
        except:
            return None

    def _type_tmp(self):    # TODO complete these methods.
        return self.data

    def _type_null(self):
        return None

    def _type_reference(self):
        return hex(self.data)

    def _type_string(self):
        return self.string_pool.get_string(self.data)
    
    def _type_int_dec(self):
        return self.data

    def _type_int_hex(self):
        return hex(self.data)
    
    def _type_int_bool(self):
        return True if self.data else False

    def _type_float(self):
        return struct.unpack("<f", self.data_bin)



    # Structure of complex data values (TYPE_UNIT and TYPE_FRACTION)
    class ComplexDataValues:
        # Where the unit type information is.  This gives us 16 possible
        # types, as defined below.
        COMPLEX_UNIT_SHIFT = 0,
        COMPLEX_UNIT_MASK = 0xf,

        # TYPE_DIMENSION: Value is raw pixels.
        COMPLEX_UNIT_PX = 0,
        # TYPE_DIMENSION: Value is Device Independent Pixels.
        COMPLEX_UNIT_DIP = 1,
        # TYPE_DIMENSION: Value is a Scaled device independent Pixels.
        COMPLEX_UNIT_SP = 2,
        # TYPE_DIMENSION: Value is in points.
        COMPLEX_UNIT_PT = 3,
        # TYPE_DIMENSION: Value is in inches.
        COMPLEX_UNIT_IN = 4,
        # TYPE_DIMENSION: Value is in millimeters.
        COMPLEX_UNIT_MM = 5,

        # TYPE_FRACTION: A basic fraction of the overall size.
        COMPLEX_UNIT_FRACTION = 0,
        # TYPE_FRACTION: A fraction of the parent size.
        COMPLEX_UNIT_FRACTION_PARENT = 1,

        # Where the radix information is, telling where the decimal place
        # appears in the mantissa.  This give us 4 possible fixed point
        # representations as defined below.
        COMPLEX_RADIX_SHIFT = 4,
        COMPLEX_RADIX_MASK = 0x3,

        # The mantissa is an integral number -- i.e., 0xnnnnnn.0
        COMPLEX_RADIX_23p0 = 0,
        # The mantissa magnitude is 16 bits -- i.e, 0xnnnn.nn
        COMPLEX_RADIX_16p7 = 1,
        # The mantissa magnitude is 8 bits -- i.e, 0xnn.nnnn
        COMPLEX_RADIX_8p15 = 2,
        # The mantissa magnitude is 0 bits -- i.e, 0x0.nnnnnn
        COMPLEX_RADIX_0p23 = 3,

        # Where the actual value is.  This gives us 23 bits of
        # precision.  The top bit is the sign.
        COMPLEX_MANTISSA_SHIFT = 8,
        COMPLEX_MANTISSA_MASK = 0xffffff


#######################
#                     #
#   ARSC struct       #
#                     #
#######################

class ResTableEntry:
    # flag的取值
    FLAG_COMPLEX    = 0x0001    # 此entry后面跟着ResTable_map
    FLAG_PUBLIC     = 0x0002    # 此entry为公有，可被其他库引用
    FLAG_WEAK       = 0x0004    # 此资源会被其他同类型且同名资源覆盖

    # 这里有个offset参数，表示从buff[offset:]开始解析数据，如果传入buff[xxx:yyy]，
    # 内存中会额外复制一份切片后的buff传入此类，导致效率降低，所以直接传入完整的buff，这样python会自动复用同一个buff，
    # 其他很多类是传入的buff[xxx:yyy]，但是那些类调用次数很少（个位数到百位数），这点内存复制耗时可忽略了，这个类调用次数的数量级在万级以上
    # 不过后续可以考虑全部代码共用一个buff，这样耗时大概能缩短几十毫秒
    def __init__(self, buff: bytes, key_sp:StringPool, offset:int) -> None:
        (self.size,
        self.flag,
        self.key_str_id) = struct.unpack("<2HI", buff[offset: offset + 8])

        if (self.flag & self.FLAG_COMPLEX):     # 逆向apk一般用不到这个数据
            (self.ref_parant,
            self.count) = struct.unpack("<2I", buff[offset + 8: offset + 16])

            self.value = {"map object":"is not yet parsed"}
        else:
            self.value = ResValue(buff[offset + 8: offset + 16])

        self.key_str = key_sp.get_string(self.key_str_id)
        

class ResTablePackage(ResChunkHeader):
    # 资源id形式如：0x7f010002
    # 前一个字节 0x7f 为package的id，就是此结构体的id
    # 中间一个字节 0x01 为资源类型id，如string、layout等
    # 最后的0x0002 为此类型的资源序号，表示0x01类当中的第2个资源
    # 一般在android开发中写法为@res_type/res_name，与资源id的0x010002相对应
    # 此结构体中的两个字符串池 type_str_pool，key_str_pool就是保存的res_type和res_name字符串

    def __init__(self, buff: bytes, global_sp:StringPool) -> None:
        '''
        读取table package信息

        args:
            buff: 待分析的数据块
            global_sp: 全局字符串池，表示此arsc文件的字符串池，部分属性的解析需要用到
        '''
        super().__init__(buff)

        self.name:str = ""
        
        # table package header
        (self.id,
        self.name,
        self.type_str_offset,
        self.last_pub_type,
        self.key_str_offset,
        self.last_pub_key,
        self.type_id_offset) = struct.unpack("<I256s5I", 
                            self.buff[RES_CHUNK_HEADER_SIZE: RES_TABLE_PACKAGE_HEADER_SIZE])
        logger.debug(f"ResTablePackage: id:{hex(self.id)},len:{hex(self.size)}")

        self.type_str_pool:StringPool = StringPool(self.buff[self.type_str_offset:])
        self.key_str_pool:StringPool = StringPool(self.buff[self.key_str_offset:])

        # table package spec dict: {type_id: type_spec, ...}
        self.specs:Dict[int, ResTypeSpec] = {}

        # table package Types dict: {type_id: [type_type1, type_type2, ... ], ...}
        self.tp_types:Dict[int, List[ResTableType]] = {}

        self.ptr = self.key_str_offset + self.key_str_pool.size
        while (self.ptr < self.size):
            next_chunk_type = struct.unpack("<H", self.buff[self.ptr: self.ptr + 2])[0]
            # print(self.ptr, next_chunk_type)
            if next_chunk_type == RES_TABLE_TYPE_SPEC_TYPE:
                tmp_obj = ResTypeSpec(self.buff[self.ptr:])
                self.specs[tmp_obj.id] = tmp_obj
                self._ptr_add(tmp_obj.size)
            elif next_chunk_type == RES_TABLE_TYPE_TYPE:
                tmp_obj = ResTableType(self.buff[self.ptr:], global_sp, self.key_str_pool)
                self.tp_types.setdefault(tmp_obj.id, []).append(tmp_obj)
                self._ptr_add(tmp_obj.size)
            else:   # TODO 完善其他数据块的读取
                h = ResChunkHeader(self.buff[self.ptr:])
                logger.debug(f"ResTablePackage: read unknow chunk:{h.res_type},size:{h.size}")
                self._ptr_add(h.size)


class ResTypeSpec(ResChunkHeader):
    SPEC_PUBLIC = 0x40000000        # TODO flags的取值，目前没有用到
    SPEC_STAGED_API = 0x20000000

    def __init__(self, buff: bytes) -> None:
        super().__init__(buff)

        (self.id,
        self.res0,
        self.res1,
        self.entry_count) = struct.unpack("<2BHI", self.buff[RES_CHUNK_HEADER_SIZE: RES_TABLE_TYPE_SPEC_SIZE])

        self.flags:Tuple[int, ...] = struct.unpack(f"<{self.entry_count}I", self.buff[self.header_size: self.header_size + 4 * self.entry_count])


class ResTableType(ResChunkHeader):

    
    def __init__(self, buff: bytes, global_sp:StringPool, key_sp:StringPool) -> None:
        '''
        读取res_table_type
        '''
        super().__init__(buff)

        (self.id,
        self.flag,
        self.res1,
        self.entry_count,
        self.entry_start) = struct.unpack("<2BH2I", self.buff[RES_CHUNK_HEADER_SIZE: RES_TABLE_TYPE_SIZE])
        logger.debug(f"ResTableType: id:{self.id},size:{self.size},flag:{self.flag}")

        # TODO 完善config解析，config用于资源的语言适配，屏幕大小适配等，反编译一般用不到这个东西，暂不处理
        # config是在ResChunkHeader头部里面的，只能用固定长度0x14获取到其位置了
        self.config_count = struct.unpack("<I",self.buff[0x14: 0x18])[0]
        self.config:bytes = self.buff[0x14: 0x14 + self.config_count]

        entry_off_end = self.header_size + self.entry_count*4
        self.entry_offsets:Tuple[int, ...] = struct.unpack(f"<{self.entry_count}I", 
                                    self.buff[self.header_size : entry_off_end])
        
        # entries字典，{entry序号: [ResTableEntry,Resvalue], ...}，方便根据序号查询对应的资源
        self.entries:Dict[int, ResTableEntry] = {}
        # entry的编码方式有区别，参考ResourceTypes.h里面的ResTable_type.flags
        if self.flag == 0:
            count = 0
            for i in self.entry_offsets:
                if i == 0xffffffff:
                    count += 1
                    continue
                # logger.debug(f"ResTableEntry: count:{count}")
                tmp_entry = ResTableEntry(self.buff, key_sp, self.entry_start + i)
                self.entries[count] = tmp_entry
                count += 1
        elif self.flag == 1:
            for sparse_entry in self.entry_offsets:
                count = sparse_entry & 0xff
                offsets = (sparse_entry >> 16) * 4
                tmp_entry = ResTableEntry(self.buff, key_sp, self.entry_start + offsets)
                self.entries[count] = tmp_entry
        elif self.flag == 2:
            raise Exception(f"ResTableType flag==2, please open a issue. I need a example to complete this part")
        else:
            raise Exception(f"ResTableType flag error:{self.flag}")


#######################
#                     #
#       Parser        #
#                     #
#######################

class Axml(ResChunkHeader):
    def __init__(self, buff: bytes, pre_decode:bool = True) -> None:
        super().__init__(buff)
        self.pre_decode = pre_decode

        self.string_pool:StringPool = None
        self.res_map:ResMap = None
        self.start_nss:List[StartNS] = []
        self.end_nss:List[EndNS] = []
        self.start_elements:List[StartElement] = []
        self.end_elements:List[EndElement] = []
        self.cdatas:List[CData] = []

        # 字典格式保存的xml内容，相比xml缺少了层级关系，我写出来了但是不知道有啥用，先放着。
        # 下面有相应的解析函数_parse_nodes_dict()
        self.xml_nodes_dict:Dict[str,list] = {}

        self.node_ptr = None
        first_tag = ""
        count = 0
        while(self.ptr < self.size):
            next_chunk_type = struct.unpack("<H", self.buff[self.ptr: self.ptr + 2])[0]

            # 出现频率高的类型往前放，提高效率
            if next_chunk_type == RES_XML_START_ELEMENT_TYPE:
                tmp = StartElement(self.buff[self.ptr:])
                tmp_node = self._create_node(tmp)
                if tmp_node == None:
                    self._ptr_add(tmp.size)
                    continue
                if count == 0:  # first_node
                    self.node_ptr = tmp_node
                    first_tag = tmp_node.tag
                else:
                    self.node_ptr.append(tmp_node)   # 增加当前节点，并指向它
                    self.node_ptr = list(self.node_ptr)[-1]
                self.start_elements.append(tmp)
                self._ptr_add(tmp.size)
                count += 1

            # 发现一个样本，manifest的最后一个end_element没有name，不确定是不是所有的end_element都能这样，先跳过这个特例
            # 如果后续发现新样本，确定了所有end_element都可以没有name，则可以删掉下面“名称匹配”的if分支，遇到end_element
            # 直接返回父节点
            elif next_chunk_type == RES_XML_END_ELEMENT_TYPE:
                tmp = EndElement(self.buff[self.ptr:])
                tmp_name = self.string_pool.get_string(tmp.name)
                if tmp_name == first_tag or self.node_ptr.tag == first_tag:    # 遇到第一个node表示xml解析完成
                    pass
                elif tmp_name != self.node_ptr.tag:   # 一个node的结尾需要与开头名称匹配，如<activity>xxxx</activity>
                    raise Exception(f"Parse xml error. start_tag not equal to end_tag: {self.node_ptr.tag}=={tmp_name}")
                else:
                    self.node_ptr = self.node_ptr.getparent()
                self.end_elements.append(tmp)
                self._ptr_add(tmp.size)

            elif next_chunk_type == RES_XML_CDATA_TYPE:
                tmp = CData(self.buff[self.ptr:])
                self.cdatas.append(tmp)
                self._ptr_add(tmp.size)

            elif next_chunk_type == RES_STRING_POOL_TYPE:
                self.string_pool = StringPool(self.buff[self.ptr:], pre_decode)
                self._ptr_add(self.string_pool.size)

            elif next_chunk_type == RES_XML_RESOURCE_MAP_TYPE:
                self.res_map = ResMap(self.buff[self.ptr:])
                self._ptr_add(self.res_map.size)

            elif next_chunk_type == RES_XML_START_NAMESPACE_TYPE:
                tmp = StartNS(self.buff[self.ptr:])
                self.start_nss.append(tmp)
                self._ptr_add(tmp.size)

            elif next_chunk_type == RES_XML_END_NAMESPACE_TYPE:
                tmp = EndNS(self.buff[self.ptr:])
                self.end_nss.append(tmp)
                if tmp.size <= START_NAMESPACE_SIZE:
                    self._ptr_add(START_NAMESPACE_SIZE)
                else:
                    # 理论上可以自己添加额外数据
                    self._ptr_add(tmp.size)

            else:
                logger.warning(f"undefined chunk type:{next_chunk_type}")
                self._ptr_add(4)
                continue


    def _create_node(self, element:StartElement) -> Union[Element,None]:
        '''
        使用StartElement实例创建xml node
        '''
        attr_dict = {}
        for attr in element.attributes:
            attr_ns = self._parse_name(attr.ns)
            attr_name = self._parse_name(attr.name)
            if attr_ns:
                key = "{{{0}}}{1}".format(attr_ns, attr_name)
            else:
                key = attr_name
            # xml中所有的value都是字符串格式，这里要用str()转换一下
            attr_dict[key] = str(attr.value.parse_data(self.string_pool))
        
        # 有apk会故意加入错误字符，导致无法解析成标准xml，只要app没有使用此字符串，则可以正常安装
        # 这里如果遇到这种对抗，就插入一个空的node
        # 如果tag name被插入错误字符，则直接返回None，错误的tag 并没有实际作用，只是妨碍逆向
        tag_name = self.string_pool.get_string(element.name)
        if tag_name == "":
            return None
        try:
            node:Element = etree.Element(
                tag_name,
                attrib=attr_dict,
                nsmap=None
            )
        except:
            node:Element = etree.Element(
                tag_name,
                attrib={"this":"is_not_a_valid_unicode_str"},
                nsmap=None
            )
        return node


    def _parse_nodes_dict(self):
        '''
        吧xml保存为字典格式
        '''
        for line in self.start_elements:
            name = self.string_pool.get_string(line.name)
            self.xml_nodes_dict.setdefault(name,[])

            inline_data = {}
            for attr in line.attributes:
                
                inline_data[self._parse_name(attr.name)] = attr.value.parse_data(self.string_pool)
            
            self.xml_nodes_dict[name].append(inline_data)


    def _parse_name(self, idx:int) -> str:
        '''
        解析以id形式保存的name(如AxmlAttribute.name), 解析出对应的字符串返回
        也可以解析AxmlAttribute.ns

        如果解析出错, 返回空字符串
        '''
        #某些namespace字段可能取这个值，用于表示没有namespace
        if idx == 0xffffffff:
            return ""
        
        try:    # 某些attributes会使用错误的字符串索引，这里直接跳过
            name = self.string_pool.get_string(idx)
        except:
            return ""
        
        if name == "":
            try:
                name = self.res_map.res_id_str[idx]
                name = name.split("_", 1)[-1]
            except:
                name = ""
        
        return name


    def list_strings(self) -> list:
        '''
        返回所有字符串
        '''
        if self.pre_decode:
            return list(self.string_pool.strings.values())
        else:
            raise Exception("Strings are not decoded. ")


    def get_xml_str(self) -> str:
        '''
        返回字符串格式的xml数据
        '''
        return etree.tostring(self.node_ptr, encoding="utf-8").decode('utf-8')


class Arsc(ResChunkHeader):
    def __init__(self, buff: bytes, pre_decode:bool = True) -> None:
        super().__init__(buff)
        self.pre_decode = pre_decode
        self.package_count = struct.unpack("<I",self.buff[self.ptr: self.ptr + 4])[0]
        self._ptr_add(4)
        # 重置ptr位置，因为部分apk的资源文件头部可能会添加自定义的额外数据
        self._ptr_reset(self.header_size)

        self.string_pool:StringPool= None
        self.table_packages:Dict[int, ResTablePackage] = {}

        while (self.ptr < self.size):
            next_chunk_type = struct.unpack("<H", self.buff[self.ptr: self.ptr + 2])[0]

            if next_chunk_type == RES_STRING_POOL_TYPE:
                self.string_pool = StringPool(self.buff[self.ptr:], pre_decode)
                self._ptr_add(self.string_pool.size)
            elif next_chunk_type == RES_TABLE_PACKAGE_TYPE:
                tmp_tp = ResTablePackage(self.buff[self.ptr:], self.string_pool)
                if (not self.table_packages.get(tmp_tp.id, None)):  # 不覆盖之前获取到的包，以第一个获取到的为准
                    self.table_packages[tmp_tp.id] = tmp_tp
                self._ptr_add(tmp_tp.size)
            else:
                # TODO add warning log: undefined chunk type:xxx
                # print(f"undefined chunk type:{hex(next_chunk_type)}")
                self._ptr_add(4)
                continue

    def get_resources(self, res_id:int) -> list:
        '''
        通过资源id获取资源的数据

        return:
            [(key,value), (key,value)...]
        '''
        res = []
        num = res_id & 0xffff
        type_num = (res_id >> 16) & 0xff
        pkg_num = (res_id >> 24) & 0xff
        # print(hex(pkg_num), hex(type_num), num)
        pkg = self.table_packages.get(pkg_num)
        for item in pkg.tp_types.get(type_num,[]):
            entry = item.entries.get(num)
            if entry:
                if type(entry.value) == dict:
                    res.append((entry.key_str, entry.value))
                    continue
                res.append((entry.key_str, entry.value.parse_data(self.string_pool)))

        return res

