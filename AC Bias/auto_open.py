import time
from selenium import webdriver

url = "G:/rhoover/python/Code/ccdm/AC%20Bias/Output/ACBIAS_example.html"
driver = webdriver.Chrome()
driver.get(url)

try:
    while True:
        time.sleep(5)
        driver.refresh()
except KeyboardInterrupt:
    print("Ending Auto-Refresh")
