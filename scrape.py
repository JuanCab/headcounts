import re
import os
import time
import datetime
import argparse

import requests
from bs4 import BeautifulSoup
import lxml.html
import numpy as np

from astropy.table import Table, Column, vstack

URL_ROOT = 'https://webproc.mnscu.edu/registration/search/basic.html?campusid=072'
SUBJECT_SEARCH_URL = 'https://webproc.mnscu.edu/registration/search/advancedSubmit.html?campusid=072&searchrcid=0072&searchcampusid=072&yrtr={year_term}&subject={subj}&courseNumber=&courseId=&openValue=ALL&showAdvanced=&delivery=ALL&starttime=&endtime=&mntransfer=&gened=&credittype=ALL&credits=&instructor=&keyword=&begindate=&site=&resultNumber=250'
COURSE_DETAIL_URL = 'https://webproc.mnscu.edu/registration/search/detail.html?campusid=072&courseid={course_id}&yrtr={year_term}&rcid=0072&localrcid=0072&partnered=false&parent=search'

SIZE_KEYS = ['Size', 'Enrolled']

DESTINATION_DIR_BASE = 'results'

# Name of symlink to create to most recent scrape
LATEST = 'latest'


def get_subject_list(year_term):
    """
    Scrape the list of subjects (aka course rubrics, e.g. PHYS or BCBT) for
    the given year/term.

    Parameters
    ----------

    year_term: str or int
        The year and term for which the list is desired. This should follow
        the "fiscal year" format, in which YYYY3 is the fall of fiscal year
        YYYY, YYYY5 is the spring of fiscal year YYYY and summer is...well,
        summer is something. No idea what.

    Returns
    -------

    list
        List of course rubrics as strings.
    """
    result = requests.get(URL_ROOT)
    soup = BeautifulSoup(result.text)
    select_box = soup.find('select', id='subject')
    subjects = select_box.find_all('option', class_=year_term)
    subject_str = [s['value'] for s in subjects]
    return subject_str


def decrap_item(item):
    """
    Utility function to strip out some whitespace. It removes any unicode,
    all line break and tab characters, compresses multiple spaces to a
    single space, and removes any leading/trailing whitespace.

    Parameters
    ----------

    item : str
        The raw item scraped from the web page.
    """
    remove_nbsp = item.encode('ascii', errors='ignore')
    no_linebreaks = remove_nbsp.replace('\n', '')
    no_linebreaks = no_linebreaks.replace('\r', '')
    no_tabs = no_linebreaks.replace('\t', '')
    less_spaces = re.sub('\s+', ' ', no_tabs)
    return less_spaces.strip()


def class_list_for_subject(subject, year_term='20153'):
    """
    Return a table with one row for each class offered in a subject (aka
    course rubric).

    Parameters
    ----------

    subject : str
        The course rubric (aka subject) for which the list of courses is
        desired. Examples are PHYS, ED, ART...

    year_term: str, optional
        The year/term in "fiscal year" notation. See the documentation for
        ``get_subject_list`` for a description of that notation.

    Returns
    -------

    astropy.table.Table
        Table with one column for each column in the search results in which
        each row is one course.
    """

    # Get and parse the course list for this subject
    list_url = SUBJECT_SEARCH_URL.format(subj=subject, year_term=year_term)
    result = requests.get(list_url)
    lxml_parsed = lxml.html.fromstring(result.text)

    # Find all instances of the second column, which is the column with course ID
    # number in it.
    foo = lxml_parsed.findall('.//tbody/tr/td[2]')
    course_ids = [f.text.strip() for f in foo]

    # Grab the table of results...
    results = lxml_parsed.findall(".//table[@id='resultsTable']")[0]

    # ...and then the headers for that table, to use as column names later...
    headers = results.findall('.//th')
    header_list = [decrap_item(h.text_content()) for h in headers[1:]]

    # ...and finally grab all of the rows in the table.
    hrows = results.findall('.//tbody/tr')

    # Construct the table by adding a bunch of columns (which is probably
    # slow).
    table = Table()
    for h in header_list:
        table.add_column(Column(name=h, dtype='S200'))

    # Not clear why data is created and appended to, since it is not actually
    # used for anything.
    data = []

    # Append the data for each row to the table (likely also slow)
    for row in hrows:
        cols = row.findall('td')
        # Skip the first column, which is a set of buttons for user actions.
        dat = [decrap_item(c.text_content()) for c in cols[1:]]

        data.append(dat)
        table.add_row(dat)

    return table


