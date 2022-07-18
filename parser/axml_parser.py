import struct
from typing import Dict, List
from lxml import etree
from xml.etree.ElementTree import Element   #这个用于开启代码提示


from utils.public_res_ids import PUBLIC_RES_ID

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

############ attribute value types
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

############ attribute value types end

############ size of some struct
RES_CHUNK_HEADER_SIZE = 8   # 只有这个chunkheader大小是固定的，其他的供参考
STRING_POOL_HEADER_SIZE = 0x1C  # string pool 头部大小
START_NAMESPACE_SIZE = 0x18     # namespace结构体的大小，start namespace和end namespace是一样的
RES_XML_TREE_ATTREXT_SIZE = 0x14    # res xml tree中关于attribute的描述信息的大小
RES_VALUE_SIZE = 0x08          # ResValue结构体的大小
############ size end

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
        else:
            raise Exception(f"Chunk header length error: {len(buff)}")

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
            # TODO add log
            pass
        
        header_buff = self.buff[RES_CHUNK_HEADER_SIZE: STRING_POOL_HEADER_SIZE]

        (self.string_cnt,
        self.style_cnt,
        self.flag,
        self.string_offset,
        self.style_offset) = struct.unpack("<5I", header_buff)
        self.is_utf8 = ((self.flag & UTF8_FLAG) != 0)

        self.string_offsets:List[int] = []
        self.style_offsets:List[int] = []
        if self.string_cnt > 0:
            self.string_offsets:List[int] = list(struct.unpack(f"<{self.string_cnt}I", 
                        self.buff[self.header_size: self.header_size + 4*self.string_cnt]))
        if self.style_cnt > 0:
            self.style_offsets:List[int] = list(struct.unpack(f"<{self.style_cnt}I", 
                        self.buff[self.header_size + 4*self.string_cnt: self.header_size + 4*self.string_cnt + 4*self.string_cnt]))
        
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
            raise Exception(f"AXML: Invalid String id number, {num}")
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
                return ""
        else:
            try:
                return self._decode_utf16(index)
            except:
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
        data = data_b.decode("utf-8")
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
            pass    # TODO add log: "EndNamespace size is not equal to 0x18"

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


class AxmlAttribute:
    def __init__(self, buff: bytes) -> None:
        (self.ns,
        self.name,
        self.raw_value) = struct.unpack("<3I", buff[:12])
        
        self.value:ResValue = ResValue(buff[12:])

class ResValue:
    def __init__(self, buff: bytes) -> None:
        if len(buff) != RES_VALUE_SIZE:
            pass # TODO add log: res value length error

        (self.size,
        self.res0,
        self.data_type,
        self.data) = struct.unpack("<H2BI", buff)

        if self.data_type > 0x1f:
            pass # TODO add log: res value type error
    
    def parse_data(self, string_pool:StringPool):
        '''
        使用指定的字符串池解析当前的value
        '''
        self.string_pool = string_pool

        # Type of the data value.
        decode_methods = {        
            0x00:self._type_null,
            0x01:self._type_reference,
            0x02:self._type_tmp,
            0x03:self._type_string,
            0x04:self._type_tmp,
            0x05:self._type_tmp,
            0x06:self._type_tmp,
            0x07:self._type_tmp,
            0x08:self._type_tmp,
            0x10:self._type_int_dec,
            0x11:self._type_int_hex,
            0x12:self._type_int_bool,
            0x1c:self._type_tmp,
            0x1c:self._type_tmp,
            0x1d:self._type_tmp,
            0x1e:self._type_tmp,
            0x1f:self._type_tmp,
            0x1f:self._type_tmp,
            0x1f:self._type_tmp,
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



class Axml(ResChunkHeader):
    def __init__(self, buff: bytes, pre_decode:bool = True) -> None:
        super().__init__(buff)
        self.pre_decode = pre_decode

        self.ptr = self.header_size

        self.string_pool:StringPool = None
        self.res_map:ResMap = None
        self.start_nss:List[StartNS] = []
        self.end_nss:List[EndNS] = []
        self.start_elements:List[StartElement] = []
        self.end_elements:List[EndElement] = []
        self.xml_nodes_dict:Dict[str,list] = {}

        self.node_ptr = None
        while(self.ptr < self.size):
            next_chunk_type = struct.unpack("<H", self.buff[self.ptr: self.ptr + 2])[0]

            if next_chunk_type == RES_STRING_POOL_TYPE:
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
                self._ptr_add(tmp.size)

            elif next_chunk_type == RES_XML_START_ELEMENT_TYPE:
                tmp = StartElement(self.buff[self.ptr:])
                tmp_node = self._create_node(tmp)
                if tmp_node.tag == "manifest":
                    self.node_ptr = tmp_node
                else:
                    self.node_ptr.append(tmp_node)   # 增加当前节点，并指向它
                    self.node_ptr = list(self.node_ptr)[-1]
                self.start_elements.append(tmp)
                self._ptr_add(tmp.size)

            elif next_chunk_type == RES_XML_END_ELEMENT_TYPE:
                tmp = EndElement(self.buff[self.ptr:])
                tmp_name = self.string_pool.get_string(tmp.name)
                if tmp_name != self.node_ptr.tag:
                    raise Exception("Parse xml error")
                elif tmp_name == "manifest":    # 遇到manifest表示xml解析完成
                    pass
                else:
                    self.node_ptr = self.node_ptr.getparent()
                self.end_elements.append(tmp)
                self._ptr_add(tmp.size)

            else:
                pass # TODO add warning log: undefined chunk type:xxx
                print(f"undefined chunk type:{next_chunk_type}")
                self._ptr_add(4)
                continue
        

    def _ptr_add(self, offset) -> None:
        self.ptr += offset
        while self.ptr % 4 != 0:
            self.ptr += 1


    def _create_node(self, element:StartElement) -> Element:
        '''
        使用StartElement实例创建xml node
        '''
        attr_dict = {}
        for attr in element.attributes:
            # xml中所有的value都是字符串格式，这里要转换一下
            attr_dict[self._parse_name(attr.name)] = str(attr.value.parse_data(self.string_pool))
        
        node:Element = etree.Element(
            self.string_pool.get_string(element.name),
            attrib=attr_dict,
            nsmap=None)
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


    def _parse_name(self, idx):
        '''
        解析以id形式保存的name(如AxmlAttribute.name), 解析出对应的字符串返回

        如果解析出错, 返回空字符串
        '''
        name = self.string_pool.get_string(idx)
        if name == "":
            try:
                name = self.res_map.res_id_str[idx]
                name = name.split("_", 1)[-1]
            except:
                name = ""
        
        return name


    def list_strings(self) -> list:
        if self.pre_decode:
            return list(self.string_pool.strings.values())
        else:
            raise Exception("Strings are not decoded. ")

    def get_xml_str(self) -> str:
        '''
        获取字符串格式的manifest.xml
        '''
        return etree.tostring(self.node_ptr, encoding="utf-8").decode('utf-8')