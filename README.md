## 主要功能

- [x] 获取manifest里面的数据
- [x] 获取resources里面的数据
- [ ] ~~获取apk签名~~ (暂时停止)
- [x] 获取apk中指定文件
- [ ] ~~解析dex文件~~，发现了一个非常完善的专门用于逆向的库：https://github.com/lief-project/LIEF， 包含了DEX的解析


## 使用

### 0 安装
```
git clone https://github.com/zxvzxv/ApkParse.git
cd ApkParse
pip3 install .
```
### 1 使用方法

```python
from ApkParse.main import ApkFile

log = logging.getLogger("apk_parse")
log.setLevel(logging.ERROR) # 自定义logger等级，部分有对抗app的warning以下日志会很多

apk = ApkFile(sys.argv[1])  # 输入apk路径进行初始化

apk.get_app_name()          # app名称
apk.get_package()           # 包名
apk.get_version()           # 版本
apk.get_main_activity()     # main_activity

apk.get_manifest()          # xml格式的manifest
apk.get_file(file_name)     # 获取文件, 文件名为bytes格式，如b"AndroidManifest.xml"
apk.get_resources(res_id)   # 获取资源，输入为资源id，如 0x7f100010

apk.get_icon()              # 获取图标路径
apk.get_file(apk.get_icon().encode())   # 获取图标文件
apk.get_icon_bytes()        # 或者这样获取图标文件

# 这两个解压功能，在处理某些比较大的apk可能会花很长时间，程序一直没动并不是卡死了
apk.unzip(out)              # 解压apk到out目录
apk.re_zip(tmp, out)        # 解压apk到tmp目录，然后重新zip压缩，最后输出名为out的文件，非重打包
                            # 部分恶意apk直接用jeb等软件分析会报错，直接重压缩一遍就可以正常分析了

```

## 解决的问题

目前需要一个方便的自动化分析apk工具

python解析apk已经有现成的库`androguard`，但是此库很久没更新了，
而且它使用了一些标准库如zipfile，lxml等，这些库并不是专门为解析apk而
编写的，部分恶意apk会利用 ‘标准zip和xml文件’ 和 ‘apk使用的zip和xml’ 之间的差异
来对抗自动化分析，androguard无法解决这种问题

后来尝试google官方的解析工具，结果还是无法正常解析某些恶意apk

最终选择自己写解析程序，主要是zip，axml，arsc的解析，后续考虑增加dex解析工具

## TODO

~~dex解析，测试用apk：b00f2e7d4b20c42383587b205b51dff3ed2b7ec9~~

证书解析：b3c578a48cb6eb673feb3b52095d4d199f08b034
