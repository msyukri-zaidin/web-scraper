import time
from datetime import datetime
import re
import os
import sys
import csv
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from joblib import Parallel, delayed, parallel_backend
from dotenv import load_dotenv
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class House:
    def __init__(self):
        self.num_bedroom = 'NA'
        self.num_bathroom = 'NA'
        self.num_garage = 'NA'
        self.floor_area = 'NA'
        self.land_area = 'NA'
        #self.building_type = 'NA'
        self.yr_built = 'NA'
        #self.primary_use = 'NA'
        self.last_sold_date = 'NA'
        self.last_sold_price = 'NA'
        self.land_price = 'NA'
    
    def toList(self):
        attribute_list = [self.num_bedroom, self.num_bathroom, self.num_garage, 
                        self.floor_area, self.land_area, self.yr_built,
                        self.last_sold_date, self.last_sold_price, self.land_price]
        return attribute_list

    def toDict(self):
        attribute_dict = {
            'bedrooms': self.num_bedroom,
            'bathrooms': self.num_bathroom,
            'garage': self.num_garage,
            'land_area': self.land_area,
            'floor_area': self.floor_area,
            'year_built': self.yr_built,
            'last_sold_date': self.last_sold_date,
            'last_sold_price': self.last_sold_price,
            'land_price': self.land_price,
            'status':True

        }
        return attribute_dict

    def printAll(self):
        print("Bedrooms: ", self.num_bedroom)
        print("Bathrooms: ", self.num_bathroom)
        print("Garages: ", self.num_garage)
        print("Land Area: ", self.land_area)
        print("Floor Area: ", self.floor_area)
        print("Year Built: ", self.yr_built)
        print("Last Sold Date: ", self.last_sold_date)
        print("Last Sold Price: ", self.last_sold_price)
        print("Land Price: ", self.land_price)

def main(argv):
    if argv[0] == '-p' and len(argv) == 2:
        #Check proxy
        Parallel(n_jobs=int(argv[1]))(delayed(manual_proxy_check)(i) for i in range(1, int(argv[1]) + 1))
        return
    if len(argv) < 2:
        print("ERROR: No arguments\nUsage: python scraper.py [file name] [number of processor(s)]")
        return
    elif len(argv) > 2:
        print("ERROR: Too many arguments\nUsage: python scraper.py [file name] [number of processor(s)]")
        return
    
    file_name = argv[0].replace('.csv', '')
    num_cores = int(argv[1])

    CWD = os.getcwd()
    files = []
    CWD += '/address_data/'
    for i in range(1, num_cores + 1):
        files.append(CWD + file_name + '_part_' + str(i) + '.csv')

    Parallel(n_jobs=num_cores)(delayed(get_addresses)(file_name, process_index) for process_index, file_name in enumerate(files, 1))

# Checks that proxies are working
def manual_proxy_check(num):
    options = webdriver.ChromeOptions()

    #User/PW Authenticated Proxies
    options.add_extension(os.getenv("PROXY_FILE"))

    prefs={"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option('prefs', prefs)
    prefs = {'disk-cache-size': 4096}
    options.add_experimental_option('prefs', prefs)
    caps = DesiredCapabilities().CHROME.copy()
    caps["pageLoadStrategy"] = "eager"
    options.add_argument("user-data-dir=" + os.getenv("USER_DATA_DIR") + str(num))
    options.add_argument("profile-directory=Profile_1")
    options.add_argument('start-maximized')

    driver = webdriver.Chrome(desired_capabilities = caps, options=options)
    url = 'http://lumtest.com/myip.json'
    driver.get(url)
    body = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '/html/body'))
    )
    print(body.text)
    driver.quit()
    return

