### 背景
公司所在项目每个周一都会要求检查一遍我们投放的产品在华米OV四大市场中有没有报毒，如果报毒就及时暂停投放某个产品。刚开始每次都是把产品复制到各大手机中，然后在文件管理里逐一检查，后面发现这种重复性工作完全可以交给程序去做。

### 技术
说到移动端的UI自动化一开始最先想到使用appium，但是本身就是一个小脚本，appium太重加上环境复杂完全不适合。于是想到adb也可以自动化去点击，于是采用先利用正则获取每个界面UI树的坐标，然后使用adb shell input tap加上坐标位置去点击，截图保存每次检测的结果,最后利用jinja2生成html测试报告

### 使用方法
```python
pip install loguru
pip install jinja2
```
```python
脚本所在目录> python CheckVirus.py -p path
```
-path  传入文件路径则是检测单文件报毒情况，传入目录则是检测该目录下所有apk格式文件的报毒情况，默认路径是CheckVirus项目下的apk文件夹

建议：该脚本使用threading进行多线程操作，最好一台电脑直接连接四个不同品牌的手机最省时
