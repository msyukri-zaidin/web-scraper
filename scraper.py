from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime
import re
import os
from pathlib import Path
#from django.conf import settings #For Django app
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
        #self.nearest_pri = 'NA'
        #self.nearest_pri_dist = 'NA'
        #self.nearest_sec = 'NA'
        #self.nearest_sec_dist = 'NA'

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

def scrape(search_term_data):
    #Configure timer
    start_time = time.time()

    #Configure options
    options = webdriver.ChromeOptions()
    PROXY = 'au.smartproxy.com:30000' #Residential
    options.add_argument('--proxy-server=%s' % PROXY)
    options.add_argument('--disable-extensions')

    #User/PW Authenticated Proxies
    #options.add_extension("proxy.zip") #Residential
    #options.add_extension(os.path.abspath("proxy_pp.zip"))
    
    options.add_argument('start-maximized')
    prefs={"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option('prefs', prefs)
    prefs = {'disk-cache-size': 4096}
    options.add_experimental_option('prefs', prefs)
    #options.add_experimental_option("prefs", {"profile.default_content_setting_values.cookies": 2}) #Disables cookies
    #options.add_argument("user-data-dir=" + settings.USER_DATA_DIR) #For Django webapp
    options.add_argument("user-data-dir=" + os.getenv("USER_DATA_DIR"))
    options.add_argument("profile-directory=Profile_1")

    url = 'https://www.propertyvalue.com.au/'
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "eager"
    driver = webdriver.Chrome(desired_capabilities=caps, options=options)

    try:
        driver.get(url)
    except Exception as exc:
        print(exc)
        return {'status':False}

    #Input
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'propertysearch'))
        )
    except Exception as exc:
        print(exc)
        driver.close()
        return {'status':False}
    inputElement = driver.find_element_by_id("propertysearch")
    inputElement.send_keys(search_term_data)
    inputElement.send_keys(Keys.ENTER)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="paddress"]/span[1]'))
        )
    except Exception as exc:
        print(exc)
        driver.close()
        return {'status':False}

    h1 = House()
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="property-insights"]/div[3]/div[1]/div[1]/div'))
        )
    except Exception as exc:
        print(exc)
        driver.close()
        return {'status':False}
    #print(driver.find_element_by_xpath('//*[@id="property-insights"]/div[3]/div[1]/div[1]/div').text)
    property_details = driver.find_element_by_xpath('//*[@id="property-insights"]/div[3]/div[1]/div[1]/div').text.split('\n')
    for item in property_details:
        if "Bedrooms" in item:
            h1.num_bedroom = re.sub("\D", "", item)
        elif "Bathrooms" in item:
            h1.num_bathroom = re.sub("\D", "", item)
        elif "Car Spaces" in item:
            h1.num_garage = re.sub("\D", "", item)
        elif "Land Size" in item:
            h1.land_area = re.sub("\D", "", item.strip('m2'))
        elif "Floor Area" in item:
            h1.floor_area = re.sub("\D", "", item.strip('m2'))
        elif "Year Built" in item:
            h1.yr_built = int(re.sub("\D", "", item))

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="property-insights"]/div[2]/div[1]/div[2]/div[1]/div[1]/p[1]'))
        )
    except Exception as exc:
        print(exc)
        driver.close()
        return h1.toDict()
    sale_details = driver.find_element_by_xpath('//*[@id="property-insights"]/div[2]/div[1]/div[2]/div[1]/div[1]/p[1]').text.strip("Last sold for").split(" on ")
    sale_date_obj = datetime.strptime(sale_details[1], '%d/%m/%Y')
    if h1.yr_built >= sale_date_obj.year : #If built after last sold, then the last sold price is the price of land
        h1.land_price = sale_details[0]
    else:
        h1.last_sold_price = sale_details[0]
    h1.last_sold_date = sale_details[1]
    h1.printAll()
    driver.close()
    print("--- %s seconds ---" % (time.time() - start_time))
    return h1.toDict()

if __name__ == '__main__':
    scrape('10 hutt way gosnells wa 6110')
