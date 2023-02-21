from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
import time
import datetime

def get_file_content_chrome(driver, uri):
  result = driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
    """, uri)
  if type(result) == int :
    raise Exception("Request failed with status %s" % result)
  return base64.b64decode(result)


today = datetime.datetime.today().strftime('%Y%m%d')

options = Options()
options.add_experimental_option('detach', True)
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument("headless")
driver = webdriver.Chrome('chromedriver', options=options)
actions = ActionChains(driver)
# wait = driver.implicitly_wait(10)

url = 'https://www.cboe.com/delayed_quotes/spx/quote_table'
driver.get(url)

time.sleep(10)
# button = WebDriverWait(driver, 10).until(EC.presence_of_element_located(By.XPATH, "/html/body/main/section[1]/div/div/div/div/div[2]/div[2]/div[2]/div[2]/div[3]/div/div[2]/div/div/div/div[1]/div[1]"))

option_range_button = driver.find_element(By.XPATH, "/html/body/main/section[1]/div/div/div/div/div[2]/div[2]/div[2]/div[2]/div[3]/div/div[2]/div/div/div/div[1]/div[1]")
# option_range_button.click()
# actions.click(option_range_button).perform()
# option_range_all = driver.find_element(By.XPATH, "//*[text()='All']")
# driver.execute_script("arguments[0].scrollIntoView();", option_range_all)
# actions.move_to_element(option_range_button).perform()
driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'})", option_range_button);
actions.click(option_range_button).send_keys(Keys.UP).send_keys(Keys.ENTER).perform()

expiration_button = driver.find_element(By.XPATH, "/html/body/main/section[1]/div/div/div/div/div[2]/div[2]/div[2]/div[2]/div[4]/div/div[2]/div/div/div/div[1]")
# actions.click(expiration_button).perform()
# expiration_all = driver.find_element(By.XPATH, "//*[text()='All']")
# driver.execute_script("arguments[0].scrollIntoView();", expiration_all)
actions.click(expiration_button).send_keys(Keys.UP).send_keys(Keys.ENTER).perform()

view_button = driver.find_element(By.XPATH, "/html/body/main/section[1]/div/div/div/div/div[2]/div[2]/div[2]/div[2]/div[5]/div/button/span")
view_button.click()

# time.sleep(5)

source = driver.page_source
download_blob = "blob:" + source.split("blob:")[1].split("\"")[0]
spx_option_csv = get_file_content_chrome(driver, download_blob)
spx_option_csv_fpath = f"option/spx_{today}.csv"

with open(spx_option_csv_fpath, 'wb') as f:
    f.write(spx_option_csv)


###############

import pandas as pd
import numpy as np
import scipy
from scipy.stats import norm
import matplotlib.pyplot as plt
from datetime import timedelta

pd.options.display.float_format = '{:,.4f}'.format

# Inputs and Parameters
filename = spx_option_csv_fpath

# Black-Scholes European-Options Gamma
def calcGammaEx(S, K, vol, T, r, q, optType, OI):
    if T == 0 or vol == 0:
        return 0

    dp = (np.log(S/K) + (r - q + 0.5*vol**2)*T) / (vol*np.sqrt(T))
    dm = dp - vol*np.sqrt(T)

    if optType == 'call':
        gamma = np.exp(-q*T) * norm.pdf(dp) / (S * vol * np.sqrt(T))
        return OI * 100 * S * S * 0.01 * gamma
    else: # Gamma is same for calls and puts. This is just to cross-check
        gamma = K * np.exp(-r*T) * norm.pdf(dm) / (S * S * vol * np.sqrt(T))
        return OI * 100 * S * S * 0.01 * gamma

def isThirdFriday(d):
    return d.weekday() == 4 and 15 <= d.day <= 21

# This assumes the CBOE file format hasn't been edited, i.e. table beginds at line 4
optionsFile = open(filename)
optionsFileData = optionsFile.readlines()
optionsFile.close()

# Get SPX Spot
spotLine = optionsFileData[1]
spotPrice = float(spotLine.split('Last:')[1].split(',')[0])
fromStrike = 0.8 * spotPrice
toStrike = 1.2 * spotPrice

# Get Today's Date - Korean Ver.
# dateLine = optionsFileData[2]
# todayDate = dateLine.split('Date: ')[1].split(',')
# monthDay = todayDate[0].split(' ')
#
# year = int(monthDay[0][:-1])
# month = int(monthDay[1][:-1])
# day = int(monthDay[2][:-1])
# todayDate = date(year, month, day)

todayDate = datetime.date.today()

# Get SPX Options Data
df = pd.read_csv(filename, sep=",", header=None, skiprows=4)
df.columns = ['ExpirationDate','Calls','CallLastSale','CallNet','CallBid','CallAsk','CallVol',
              'CallIV','CallDelta','CallGamma','CallOpenInt','StrikePrice','Puts','PutLastSale',
              'PutNet','PutBid','PutAsk','PutVol','PutIV','PutDelta','PutGamma','PutOpenInt']

df['ExpirationDate'] = pd.to_datetime(df['ExpirationDate'], format='%a %b %d %Y')
df['ExpirationDate'] = df['ExpirationDate'] + timedelta(hours=16)
df['StrikePrice'] = df['StrikePrice'].astype(float)
df['CallIV'] = df['CallIV'].astype(float)
df['PutIV'] = df['PutIV'].astype(float)
df['CallGamma'] = df['CallGamma'].astype(float)
df['PutGamma'] = df['PutGamma'].astype(float)
df['CallOpenInt'] = df['CallOpenInt'].astype(float)
df['PutOpenInt'] = df['PutOpenInt'].astype(float)


# ---=== CALCULATE SPOT GAMMA ===---
# Gamma Exposure = Unit Gamma * Open Interest * Contract Size * Spot Price
# To further convert into 'per 1% move' quantity, multiply by 1% of spotPrice
df['CallGEX'] = df['CallGamma'] * df['CallOpenInt'] * 100 * spotPrice * spotPrice * 0.01
df['PutGEX'] = df['PutGamma'] * df['PutOpenInt'] * 100 * spotPrice * spotPrice * 0.01 * -1

df['TotalGamma'] = (df.CallGEX + df.PutGEX) / 10**9
dfAgg = df.groupby(['StrikePrice']).sum()
strikes = dfAgg.index.values

# Chart 1: Absolute Gamma Exposure
plt.grid()
plt.bar(strikes, dfAgg['TotalGamma'].to_numpy(), width=6, linewidth=0.1, edgecolor='k', label="Gamma Exposure")
plt.xlim([fromStrike, toStrike])
chartTitle = "Total Gamma: $" + str("{:.2f}".format(df['TotalGamma'].sum())) + " Bn per 1% SPX Move"
plt.title(chartTitle, fontweight="bold", fontsize=15)
plt.xlabel('Strike', fontweight="bold")
plt.ylabel('Spot Gamma Exposure ($ billions/1% move)', fontweight="bold")
plt.axvline(x=spotPrice, color='r', lw=1, label="SPX Spot: " + str("{:,.0f}".format(spotPrice)))
plt.legend()
plt.savefig(f'figure/gamma_exposure_profile_{today}_0.png')

# Chart 2: Absolute Gamma Exposure by Calls and Puts
plt.grid()
plt.bar(strikes, dfAgg['CallGEX'].to_numpy() / 10**9, width=6, linewidth=0.1, edgecolor='k', label="Call Gamma")
plt.bar(strikes, dfAgg['PutGEX'].to_numpy() / 10**9, width=6, linewidth=0.1, edgecolor='k', label="Put Gamma")
plt.xlim([fromStrike, toStrike])
chartTitle = "Total Gamma: $" + str("{:.2f}".format(df['TotalGamma'].sum())) + " Bn per 1% SPX Move"
plt.title(chartTitle, fontweight="bold", fontsize=15)
plt.xlabel('Strike', fontweight="bold")
plt.ylabel('Spot Gamma Exposure ($ billions/1% move)', fontweight="bold")
plt.axvline(x=spotPrice, color='r', lw=1, label="SPX Spot:" + str("{:,.0f}".format(spotPrice)))
plt.legend()
plt.savefig(f'figure/gamma_exposure_profile_{today}_1.png')


# ---=== CALCULATE GAMMA PROFILE ===---
levels = np.linspace(fromStrike, toStrike, 60)

# For 0DTE options, I'm setting DTE = 1 day, otherwise they get excluded
df['daysTillExp'] = [1/252 if (np.busday_count(todayDate, x.date())) == 0 \
                           else np.busday_count(todayDate, x.date())/252 for x in df.ExpirationDate]

nextExpiry = df['ExpirationDate'].min()

df['IsThirdFriday'] = [isThirdFriday(x) for x in df.ExpirationDate]
thirdFridays = df.loc[df['IsThirdFriday'] == True]
nextMonthlyExp = thirdFridays['ExpirationDate'].min()

totalGamma = []
totalGammaExNext = []
totalGammaExFri = []

# For each spot level, calc gamma exposure at that point
for level in levels:
    df['callGammaEx'] = df.apply(lambda row : calcGammaEx(level, row['StrikePrice'], row['CallIV'],
                                                          row['daysTillExp'], 0, 0, "call", row['CallOpenInt']), axis = 1)

    df['putGammaEx'] = df.apply(lambda row : calcGammaEx(level, row['StrikePrice'], row['PutIV'],
                                                         row['daysTillExp'], 0, 0, "put", row['PutOpenInt']), axis = 1)

    totalGamma.append(df['callGammaEx'].sum() - df['putGammaEx'].sum())

    exNxt = df.loc[df['ExpirationDate'] != nextExpiry]
    totalGammaExNext.append(exNxt['callGammaEx'].sum() - exNxt['putGammaEx'].sum())

    exFri = df.loc[df['ExpirationDate'] != nextMonthlyExp]
    totalGammaExFri.append(exFri['callGammaEx'].sum() - exFri['putGammaEx'].sum())

totalGamma = np.array(totalGamma) / 10**9
totalGammaExNext = np.array(totalGammaExNext) / 10**9
totalGammaExFri = np.array(totalGammaExFri) / 10**9

# Find Gamma Flip Point
zeroCrossIdx = np.where(np.diff(np.sign(totalGamma)))[0]

negGamma = totalGamma[zeroCrossIdx]
posGamma = totalGamma[zeroCrossIdx+1]
negStrike = levels[zeroCrossIdx]
posStrike = levels[zeroCrossIdx+1]

zeroGamma = posStrike - ((posStrike - negStrike) * posGamma/(posGamma-negGamma))
zeroGamma = zeroGamma[0]

# Chart 3: Gamma Exposure Profile
fig, ax = plt.subplots()
plt.grid()
plt.plot(levels, totalGamma, label="All Expiries")
plt.plot(levels, totalGammaExNext, label="Ex-Next Expiry")
plt.plot(levels, totalGammaExFri, label="Ex-Next Monthly Expiry")
chartTitle = "Gamma Exposure Profile, SPX, " + todayDate.strftime('%d %b %Y')
plt.title(chartTitle, fontweight="bold", fontsize=15)
plt.xlabel('Index Price', fontweight="bold")
plt.ylabel('Gamma Exposure ($ billions/1% move)', fontweight="bold")
plt.axvline(x=spotPrice, color='r', lw=1, label="SPX Spot: " + str("{:,.0f}".format(spotPrice)))
plt.axvline(x=zeroGamma, color='g', lw=1, label="Gamma Flip: " + str("{:,.0f}".format(zeroGamma)))
plt.axhline(y=0, color='grey', lw=1)
plt.xlim([fromStrike, toStrike])
trans = ax.get_xaxis_transform()
plt.fill_between([fromStrike, zeroGamma], min(totalGamma), max(totalGamma), facecolor='red', alpha=0.1, transform=trans)
plt.fill_between([zeroGamma, toStrike], min(totalGamma), max(totalGamma), facecolor='green', alpha=0.1, transform=trans)
plt.legend()
plt.savefig(f'figure/gamma_exposure_profile_{today}_2.png')
