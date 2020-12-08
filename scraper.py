from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
import csv
import os
from datetime import datetime
import re
from joblib import Parallel, delayed, parallel_backend
import sys

class House:
    def __init__(self):
        self.num_bedroom = 'NA'
        self.num_bathroom = 'NA'
        self.num_garage = 'NA'
        self.floor_area = 'NA'
        self.land_area = 'NA'
        self.building_type = 'NA'
        self.yr_built = 'NA'
        self.primary_use = 'NA'
        self.last_sold_date = 'NA'
        self.last_sold_price = 'NA'
        self.land_price = 'NA'
        self.nearest_pri = 'NA'
        self.nearest_pri_dist = 'NA'
        self.nearest_sec = 'NA'
        self.nearest_sec_dist = 'NA'

    def toList(self):
        attribute_list = [self.num_bedroom, self.num_bathroom, self.num_garage, 
                        self.floor_area, self.land_area, self.building_type, self.yr_built, self.primary_use,
                        self.last_sold_date, self.last_sold_price, self.land_price, self.nearest_pri, self.nearest_pri_dist,
                        self.nearest_sec, self.nearest_sec_dist]
        return attribute_list
    
def check_proxy(process_index):
    options = webdriver.ChromeOptions()

    #Residential Proxies
    PROXY = 'au.smartproxy.com:30000'
    options.add_argument('--proxy-server=%s' % PROXY)
    options.add_argument('--disable-extensions')

    #Datacenter Proxies
    #options.add_extension("proxy.zip")

    options.add_argument('start-maximized')
    prefs={"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option('prefs', prefs)
    prefs = {'disk-cache-size': 4096}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("user-data-dir=C:/Selenium_profile/User Data " + str(process_index))
    options.add_argument("profile-directory=Profile 1")

    #options.add_argument(f'user-agent={userAgent}')

    driver = webdriver.Chrome(executable_path='chromedriver.exe', options=options)
    return driver

def search_func(search_term_data, driver):
    url = 'https://www.onthehouse.com.au/real-estate/wa/'
    search_term_data = [s.lower() for s in search_term_data]
    search_term_data[3].replace(' ', '-') #If suburb is 2 words or more long, put a dash inbetween
    search_term_data[1].replace(' ', '-') #If street is 2 words or more long, put a dash inbetween
    url += search_term_data[3] + '-' + search_term_data[5] + '/' + search_term_data[1] + '-' + search_term_data[2] + '?' + 'streetNumber=' + search_term_data[0]
    try:
        driver.get(url)
    except: #URL does not exist
        return 0
        
    #Wait for new page to load then click the card link that appears
    try:
        card_link = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'PropertySearch__resultSlot--1YH_u'))
        )
    except TimeoutException:
        return 0

    card_link.click()
    return 1

#Basic details present in all houses
def get_basic_details(obj, driver):
    obj.num_bedroom = driver.find_element_by_xpath('//*[@id="root"]/div/div[2]/div/div[2]/div/div[1]/div/div[1]/div[2]/div[1]/div[2]').text
    obj.num_bathroom = driver.find_element_by_xpath('//*[@id="root"]/div/div[2]/div/div[2]/div/div[1]/div/div[1]/div[2]/div[2]/div[2]').text
    obj.num_garage = driver.find_element_by_xpath('//*[@id="root"]/div/div[2]/div/div[2]/div/div[1]/div/div[1]/div[2]/div[3]/div[2]').text

#Details which may or may not be present
def get_intermediate_details(obj, driver):
    property_details = driver.find_elements_by_xpath("//li[contains(@class, 'pb-2') and contains(@class, 'mb-2')]")
    for i in range(len(property_details)):
        p = property_details[i].text.split('\n') #Each item in property details has its value and description separated by \n
        if p[0] == 'Building Type':
            obj.building_type = p[1]
        elif p[0] == 'Year Built':
            obj.yr_built = p[1]
        elif p[0] == 'Floor Size':
            obj.floor_area = re.sub('\D\w+', '', p[1])
        elif p[0] == 'Land Size':
            obj.land_area = re.sub('\D\w+', '', p[1])
        elif p[0] == 'Primary Land Use':
            obj.primary_use = p[1]
        else:
            continue

#Gets history. May or may not be present
def get_history(obj, driver):
    try:
        history_text = driver.find_element_by_xpath("//div[contains(@class, 'mb-4') and contains(@class, 'pb-4') and contains(@class, 'PropertyHistory__latestEvent--2QiUe')]")
        #print("there is history")
    except:
        #print("no history")
        return

    history_list = driver.find_elements_by_xpath("//div[contains(@class, 'flex-column') and contains(@class, 'w-50')]//*")

    try:
        obj.last_sold_date = history_list[2].text
        last_sold_obj = datetime.strptime(obj.last_sold_date, '%d %b %Y')
    except IndexError:
        return

    try:
        int(obj.yr_built)
    except ValueError:
        #No year built data was found
        return

    if int(obj.yr_built) >= last_sold_obj.year:
        #if house built after it was sold, then the price stated is the land price
        obj.land_price = history_list[1].text.strip('$k')
    else:
        obj.last_sold_price = history_list[1].text.strip('$k')

