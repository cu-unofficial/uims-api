from uims_api import SessionUIMS
import sys

def getAttendence(uid=""):
    password = input("Enter your Password: ")
    my_account = SessionUIMS(uid, password)

    subjects = my_account.attendance

    for subject in subjects:
        subject_attendence = f"{subject['Title']} - {subject['TotalPercentage']}"
        print(subject_attendence)


if __name__ == '__main__':
    argv = sys.argv
    if argv[1] == 'attendence' and len(argv) == 3:
        getAttendence(argv[2])
