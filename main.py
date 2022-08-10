from loguru import logger
import subprocess
import threading
import os
import re
import time
import argparse


def get_device_list():
    res = os.popen("adb devices")
    res_str = res.readlines()
    res.close()
    device_list = [sub.split('\t')[0] for sub in res_str[1:-1] if sub.split('\t')[1].strip() == 'device']
    device_status = ''
    for i in res_str[1:-1]:
        device_status += i
    if device_status:
        logger.info(f'在线Android设备状态：\n{device_status}')
    else:
        logger.info(f'暂无Android在线设备')
    return device_list


def push_file(udid, apk_path):
    os.system(f'adb -s {udid} shell mkdir /sdcard/111')
    if apk_path.split('.')[-1] == 'apk':
        os.system(f'adb -s {udid} push {apk_path} /sdcard/111/1.apk')
    else:
        os.system(f'adb -s {udid} push {apk_path} /sdcard/111')


def is_brand(udid):
    brand = os.popen(f'adb -s {udid} shell getprop ro.product.brand')
    brand = brand.read().strip()
    logger.info(f'Android设备{udid}手机品牌是{brand}')
    return brand


def read_xml(udid):
    os.system(f'adb -s {udid} shell uiautomator dump')
    try:
        res = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
        return res
    except subprocess.CalledProcessError:
        logger.warning(f'Android设备{udid}已拔出，不再监听安装事件')
        return ''


def parse_location(keyword, text):
    try:
        location = re.findall(f'text="{keyword}".*?bounds="(.*?)"', text)[0]
        _x = location.split('][')[0][1:].split(',')
        _y = location.split('][')[-1][:-1].split(',')
        x = str((int(_x[0]) + int(_y[0])) // 2)
        y = str((int(_x[-1]) + int(_y[-1])) // 2)
        return x, y
    except IndexError:
        return '0', '0'


def auto_click(brand, udid, keyword, package, file=None, apk_path=None):
    logger.info(f'Android设备{udid}正在启动文件管理')
    if brand.lower() == 'vivo':
        os.system(f'adb -s {udid} shell am start -n '
                  f'com.android.filemanager/com.android.filemanager.FirstPermissionActivity')
    else:
        os.system(f'adb -s {udid} shell monkey -p {package} 1')
    res1 = read_xml(udid)
    x, y = parse_location(keyword, res1)
    os.system(f'adb -s {udid} shell input tap {x} {y}')
    res2 = read_xml(udid)
    x, y = parse_location('111', res2)
    os.system(f'adb -s {udid} shell input tap {x} {y}')
    res3 = read_xml(udid)
    if not file:
        x, y = parse_location('1.apk', res3)

    else:
        x, y = parse_location(apk_path.split('\\')[-1], res3)
        os.system(f'adb -s {udid} shell input tap {x} {y}')
        res4 = read_xml(udid)
        x, y = parse_location(file, res4)
    os.system(f'adb -s {udid} shell input tap {x} {y}')


def is_check(udid):
    while True:
        res = read_xml(udid)
        if '权限' in res and ('安装准备中' not in res or '正在查验' not in res or '正在扫描' not in res or '正为您' not in res):
            break
        time.sleep(1)


def screenshot(brand, udid):
    is_check(udid)
    logger.info(f'Android设备{udid}正在截图')
    c_time = str(time.strftime("%Y%m%d%H%M%S", time.localtime()))
    os.system(f'adb -s {udid} shell screencap -p /sdcard/111/{brand}_{udid}_{c_time}.png')
    os.system(f'adb -s {udid} pull /sdcard/111/{brand}_{udid}_{c_time}.png')


def check_virus(udid, apk_path, result_list=None):
    push_file(udid, apk_path)
    brand = is_brand(udid)
    if not result_list:
        if brand.lower() == 'oppo':
            os.system(f'adb -s {udid} shell am force-stop com.coloros.filemanager')
            auto_click(brand, udid, '手机存储', 'com.coloros.filemanager')
        elif brand.lower() == 'huawei' or brand.lower() == 'honor':
            os.system(f'adb -s {udid} shell am force-stop com.huawei.filemanager')
            auto_click(brand, udid, '我的手机', 'com.huawei.filemanager')
        elif brand.lower() == 'xiaomi':
            os.system(f'adb -s {udid} shell am force-stop com.android.fileexplorer')
            auto_click(brand, udid, '手机', 'com.android.fileexplorer')
        elif brand.lower() == 'vivo':
            os.system(f'adb -s {udid} shell am force-stop com.android.fileexplorer')
            auto_click(brand, udid, '手机存储', 'com.android.fileexplorer')
        screenshot(brand, udid)
        os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
        logger.info(f'Android设备{udid}病毒检查完成')
    else:
        for index, value in enumerate(result_list):
            if index == 0:
                if brand.lower() == 'oppo':
                    os.system(f'adb -s {udid} shell am force-stop com.coloros.filemanager')
                    auto_click(brand, udid, '手机存储', 'com.coloros.filemanager', value, apk_path)
                elif brand.lower() == 'huawei' or brand.lower() == 'honor':
                    os.system(f'adb -s {udid} shell am force-stop com.huawei.filemanager')
                    auto_click(brand, udid, '我的手机', 'com.huawei.filemanager', value, apk_path)
                elif brand.lower() == 'xiaomi':
                    os.system(f'adb -s {udid} shell am force-stop com.android.fileexplorer')
                    auto_click(brand, udid, '手机', 'com.android.fileexplorer', value, apk_path)
                elif brand.lower() == 'vivo':
                    os.system(f'adb -s {udid} shell am force-stop com.android.fileexplorer')
                    auto_click(brand, udid, '手机存储', 'com.android.fileexplorer', value, apk_path)
            if index != 0:
                res = read_xml(udid)
                x, y = parse_location(value, res)
                os.system(f'adb -s {udid} shell input tap {x} {y}')
            screenshot(brand, udid)
            logger.info(f'Android设备{udid}的应用{value}病毒检查完成')
            os.system(f'adb -s {udid} shell input keyevent 4')
            if index == len(result_list) - 1:
                os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
                logger.info(f'Android设备{udid}病毒检查完成')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='一个自动检测华米OV安装APP是否报毒的程序')
    parser.add_argument('path', type=str, help='传入的目录或者文件路径')
    file_path = parser.parse_args().path
    if os.path.exists(file_path):
        devices_list = get_device_list()
        if file_path.split('.')[-1] == 'apk':
            for device in devices_list:
                threading.Thread(target=check_virus, args=(device, file_path)).start()
        else:
            target_apk = []
            apk_list = os.listdir(file_path)
            for apk in apk_list:
                if apk.split('.')[-1] == 'apk':
                    target_apk.append(apk)
            if len(target_apk) > 0:
                for device in devices_list:
                    threading.Thread(target=check_virus, args=(device, file_path, target_apk)).start()
            else:
                logger.error('该路径下没有apk格式的文件')
    else:
        logger.error('不存在该路径，请确认路径是否正确')
