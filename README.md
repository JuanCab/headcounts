# A small scraper to extract course enrollment information

The MinnState system of colleges and universities (neé MnSCU) maintains a
searchable listing of course subjects for the current, one past and one future
semester at [https://eservices.minnstate.edu/registration/search/basic.html?ca
mpusid=072](https://eservices.minnstate.edu/registration/search/basic.html?campusid=072).

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

# How do I get course information for past semesters?

This involves two steps:

1. Get a list of all of the course ID numbers used for a particular semester.
2. Scrape the data for each of those courses.

Though one could imagine doing a data request to the course ID numbers it turns out to be reasonably easy to simply try all course ID numbers up to some maximum (the default is 4000) and see which do not return errors.

The script `get_cids.py` does that. Its usage is:

```
$ python get_cids.py --help

usage: get_cids.py [-h] [--year-term YEAR_TERM] [--max-cid MAX_CID]

Discover CID numbers

optional arguments:
  -h, --help            show this help message and exit
  --year-term YEAR_TERM
                        Code for year/term, a 5 digit number like 20155
                        (spring of 2015)
  --max-cid MAX_CID     The largest course ID number to look for.
```

# Does this work for other campuses besides Minnesota State University Moorhead?

Not at the moment, though I would merge a pull request that added that
ability. The codes for all of the MinnState campuses are in the table below,
and I think the modification needed is fairly minor.

However, the default will always be to search for MSUM because that is where I
am.

| Campus code | Campus name |
|:-----------:|:-----------:|
| 0203 | Alexandria Technical and Community College |
| 0202 | Anoka Technical College |
| 0152 | Anoka-Ramsey Community College |
| 0070 | Bemidji State University |
| 0301 | Central Lakes College |
| 0304 | Century College |
| 0211 | Dakota County Technical College |
| 0163 | Fond du Lac Tribal and Community College |
| 0204 | Hennepin Technical College |
| 0310 | Hibbing Community College |
| 0157 | Inver Hills Community College |
| 0144 | Itasca Community College |
| 0302 | Lake Superior College |
| 0411 | Mesabi Range College |
| 0076 | Metropolitan State University |
| 0305 | Minneapolis Community and Technical College |
| 0213 | Minnesota State College Southeast |
| 0142 | Minnesota State Community and TechnicalCollege |
| 0072 | Minnesota State University Moorhead |
| 0071 | Minnesota State University, Mankato |
| 0209 | Minnesota West Community and TechnicalCollege |
| 0156 | Normandale Community College |
| 0153 | North Hennepin Community College |
| 0303 | Northland Community and Technical College
| 0263 | Northwest Technical College |
| 0205 | Pine Technical and Community College |
| 0155 | Rainy River Community College |
| 0308 | Ridgewater College |
| 0307 | Riverland Community College |
| 0306 | Rochester Community and Technical College
| 0206 | Saint Paul College |
| 0309 | South Central College |
| 0075 | Southwest Minnesota State University |
| 0073 | St. Cloud State University |
| 0208 | St. Cloud Technical and Community College |
| 0147 | Vermilion Community College |
| 0074 | Winona State University |
