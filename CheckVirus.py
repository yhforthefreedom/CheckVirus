from loguru import logger
import subprocess
import threading
import os
import re
import time
import argparse
from jinja2 import Environment, FileSystemLoader
import webbrowser
import shutil


def get_device_list():
    _res = os.popen("adb devices")
    res_str = _res.readlines()
    device_list = [sub.split('\t')[0] for sub in res_str[1:-1] if sub.split('\t')[1].strip() == 'device']
    device_status = ''
    for _i in res_str[1:-1]:
        device_status += _i
    if device_status:
        logger.info(f'在线Android设备状态：\n{device_status}')
    else:
        logger.info(f'暂无Android在线设备')
    return device_list


def push_file(udid, apk_path, result_list):
    os.system(f'adb -s {udid} shell mkdir /sdcard/111')
    os.system(f'adb -s {udid} shell mkdir /sdcard/111/img')
    if apk_path.split('.')[-1] == 'apk':
        os.system(f'adb -s {udid} push {apk_path} /sdcard/111/1.apk')
    else:
        if len(result_list) <= 6:
            os.system(f'adb -s {udid} push {apk_path} /sdcard/111')
        else:
            num = len(result_list) // 6 + 1
            for n in range(0, num):
                os.system(f'adb -s {udid} push {apk_path}/{n} /sdcard/111')


def is_brand(udid):
    _brand = os.popen(f'adb -s {udid} shell getprop ro.product.brand')
    _brand = _brand.read().strip()
    logger.info(f'Android设备{udid}手机品牌是{_brand}')
    return _brand


def is_model(udid):
    model = os.popen(f'adb -s {udid} shell getprop ro.product.model')
    model = model.read().strip()
    logger.info(f'Android设备{udid}手机机型是{model}')
    model_list.append(model)


def read_xml(udid, keyword):
    retry_count = 0
    while True:
        os.system(f'adb -s {udid} shell uiautomator dump')
        try:
            _res = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
            if keyword in _res:
                return _res, 1
            retry_count += 1
            if retry_count >= 3:
                if keyword[:10] in _res:
                    return _res, 2
                return ''
        except subprocess.CalledProcessError:
            logger.warning(f'Android设备{udid}已拔出，无法正常完成检测')
            return ''


