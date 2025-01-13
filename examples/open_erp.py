import requests
import webbrowser
import os, sys
rootDir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(rootDir)
from iitkgp_erp.urls import HOMEPAGE_URL
from iitkgp_erp.erp import login
from erpcreds_local import erpcreds # Comment this line and uncomment the next line to use the erpcreds.py file
# from erpcreds import erpcreds

def open_erp(erpcreds: dict, log: bool = False, session: requests.Session = None, headers: dict = None, gmailAuto: bool = False):
    _, ssoToken, error = login(log, session, erpcreds, headers, gmailAuto)
    if error is not None:
        if log:
            print(error)
        return False
    if log:
        print("Opening ERP")
    logged_in_url = f"{HOMEPAGE_URL}?ssoToken={ssoToken}"
    print(logged_in_url)
    try:
        webbrowser.open(logged_in_url)
    except:
        if log:
            print("Error in opening ERP")
        return False
    if log:
        print("ERP opened")
    return True

if __name__ == "__main__":
    open_erp(log=True, erpcreds=erpcreds, gmailAuto=True)