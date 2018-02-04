from __future__ import print_function

import re
import os
import time
import datetime
import argparse
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
import lxml.html
import numpy as np

from astropy.table import Table, Column, vstack

URL_ROOT = 'https://webproc.mnscu.edu/registration/search/basic.html?campusid=072'
SUBJECT_SEARCH_URL = 'https://webproc.mnscu.edu/registration/search/advancedSubmit.html?campusid=072&searchrcid=0072&searchcampusid=072&yrtr={year_term}&subject={subj}&courseNumber=&courseId=&openValue=ALL&showAdvanced=&delivery=ALL&starttime=&endtime=&mntransfer=&gened=&credittype=ALL&credits=&instructor=&keyword=&begindate=&site=&resultNumber=250'
COURSE_DETAIL_URL = 'https://webproc.mnscu.edu/registration/search/detail.html?campusid=072&courseid={course_id}&yrtr={year_term}&rcid=0072&localrcid=0072&partnered=false&parent=search'

SIZE_KEYS = ['Enrolled', 'Size:']

TUITION_COURSE_KEYS = [
    'Tuition -resident',
    'Tuition -nonresident',
    'Approximate Course Fees'
]

TUITION_PER_CREDIT_KEYS = [
    'Tuition per credit -resident',
    'Tuition per credit -nonresident',
    'Approximate Course Fees'
]

LASC_AREAS = [
    '10-People and the Environment',
    '11-Information Literacy',
    '1A-Oral Communication',
    '1B-Written Communication',
    '2-Critical Thinking',
    '3-Natural Sciences',
    '3L-Natural Sciences with Lab',
    '4-Math/Logical Reasoning',
    '5-History and the Social Sciences',
    '6-Humanities and Fine Arts',
    '7-Human Diversity',
    '8-Global Perspective',
    '9-Ethical and Civic Responsibility',
    'WI-Writing Intensive',
]

# Define some constants for column names...
LASC_WI = 'LASC/WI'
ONLINE_18 = '18online'
TUITION_UNIT = 'Tuition unit'
COURSE_LEVEL = 'Course level'
EXTRA_COLUMNS = [
    LASC_WI,
    ONLINE_18,
    TUITION_COURSE_KEYS[0],  # Resident tuition
    TUITION_UNIT,
    TUITION_COURSE_KEYS[1],  # Course fees
    COURSE_LEVEL,
    TUITION_COURSE_KEYS[2],  # Non-resident tuition
]

def lasc_area_label(full_name):
    """
    Return just the area number/letter from the full name that appears
    in the course detail page.
    """
    return full_name.split('-')[0]


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


def get_location(loc):
    """
    Extract the class location, which is stored as the alt text in an image
    in one of the table cells.

    Yes, you read that right. Someone thought to themselves 'Hey, you know
    what would be handy? Having to mouse over a little location icon and
    hover to see a list of rooms.'

    It is also available as the title of the image...
    """
    img = loc.find('.//img')
    locations = img.attrib['alt'].splitlines()
    # Drop the first line, which just says the class is at MSUM.
    locations = [l for l in locations if l.startswith('Building')]

    # For the rest, ditch "Building/Room:" from the front of the line
    locations = [l.split('Building/Room: ')[1] for l in locations]
    return '\n'.join(locations)


def scrape_class_data_from_results_table(page_content, page_type='search'):
    """
    Given the html content of either a course search result page or
    an individual course page, scrape the useful data from the table.
    """
    lxml_parsed = lxml.html.fromstring(page_content)

    # Grab the table of results...
    if page_type == 'search':
        results = lxml_parsed.findall(".//table[@id='resultsTable']")[0]
    else:
        results = lxml_parsed.findall(".//table[@class='myplantable']")[0]

    # ...and then the headers for that table, to use as column names later...
    headers = results.findall('.//th')
    header_list = [decrap_item(h.text_content()) for h in headers[1:]]

    # ...and finally grab all of the rows in the table.
    hrows = results.findall('.//tbody/tr')

    # Construct the table by adding a bunch of columns (which is probably
    # slow).
    # table = Table()
    # for h in header_list:
    #     table.add_column(Column(name=h, dtype='S200'))

    # Not clear why data is created and appended to, since it is not actually
    # used for anything.
    data = []

    # Append the data for each row to the table (likely also slow)
    for row in hrows:
        cols = row.findall('td')
        # Skip the first column, which is a set of buttons for user actions,
        # and the last column, which has room information embedded in it, but
        # not as text.
        dat = [decrap_item(c.text_content()) for c in cols[1:-1]]
        # Last column is location
        loc = cols[-1]
        dat.append(get_location(loc))
        data.append(dat)
        # table.add_row(dat)

    # Yay stackoverflow: https://stackoverflow.com/a/6473724/3486425
    data = list(map(list, zip(*data)))

    if not data:
        # So apparently a subject which has no courses can be listed...
        return None

    table = Table(data=data,
                  names=header_list,
                  dtype=['S200'] * len(header_list))
    return table


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
    return scrape_class_data_from_results_table(result.text)


