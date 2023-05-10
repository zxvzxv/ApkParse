import hashlib
import os,sys
import shutil


from parser.zip_parser import ZipFile
from parser.res_parser import Axml, Arsc


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
        self.resources = Arsc(self.zip.get_file(b"resources.arsc"))

        self.common_k_v = {}    # 保存manifest中常用字段
        manifest_attrs = self.manifest.start_elements[0].attributes
        for item in manifest_attrs:
            name_str = self.manifest._parse_name(item.name)
            if name_str in COMMON_KEYS:     # 只取指定数据，防止manifest恶意加入乱七八糟的东西
                self.common_k_v[name_str] = item.value.parse_data(self.manifest.string_pool)
        
        self.flag = 0   # 标记是否解析了基本数据
        self._set_basic_info()

    def _set_basic_info(self):
        with open(self.file_path, 'rb') as fr:
            self.sha1 = hashlib.sha1(fr.read()).hexdigest()
        self.app_name = self.get_app_name()
        self.version = self.common_k_v.get('versionName', '')
        if self.version.startswith("0x"):   # 过滤掉返回值为资源ID的16进制值，例如：'0x7f0b0039'
            self.version = self.resources.get_resources(int(self.version, base=16))[0][-1]
        self.package = self.common_k_v.get('package', '')
        if self.package.startswith("0x"):   # 过滤掉返回值为资源ID的16进制值，例如：'0x7f0b0039'
            self.package = self.resources.get_resources(int(self.package, base=16))[0][-1]
        self.cert = ''          # 完整的证书，包括subject和issuer
        self.cert_name = ''     # subject的名称
        self.cert_sha1 = ''     # 证书hash
        self.main_activity = self.get_main_activity()
        self.services = []
        self.receivers = []
        self.providers = []
        self.activitise = []
        self.flag = 1

    def get_basic_info(self) -> list:
        return [self.sha1, self.app_name, self.version, self.package, self.cert_name, self.cert_sha1, self.main_activity]

    def get_app_name(self) -> str:
        ret = ""
        if self.flag:
            ret = self.app_name
        else:
            # http://schemas.android.com/apk/res/android 这个命名空间是固定死的
            label = self.manifest.node_ptr.find("application").get("{http://schemas.android.com/apk/res/android}label")
            # 有的apk这里会直接返回应用名称而不是资源ID
            if label.startswith('0x'):
                ret = self.resources.get_resources(int(label,base=16))[0][-1]


        return ret

    def get_main_activity(self) -> str:
        if self.flag:
            ret = self.main_activity
        else:
            # 先定位android.intent.action.MAIN，之后找上两级的element，确定element为activity则成功获取到结果
            for item in self.manifest.node_ptr.iter("action"):
                if item.get("{http://schemas.android.com/apk/res/android}name") != "android.intent.action.MAIN":
                    continue
                

                # 发现一种对抗方法, 故意写入多个假的activity并赋予android.intent.action.MAIN，同时不设置category
                # 就会使此程序获取mainactivity 出错
                # 
                # <activity name=".SplashActivity">
                #     <intent-filter>
                #         <action ns0:name="android.intent.action.MAIN" />
                #         <category ns0:name="android.intent.category.LAUNCHER" />
                #     </intent-filter>
                # </activity>
                # <activity name=".FakeActivity">
                #     <intent-filter>
                #         <action ns0:name="android.intent.action.MAIN" />
                #     </intent-filter>
                # </activity>
                # 
                category = item.getparent().iter("category")
                try:
                    category.__next__()     # ElementDepthFirstIterator为啥没有一个判空的方法？？
                except:
                    continue
                for i in category:
                    # print(item.get("{http://schemas.android.com/apk/res/android}name"))
                    if item.get("{http://schemas.android.com/apk/res/android}name") != "android.intent.category.LAUNCHER":
                        continue


                target_element = item.getparent().getparent()
                if target_element.tag == "activity":
                    ret = target_element.get("{http://schemas.android.com/apk/res/android}name")
                    if not ret:
                        ret = target_element.get("name")    #activity可以没有namespace
                    return ret

        return "not_found_main_activity!!"

    def get_icon(self) -> str:
        """获取应用图标

        Returns:
            str: 图标在apk包中的路径
        """
        icon_ls = []

        # http://schemas.android.com/apk/res/android 这个命名空间是固定死的
        icon_resid = self.manifest.node_ptr.find("application").get("{http://schemas.android.com/apk/res/android}icon")
        
        if icon_resid.startswith("0x"):
            for k,v in self.resources.get_resources(int(icon_resid, base=16)):
                if v.endswith(".png"):
                    icon_ls.append(v)
                elif v.endswith(".xml"):
                    continue
                else:
                    icon_ls.append(v)
                    # 图片不需要后缀也行...
                    continue
        
        if len(icon_ls) == 0:
            return ""
        return icon_ls[0]   # TODO 考虑加个get_icons()获取图标列表，按大小排序？

    def get_package(self) -> str:
        if self.flag:
            return self.package
        else:
            return self.common_k_v.get('package', '')

    def get_version(self) -> str:
        if self.flag:
            return self.version
        else:
            return self.common_k_v.get('versionName', '')

    def get_file(self, fname:bytes) -> bytes:
        '''
        通过文件名获取文件，文件名需要转换为bytes
        '''
        return self.zip.get_file(fname)

    def get_manifest(self) -> str:
        '''
        获取xml格式的manifest文件
        '''
        return self.manifest.get_xml_str()

    def get_resources(self, res_id:int) -> list:
        '''
        输入资源id, 如 0x7f100010
        return: 
            [(key,value), (key,value)...]
        '''
        return self.resources.get_resources(res_id)

    def unzip(self, out_path):
        '''
        解压apk中的全部文件
        '''
        zip_file = self.zip
        for fname in zip_file.cds.keys():
            out_fname = os.path.join(out_path.encode('utf-8'), fname)
            fdir = b"/".join(out_fname.split(b"/")[:-1])
            if len(fdir) >= 255:    # 文件名长度限制，只能跳过
                continue
            os.makedirs(fdir, exist_ok=True)
            try:    # TODO 文件夹和文件重名时，会报错，所以用try跳过，目前不知道怎么解决
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



if __name__ == "__main__":
    # test
    apk = ApkFile(sys.argv[1])
    # print(apk.get_manifest())
    print(apk.get_icon())

    # with open("/mnt/c/Users/user/Downloads/t.png",'wb') as fw:
    #     fw.write(apk.get_file(apk.get_icon().encode()))
        # fw.write(apk.get_file(b"AndroidManifest.xml"))
        # fw.write(apk.get_file(b"resources.arsc"))

    # print(apk.get_basic_info())
    # apk.re_zip('./tmp_apk', './ttt.apk')
    # print(apk.get_package())
    
    # print(apk.get_resources(0x7F050021))
