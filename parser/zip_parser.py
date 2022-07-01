import os
import struct
from typing import Dict, List

# 压缩算法
import zlib
import bz2
import lzma

import logging  # TODO 完善log配置
# logging.basicConfig(format=)

END_CENTDIR_SIZE = 22   # end of central directory minimum size
CENTDIR_SIZE = 46       # central directory minimum size
FILE_HEADER_SIZE = 30   # file header minimum size

END_CENTDIR_TAG = b"\x50\x4b\x05\x06"
FILE_HEADER_TAG = b"\x50\x4b\x03\x04"
CENTDIR_TAG = b"\x50\x4b\x01\x02"


# constants for Zip file compression methods
ZIP_STORED = 0
ZIP_DEFLATED = 8
ZIP_BZIP2 = 12
ZIP_LZMA = 14
# Other ZIP compression methods not supported


class LocalFileHeader:
    # header signature                4 bytes (0x504b0304) 
    # version needed to extract       2 bytes
    # general purpose bit flag        2 bytes
    # compression method              2 bytes
    # last mod file time              2 bytes
    # last mod file date              2 bytes
    # crc-32                          4 bytes
    # compressed size                 4 bytes
    # uncompressed size               4 bytes
    # file name length                2 bytes
    # extra field length              2 bytes
    # file name (variable size)
    # extra field (variable size)

    def __init__(self, fpin:bytes, offset:int) -> None:
        # 下面三个属性应该都是字符串，
        # 但是防止恶意软件使用异常的字符进行对抗，还是用二进制保存
        self.file_name:bytes = None
        self.extra_field:bytes = None
        self.file_data:bytes = None

        self.tag = fpin[offset: offset + 4]
        if self.tag != FILE_HEADER_TAG:
            raise Exception("local file header error!!")
        data = fpin[offset + 4 : offset + FILE_HEADER_SIZE]

        (self.version_need,
        self.bit_flag,
        self.compression_method,
        self.last_mod_time,
        self.last_mod_date,
        self.crc_32,
        self.compressed_size,
        self.uncompressed_size,
        self.fname_len,
        self.extra_field_len) = struct.unpack("<5H3I2H", data)

        file_name_end = offset + FILE_HEADER_SIZE + self.fname_len
        extra_field_end = file_name_end + self.extra_field_len
        file_data_end = extra_field_end + self.compressed_size

        self.file_name = fpin[offset + FILE_HEADER_SIZE: file_name_end]
        self.extra_field = fpin[file_name_end : extra_field_end]
        self.file_data = fpin[extra_field_end : file_data_end]
    

class CentralDirectory:
    # central file header signature   4 bytes  (0x504b0102)
    # version made by                 2 bytes
    # version needed to extract       2 bytes
    # general purpose bit flag        2 bytes
    # compression method              2 bytes
    # last mod file time              2 bytes
    # last mod file date              2 bytes
    # crc-32                          4 bytes
    # compressed size                 4 bytes
    # uncompressed size               4 bytes
    # file name length                2 bytes
    # extra field length              2 bytes
    # file comment length             2 bytes
    # disk number start               2 bytes
    # internal file attributes        2 bytes
    # external file attributes        4 bytes
    # relative offset of local header 4 bytes
    # file name (variable size)
    # extra field (variable size)
    # file comment (variable size)

    def __init__(self, fpin:bytes, offset:int) -> None:
        # 下面三个属性应该都是字符串，
        # 但是防止恶意软件使用异常的字符进行对抗，还是用二进制保存
        self.file_name:bytes = None
        self.extra_field:bytes = None
        self.comment:bytes = None

        self.tag = fpin[offset: offset + 4]
        if self.tag != CENTDIR_TAG:
            raise Exception("central dir header error!!")
        data = fpin[offset + 4: offset + CENTDIR_SIZE]

        (self.version_made_by,
        self.version_need,
        self.bit_flag,
        self.compression_method,
        self.last_mod_time,
        self.last_mod_date,
        self.crc_32,
        self.compressed_size,
        self.uncompressed_size,
        self.fname_len,
        self.extra_field_len,
        self.comment_len,
        self.disk_num_start,
        self.in_file_attr,
        self.ex_file_attr,
        self.local_header_off) = struct.unpack("<6H3I5H2I", data)

        fname_end = offset + CENTDIR_SIZE + self.fname_len
        ex_field_end = fname_end + self.extra_field_len
        comment_end = ex_field_end + self.comment_len
        self.file_name = fpin[offset + CENTDIR_SIZE: fname_end]
        self.extra_field = fpin[fname_end: ex_field_end]
        self.comment = fpin[ex_field_end: comment_end]