def course_detail(cid, year_term='20155'):
    """
    Parse enrollment size information from detail page for a course.

    Note that a failed search for a course gives a result whose values are
    -1, but no exception is raised.

    Parameters
    ----------

    cid : str
        Course ID number, with leading zeros to pad it to six digits.

    Returns
    -------

    dict
        A dict whose keys are the sizes in SIZE_KEYS and whose values are
        either the enrollment number, if the course lookup is successful,
        or **-1 if the course lookup fails**.
    """

    def parse_size_cap(element):
        """
        Handle extracting the actual size from the matched element in the XML
        tree.
        """
        return int(element.getparent().text_content().split(':')[1].strip())

    # Get and parse the course detail page.
    course_url = COURSE_DETAIL_URL.format(course_id=cid, year_term=year_term)
    result = requests.get(course_url)
    lxml_parsed = lxml.html.fromstring(result.text)

    # Check for an error in the page text, and return sizes of -1 to indicate
    # error.
    if 'System Error' in result.text:
        print "Errored on {}".format(cid)
        return {k: -1 for k in SIZE_KEYS}

    # Define an xpath expression to the class sizes. The value $key
    # will be filled in below with one of the SIZE_KEYS.
    xpath_expr = './/*[contains(text(), $key)]'
    to_get = {k: None for k in SIZE_KEYS}

    for key in to_get.keys():
        foo = lxml_parsed.xpath(xpath_expr, key=key)
        to_get[key] = parse_size_cap(foo[0])
    return to_get


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape enrollment numbers '
                                     'from public MnSCU search site')
    parser.add_argument('year_term', help='Code for year/term, a 5 digit '
                        'number like 20155 (spring of 2015)')
    args = parser.parse_args()

    # Grab the list of subjects for this year/term
    subjects = get_subject_list(args.year_term)

    # print "Trying {}".format(subjects[0])
    overall_table = None

    # Generate a date/time to use in naming directory with results
    now = time.localtime()
    formatted_datetime = datetime.datetime(*now[:-3]).isoformat()
    formatted_datetime = formatted_datetime.replace(':', '-')
    destination = '-'.join([DESTINATION_DIR_BASE, formatted_datetime])

    # Make the directory
    try:
        os.makedirs(destination)
    except OSError:
        raise OSError('Destination folder %s already exists' % destination)

    # Process each course rubric (aka subject)
    for subject in subjects:
        print "On subject {}".format(subject)

        # Pull list of classes for subject. Note that this is the table
        # from which most of the course information is derived.
        table = class_list_for_subject(subject, year_term=args.year_term)
        IDs = table['ID #']
        results = {k: [] for k in SIZE_KEYS}
        timestamps = []

        # Obtain the enrollment and enrollment cap, and add a timestamp.
        for an_id in IDs:
            size_info = course_detail(an_id, year_term=args.year_term)
            for k, v in size_info.iteritems():
                results[k].append(v)
            timestamps.append(time.time())

        # Add columns for sizes and timestamp
        for k, v in results.iteritems():
            table.add_column(Column(name=k, data=v, dtype=np.int), index=8)
        table.add_column(Column(name='timestamp', data=timestamps))

        # Add a year_term column to the table
        if len(table):
            table.add_column(Column(name='year_term',
                                    data=[str(args.year_term)] * len(table)))

        # Add the table to the overall table...
        if not overall_table:
            overall_table = table
        else:
            overall_table = vstack([overall_table, table])

        # ...but also write out this individual table in case we have a
        # failure along the way.
        table.write(os.path.join(destination, subject + '.csv'))

    # Write out a file for the overall (i.e. all subjects) table.
    overall_table.write(os.path.join(destination, 'all_enrollments.csv'))

    # symlink LATEST to this run of the scraper.
    try:
        os.remove(LATEST)
    except OSError:
        # Not a problem if it doesn't already exist.
        pass
    os.symlink(destination, LATEST)