def class_list_for_cid(cid, year_term):
    course_url = COURSE_DETAIL_URL.format(course_id=cid, year_term=year_term)
    result = requests.get(course_url)
    return scrape_class_data_from_results_table(result.text,
                                                page_type='detail')


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
        return element.getparent().text_content().split(':')[1].strip()

    # Get and parse the course detail page.
    course_url = COURSE_DETAIL_URL.format(course_id=cid, year_term=year_term)
    result = requests.get(course_url)
    lxml_parsed = lxml.html.fromstring(result.text)

    # Check for an error in the page text, and return sizes of -1 to indicate
    # error.
    if 'System Error' in result.text:
        print("Errored on {}".format(cid))
        return {k: -1 for k in SIZE_KEYS}

    if TUITION_PER_CREDIT_KEYS[0] in result.text:
        tuition_keys = TUITION_PER_CREDIT_KEYS
        tuition_unit = 'credit'
    else:
        # if TUITION_COURSE_KEYS[0] in result.text:
        tuition_keys = TUITION_COURSE_KEYS
        tuition_unit = 'course'

    lasc_areas = [lasc_area_label(area) for area in LASC_AREAS
                  if area in result.text]

    # Define an xpath expression to the class sizes. The value $key
    # will be filled in below with one of the SIZE_KEYS.
    xpath_expr = './/*[contains(text(), $key)]'
    to_get = {}

    for key in SIZE_KEYS + tuition_keys:
        foo = lxml_parsed.xpath(xpath_expr, key=key)
        try:
            value = parse_size_cap(foo[0])
        except IndexError:
            value = ''
        # Make the sizes integers
        if key in SIZE_KEYS:
            value = int(value)

        # If we have one of the per-credit keys change it to a per-course key
        try:
            idx = TUITION_PER_CREDIT_KEYS.index(key)
        except ValueError:
            to_get[key] = value
        else:
            use_key = TUITION_COURSE_KEYS[idx]
            to_get[use_key] = value

    # Add a couple last things to the results...
    to_get[TUITION_UNIT] = tuition_unit
    to_get[LASC_WI] = ','.join(lasc_areas)
    to_get[ONLINE_18] = '18 On-Line' in result.text

    # So....how do you get free floating text in a web page out of that page?
    # Any suggestions, MnSCU? Didn't think so. How about a regex for what
    # we need, which is sandwiched between two divs that contain text that is
    # easy to find? Note the actual text is not in any element, not even a <p>.
    all_the_text = lxml_parsed.text_content()
    matches = re.search('.*Course Level\s+(\w+)\s+(Description|General/Liberal|Lectures/Labs|Corequisites|Add To Wait List)',
                        all_the_text)

    # Oh ha, ha, turns out any number of things can follow Course Level.
    if matches:
        to_get[COURSE_LEVEL] = matches.groups(1)[0]
    else:
        to_get[COURSE_LEVEL] = 'Unknown'
        raise RuntimeError

    return to_get


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape enrollment numbers '
                                     'from public MnSCU search site')
    parser.add_argument('--year-term',action='store',
                        help='Code for year/term, a 5 digit '
                        'number like 20155 (spring of 2015)')
    parser.add_argument('--cid-list', action='store',
                        help='CSV that has at least two columns, "ID #", a '
                        'course ID number, and "year_term" a year/term code.')
    args = parser.parse_args()

    year_term = args.year_term
    cid_list = args.cid_list

    if year_term and cid_list:
        raise RuntimeError('Can only use one of --year-term and --cid-list')
    elif not (year_term or cid_list):
        raise RuntimeError('Must use exactly one of --year-term and --cid-list')
    print(year_term)

    if year_term:
        # Grab the list of subjects for this year/term
        subjects = get_subject_list(args.year_term)
        source_list = subjects

    if cid_list:
        inp_data = Table.read(cid_list)
        cids = inp_data['ID #']
        year_terms = inp_data['year_term']
        source_list = [('{:06d}'.format(int(c)), str(y)) for c, y in zip(cids, year_terms)]

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

    temp_paths = []
    bads = []
    # Process each course rubric (aka subject)
    for source in source_list:
        print("On source {}".format(source))

        # Pull list of classes for subject. Note that this is the table
        # from which most of the course information is derived.
        try:
            if year_term:
                table = class_list_for_subject(source, year_term=year_term)
            elif cid_list:
                table = class_list_for_cid(source[0], source[1])
        except IndexError:
            bads.append(source)
            print("     Failed!")
            continue

        if not table:
            # This can happen, for example, if there are no courses listed
            # for a subject...
            continue

        IDs = table['ID #']
        results = defaultdict(list)
        timestamps = []

        use_year_term = year_term or source[1]
        # Obtain the enrollment and enrollment cap, and add a timestamp.
        for an_id in IDs:
            size_info = course_detail(an_id, year_term=use_year_term)
            for k, v in size_info.iteritems():
                results[k].append(v)
            timestamps.append(time.time())

        # Add columns from course detail
        for k in SIZE_KEYS:
            table.add_column(Column(name=k, data=results[k], dtype=np.int),
                             index=8)

        for k in EXTRA_COLUMNS:
            table.add_column(Column(name=k, data=results[k]))

        table.add_column(Column(name='timestamp', data=timestamps))

        # Add a year_term column to the table
        if len(table):
            table.add_column(Column(name='year_term',
                                    data=[str(use_year_term)] * len(table)))

        # Add the table to the overall table...
        if not overall_table:
            overall_table = table
        else:
            overall_table = vstack([overall_table, table])

        # ...but also write out this individual table in case we have a
        # failure along the way.
        temp_file = '-'.join(source) + '.csv'

        table.write(os.path.join(destination, temp_file))
        temp_paths.append(os.path.join(destination, temp_file))

    # Write out a file for the overall (i.e. all subjects) table.
    overall_table.write(os.path.join(destination, 'all_enrollments.csv'))

    # Verify that the table wrote out correctly
    from_disk = Table.read(os.path.join(destination, 'all_enrollments.csv'))

    if len(from_disk) != len(overall_table):
        raise RuntimeError('Enrollment data did not properly write to disk!')

    for path in temp_paths:
        os.remove(path)

    # symlink LATEST to this run of the scraper.
    try:
        os.remove(LATEST)
    except OSError:
        # Not a problem if it doesn't already exist.
        pass
    os.symlink(destination, LATEST)
