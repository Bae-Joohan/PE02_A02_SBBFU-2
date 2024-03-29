from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
from dateutil.parser import parse
from lmfit import Model
from numpy import exp
import statsmodels.api as sm
import os
import warnings
warnings.filterwarnings(action='ignore')

def poly(x, y, degree):
    coeffs = np.polyfit(x, y, degree)
    # r-squared
    p = np.poly1d(coeffs)
    yhat = p(x)
    ybar = np.sum(y) / len(y)  # or sum(y)/len(y)
    ssreg = np.sum((yhat - ybar) ** 2)  # or sum([ (yihat - ybar)**2 for yihat in yhat])
    sstot = np.sum((y - ybar) ** 2)  # or sum([ (yi - ybar)**2 for yi in y])
    results = ssreg / sstot
    return results

def csv_mod(filename):

    fp = open(filename, "r")
    soup = BeautifulSoup(fp, "html.parser")

    voltage = soup.findAll('voltage')[0].string.split(',')
    current = soup.findAll('current')[0].string.split(',')

    x = list(map(float, voltage))
    y = list(map(float, current))
    y = np.abs(y)

    # 2번째 그래프

    C = np.array(y[:10])
    V = np.array(x[:10])
    fit1 = np.polyfit(V, C, 11)
    fit1 = np.poly1d(fit1)

    # I = a(exp(bV-1)+alpha
    def IV_fit(x, a, b):
        return (a * (exp(b * x) - 1) + fit1(x))

    model = Model(IV_fit)
    result = model.fit(y, x=x, a=10e-16, b=1 / 0.026)

    initial_list = []
    for i in x:
        x_value = IV_fit(i, 10e-16, 1 / 0.026)
        initial_list.append(x_value)

    initial = sm.add_constant(np.abs(y))
    result1 = sm.OLS(initial_list, initial).fit()
    IVdic = {y: x for x, y in zip(result.best_fit, x)}
    refx = list(map(float, soup.findAll('l')[6].string.split(',')))
    refy = list(map(float, soup.findAll('il')[6].string.split(',')))

    Rsqref = poly(refx, refy, 6)

    Lot = soup.select('testsiteinfo')[0]['batch']
    Wafer = soup.select('testsiteinfo')[0]['wafer']
    Mask = soup.select('testsiteinfo')[0]['maskset']
    Column = soup.select('testsiteinfo')[0]['diecolumn']
    Row = soup.select('testsiteinfo')[0]['dierow']
    TestSite = soup.select('testsiteinfo')[0]['testsite']
    Name = soup.select("modulator")[0]['name']

    Date = soup.select('oiomeasurement')[0]['creationdate']
    Date = parse(Date).strftime("%Y%m%d_%H%M%S")

    error_flag_list = []
    error_description = []
    WL_list = []
    Rsq = result1.rsquared
    if Rsq < 0.95:
        error_flag_list.append(1)
        error_description.append('Rsq error')
    else:
        error_flag_list.append(0)
        error_description.append('No error')

    WL_analy = soup.findAll('designparameter')
    for k in range(0, len(WL_analy)):
        if WL_analy[k]['symbol'] == 'WL':
            WL_list.append(WL_analy[k].text)

    df = pd.DataFrame(columns=['Lot', 'Wafer', 'Mask', 'TestSite' , 'Name', 'Date', 'Script ID',
     'Script Version', 'Script Owner', 'Operator', 'Row','Column',
     'ErrorFlag', 'Error description','Analysis Wavelength', 'Rsq of Ref.spectrum (Nth)',
     'Max transmission of Ref. spec. (dB)', 'Rsq of IV', 'I at -1V [A]', 'I at 1V [A]'])

    df.loc[0] = [Lot, Wafer, Mask, TestSite, Name, Date,'process LMZ', '0.1', 'A02' ,'JoohanBae',Row, Column, error_flag_list[0],
                 error_description[0], WL_list[0], Rsqref, max(refy), Rsq, IVdic[-1.0],IVdic[1.0]]
