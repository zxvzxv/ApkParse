import os,sys
from cProfile import Profile
import datetime
from types import FunctionType

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
from ApkParse.parser.zip_parser import ZipFile
from ApkParse.main import ApkFile
from androguard.core.bytecodes.apk import APK

test_apk = os.path.join(SELF_PATH, "test/apks/app-debug.apk")

# 与androguard库简单对比，确保不要有很大的性能差距

def timer(func:FunctionType):
    '''
    获取函数运行时间，测试用
    '''
    profile = Profile()

    def get_time_and_run(*args, **kwargs):
        profile.enable()
        result = func(*args, **kwargs)
        profile.disable()
        
        print(f'-------func name: {func.__name__}--------')
        profile.print_stats("tottime")
        return result

    return get_time_and_run

def get_file():
    a = APK(sys.argv[1])
    print(a.get_package())
    # zip_file = ZipFile(sys.argv[1])
    # for k,v in zip_file.cds.items():
    #     print(k)

    # for f in [b'classes.dex',b'classes2.dex',b'classes3.dex',b'classes4.dex']:
    #     res = zip_file.get_file(f)
    #     with open(f'/mnt/c/Users/user/Downloads/{f.decode()}', 'wb') as fw:
    #         fw.write(res)
    # assert len(res) == 22528


@timer
def arsc(target):
    if target == 1:
        a = APK(test_apk)
        pkg = a.get_package()
        res = a.get_android_resources().get_color_resources(pkg)
    else:
        a = ApkFile(test_apk)
        res = a.get_resources(0x7F050021)

    print(target, res)

# @timer
def basic(target):
    if target == 1:
        a = APK(test_apk)
        pkg = a.get_package()
        appname = a.get_app_name()
        version = a.get_androidversion_name()
        main_ac = a.get_main_activity()
        res = [appname, version, pkg, '', '', main_ac]
    else:
        a = ApkFile(test_apk)
        res = a.get_basic_info()

if __name__ == "__main__":
    # arsc(1)
    # arsc(2)
    basic(int(sys.argv[1]))
