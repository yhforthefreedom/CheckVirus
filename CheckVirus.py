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
from datetime import datetime
from do_db import DoDb
from androguard.core.bytecodes.apk import APK

db = DoDb()


def get_device_list():
    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
    devices = result.stdout.splitlines()
    device_list = [sub.split('\t')[0] for sub in devices[1:-1] if sub.split('\t')[1].strip() == 'device']
    device_status = '\n'.join(devices[1:-1])
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
                return '', ''
        except subprocess.CalledProcessError:
            logger.warning(f'Android设备{udid}已拔出，无法正常完成检测')
            return '', ''


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
    os.system(f'adb -s {udid} shell uiautomator dump')
    text = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
    for keyword in ['我的手机', '手机存储', '设备存储', '手机', '内部存储']:
        logger.info(f'Android设备{udid}寻找关键字"{keyword}"')
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
    os.system(f'adb -s {udid} shell uiautomator dump')
    res6 = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
    if '以后都允许' in res6:
        x, y = parse_location('以后都允许', res6)
        os.system(f'adb -s {udid} shell input tap {x} {y}')
    elif '记住我的选择' in res6:
        x, y = parse_location('记住我的选择', res6)
        os.system(f'adb -s {udid} shell input tap {x} {y}')
        x, y = parse_location('允许', res6)
        os.system(f'adb -s {udid} shell input tap {x} {y}')


def is_check(udid):
    timeout = 0
    while True:
        os.system(f'adb -s {udid} shell uiautomator dump')
        try:
            _res = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
            if '安装准备中' not in _res and '正在查验' not in _res and '正在扫描' not in _res and \
                    '正为您' not in _res and '风险检测中' not in _res and '安装包扫描中' not in _res and '正在解析' not in _res:
                result = subprocess.check_output(f'adb -s {udid} shell cat /sdcard/window_dump.xml').decode('utf-8')
                if '病毒' in result:
                    if '无法继续安装' not in result:
                        return 'yes'
                    else:
                        return 'unsure'
                else:
                    return 'no'
            time.sleep(1)
            timeout += 1
            if timeout >= 10:
                logger.warning(f'Android设备{udid}检测应用时间超时')
                break
        except subprocess.CalledProcessError:
            logger.warning(f'Android设备{udid}已拔出，无法正常完成检测')
            break


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
    tmp = APK(file)
    package_name = tmp.get_package()
    version_code = tmp.get_androidversion_code()
    version_name = tmp.get_androidversion_name()
    return package_name, version_code, version_name


def has_file_manager(udid):
    result = os.popen(f'adb -s {udid} shell pm list packages').read()
    if 'com.huawei.filemanager' in result:
        return False
    else:
        return True


def check_virus(udid, apk_path, result_list=None):
    brand = is_brand(udid)
    if brand.lower() not in ['oppo', 'vivo', 'xiaomi', 'huawei', 'honor', 'redmi']:
        logger.error(f'Android设备{udid}的品牌机型暂未适配')
        return
    is_model(udid)
    os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
    push_file(udid, apk_path, result_list)
    file_manager_dict = {
        'oppo': 'com.coloros.filemanager',
        'vivo': 'com.android.filemanager',
        'xiaomi': 'com.android.fileexplorer',
        'redmi': 'com.android.fileexplorer',
        'huawei': 'com.huawei.filemanager',
        'honor': 'com.hihonor.filemanager' if has_file_manager(udid) else 'com.huawei.filemanager'
    }
    if not result_list:
        package = file_manager_dict[brand.lower()]
        os.system(f'adb -s {udid} shell am force-stop {package}')
        auto_click(udid, package)
        screenshot(brand, udid)
        os.system(f"adb -s {udid} shell rm -rf /sdcard/111")
        logger.info(f'Android设备{udid}病毒检查完成')
    else:
        count = 0
        for index, value in enumerate(result_list):
            if index == 0:
                package = file_manager_dict[brand.lower()]
                os.system(f'adb -s {udid} shell am force-stop {package}')
                auto_click(udid, package, value, apk_path, len(result_list))
            if index != 0:
                if index % 6 == 0:  # 下一个文件夹的apk
                    time.sleep(0.5)
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
                    unsure_virus_list = []
                    failed = 0
                    apk_arr = [i[:-4] for i in target_apk]
                    res = dict()
                    brand_dict = {
                        'oppo': 'oppo',
                        'vivo': 'vivo',
                        'xiaomi': 'xiaomi',
                        'redmi': 'xiaomi',
                        'huawei': 'huawei',
                        'honor': 'huawei'
                    }
                    for i in apk_arr:
                        res.setdefault(i, {})
                        if package_info(f'{file_path}/{i}.apk'):
                            a, b, c = package_info(f'{file_path}/{i}.apk')
                            res[i].update({"package_name": a, "version_code": b, "version_name": c})
                        res[i].update({"huawei": {}, "xiaomi": {}, "oppo": {}, "vivo": {}})
                        for img in img_list:
                            phone, serial, check_time = img.split('_')[-4:-1]
                            app = img.split(f'_{phone}')[0]
                            if i in img and ('yes' in img or 'unsure' in img):
                                check_time = datetime.strptime(check_time, "%Y%m%d%H%M%S")
                                failed += 1
                                max_code = db.search_version_code(app) or 0
                                if max_code < int(res[i]['version_code']) or \
                                        (max_code == int(res[i]['version_code']) and
                                         tuple([phone]) not in db.search_brand(app)):
                                    virus_data = (app, res[i]['package_name'], phone, serial,
                                                  res[i]['version_code'], res[i]['version_name'],
                                                  check_time)
                                    db.insert_data(virus_data)
                                    logger.info(f'插入数据：{virus_data}到数据库')
                                elif max_code == int(res[i]['version_code']) and tuple(
                                        [phone]) in db.search_brand(app):
                                    db.update_time(check_time, app, res[i]['version_code'],
                                                   phone, serial)
                                    logger.info(f'更新检查时间：{app}')
                                if app not in virus_list and 'yes' in img:
                                    virus_list.append(app)
                                if app not in unsure_virus_list and 'unsure' in img:
                                    unsure_virus_list.append(app)
                                res[i].update({brand_dict[phone.lower()]: {'address': f'{path}/img/{img}',
                                                                           'is_virus': 1}})
                            elif i in img and 'no' in img:
                                res[i].update({brand_dict[phone.lower()]: {'address': f'{path}/img/{img}'}})
                    total = len(devices_list)*len(apk_arr)
                    fail_rate = round(failed / total * 100, 1)
                    context = {
                        'create_time': time.strftime("%Y-%m-%d %H:%M:%S"),
                        'target_dict': res,
                        'model_list': model_list,
                        'duration': round(end_time - start_time, 2),
                        'status': {'pass': int(total-failed), 'fail': int(failed),
                                   'fail_rate': fail_rate, 'pass_rate': round((100 - fail_rate), 1)},
                        'virus_list': virus_list,
                        'unsure_virus_list': unsure_virus_list
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
    db.close()
