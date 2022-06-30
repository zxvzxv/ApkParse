## 主要功能

1. 获取manifest和resources里面的数据
2. 获取apk签名
3. 获取apk中指定文件
4. （待定）解析dex文件

## 解决的问题

目前需要一个方便的自动化分析apk工具

python解析apk已经有现成的库`androguard`，但是此库很久没更新了，
而且它使用了一些标准库如zipfile，lxml等，这些库并不是专门为解析apk而
编写的，部分恶意apk会利用 ‘标准zip和xml文件’ 和 ‘apk使用的zip和xml’ 之间的差异
来对抗自动化分析，androguard无法解决这种问题

后来尝试google官方的解析工具，结果还是无法正常解析某些恶意apk

最终选择自己写解析程序，主要是zip，axml，arsc的解析，后续考虑增加dex解析工具