def get_addresses(file_name, process_index):
    with open(file_name, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        for line_number, line in enumerate(reader):
            if process_index == 1:
                print("On line: ", line_number)
            if line_number == 0: #Ignore header
                continue
            else:
                search_term_data = line[:-4]
                additional_data = line[-4:]
                scrape(search_term_data, additional_data, file_name, process_index)

def scrape(search_term_data, additional_data, file_name, process_index): 
    #Configure options
    options = webdriver.ChromeOptions()

    #User/PW Authenticated Proxies
    options.add_extension(os.getenv("PROXY_FILE"))
    
    options.add_argument('start-maximized')
    prefs={"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option('prefs', prefs)
    prefs = {'disk-cache-size': 4096}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("user-data-dir=" + os.getenv("USER_DATA_DIR") + str(process_index))
    options.add_argument("profile-directory=Profile_1")

    url = 'https://www.propertyvalue.com.au/'
    caps = DesiredCapabilities().CHROME.copy()
    caps["pageLoadStrategy"] = "eager"
    driver = webdriver.Chrome(desired_capabilities=caps, options=options)

    # Initiate URL
    try:
        driver.get(url)
    except TimeoutException as toe:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return
    
    #Accept Cookie Button
    '''try:
        cookie_button = WebDriverWait(driver,10).until(
            EC.presence_of_element_located((By.ID, 'acceptCookieButton'))
        )
    except TimeoutException as toe:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return
    cookie_button.click()'''

    # Input address details
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'propertysearch'))
        )
    except TimeoutException as toe:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return

    # Initiate Enter button
    try:
        inputElement = driver.find_element_by_id("propertysearch")
        inputElement.send_keys(' '.join(search_term_data))
        inputElement.send_keys(Keys.ENTER)
    except NoSuchElementException as nse:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return

    # Inital page loading wait
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="paddress"]/span[1]'))
        )
    except TimeoutException as toe:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return

    h1 = House()
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="property-insights"]/div[3]/div[1]/div[1]/div'))
        )
    except TimeoutException as toe:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return

    try:
        property_details = driver.find_element_by_xpath('//*[@id="property-insights"]/div[3]/div[1]/div[1]/div').text.split('\n')
    except NoSuchElementException as nse:
        skipped(search_term_data, process_index, file_name)
        driver.quit()
        return

    # Get property details
    for item in property_details:
        if "Bedrooms" in item:
            h1.num_bedroom = re.sub("\D", "", item)
        elif "Bathrooms" in item:
            h1.num_bathroom = re.sub("\D", "", item)
        elif "Car Spaces" in item:
            h1.num_garage = re.sub("\D", "", item)
        elif "Land Size" in item:
            h1.land_area = re.sub("[a-zA-Z ]", "", item.strip('m2'))
        elif "Floor Area" in item:
            h1.floor_area = re.sub("[a-zA-Z ]", "", item.strip('m2'))
        elif "Year Built" in item:
            try:
                h1.yr_built = int(re.sub("\D", "", item))
            except:
                h1.yr_built = 'NA'

    # Wait to ensure next line of details are loaded
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="property-insights"]/div[2]/div[1]/div[2]/div[1]/div[1]/p[1]'))
        )
    except TimeoutException as toe:
        driver.quit()
        write_data(h1, search_term_data, additional_data, file_name)        
        return
    
    try:
        sale_details = driver.find_element_by_xpath('//*[@id="property-insights"]/div[2]/div[1]/div[2]/div[1]/div[1]/p[1]').text.strip("Last sold for").split(" on ")
    except NoSuchElementException as nse:
        driver.quit()
        write_data(h1, search_term_data, additional_data, file_name)
        return

    # Get property sale details
    sale_date_obj = datetime.strptime(sale_details[1], '%d/%m/%Y')
    if h1.yr_built == 'NA':
        h1.land_price = sale_details[0].strip(',')
    elif h1.yr_built >= sale_date_obj.year : #If built after last sold, then the last sold price is the price of land
        h1.land_price = sale_details[0].strip(',')
    else:
        h1.last_sold_price = sale_details[0].strip(',')
    h1.last_sold_date = sale_details[1]
    driver.quit()
    write_data(h1, search_term_data, additional_data, file_name)
    #h1.printAll()
    return

#Addresses that were skipped are printed into a .txt file
def skipped(search_term_data, process_index, file_name):
    with open('address_data/' +  file_name +'_skipped' + str(process_index) + '.txt', 'a+') as f:
        f.write(' '.join(e.strip('\r') for e in search_term_data) + '\n')
    return

def write_data(h1, search_term_data, additional_data, file_name):
    file_name = re.sub('[.]', '_result.', file_name)
    with open(file_name, 'a+', newline='') as csv_write_file:
        writer = csv.writer(csv_write_file, delimiter=',')
        writer.writerow(search_term_data + additional_data + h1.toList())
    return


if __name__ == '__main__':
    start_time = time.time()
    main(sys.argv[1:])
    print("--- %s seconds ---" % (time.time() - start_time))
