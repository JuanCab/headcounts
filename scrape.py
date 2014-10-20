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

def get_subject_list(year_term):
    result = requests.get(URL_ROOT)
    soup = BeautifulSoup(result.text)
    select_box = soup.find('select', id='subject')
    subjects = select_box.find_all('option', class_=year_term)
    subject_str = [s['value'] for s in subjects]
    return subject_str


def decrap_item(item):
    remove_nbsp = item.encode('ascii', errors='ignore')
    no_linebreaks = remove_nbsp.replace('\n', '')
    no_linebreaks = no_linebreaks.replace('\r', '')
    no_tabs = no_linebreaks.replace('\t', '')
    less_spaces = re.sub('\s+', ' ', no_tabs)
    return less_spaces.strip()


def class_list_for_subject(subject, year_term='20153'):
    list_url = SUBJECT_SEARCH_URL.format(subj=subject, year_term=year_term)
    result = requests.get(list_url)
    lxml_parsed = lxml.html.fromstring(result.text)
    #print result.text
    foo = lxml_parsed.findall('.//tbody/tr/td[2]')
    course_ids = [f.text.strip() for f in foo]
    results = lxml_parsed.findall(".//table[@id='resultsTable']")[0]
    headers = results.findall('.//th')
    header_list = [decrap_item(h.text_content()) for h in headers[1:]]
    hrows = results.findall('.//tbody/tr')
    table = Table()
    for h in header_list:
        table.add_column(Column(name=h, dtype='S200'))
    data = []
    for row in hrows:
        cols = row.findall('td')
        #print repr(cols[6].text_content())
        dat = [decrap_item(c.text_content()) for c in cols[1:]]
        data.append(dat)
        table.add_row(dat)
    return table


def course_detail(cid, year_term='20155'):
    tbl_fields_to_scrape = [
        'ID #',
        'Subj',
        '#',
        'Sec',
        'Title',
        'Dates',
        'Days',
        'Time',
        'Crds',
        'Status',
        'Instructor',
        'Delivery Method',
        'Loc'
    ]

    def parse_size_cap(element):
        return int(element.getparent().text_content().split(':')[1].strip())

    course_url = COURSE_DETAIL_URL.format(course_id=cid, year_term=year_term)
    result = requests.get(course_url)
    lxml_parsed = lxml.html.fromstring(result.text)

    if 'System Error' in result.text:
        print "Errored on {}".format(cid)
        return {k: -1 for k in SIZE_KEYS}

    xpath_expr = './/*[contains(text(), $key)]'
    to_get = {k: None for k in SIZE_KEYS}
    #print course_url
    for key in to_get.keys():
        foo = lxml_parsed.xpath(xpath_expr, key=key)
        #print foo
        to_get[key] = parse_size_cap(foo[0])
    #print cid, to_get
    return to_get

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape enrollment numbers '
                                     'from public MnSCU search site')
    parser.add_argument('year_term', help='Code for year/term, a 5 digit '
                        'number like 20155 (spring of 2015)')
    args = parser.parse_args()

    subjects = get_subject_list(args.year_term)
    #print "Trying {}".format(subjects[0])
    overall_table = None
    now = time.localtime()
    formatted_datetime = datetime.datetime(*now[:-3]).isoformat()
    formatted_datetime = formatted_datetime.replace(':', '-')
    destination = '-'.join([DESTINATION_DIR_BASE, formatted_datetime])
    try:
        os.makedirs(destination)
    except OSError:
        raise OSError('Destination folder %s already exists' % destination)

    for subject in subjects:
        if subject != 'MATH':
            pass
        print "On subject {}".format(subject)
        table = class_list_for_subject(subject, year_term=args.year_term)
        IDs = table['ID #']
        results = {k: [] for k in SIZE_KEYS}
        timestamps = []
        for an_id in IDs:
            #print "On ID: {}".format(an_id)
            size_info = course_detail(an_id, year_term=args.year_term)
            for k, v in size_info.iteritems():
                results[k].append(v)
            timestamps.append(time.time())
        #print results
        for k, v in results.iteritems():
            table.add_column(Column(name=k, data=v, dtype=np.int), index=8)
        table.add_column(Column(name='timestamp', data=timestamps))
        if len(table):
            table.add_column(Column(name='year_term',
                                    data=[str(args.year_term)] * len(table)))
        if not overall_table:
            overall_table = table
        else:
            overall_table = vstack([overall_table, table])
        table.write(os.path.join(destination, subject+'.csv'))
    overall_table.write(os.path.join(destination, 'all_enrollments.csv'))
