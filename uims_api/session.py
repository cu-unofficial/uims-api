import requests
from bs4 import BeautifulSoup
import json
import re
import pytesseract
from .exceptions import ApiLoginFailureError, UIMSInternalError
from PIL import Image
from io import BytesIO

AUTHENTICATE_URL = "https://students.cuchd.in/"

ENDPOINTS = {
    "Attendance": "frmStudentCourseWiseAttendanceSummary.aspx",
    "Timetable": "frmMyTimeTable.aspx",
    "Profile": "StudentHome.aspx",
    "Marks": "frmStudentMarksView.aspx",
}
# Workaround fix for new url
ATTENDANCE_STATIC_EXTRA = "?type=etgkYfqBdH1fSfc255iYGw=="
ERROR_HEAD = "Whoops, Something broke!"
HEADERS = {"Content-Type": "application/json"}


class SessionUIMS:
    def __init__(self, uid, password):
        self._uid = uid
        self._password = password
        self.cookies = None
        self.refresh_session()

        self._attendance = None
        self._full_attendance = None
        self._timetable = None
        self._marks = None
        self._available_sessions = None
        self._report_id = None
        self._session_id = None
        self._full_name = None

    def _login(self):
        response = requests.get(AUTHENTICATE_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        viewstate_tag = soup.find("input", {"id": "__VIEWSTATE"})

        data = {
            "__VIEWSTATE": viewstate_tag["value"],
            "txtUserId": self._uid,
            "btnNext": "NEXT",
        }

        response = requests.post(
            AUTHENTICATE_URL, data=data, cookies=response.cookies, allow_redirects=False
        )
        soup = BeautifulSoup(response.text, "html.parser")
        password_url = AUTHENTICATE_URL + response.headers["location"]
        response = requests.get(password_url, cookies=response.cookies)
        login_cookies = response.cookies
        soup = BeautifulSoup(response.text, "html.parser")
        viewstate_tag = soup.find("input", {"name": "__VIEWSTATE"})
        view_state_generator_tag = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})

        captcha_img_source_str = soup.find("img", {"id": "imgCaptcha"}).attrs["src"]
        # get captcha image now
        response = requests.get(AUTHENTICATE_URL + captcha_img_source_str)
        captcha_answer = str(
            pytesseract.image_to_string(
                Image.open(BytesIO(response.content)), lang="eng"
            )
        )

        cleaned_captcha_answer = "".join(l for l in captcha_answer if l.isalnum())
        data = {
            "__VIEWSTATE": viewstate_tag["value"],
            "__VIEWSTATEGENERATOR": view_state_generator_tag["value"],
            "txtLoginPassword": self._password,
            "txtcaptcha": cleaned_captcha_answer,
            "btnLogin": "LOGIN",
        }
        login_and_aspnet_session_cookies = requests.cookies.merge_cookies(
            login_cookies, response.cookies
        )
        # final request, lets hit it
        response = requests.post(
            password_url,
            data=data,
            cookies=login_cookies,
            allow_redirects=False,
        )
        login_failure = response.status_code == 200
        if login_failure:
            raise ApiLoginFailureError(
                "Invalid login request sent to UIMS, check credentials or captcha"
            )
        return login_and_aspnet_session_cookies

    def refresh_session(self):
        self.cookies = self._login()

    @property
    def attendance(self):
        "Attendance for current session"
        if self._attendance is None:
            self._attendance = self._get_attendance()

        return self._attendance

    @property
    def full_name(self):
        "Full Name of user"
        if self._full_name is None:
            self._full_name = self._get_full_name()

        return self._full_name

    def _get_full_name(self):
        response = requests.get(
            AUTHENTICATE_URL + ENDPOINTS["Profile"], cookies=self.cookies
        )
        # Checking for error in response as status code returned is 200
        if response.text.find(ERROR_HEAD) != -1:
            raise UIMSInternalError("UIMS internal error occured")
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.find("div", {"class": "user-n-mob"}).get_text().strip()

    @property
    def available_sessions(self):
        "Dictionary of available sessions with current session as True"
        if self._available_sessions is None:
            self._available_sessions = self._get_available_sessions()
        return self._available_sessions

    def _get_available_sessions(self):
        marks_url = AUTHENTICATE_URL + ENDPOINTS["Marks"]

        response = requests.get(marks_url, cookies=self.cookies)
        # Checking for error in response as status code returned is 200
        if response.text.find(ERROR_HEAD) != -1:
            raise UIMSInternalError("UIMS internal error occured")
        soup = BeautifulSoup(response.text, "html.parser")
        select_tag = soup.find(
            "select",
            {"name": "ctl00$ContentPlaceHolder1$wucStudentMarksView$ddlCAndPSession"},
        )
        select_options = select_tag.findAll("option")
        sessions = {option["value"]: False for option in select_options}
        selected = select_tag.find("option", {"selected": True})
        sessions[selected["value"]] = True
        return sessions

    def marks(self, session):
        """
        Fetch marks for a session
        @session - Session value, available under available_sessions
        """
        if self._marks is None:
            self._marks = self._get_marks(session)
        return self._marks

    def _get_marks(self, session):
        marks_url = AUTHENTICATE_URL + ENDPOINTS["Marks"]

        response = requests.get(marks_url, cookies=self.cookies)
        # Checking for error in response as status code returned is 200
        if response.text.find(ERROR_HEAD) != -1:
            raise UIMSInternalError("UIMS internal error occured")
        soup = BeautifulSoup(response.text, "html.parser")
        viewstate_tag = soup.find("input", {"name": "__VIEWSTATE"})
        event_validation_tag = soup.find("input", {"name": "__EVENTVALIDATION"})
        data = {
            "__VIEWSTATE": viewstate_tag["value"],
            "__EVENTVALIDATION": event_validation_tag["value"],
            "ctl00$ContentPlaceHolder1$wucStudentMarksView$ddlCAndPSession": session,
        }
        response = requests.post(marks_url, data=data, cookies=self.cookies)

        return self._extract_marks(response)

    def _extract_marks(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        accordion = soup.find("div", {"id": "accordion"})

        subject_names = [i.get_text().strip() for i in accordion.findAll("h3")]
        divs = accordion.findAll("div")

        marks = []
        if len(subject_names) == len(divs):
            for i in range(0, len(divs)):
                obj = {}
                obj["name"] = subject_names[i]
                tbody_trs = divs[i].find("tbody").findAll("tr")
                sub_marks = []
                for tr in tbody_trs:
                    tds = tr.findAll("td")
                    fields = {
                        "element": tds[0].get_text().strip(),
                        "total": tds[1].get_text().strip(),
                        "obtained": tds[2].get_text().strip(),
                    }
                    sub_marks.append(fields)
                obj["marks"] = sub_marks
                marks.append(obj)
        return marks

    def _get_attendance(self):
        # The attendance URL looks like
        # https://uims.cuchd.in/UIMS/frmStudentCourseWiseAttendanceSummary.aspx
        attendance_url = AUTHENTICATE_URL + ENDPOINTS["Attendance"]

        # We make an authenticated GET request (by passing the login cookies) to fetch the
        # contents of the attendance page
        # These cookies contain encoded information about the current logged in UID whose
        # attendance information is to be fetched
        response = requests.get(
            attendance_url + ATTENDANCE_STATIC_EXTRA, cookies=self.cookies
        )
        # Checking for error in response as status code returned is 200
        if response.text.find(ERROR_HEAD) != -1:
            raise UIMSInternalError("UIMS internal error occured")
        # Getting current session id from response
        session_block = response.text.find("CurrentSession")
        session_block_origin = session_block + response.text[session_block:].find("(")
        session_block_end = session_block + response.text[session_block:].find(")")
        current_session_id = response.text[session_block_origin + 1 : session_block_end]

        if not self._session_id:
            self._session_id = current_session_id
        # We now scrape for the uniquely generated report ID for the current UIMS session
        # in the above returned response

        # I have no idea why and what purpose this report ID serves, but this field needed to
        # fetch the attendance in JSON format in the next step as you'll see, otherwise the
        # server will return an error response
        js_report_block = response.text.find("getReport")
        initial_quotation_mark = js_report_block + response.text[js_report_block:].find(
            "'"
        )
        ending_quotation_mark = initial_quotation_mark + response.text[
            initial_quotation_mark + 1 :
        ].find("'")
        report_id = response.text[
            initial_quotation_mark + 1 : ending_quotation_mark + 1
        ]

        if not self._report_id:
            self._report_id = report_id
        # On intercepting the requests made by my browser, I found that this URL returns the
        # attendance information in JSON format
        report_url = attendance_url + "/GetReport"

        # This attendance information in JSON format is exactly what we need, and it is possible
        # to replicate the web-browser intercepted request using python requests by passing
        # the following fields
        data = "{UID:'" + report_id + "',Session:'" + current_session_id + "'}"
        response = requests.post(report_url, headers=HEADERS, data=data)
        # We then return the extracted JSON content
        attendance = json.loads(response.text)["d"]
        return json.loads(attendance)

    @property
    def full_attendance(self):
        """
        Attendance with marked status from instructor
        - Accessible under 'FullAttendanceReport' of every subject
        """
        if not self._full_attendance:
            self._full_attendance = self._get_full_attendance()
        return self._full_attendance

    def _get_full_attendance(self):
        # getting minimal attendance
        attendance = self.attendance
        # Full report URL
        full_report_url = AUTHENTICATE_URL + ENDPOINTS["Attendance"] + "/GetFullReport"
        # Querying for every subject in attendance
        for subect in attendance:
            data = (
                "{course:'"
                + subect["EncryptCode"]
                + "',UID:'"
                + self._report_id
                + "',fromDate: '',toDate:''"
                + ",type:'All'"
                + ",Session:'"
                + self._session_id
                + "'}"
            )
            response = requests.post(full_report_url, headers=HEADERS, data=data)
            # removing all esc sequence chars
            subect["FullAttendanceReport"] = json.loads(json.loads(response.text)["d"])
        return attendance

    @property
    def timetable(self):
        "Timetable for current session"
        if not self._timetable:
            self._timetable = self._get_timetable()
        return self._timetable

    def _get_timetable(self):
        timetable_url = AUTHENTICATE_URL + ENDPOINTS["Timetable"]
        response = requests.get(timetable_url, cookies=self.cookies)
        # Checking for error in response as status code returned is 200
        if response.text.find(ERROR_HEAD) != -1:
            raise UIMSInternalError("UIMS internal error occured")
        soup = BeautifulSoup(response.text, "html.parser")
        viewstate_tag = soup.find("input", {"name": "__VIEWSTATE"})
        data = {
            "__VIEWSTATE": viewstate_tag["value"],
            "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ReportViewer1$ctl09$Reserved_AsyncLoadTarget",
        }
        response = requests.post(timetable_url, data=data, cookies=self.cookies)
        return self._extract_timetable(response)

    def _extract_timetable(self, response):
        soup = BeautifulSoup(response.text, "html.parser")
        timetable_table = soup.find(
            "table", {"id": "ContentPlaceHolder1_gvMyTimeTable"}
        )
        course_code_mapping_table = soup.find(
            "table", {"id": "ContentPlaceHolder1_gvMyTimeTableDetails"}
        )
        # extract course_codes first
        course_codes = dict()
        mapping_table_rows = course_code_mapping_table.find_all("tr")
        for row in mapping_table_rows:
            tds = row.find_all("td")
            # first is code, second is course name
            if len(tds) > 1:
                course_codes[tds[0].get_text(strip=True)] = tds[1].get_text(strip=True)

        # now extract day wise timetable from timetable_table
        timetable_table_rows = timetable_table.find_all("tr")
        # first row represents days
        all_days = timetable_table_rows[0].find_all("th", {"scope": "col"})
        actual_days = [day.get_text(strip=True) for day in all_days[1:]]

        # result timetable object
        timetable = dict()

        actual_timetable_rows = timetable_table_rows[1:]

        # all tds as array of array ( used in future )
        tds_in_actual_timetable_rows = []
        for row in actual_timetable_rows:
            tds = row.find_all("td")
            tds_in_actual_timetable_rows.append(tds)

        # represents [09:40 - 10:20 AM, 1:00 - 1:40 PM, ...]
        timings_in_a_day = [
            tds_row[0].get_text(strip=True) for tds_row in tds_in_actual_timetable_rows
        ]

        for i in range(len(actual_days)):
            timings = dict()
            for timing in range(len(timings_in_a_day)):
                result_subject = tds_in_actual_timetable_rows[timing][i + 1].get_text(
                    strip=True
                )
                timings[timings_in_a_day[timing]] = (
                    self._parse_timetable_subject(result_subject, course_codes)
                    if result_subject
                    else None
                )
            timetable[actual_days[i]] = timings

        return timetable

    def _parse_timetable_subject(self, subject, course_codes):
        # For Reference
        # "CSB-421:L :: GP-All: By Steve Samson(E11030) at 1-3-C",
        # "CSR-410:P :: GP-C: By Steve Samson(E11030) at 1-2-C"
        if subject == None:
            return None
        parsed_subject = {}

        # Finding Subject Name
        sub_code_end = subject.find(":")
        sub_code = subject[0:sub_code_end]
        subject = subject[sub_code_end + 1 :]
        parsed_subject["title"] = str(course_codes[sub_code]).upper()

        # Finding Type of Lecture
        session_type = subject[0]
        subject = subject[1:]
        if session_type == "L":
            parsed_subject["type"] = "Lecture"
        elif session_type == "P":
            parsed_subject["type"] = "Practical"
        else:
            parsed_subject["type"] = "Tutorial"

        # Finding Group Type
        gp_start = subject.find("GP-")
        subject = subject[gp_start:]
        ending_colon = subject.find(":")
        group_type = subject[3:ending_colon]
        parsed_subject["group"] = group_type
        subject = subject[ending_colon + 1 :]

        # Finding Teacher's Name
        exp_start = subject.find("By ")
        exp_end = subject.find("(")
        teacher_name = subject[exp_start + 3 : exp_end]
        pattern = re.compile("^[a-zA-Z ]*$")
        parsed_subject["teacher"] = (
            teacher_name if pattern.match(teacher_name) else None
        )

        return parsed_subject