#Gets schools by proximity. Almost always present but have to get the nearest
def get_schools(obj, driver):
    try:
        school_list = driver.find_elements_by_xpath("//div[contains(@class, 'Explore__schoolRow--3TE8e')]")
    except NoSuchElementException:
        #No school list
        return

    for i in range(len(school_list)):
        s = school_list[i].text.split('\n')
        school = s[0]
        distance = s[1]
        attributes = s[3]
        if 'PRIMARY' in attributes and obj.nearest_pri_dist == 'NA':
            obj.nearest_pri = school
            obj.nearest_pri_dist = distance
        elif 'SECONDARY' in attributes and obj.nearest_sec_dist == 'NA':
            obj.nearest_sec = school
            obj.nearest_sec_dist = distance
        elif attributes.count('COMBINED') >= 2 and obj.nearest_sec_dist == 'NA':
            obj.nearest_sec = school
            obj.nearest_sec_dist = distance

#Opens a file for appending
def write_data(h1, search_term_data, additional_data, file_name):
    file_name = re.sub('[.]', '_result.', file_name)
    with open(file_name, 'a+', newline='') as csv_write_file:
        writer = csv.writer(csv_write_file, delimiter=',')
        writer.writerow(search_term_data + additional_data + h1.toList())
    return

#Opens a file that prints a search that was skipped
def skipped(search_term_data, driver):
    with open('address_data/skipped_searches.txt', 'a') as f:
        f.write(' '.join(e.strip('\r') for e in search_term_data) + '\r\n')
        driver.close()

def scrape(search_term_data, additional_data, file_name, process_index):
    #Initialisation of driver
    driver = check_proxy(process_index)

    #Better error handling here?
    if search_func(search_term_data, driver) == 0: #If search failed
        skipped(search_term_data, driver)
        return

    #Wait for new page to appear
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'smText'))
        )
    except:#Timeout
        skipped(search_term_data, driver)
        return 

    h1 = House() #House object
    try:
        get_basic_details(h1, driver)
    except:
        skipped(search_term_data, driver)
        return
    try:
        get_intermediate_details(h1, driver)
    except:
        pass
    
    get_history(h1, driver)

    #Wait for 'nearby schools' section to appear
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'Explore__schoolRow--3TE8e'))
        )
        get_schools(h1, driver)
    except: #Timeout
        pass
    
    write_data(h1, search_term_data, additional_data, file_name)
    driver.close()

def get_addresses(file_name, process_index):
    with open(file_name, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for line_number, line in enumerate(reader):
            if process_index == 1:
                print("On line: ", line_number)
            if line_number == 0: #Ignore header
                continue
            else:
                search_term_data = line[:-2]
                additional_data = line[-2:]
                scrape(search_term_data, additional_data, file_name, process_index)
                #scrape()
                #write to another file

def manual_proxy_check(num):
    options = webdriver.ChromeOptions()

    #IP Authenticated Proxies
    #PROXY = 'au.smartproxy.com:30000' #Residential
    #PROXY = '23.250.83.82:80' #Datacenter
    #options.add_argument('--proxy-server=%s' % PROXY)
    #options.add_argument('--disable-extensions')

    #User/PW Authenticated Proxies
    options.add_extension("proxy.zip") #Residential
    

    options.add_argument("user-data-dir=C:/Selenium_profile/User Data " + str(num))
    options.add_argument("profile-directory=Profile 1")
    options.add_argument('start-maximized')
    driver = webdriver.Chrome(executable_path='chromedriver.exe', options=options)
    #url = 'https://www.realestateview.com.au/'
    #url = 'https://www.domain.com.au/'
    #url = 'https://www.onthehouse.com.au'
    url = 'http://lumtest.com/myip.json'
    driver.get(url)
    time.sleep(5)
    return
    
#Could possibly use getopt to improve
def main(argv):
    if argv[0] == '-p' and len(argv) == 2:
        #Check proxy
        Parallel(n_jobs=int(argv[1]), prefer="threads")(delayed(manual_proxy_check)(i) for i in range(1, int(argv[1]) + 1))
        return
    if len(argv) < 2:
        print("ERROR: No arguments\nUsage: python scraper.py [file name] [number of processor(s)]")
        return
    elif len(argv) > 2:
        print("ERROR: Too many arguments\nUsage: python scraper.py [file name] [number of processor(s)]")
        return

    file_name = argv[0]
    num_cores = int(argv[1])

    CWD = os.getcwd()
    files = []
    CWD += '/address_data/'
    for i in range(1, num_cores + 1):
        files.append(CWD + file_name + '_part_' + str(i) + '.csv')

    Parallel(n_jobs=num_cores, prefer="threads")(delayed(get_addresses)(file_name, process_index) for process_index, file_name in enumerate(files, 1))

if __name__ == '__main__':
    main(sys.argv[1:])