def parse_location(keyword, text, mode=1):
    try:
        if mode == 1:
            location = re.findall(f'text="{keyword}".*?bounds="(.*?)"', text)[0]
        else:
            location = re.findall(f'text="{keyword[:10]}.*?".*?bounds="(.*?)"', text)[0]
        _x = location.split('][')[0][1:].split(',')
        _y = location.split('][')[-1][:-1].split(',')
        x = str((int(_x[0]) + int(_y[0])) // 2)
        y = str((int(_x[-1]) + int(_y[-1])) // 2)
        return x, y
    except IndexError:
        return '0', '0'


def auto_click(udid, package, file=None, apk_path=None, apk_count=None):
    logger.info(f'Android设备{udid}正在启动文件管理')
    os.system(f'adb -s {udid} shell monkey -p {package} 1')
    for keyword in ['我的手机', '手机存储', '设备存储', '手机', '内部存储']:
        logger.info(f'Android设备{udid}寻找关键字"{keyword}"')
        os.system(f'adb -s {udid} shell uiautomator dump')
        text = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
        if keyword in text:
            logger.info(f'Android设备{udid}命中关键字"{keyword}"')
            x, y = parse_location(keyword, text)
            os.system(f'adb -s {udid} shell input tap {x} {y}')
            break
    res2, mode = read_xml(udid, '111')
    x, y = parse_location('111', res2, mode)
    os.system(f'adb -s {udid} shell input tap {x} {y}')

    if not file:
        res3, mode = read_xml(udid, '1.apk')
        x, y = parse_location('1.apk', res3, mode)

    else:
        if apk_count > 6:
            res4, mode = read_xml(udid, '0')
            x, y = parse_location('0', res4, mode)
            os.system(f'adb -s {udid} shell input tap {x} {y}')
        else:
            res3, mode = read_xml(udid, apk_path.split('\\')[-1])
            x, y = parse_location(apk_path.split('\\')[-1], res3, mode)
            os.system(f'adb -s {udid} shell input tap {x} {y}')
        res5, mode = read_xml(udid, file)
        x, y = parse_location(file, res5, mode)
    os.system(f'adb -s {udid} shell input tap {x} {y}')


def is_check(udid):
    while True:
        _res = read_xml(udid, '权限')
        if not _res:
            break
        if '安装准备中' not in _res and '正在查验' not in _res and '正在扫描' not in _res and \
                '正为您' not in _res and '风险检测中' not in _res:
            result = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
            if '病毒' in result:
                return 'yes'
            else:
                return 'no'
        time.sleep(1)


def screenshot(brand, udid, app_name=None):
    if not os.path.exists("./img"):
        os.mkdir("./img")
    result = is_check(udid)
    logger.info(f'Android设备{udid}正在截图')
    c_time = str(time.strftime("%Y%m%d%H%M%S", time.localtime()))
    if not app_name:
        os.system(f'adb -s {udid} shell screencap -p /sdcard/111/img/{brand}_{udid}_{c_time}.png')
        os.system(f'adb -s {udid} pull /sdcard/111/img/{brand}_{udid}_{c_time}.png ./img')
    else:
        os.system(f'adb -s {udid} shell screencap -p /sdcard/111/img/{brand}_{udid}_{c_time}.png')
        os.system(f'adb -s {udid} pull /sdcard/111/img/{brand}_{udid}_{c_time}.png ./img')
        try:
            os.rename(f'./img/{brand}_{udid}_{c_time}.png', f'./img/{app_name}_{brand}_{udid}_{c_time}_{result}.png')
            img_list.append(f'{app_name}_{brand}_{udid}_{c_time}_{result}.png')
        except FileNotFoundError:
            pass


def package_info(file):
    envs = os.getenv('path')
    for env in envs.split(';'):
        if 'build-tools' in env:
            info = subprocess.check_output(f'aapt2 dump badging {file} | findstr versionName', shell=True)\
                .decode('utf-8')
            package_name, version_code, version_name = re.findall(r"name='(.*?)' versionCode='(.*?)' "
                                                                  r"versionName='(.*?)'", info)[0]
            return package_name, version_code, version_name


def check_virus(udid, apk_path, result_list=None):
    brand = is_brand(udid)
    if brand.lower() not in ['oppo', 'vivo', 'xiaomi', 'huawei', 'honor']:
        logger.error(f'Android设备{udid}的品牌机型暂未适配')
        return
    is_model(udid)
    os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
    push_file(udid, apk_path, result_list)

    if not result_list:
        if brand.lower() == 'oppo':
            os.system(f'adb -s {udid} shell am force-stop com.coloros.filemanager')
            auto_click(udid, 'com.coloros.filemanager')
        elif brand.lower() == 'huawei' or brand.lower() == 'honor':
            package = os.popen(f'adb -s {udid} shell pm list package | findstr com.huawei.filemanager') \
                .read().strip()
            if package:
                os.system(f'adb -s {udid} shell am force-stop com.huawei.filemanager')
                auto_click(udid, 'com.huawei.filemanager')
            else:
                os.system(f'adb -s {udid} shell am force-stop com.hihonor.filemanager')
                auto_click(udid, 'com.hihonor.filemanager')
        elif brand.lower() == 'xiaomi':
            os.system(f'adb -s {udid} shell am force-stop com.android.fileexplorer')
            auto_click(udid, 'com.android.fileexplorer')
        elif brand.lower() == 'vivo':
            os.system(f'adb -s {udid} shell am force-stop com.android.filemanager')
            auto_click(udid, 'com.android.filemanager')
        screenshot(brand, udid)
        os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
        logger.info(f'Android设备{udid}病毒检查完成')
    else:
        count = 0
        for index, value in enumerate(result_list):
            if index == 0:
                if brand.lower() == 'oppo':
                    os.system(f'adb -s {udid} shell am force-stop com.coloros.filemanager')
                    auto_click(udid, 'com.coloros.filemanager', value, apk_path, len(result_list))
                elif brand.lower() == 'huawei' or brand.lower() == 'honor':
                    package = os.popen(f'adb -s {udid} shell pm list package | findstr com.huawei.filemanager')\
                        .read().strip()
                    if package:
                        os.system(f'adb -s {udid} shell am force-stop com.huawei.filemanager')
                        auto_click(udid, 'com.huawei.filemanager', value, apk_path, len(result_list))
                    else:
                        os.system(f'adb -s {udid} shell am force-stop com.hihonor.filemanager')
                        auto_click(udid, 'com.hihonor.filemanager', value, apk_path, len(result_list))
                elif brand.lower() == 'xiaomi':
                    os.system(f'adb -s {udid} shell am force-stop com.android.fileexplorer')
                    auto_click(udid, 'com.android.fileexplorer', value, apk_path, len(result_list))
                elif brand.lower() == 'vivo':
                    os.system(f'adb -s {udid} shell am force-stop com.android.filemanager')
                    auto_click(udid, 'com.android.filemanager', value, apk_path, len(result_list))
            if index != 0:
                if index % 6 == 0:  # 下一个文件夹的apk
                    count += 1
                    os.system(f'adb -s {udid} shell input keyevent 4')
                    res2, mode = read_xml(udid, f'{count}')
                    x, y = parse_location(f'{count}', res2, mode)
                    os.system(f'adb -s {udid} shell input tap {x} {y}')
                res1, mode = read_xml(udid, value)
                x, y = parse_location(value, res1, mode)
                os.system(f'adb -s {udid} shell input tap {x} {y}')
            app_name = value.split('.apk')[0]
            screenshot(brand, udid, app_name)
            logger.info(f'Android设备{udid}的应用{value}病毒检查完成')
            os.system(f'adb -s {udid} shell input keyevent 4')
            if index == len(result_list) - 1:
                os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
                logger.info(f'Android设备{udid}病毒检查完成')


if __name__ == '__main__':
    if not os.path.exists("./apk"):
        os.mkdir("./apk")
    path = os.path.abspath(os.path.dirname(__file__))
    parser = argparse.ArgumentParser(description='一个自动检测华米OV安装APP是否报毒的程序')
    parser.add_argument('-p', type=str, help='传入的目录或者文件路径', default=fr'{path}\apk')
    file_path = parser.parse_args().p
    model_list = []
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
            logger.info(f'安装包检查顺序：{target_apk}')
            if len(target_apk) > 0:
                img_list = []
                task = []
                group = len(target_apk) // 6 + 1
                if len(target_apk) > 6:
                    logger.info('由于需要检测的安装包大于6个，采用6个为一组，创建多个文件夹的方法')
                    for i in range(0, group):
                        os.mkdir(f'{file_path}/{i}')
                        for j in target_apk[6 * i:6 * i + 6]:
                            shutil.copy(f'{file_path}/{j}', f'{file_path}/{i}')
                start_time = time.time()
                for device in devices_list:
                    t = threading.Thread(target=check_virus, args=(device, file_path, target_apk))
                    task.append(t)
                    t.start()
                for t in task:
                    t.join()
                end_time = time.time()
                logger.info('----------测试报告正在生成,请稍候----------')
                if len(target_apk) > 6:
                    for i in range(0, group):
                        shutil.rmtree(f'{file_path}/{i}')
                if img_list:
                    virus_list = []
                    failed = 0
                    apk_arr = [i[:-4] for i in target_apk]
                    res = dict()
                    for i in apk_arr:
                        res[i] = {}
                        if package_info(f'{file_path}/{i}.apk'):
                            a, b, c = package_info(f'{file_path}/{i}.apk')
                            res[i].update({"package_name": a})
                            res[i].update({"version_code": b})
                            res[i].update({"version_name": c})
                        res[i].update({"huawei": {}})
                        res[i].update({"xiaomi": {}})
                        res[i].update({"oppo": {}})
                        res[i].update({"vivo": {}})
                        for img in img_list:
                            if 'yes' in img:
                                failed += 1
                                app = img.split('_')[0]
                                if app not in virus_list:
                                    virus_list.append(app)
                            if 'oppo' in img.lower() and i in img:
                                if 'yes' in img:
                                    res[i].update({"oppo": {'address': f'{path}/img/{img}', 'is_virus': 1}})
                                else:
                                    res[i].update({"oppo": {'address': f'{path}/img/{img}'}})
                            elif 'xiaomi' in img.lower() and i in img:
                                if 'yes' in img:
                                    res[i].update({"xiaomi": {'address': f'{path}/img/{img}', 'is_virus': 1}})
                                else:
                                    res[i].update({"xiaomi": {'address': f'{path}/img/{img}'}})
                            elif 'vivo' in img.lower() and i in img:
                                if 'yes' in img:
                                    res[i].update({"vivo": {'address': f'{path}/img/{img}', 'is_virus': 1}})
                                else:
                                    res[i].update({"vivo": {'address': f'{path}/img/{img}'}})
                            elif ('huawei' in img.lower() or 'honor' in img.lower()) and i in img:
                                if 'yes' in img:
                                    res[i].update({"huawei": {'address': f'{path}/img/{img}', 'is_virus': 1}})
                                else:
                                    res[i].update({"huawei": {'address': f'{path}/img/{img}'}})
                    failed = failed / len(apk_arr)
                    total = len(devices_list)*len(apk_arr)
                    fail_rate = round(failed / total * 100, 1)
                    context = {
                        'create_time': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'target_dict': res,
                        'model_list': model_list,
                        'duration': round(end_time - start_time, 2),
                        'status': {'pass': int(total-failed), 'fail': int(failed),
                                   'fail_rate': fail_rate, 'pass_rate': round((100 - fail_rate), 1)},
                        'virus_list': virus_list
                    }
                    report_context = {
                        "context": context
                    }
                    template_environment = Environment(
                        autoescape=False,
                        loader=FileSystemLoader(path),
                        trim_blocks=False)
                    if not os.path.exists("./report"):
                        os.mkdir("./report")
                    html_name = time.strftime("%Y%m%d%H%M%S")
                    with open(f'{path}/report/{html_name}.html',
                              'w', encoding='utf8') as f:
                        html = template_environment.get_template('./report.html').render(report_context)
                        f.write(html)
                    logger.info("----------测试报告生成完成,正在打开----------")
                    webbrowser.open(f'file://{path}/report/{html_name}.html')
            else:
                logger.error('该路径下没有apk格式的文件')
    else:
        logger.error('不存在该路径，请确认路径是否正确')
