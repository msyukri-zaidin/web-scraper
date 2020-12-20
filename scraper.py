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
import sys

class House:
    def __init__(self):
        self.num_bedroom = 'NA'
        self.num_bathroom = 'NA'
        self.num_garage = 'NA'
        #self.floor_area = 'NA'
        self.land_area = 'NA'
        #self.building_type = 'NA'
        #self.yr_built = 'NA'
        #self.primary_use = 'NA'
        self.last_sold_date = 'NA'
        self.last_sold_price = 'NA'
        self.land_price = 'NA'
        #self.nearest_pri = 'NA'
        #self.nearest_pri_dist = 'NA'
        #self.nearest_sec = 'NA'
        #self.nearest_sec_dist = 'NA'

    def toList(self):
        attribute_list = [self.num_bedroom, self.num_bathroom, self.num_garage, self.land_area,
                        self.last_sold_date, self.last_sold_price, self.land_price]
        return attribute_list

    def printAll(self):
        print("Bedrooms: ", self.num_bedroom)
        print("Bathrooms: ", self.num_bathroom)
        print("Garages: ", self.num_garage)
        print("Land Area: ", self.land_area)
        print("Last Sold Date: ", self.last_sold_date)
        print("Last Sold Price: ", self.last_sold_price)
        print("Land Price: ", self.land_price)
    
def check_proxy():
    options = webdriver.ChromeOptions()

    #IP Authenticated Proxies
    PROXY = 'au.smartproxy.com:30000' #Residential
    #PROXY = '23.250.83.82:80' #Datacenter
    options.add_argument('--proxy-server=%s' % PROXY)
    options.add_argument('--disable-extensions')

    #User/PW Authenticated Proxies
    #options.add_extension("proxy.zip") #Residential

    options.add_argument('start-maximized')
    prefs={"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option('prefs', prefs)
    prefs = {'disk-cache-size': 4096}
    options.add_experimental_option('prefs', prefs)
    #options.add_argument("user-data-dir=C:/Selenium_profile/User Data " + str(process_index))
    #options.add_argument("profile-directory=Profile 1")

    #ua = UserAgent()
    #userAgent = ua.random
    #options.add_argument(f'user-agent={userAgent}')

    driver = webdriver.Chrome(executable_path='chromedriver.exe', options=options)
    return driver

def search_func(search_term_data, driver):
    #url = 'https://www.onthehouse.com.au/real-estate/wa/'
    url = 'https://www.realestateview.com.au/property-360/property/'
    #url = 'https://www.domain.com.au/'
    search_term_data = [s.lower() for s in search_term_data]
    search_term_data[3] = search_term_data[3].replace(' ', '-') #If suburb is 2 words or more long, put a dash inbetween
    search_term_data[1] = search_term_data[1].replace(' ', '-') #If street is 2 words or more long, put a dash inbetween
    url += search_term_data[0] + '-' + search_term_data[1] + '-' + search_term_data[2] + '-' + search_term_data[3] + '-' + search_term_data[4] + '-' + search_term_data[5] 
    try:
        driver.get(url)
    except: #URL does not exist
        return 0
        
    #Wait for new page to load then click the card link that appears
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'pe-bbc-size__item'))
        )
    except:
        return 0

    return 1

def hasNumbers(inputString):
    return bool(re.search(r'\d', inputString))

#Basic details present in all houses
def get_basic_details(obj, driver):
    obj.num_bedroom = driver.find_element_by_xpath('/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div[2]/div/div[1]/span[1]/span').text
    obj.num_bathroom = driver.find_element_by_xpath('/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div[2]/div/div[1]/span[2]/span').text
    obj.num_garage = driver.find_element_by_xpath('/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div[2]/div/div[1]/span[3]/span').text
    obj.land_area = driver.find_element_by_xpath('/html/body/div[1]/div[2]/div[2]/div[1]/div/div/div[2]/div/div[1]/span[4]').text
#Details which may or may not be present
def get_intermediate_details(obj, driver):
    history_list = driver.find_elements_by_xpath("//div[contains(@class, '_table-row')]")
    sale_history = []
    for item in history_list:
        if "Sold" in item.text:
            s = item.text.split() #E.g May 2016 Sold $335,000 would be ['May', '2016', 'Sold', '$335,000']
            sale_history.append(s)

    if len(sale_history) == 1: #history_list[0] would be considered land price
        if hasNumbers(sale_history[0][3]):
            obj.land_price = sale_history[0][3]
        obj.last_sold_date = sale_history[0][0] + ' ' + sale_history[0][1]
    elif len(sale_history) >= 1:
        if hasNumbers(sale_history[0][3]):
            obj.last_sold_price = sale_history[0][3]
        obj.last_sold_date = sale_history[0][0] + ' ' + sale_history[0][1]
    else:
        return

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

def scrape(search_term_data):
    #Initialisation of driver
    driver = check_proxy()

    #Better error handling here?
    if search_func(search_term_data, driver) == 0: #If search failed
        return None

    h1 = House() #House object
    try:
        get_basic_details(h1, driver)
    except:
        return None

    try:
        get_intermediate_details(h1, driver)
    except:
        pass

    h1.printAll()
    #write_data(h1, search_term_data, additional_data, file_name)
    driver.close()
    return data