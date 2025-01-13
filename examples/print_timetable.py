import requests
import os, sys
rootDir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(rootDir)
from erpcreds_local import erpcreds
from iitkgp_erp.timetable import getTimeTable
from iitkgp_erp.result import useXL

s = requests.Session()

error = getTimeTable(s, erpcreds=erpcreds, log=True)
if error:
    print(error)
    exit(1)

useXL()