class EndOfCentralDirectory:
    # end of central dir signature    4 bytes  (0x504b0506)
    # number of this disk             2 bytes
    # number of the disk with the
    # start of the central directory  2 bytes
    # total number of entries in the
    # central directory on this disk  2 bytes
    # total number of entries in
    # the central directory           2 bytes
    # size of the central directory   4 bytes
    # offset of start of central
    # directory with respect to
    # the starting disk number        4 bytes
    # .ZIP file comment length        2 bytes
    # .ZIP file comment       (variable size)

    def __init__(self, fpin:bytes, offset:int) -> None:
        self.tag = fpin[offset: offset + 4]
        if self.tag != END_CENTDIR_TAG:
            raise Exception("Not Zip File")

        data = fpin[offset + 4: offset + END_CENTDIR_SIZE]
        self.comment = fpin[offset + END_CENTDIR_SIZE: ]

        (self.num_disk, 
        self.num_disk_start, 
        self.entries_num_this, 
        self.entries_num_all, 
        self.central_dir_size, 
        self.central_dir_offset, 
        self.comment_size) = struct.unpack("<4H2IH",data)

        if len(self.comment) != self.comment_size:
            logging.warning("EndOfCentralDirectory comment length error !!")


class LZMADecompressor:

    def __init__(self):
        self._decomp = None
        self._unconsumed = b''
        self.eof = False

    def decompress(self, data):
        if self._decomp is None:
            self._unconsumed += data
            if len(self._unconsumed) <= 4:
                return b''
            psize, = struct.unpack('<H', self._unconsumed[2:4])
            if len(self._unconsumed) <= 4 + psize:
                return b''

            self._decomp = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[
                lzma._decode_filter_properties(lzma.FILTER_LZMA1,
                                               self._unconsumed[4:4 + psize])
            ])
            data = self._unconsumed[4 + psize:]
            del self._unconsumed

        result = self._decomp.decompress(data)
        self.eof = self._decomp.eof
        return result


compressor_names = {
    0: 'store',
    1: 'shrink',
    2: 'reduce',
    3: 'reduce',
    4: 'reduce',
    5: 'reduce',
    6: 'implode',
    7: 'tokenize',
    8: 'deflate',
    9: 'deflate64',
    10: 'implode',
    12: 'bzip2',
    14: 'lzma',
    18: 'terse',
    19: 'lz77',
    97: 'wavpack',
    98: 'ppmd',
}


def _get_decompressor(compress_type:int):
    if compress_type == ZIP_STORED:
        return None
    elif compress_type == ZIP_DEFLATED:
        return zlib.decompressobj(-15)
    elif compress_type == ZIP_BZIP2:
        return bz2.BZ2Decompressor()
    elif compress_type == ZIP_LZMA:
        return LZMADecompressor()
    else:
        descr = compressor_names.get(compress_type)
        if descr:
            raise NotImplementedError("compression type %d (%s)" % (compress_type, descr))
        else:
            raise NotImplementedError("compression type %d" % (compress_type,))


class ZipFile:

    def __init__(self, fpath:str) -> None:
        self.fhs:Dict[bytes,LocalFileHeader] = {}    # file headers
        self.cds:Dict[bytes,CentralDirectory] = {}    # central directories
        self.ecd:EndOfCentralDirectory = None   # end of central directory

        self.file_path:str = fpath
        self.file_size:int = os.path.getsize(fpath)
        try:
            fpin = open(fpath, 'rb')
        except Exception as e:
            print(f'Can not read file: {fpath}')
            return
        self.file_data:bytes = fpin.read()

        # 获取zip尾部信息
        # max_comment_start = max(self.file_size - (1 << 16) - END_CENTDIR_SIZE, 0)
        # fpin.seek(max_comment_start, 0)
        fpin.seek(0)
        data = fpin.read()

        
        # 从后往前读取第一个长度满足条件的文件尾
        try:
            end_len = 0
            while(end_len < 22):
                if end_len != 0:
                    data = data[:-end_len]
                ecd_start = data.rfind(END_CENTDIR_TAG)
                end_len = len(data[ecd_start:])
                
            self.ecd = EndOfCentralDirectory(data, ecd_start)
        except Exception as e:
            print(f'Not Zip File, ', e)
            return

        # 获取中心文件记录
        fpin.seek(self.ecd.central_dir_offset,0)
        data = fpin.read()
        cd_count = 0
        offset = 0
        try:
            while(cd_count < self.ecd.entries_num_all):
                cd_count += 1
                tmp_cd = CentralDirectory(data, offset)
                offset += tmp_cd.fname_len + tmp_cd.extra_field_len \
                        + tmp_cd.comment_len + CENTDIR_SIZE
                self.cds[tmp_cd.file_name] = tmp_cd
        except Exception as e:
            print("Read central dir error !", e)
            return
        
        # 初始化只获取尾部和中心文件记录的数据（504b0506和504b0102），
        # local file header通过central dir中指定的偏移，按需查找
        # 因为local file header之间可以随意插入任何数据
        

    def get_file(self, file_name:bytes):
        '''通过文件名获取文件
        '''
        cd = self.cds[file_name]
        lf = LocalFileHeader(self.file_data, cd.local_header_off)

        # 解压时用的central dir 中保存的解压方法
        return self._decompress(lf.file_data, cd.compression_method)


    def _decompress(self, buff:bytes, method:int):
        if method == 0:
            return buff
        decompressor = _get_decompressor(method)
        
        return decompressor.decompress(buff)

