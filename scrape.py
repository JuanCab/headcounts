import requests
from bs4 import BeautifulSoup
import lxml.html

URL_ROOT = 'https://webproc.mnscu.edu/registration/search/basic.html?campusid=072'
SUBJECT_SEARCH_URL = 'https://webproc.mnscu.edu/registration/search/advancedSubmit.html?campusid=072&searchrcid=0072&searchcampusid=072&yrtr=20153&subject={subj}&courseNumber=&courseId=&openValue=ALL&showAdvanced=&delivery=ALL&starttime=&endtime=&mntransfer=&gened=&credittype=ALL&credits=&instructor=&keyword=&begindate=&site=&resultNumber=250'
COURSE_DETAIL_URL = 'https://webproc.mnscu.edu/registration/search/detail.html?campusid=072&courseid={course_id}&yrtr=20153&rcid=0072&localrcid=0072&partnered=false&parent=search'


def get_subject_list():
    result = requests.get(URL_ROOT)
    soup = BeautifulSoup(result.text)
    select_box = soup.find('select', id='subject')
    subjects = select_box.find_all('option', class_="20153")
    subject_str = [s['value'] for s in subjects]
    return subject_str


def class_list_for_subject(subject):
    list_url = SUBJECT_SEARCH_URL.format(subj=subject)
    result = requests.get(list_url)
    lxml_parsed = lxml.html.fromstring(result.text)
    foo = lxml_parsed.findall('.//tbody/tr/td[2]')
    course_ids = [f.text.strip() for f in foo]
    return course_ids


def course_detail(cid):
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

    course_url = COURSE_DETAIL_URL.format(course_id=cid)
    result = requests.get(course_url)
    lxml_parsed = lxml.html.fromstring(result.text)

    detail_table_header = lxml_parsed.xpath('.//table[@summary="Course Detail"]//th//text()')
    print detail_table_header
    detail_table_data = lxml_parsed.xpath('.//table[@summary="Course Detail"]//td')
    for d in detail_table_data[1:]:
        print d.text_content().strip()
    for h, d in zip(detail_table_header, detail_table_data[1:]):
        print h.strip(), ' '.join(d.text_content().strip().split())

    xpath_expr = './/*[contains(text(), $key)]'
    to_get = {'Size': None, 'Enrolled': None}
    for key in to_get.keys():
        foo = lxml_parsed.xpath(xpath_expr, key=key)
        to_get[key] = parse_size_cap(foo[0])
    print cid, to_get


if __name__ == '__main__':
    subjects = get_subject_list()
    #print "Trying {}".format(subjects[0])
    IDs = class_list_for_subject('ART')
    for an_id in IDs[0:1]:
        print "On ID: {}".format(an_id)
        course_detail(an_id)
