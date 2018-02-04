# A small scraper to extract course enrollment information

The MinnState system of colleges and universities (neé MnSCU) maintains a
searchable listing of course subjects for the current, one past and one future
semester at [https://eservices.minnstate.edu/registration/search/basic.html?ca
mpusid=072](https://eservices.minnstate.edu/registration/search/basic.html?cam
pusid=072).

Detail on individual courses is also available by subject and/or course ID.

This scraper gathers that information for either

+ All courses in a specific term (only available for terms that appear in the
  search form above), or
+ A list of course ID numbers for a specific year/term.

All of the course detail is dumped into a CSV file.

# Usage

```
$ python scrape.py --help
usage: scrape.py [-h] [--year-term YEAR_TERM] [--cid-list CID_LIST]

Scrape enrollment numbers from public MnSCU search site

optional arguments:
  -h, --help            show this help message and exit
  --year-term YEAR_TERM
                        Code for year/term, a 5 digit number like 20155
                        (spring of 2015)
  --cid-list CID_LIST   CSV that has at least two columns, "ID #", a course ID
                        number, and "year_term" a year/term code.
```

