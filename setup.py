from setuptools import setup, find_packages
setup(name='ApkParse',
      version='0.0.1',
      description='apk parse',
      author='zxv',
      author_email='751269951@qq.com',
      requires= ['lxml'], # 定义依赖哪些模块
      packages=find_packages(),  # 系统自动从当前目录开始找包
      # 如果有的文件不用打包，则只能指定需要打包的文件
      license="apache 3.0"
      )
