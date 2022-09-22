import os,sys
import shutil


from parser.zip_parser import ZipFile
from parser.axml_parser import Axml


# manifest中常用字段
COMMON_KEYS = [
    "compileSdkVersion",
    "compileSdkVersionCodename",
    "installLocation",
    "versionCode",
    "versionName",
    "package",
    "platformBuildVersionCode",
    "platformBuildVersionName",
]

class ApkFile:
    def __init__(self, file_path) -> None:
        self.file_path = file_path
        self.zip = ZipFile(file_path)
        self.manifest = Axml(self.zip.get_file(b"AndroidManifest.xml"))
        
        self.common_k_v = {}    # 保存manifest中常用字段
        manifest_attrs = self.manifest.start_elements[0].attributes
        for item in manifest_attrs:
            name_str = self.manifest._parse_name(item.name)
            if name_str in COMMON_KEYS:
                self.common_k_v[name_str] = item.value.parse_data(self.manifest.string_pool)
        

    #### 常用函数 ####
    def get_package(self):
        return self.common_k_v.get('package')



    def get_file(self, fname:bytes) -> bytes:
        '''
        通过文件名获取文件，文件名需要转换为bytes
        '''
        return self.zip.get_file(fname)

    def unzip(self, out_path):
        '''
        解压apk中的全部文件
        '''
        zip_file = self.zip
        for fname in zip_file.cds.keys():
            out_fname = os.path.join(out_path.encode('utf-8'), fname)
            fdir = b"/".join(out_fname.split(b"/")[:-1])
            os.makedirs(fdir, exist_ok=True)
            try:
                with open(out_fname, 'wb') as fw:
                    fw.write(zip_file.get_file(fname))
            except:
                pass
    
    def re_zip(self, tmp_path:str, out_path:str):
        '''
        解压apk文件，再重新zip打包，某些apk可能有较复杂对抗，
        无法直接用jeb等工具打开，可以用此方法重打包后再用jeb等其他分析工具分析
        **此功能调用系统的zip命令进行打包，没有重签名**

        params:
            tmp_path: 解压用的临时文件夹
            out_path: 最终输出的文件名
        '''

        self.unzip(tmp_path)
        os.system(f"cd {tmp_path} && zip -r ./tmp.zip ./*")
        
        os.system(f"mv {os.path.join(tmp_path, 'tmp.zip')} {out_path}")

        shutil.rmtree(tmp_path)

    #### 常用函数结束 ####



if __name__ == "__main__":
    # test
    apk = ApkFile(sys.argv[1])
    apk.re_zip('./tmp_apk', './ttt.apk')
    print(apk.get_package())