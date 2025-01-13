import requests
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
from urls import WELCOMEPAGE_URL, LOGIN_URL, SECRET_QUESTION_URL, OTP_URL, HOMEPAGE_URL
from erp_responses import ANSWER_MISMATCH_ERROR, PASSWORD_MISMATCH_ERROR, OTP_SENT_MESSAGE, OTP_MISMATCH_ERROR
from bs4 import BeautifulSoup as bs

headers = {
    'timeout': '20',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/51.0.2704.79 Chrome/51.0.2704.79 Safari/537.36',
}

def session_alive(session):
    try:
        resp = session.get(WELCOMEPAGE_URL)
        if resp.headers.get("Content-Length") == "1034":
            return True
        else:
            return False
    except:
        return False

def get_session_token(session: requests.Session, log: bool = False):
    if log:
        print("getting session token")
    resp = session.get(HOMEPAGE_URL)
    if resp.status_code != 200:
        if log:
            print("Error in getting session token")
        return None
    soup = bs(resp.content, 'html.parser')
    sessionToken = soup.find("input", {"name": "sessionToken"}).get("value")
    if log:
        print("Session token received")
    return sessionToken

def login(log: bool = False, session: requests.Session = None, erpcreds: dict = None, headers: dict = None, gmailAuto: bool = False):
    print("log - ", log)
    s = requests.Session()
    if session is not None:
        s = session
    if session_alive(s):
        if log:
            print("Session is alive")
            ssoToken = s.cookies.get("ssoToken")
            sessionToken = get_session_token(s, log)
        return sessionToken, ssoToken, None
    else:
        if log:
            print("Session is dead, logging in again")
    if log:
        print("sending request for secret question")
    resp = s.post(SECRET_QUESTION_URL, data={"user_id": erpcreds["ROLL_NUMBER"]}, headers=headers)
    if resp.status_code != 200 or resp.text == "":
        if log:
            print("Error in sending request for secret question")
        return None, None, "Error Logging in : Error in sending request for secret question"
    if log:
        print("Secret question received")
    question = resp.text
    answer = ""
    sessionToken = get_session_token(s, log)
    for q in erpcreds["SECURITY_QUESTIONS_ANSWERS"]:
        if q["question"] == question:
            answer = q["answer"]
            break
    if answer == "":
        if log:
            print("Security question not found ", question)
        return None, None, "Error Logging in : Security question not found"
    otp_req_data = {
        "user_id": erpcreds["ROLL_NUMBER"],
        "password": erpcreds["PASSWORD"],
        "answer": answer,
        "typeee": "SI",
        "email_otp": "",
        "sessionToken": sessionToken,
        "requestedUrl": "https://erp.iitkgp.ac.in/IIT_ERP3/"
    }
    otp_resp = s.post(OTP_URL, data=otp_req_data, headers=headers)
    if PASSWORD_MISMATCH_ERROR in otp_resp.text:
        if log:
            print("Password mismatch")
        return None, None, "Error Logging in : Password mismatch"
    elif ANSWER_MISMATCH_ERROR in otp_resp.text:
        if log:
            print("Answer mismatch for the security question", question)
        return None, None, "Answer mismatch for the security question", question
    otp_resp_text = otp_resp.text.strip('{').strip('}').split(':')[1].strip('"')
    if otp_resp_text != OTP_SENT_MESSAGE:
        if log:
            print("OTP not sent")
        return None, None, "Error Logging in : OTP not sent"
    else:
        if log:
            print("OTP sent")
    # otp = ""
    # if gmailAuto:
        # Gmail auto
    # else:
        # otp = input("Enter OTP: ")
    otp = input("Enter OTP: ")
    otp_verify_data = {
        "user_id": erpcreds["ROLL_NUMBER"],
        "password": erpcreds["PASSWORD"],
        "answer": answer,
        "typeee": "SI",
        "email_otp": otp,
        "sessionToken": sessionToken,
        "requestedUrl": "https://erp.iitkgp.ac.in/IIT_ERP3/"
    }
    if log:
        print("Verifying OTP")
    otp_verify_resp = s.post(LOGIN_URL, data=otp_verify_data, headers=headers)
    if(OTP_MISMATCH_ERROR in otp_verify_resp.text):
        if log:
            print("OTP mismatch")
        return None, None, "Error Logging in : OTP mismatch"
    if log:
        print("OTP verified")
    ssoToken = otp_verify_resp.history[1].headers["Location"].split("/")[-1].split("=")[-1]
    set_cookie(s, "ssoToken", ssoToken)
    return sessionToken, ssoToken, None

def set_cookie(session: requests.Session, cookie_name: str, cookie_value: str, **kwargs):
    session.cookies.set(cookie_name, cookie_value, domain='erp.iitkgp.ac.in', **kwargs)