import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from retrying import retry

import re
from loguru import logger
from config import email, password

class Hotswind:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        self.driver = uc.Chrome(options=chrome_options, driver_executable_path=r'W:\Personal_Project\hotswind_refresh\src\chromedriver.exe', version_main=118)
        self.driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {
                "userAgent": self.driver.execute_script(
                    "return navigator.userAgent"
                ).replace("Headless", "")
            },
        )
        self.current_ip = None

    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000)
    def load_hotswind_main(self):
        url = 'https://clients.hostwinds.com/cloud/instance_details.php?loc=ips&serviceid=1055821&loc=ips'
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 5, 0.1).until(EC.presence_of_element_located((By.XPATH, "//div[@id='ips']")))
            return
        except:
            logger.info("Not yet logged in.")
            pass
        email_address_ele = WebDriverWait(self.driver, 5, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        email_address_ele.send_keys(email)
        password_ele = WebDriverWait(self.driver, 5, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        password_ele.send_keys(password)
        login_ele = WebDriverWait(self.driver, 5, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='login']")))
        login_ele.click()
        try:
            WebDriverWait(self.driver, 5, 0.1).until(EC.presence_of_element_located((By.XPATH, "//div[@id='ips']")))
        except:
            raise Exception("Need to re-login")

    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=2000)
    def get_current_ip(self):
        table_cell_blocks = self.driver.find_elements(By.XPATH, "//table[@class='table vm-table']//td")
        cell_texts = [i.text for i in table_cell_blocks]
        for cell_text in cell_texts:
            if re.match(r'\d+\.\d+\.\d+\.', cell_text):
                return cell_text
        raise Exception("Fail to get ip")

    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=10000)
    def get_instance_status(self):
        try:
            status_ele = WebDriverWait(self.driver, 5, 0.1).until(
                EC.presence_of_element_located((By.XPATH, '//span[@class="instance-status"]')))
            return status_ele.text
        except:
            raise Exception("Fail to get current status. Will retry")

    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=10000)
    def click_actions_drop_down_btn(self, dropdown_key_value):
        self.driver.refresh()
        action_btn = WebDriverWait(self.driver, 5, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//a[@class='action-blue']")))
        action_btn.click()
        try:
            target_btn = WebDriverWait(self.driver, 5, 0.1).until(
                EC.presence_of_element_located((By.XPATH, f"//a[contains(text(), '{dropdown_key_value}')]")))
            target_btn.click()
        except:
            logger.error(f"Fail to find btn {dropdown_key_value}")
            self.load_hotswind_main()
            raise Exception(f"Fail to find btn {dropdown_key_value}")

    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=10000)
    def check_ip_availability(self, ip_address):
        self.driver.get('https://www.vps234.com/ipchecker/')

        ip_input_ele = WebDriverWait(self.driver, 5, 0.1).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='ip-text']")))
        ip_input_ele.send_keys(ip_address)
        self.click_btn('检查IP', 'button')
        check_data = []
        for i in range(20):
            check_data = self.driver.find_elements(By.XPATH, "//tr[@class='check-data']//i")
            if len(check_data) == 4:
                break
            time.sleep(1)
        if not check_data:
            raise Exception("Fail to get data value in timeout")
        time.sleep(5)
        check_data = self.driver.find_elements(By.XPATH, "//tr[@class='check-data']//i")
        if check_data[0].get_attribute('class') == 'fa fa-check' and check_data[1].get_attribute(
                'class') == 'fa fa-check' and check_data[2].get_attribute('class') == 'fa fa-check' and check_data[
            3].get_attribute('class') == 'fa fa-check':
            return 1
        elif check_data[0].get_attribute('class') == 'fa fa-close' and check_data[1].get_attribute(
                'class') == 'fa fa-close' and check_data[2].get_attribute('class') == 'fa fa-check' and check_data[
            3].get_attribute('class') == 'fa fa-check':
            return 0
        else:
            return -1

    @retry(stop_max_attempt_number=3, wait_random_min=1000, wait_random_max=10000)
    def click_btn(self, btn_name, btn_class='a'):
        try:
            target_btn = WebDriverWait(self.driver, 10, 0.1).until(
                EC.presence_of_element_located((By.XPATH, f"//{btn_class}[contains(text(), '{btn_name}')]")))
            target_btn.click()
            logger.success(f'{btn_name} clicked.')
        except:
            logger.error(f"Fail to find btn {btn_name}")
            raise Exception(f"Fail to find btn {btn_name}")

    def fix_isp(self, wait_time=5):
        self.click_btn('Fix ISP')
        self.click_btn('Confirm')
        while 1:
            self.load_hotswind_main()
            status = self.get_instance_status()
            if status == 'RUNNING':
                logger.success("ISP FIXED.")
                cur_ip = self.get_current_ip()
                if not cur_ip:
                    time.sleep(wait_time)
                    continue
                logger.success(f"Current IP: {cur_ip}")
                return cur_ip
            if '\n' in status:
                logger.warning(f"Current status: {status}")
                time.sleep(wait_time)

    def regenerate_network(self):
        self.click_actions_drop_down_btn('Regenerate Networking')
        self.click_btn('Confirm')
        while 1:
            self.load_hotswind_main()
            status = self.get_instance_status()
            if status == 'RUNNING':
                logger.success("Regenerated network.")
                return
            if '\n' in status:
                logger.warning(f"Current status: {status}")
                time.sleep(5)

    def reinstall_system(self, wait_time=10):
        self.load_hotswind_main()
        self.click_actions_drop_down_btn('Reinstall')
        self.click_btn('Confirm')
        logger.warning("Sleeping for 30 sec to wait for re-installation")
        time.sleep(30)
        while 1:
            self.load_hotswind_main()
            status = self.get_instance_status()
            if status == 'RUNNING':
                logger.success("System reinstalled.")
                cur_ip = self.get_current_ip()
                if not cur_ip:
                    time.sleep(wait_time)
                    continue
                logger.success(f"Current IP: {cur_ip}")
                return cur_ip
            if '\n' in status:
                logger.warning(f"Current status: {status}")
                time.sleep(wait_time)

    def change_ip(self):
        logger.warning("Starts to change ip.")
        self.load_hotswind_main()
        time.sleep(10)
        self.fix_isp()
        self.regenerate_network()
        ip = self.reinstall_system()
        return ip

    def main(self, loop_check_duration=60 * 60):
        not_ready_count = 0
        while 1:
            if not self.current_ip:
                logger.warning("Fail to get current ip. Try to get current ip now.")
                self.load_hotswind_main()
                ip = self.get_current_ip()
                logger.success(f"Current IP: {ip}")
                self.current_ip = ip
            status = self.check_ip_availability(self.current_ip)
            if status == 1:
                logger.success(f"Current ip {self.current_ip} is clean. Will check in {loop_check_duration} second.")
                time.sleep(loop_check_duration)
            elif status == 0:
                # Change ip
                logger.error(f"Current ip {self.current_ip} is blocked. Will change ip.")
                self.current_ip = self.change_ip()
                time.sleep(30)

            else:
                # Re install
                not_ready_count += 1
                if not_ready_count < 5:
                    logger.warning(f"IP not ready for count {not_ready_count}. Will re-check.")
                    time.sleep(2)
                    continue
                logger.error(f"Current ip {self.current_ip} is not ready. Will reinstall system.")
                self.current_ip = self.reinstall_system()
                not_ready_count = 0
                logger.success("SYSTEM reinstalled. Not ready count reset to 0")
                time.sleep(30)


if __name__ == "__main__":
    a = Hotswind()
    a.main()
