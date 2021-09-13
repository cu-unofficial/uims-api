[![PyPi](https://img.shields.io/pypi/v/uims-api)](https://pypi.org/project/uims-api/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# uims-api

This is a Python library which scrapes https://uims.cuchd.in for account information. Our goal is to wrap
commonly used web functionality as easy-to-use methods.

## Installation

```
$ pip install uims-api
```

**Running locally:**

You need to have Python 3 installed on your system. Python 2 might work but we won't provide any
support for it. You also need to have the command-line version for [git](https://git-scm.com/downloads)
installed, otherwise you could directly download and extract the ZIP file of this repository and follow
along.

Open up a terminal and run:
(The `$` sign indicates the commands are to be run in a shell. It is not supposed to be a part of
the command)

```
$ git clone https://github.com/cu-unofficial/uims-api
$ cd uims-api
$ pip install -e .
```

## Usage Examples

```python
from uims_api import SessionUIMS

# replace these with your credentials
my_account = SessionUIMS("YourUID", "YourPass")

# `my_acc.attendance` returns attendance info for available subjects in JSON format
subjects = my_account.attendance

# display attendance for each subject
for subject in subjects:
    subject_attendance = "{} - {}%".format(subject["Title"], subject["TotalPercentage"])
    print(subject_attendance)
```

## Available Methods

| Methods            	| Description                                                                         	|
|--------------------	|-------------------------------------------------------------------------------------	|
| full_name          	| returns user's full name                                                            	|
| attendance         	| returns user's minimal attendance                                                   	|
| full_attendance    	| returns user's attendance including day-wise marked report history for each subject 	|
| timetable          	| returns user's timetable                                                            	|
| available_sessions 	| returns user's available sessions                                                   	|
| marks(session)     	| returns marks for the session provided as argument                                  	|

## Documentation

Coming soon?

## Contributing

Let's keep this as minimal as possible using `requests` and `BeatifulSoup` libraries.

Relying on browser automation tools (selenium) could work but isn't a very portable solution. It is
slower and takes up more processing power. Also, setting up such tools could end up being a nightmare
when attempting them to run on headless devices (such as a Raspberry Pi).

That said, if you know Python, any pull requests to enhance capabilities or cover up more end points that make use of `requests`
and `BeautifulSoup` libraries are most welcome! Otherwise if you don't know Python, you could help me complete my assignments!
