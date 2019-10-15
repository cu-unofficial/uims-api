import requests
from bs4 import BeautifulSoup
import json

from .exceptions import IncorrectCredentialsError

BASE_URL = "https://uims.cuchd.in"
AUTHENTICATE_URL = BASE_URL + "/uims/"

ENDPOINTS = {"Attendance": "frmStudentCourseWiseAttendanceSummary.aspx"}


class SessionUIMS:
    def __init__(self, uid, password):
        self._uid = uid
        self._password = password
        self.cookies = None
        self.refresh_session()

        self._attendance = None

    def _login(self):
        response = requests.get(AUTHENTICATE_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        viewstate_tag = soup.find("input", {"name":"__VIEWSTATE"})

        data = {"__VIEWSTATE": viewstate_tag["value"],
                "txtUserId": self._uid,
                "btnNext": "NEXT"}

        response = requests.post(AUTHENTICATE_URL,
                                 data=data,
                                 cookies=response.cookies,
                                 allow_redirects=False)

        soup = BeautifulSoup(response.text, "html.parser")

        password_url = BASE_URL + response.headers["location"]
        response = requests.get(password_url, cookies=response.cookies)
        login_cookies = response.cookies
        soup = BeautifulSoup(response.text, "html.parser")
        viewstate_tag = soup.find("input", {"name":"__VIEWSTATE"})

        data = {"__VIEWSTATE": viewstate_tag["value"],
                "txtLoginPassword": self._password,
                "btnLogin": "LOGIN"}

        response = requests.post(password_url,
                                 data=data,
                                 cookies=response.cookies,
                                 allow_redirects=False)

        incorrect_credentials = response.status_code == 200
        if incorrect_credentials:
            raise IncorrectCredentialsError("Make sure UID and Password are correct.")

        aspnet_session_cookies = response.cookies

        login_and_aspnet_session_cookies = requests.cookies.merge_cookies(login_cookies, aspnet_session_cookies)
        return login_and_aspnet_session_cookies

    def refresh_session(self):
        self.cookies = self._login()

    @property
    def attendance(self):
        if self._attendance is None:
            self._attendance = self._get_attendance()

        return self._attendance

    def _get_attendance(self):
        attendance_url = AUTHENTICATE_URL + ENDPOINTS["Attendance"]

        response = requests.get(attendance_url, cookies=self.cookies)
        js_report_block = response.text.find("getReport")
        initial_quotation_mark = js_report_block + response.text[js_report_block:].find("'")
        ending_quotation_mark = initial_quotation_mark + response.text[initial_quotation_mark+1:].find("'")
        report_id = response.text[initial_quotation_mark+1 : ending_quotation_mark+1]

        report_url = attendance_url + "/GetReport"
        headers = {'Content-Type': 'application/json'}
        data = "{UID:'" + report_id + "',Session:'19201'}"
        response = requests.post(report_url, headers=headers, data=data)

        attendance = json.loads(response.text)["d"]
        return json.loads(attendance)
