import requests
from bs4 import BeautifulSoup
import lxml.html

URL_ROOT = 'https://webproc.mnscu.edu/registration/search/basic.html?campusid=072'
SUBJECT_SEARCH_URL = 'https://webproc.mnscu.edu/registration/search/advancedSubmit.html?campusid=072&searchrcid=0072&searchcampusid=072&yrtr=20153&subject={subj}&courseNumber=&courseId=&openValue=ALL&showAdvanced=&delivery=ALL&starttime=&endtime=&mntransfer=&gened=&credittype=ALL&credits=&instructor=&keyword=&begindate=&site=&resultNumber=250'


def get_subject_list():
    result = requests.get(URL_ROOT)
    soup = BeautifulSoup(result.text)
    select_box = soup.find('select', id='subject')
    subjects = select_box.find_all('option', class_="20153")
    subject_str = [s['value'] for s in subjects]
    return subject_str


def class_list_for_subject(subject):
    list_url = SUBJECT_SEARCH_URL.format(subj=subject)
    #print "Starting request"
    result = requests.get(list_url)
    #print "Got request"
    #print result.text
    #print result.encoding
    tree = BeautifulSoup(result.text)
    #print(tree.prettify('ascii'))
    table = tree.find(id="resultsTable")
    #print table
    rows = table.find_all('tr')
    #print len(rows)
    for row in rows:
        #print row
        pass
    lxml_parsed = lxml.html.fromstring(result.text)
    #print lxml.html.tostring(lxml_parsed)
    foo = lxml_parsed.findall('.//tbody/tr/td[2]')
    print len(foo)
    course_ids = [f.text.strip() for f in foo]
    return course_ids

if __name__ == '__main__':
    subjects = get_subject_list()
    #print "Trying {}".format(subjects[0])
    IDs = class_list_for_subject('ART')
