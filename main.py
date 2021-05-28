from selenium import webdriver
from lxml import html
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver.v2 as uc
import time
import csv
import redis
import requests

encoding = 'cp1252'     # utf-8 #Настройка декодера
js_dir_sleep_time = 3   # Время для работы js на странице для чтения папок
js_file_sleep_time = 1  # Время для работы js на странице для чтения вложенных файлов

# GIT_LOGIN = "example"
# GIT_PASSWORD = "example"
GIT_URL = 'https://gitlab.com/Bloodies/Testing'  # URL для парсинга

REDIS_BIND = '127.0.0.1'
REDIS_HOST = 'localhost'
REDIS_PORT = '6379'
REDIS_PASSWORD = ''
REDIS_DB = 2

STR = b'$%d\r\n%b\r\n'
RAW = b'%b'
SEP = ";"

# Настройки подключения к redis
REDIS = redis.StrictRedis(host=REDIS_HOST,
                          port=REDIS_PORT,
                          # password=REDIS_PASSWORD,
                          db=REDIS_DB,
                          charset="utf-8",
                          decode_responses=True)


class Parser(object):

    def __init__(self, driver):
        self.driver = driver

    def parse(self):
        self.read_page()

    def read_page(self):
        global GIT_URL

        process = True
        tmpdir_list = []   # Список содержащий информацию о дирикториях репозитория
        tmpfile_list = []  # Список содержащий информацию о файлах репозитория

        ''' Чтение репозиторя и заполнение временного листа'''
        while process:
            self.driver.get(GIT_URL)
            time.sleep(js_dir_sleep_time)
            tree_elements = self.driver.find_elements_by_class_name("tree-item-link")
            for element in tree_elements:
                url = element.get_attribute('href')
                if url.endswith('.sql'):
                    tmpfile_list.append(url)
                else:
                    tmpdir_list.append(url)

            path = GIT_URL.rsplit('/', 1)[1:]
            print("folder " + path[0] + '\033[31m' + " Checked" + '\x1b[0m')
            iter_item = iter(tmpdir_list)
            GIT_URL = next(iter_item, None)
            del tmpdir_list[0]
            if not tmpdir_list:
                tmpdir_list.append('1')
            if GIT_URL == '1':
                process = False

        reader = True

        csv_file = open("temp.csv", mode="w", encoding='cp1251')
        file_writer = csv.writer(csv_file, delimiter=';')
        file_writer.writerow(["Date", "Name", "Path", "Short Hash", "Full Hash", "Download link"])

        # print("Date;Name;Path;Short Hash;Full Hash;Download link")
        iter_subitem = iter(tmpfile_list)
        GIT_URL = next(iter_subitem, None)

        while reader:
            self.driver.get(GIT_URL)
            time.sleep(js_file_sleep_time)

            time_element = self.driver.find_element_by_xpath("//time[@datetime]")

            file_name = GIT_URL.rsplit('/', 1)[1:]

            hash_element = self.driver.find_element_by_class_name("commit-row-message")
            HASH = hash_element.get_attribute('href').rsplit('/', 1)[1:]

            temp = GIT_URL.split('/')
            path = GIT_URL.replace("https://gitlab.com/" + temp[3] + "/" + temp[4], "").replace("/-/blob/", "")

            # region 1 variant
            # DATA = {
            #     "Date": time_element.get_attribute('datetime'),
            #     "Name": file_name[0],
            #     "Short Hash": HASH[0][:8],
            #     "Full Hash": HASH[0],
            #     "Path": GIT_URL,
            #     "Download URL": GIT_URL.replace("blob", "raw") + "?inline=false"
            # }
            # REDIS.hmset(path, DATA)
            # endregion

            # region 2 variant
            # REDIS.hset(path, 'Date', time_element.get_attribute('datetime'))
            # REDIS.hset(path, 'Name', file_name[0])
            # REDIS.hset(path, 'Short Hash', HASH[0][:8])
            # REDIS.hset(path, 'Full Hash', HASH[0])
            # REDIS.hset(path, 'Path', GIT_URL)
            # REDIS.hset(path, 'Download URL', GIT_URL.replace("blob", "raw") + "?inline=false")
            # endregion

            # region 3 variant
            REDIS.zadd(path, {
                time_element.get_attribute('datetime'): 1,
                file_name[0]: 2,
                HASH[0][:8]: 3,
                HASH[0]: 4,
                GIT_URL: 5,
                GIT_URL.replace("blob", "raw") + "?inline=false": 6
            })
            # endregion

            file_writer.writerow([time_element.get_attribute('datetime'),
                                  file_name[0],
                                  GIT_URL,
                                  HASH[0][:8],
                                  HASH[0],
                                  GIT_URL.replace("blob", "raw") + "?inline=false"])

            # region Output to console
            # print(timeElement.get_attribute('datetime') + SEP
            #       + file_name[0] + SEP
            #       + GIT_URL + SEP
            #       + HASH[0][:8] + SEP
            #       + HASH[0] + SEP
            #       + GIT_URL.replace("blob", "raw") + "?inline=false" + "\n")
            # endregion

            GIT_URL = next(iter_subitem, None)
            if not tmpfile_list:
                tmpfile_list.append('1')
            if GIT_URL == '1' or GIT_URL is None:
                reader = False

            print(file_name[0] + '\033[31m' + " Done" + '\x1b[0m')


def start():
    # region Try to access cookies
    # headers = {
    #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)
    #                   AppleWebKit/537.36 (KHTML, like Gecko)
    #                   Chrome/76.0.3809.132 Safari/537.36',
    #     'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
    # }
    # session = requests.Session()
    # page = session.get('https://gitlab.com/users/sign_in')
    # get_token = html.fromstring(page.content)
    # token = get_token.xpath('/html/head/meta[@name="csrf-token"]/@content')
    # data = {
    #     'utf8': '\u2713',
    #     'authenticity_token': token[0],
    #     'user[login]': GIT_LOGIN,
    #     'user[password]': GIT_PASSWORD
    # }
    # response_login = session.post('https://gitlab.com/users/sign_in', headers=headers, data=data)
    # endregion

    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(r"user-data-dir=C:\\Users\\Bloodies\\AppData\\Local\\Google\\Chrome\\User Data")
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    # region Try to use undetected_chromedriver
    # options = uc.ChromeOptions()
    # options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
    # driver = uc.Chrome(options=options)
    # endregion

    driver.get(GIT_URL)

    # region try to LOG IN
    # login_element = driver.find_element_by_class_name("btn-sign-in")
    # if login_element.get_attribute('href') == "https://gitlab.com/users/sign_in?redirect_to_referer=yes":
    #     driver.get("https://gitlab.com/users/sign_in")
    #     time.sleep(30)
    #     username = driver.find_element_by_class_name("top")
    #     print(username.get_attribute('data-qa-selector'))
    # endregion

    parser = Parser(driver)
    parser.parse()


def is_redis_available(REDIS):
    try:
        REDIS.ping()
        print("Successfully connected to redis")
    except (redis.exceptions.ConnectionError, ConnectionRefusedError):
        print("Redis connection error!")
        return False
    return True


if __name__ == '__main__':
    if is_redis_available(REDIS):
        REDIS.flushdb()
        start()
