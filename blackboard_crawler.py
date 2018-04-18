#coding: utf-8
# blackboard_crawler.py
# version 1.0
FOLDER_PREFIX="blackboard"
blackboard_url="https://blackboard.cuhk.edu.hk"
SLEEP_TIME = 2 # better be a patient person, so that we wont flood blackboard's traffic
MAX_DEPTH = 3 # maximum recursive folder
email_suffix = '@link.cuhk.edu.hk'
import json
import time
import requests
import urllib2
import re
import os
import uuid # in case the error happens
from getpass import getpass 
import xml.etree.ElementTree as ET # XML parser is not used because the fucking &ndash;
import inspect # debugging purpose
from sys import platform

def mkdir(name):
  try:
    if(os.path.exists(name)):
      pass # dir exists
    else:
      os.mkdir(name)
  except Exception as inst:
    print(inst)
    os.mkdir(str(name)+str(uuid.uuid4().hex[:8]))

def download_file(url, path, sess):
  if(blackboard_url not in url):
    url = blackboard_url+url
  resp = sess.get(url, stream=True)
  url = urllib2.urlparse.unquote(resp.url)
  if(platform == "darwin"):
    url = url.encode('latin1')
  print(str(path)+' '+str(url))
  local_filename = urllib2.urlparse.unquote(url.split('/')[-1])
  file_size = resp.headers['Content-Length']
  if(int(file_size)>=1024*1024*100):
    while(1):
      download = raw_input("The file is around {0}MB, still download?(y/n)".format(int(file_size)/1024/1024))
      if(download.lower() == 'y'):
        break
      elif(download.lower() == 'n'):
        return local_filename
      else:
        print("Please input only y or n!")
  # NOTE the stream=True parameter
  r = resp
  with open(os.path.join(path, local_filename.decode('utf-8')), 'wb') as f:
    for chunk in r.iter_content(chunk_size=1024): 
      if chunk: # filter out keep-alive new chunks
        f.write(chunk)
            #f.flush() commented by recommendation from J.F.Sebastian
  return local_filename

def init_bb_session():
  sess = requests.session()
  # fake header, otherwise they wont care
  sess.headers['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
  # go to starting page
  blackboard_main_resp = sess.get(blackboard_url)
  next_url_1 = re.findall('url=(.+)', blackboard_main_resp.text)[0]
  # redirected to login page
  next_url_1 = urllib2.urlparse.unquote(next_url_1)
  login_page_resp = sess.get(next_url_1)
  return (login_page_resp.url, sess)

def login(username, password, login_page_url, sess):
  try:
    form_auth_payload={
      'UserName': username,
      'Password': password,
      'AuthMethod': "FormsAuthentication"
    }
    print("logging in...")
    logging_in_resp = sess.post(login_page_url, data=form_auth_payload)
    time.sleep(SLEEP_TIME)
    next_url_3 = re.findall('action="(.+?)">',logging_in_resp.text)[0]
    SAMLResponse = re.findall('name="SAMLResponse" value="(.+?)" />',logging_in_resp.text)[0]
    resp4 = sess.post(next_url_3, data = {'SAMLResponse': SAMLResponse})
    time.sleep(SLEEP_TIME)
    print("logged in...")
    return sess
  except Exception as inst:
    print(inst)
    print("some error occurs, probably wrong password")


# must after login
def get_userid(sess):
  course_url = 'https://blackboard.cuhk.edu.hk/ultra/course'
  course_resp = sess.get(course_url)
  try:
    userid = re.findall('"id":"(.+?)"', course_resp.text)[0]
  except Exception as inst:
    print(inst)
    print("cannot get userid, probably wrong password/ not logged in")
    exit(0)
  return userid

def get_courses(userid, sess):
  print("getting courses...")
  try:
    courses_resp = sess.get("https://blackboard.cuhk.edu.hk/learn/api/v1/users/{0}/memberships?expand=course.instructorsMembership,course.effectiveAvailability,course.permissions,courseRole&limit=10000&organization=false".format(userid))
    courses = courses_resp.json()['results']
    course_infos = []
    for course in courses:
      if(course['course']['isAvailable']):
        content_id = course['id']
        course_id = course['course']['id']
        course_code = course['course']['courseId']
        display_name = course['course']['displayName']
        course_infos.append((course_id, course_code, display_name))
    return course_infos #[course_id, course_code, course_name]
  except Exception as inst:
    caller = str(inspect.stack(0)[1][3])
    inst = str(inst)
    print(caller+'\t'+inst)
    return []

def get_course_sections(course_info, sess):
  try:
    course_id, course_code, course_name = course_info
    print("reading course: {0}".format(course_name))
    mkdir(os.path.join(FOLDER_PREFIX, course_name))
    course_url = "https://blackboard.cuhk.edu.hk/webapps/blackboard/execute/courseMain?course_id={0}".format(course_id)
    course_url_resp = sess.get(course_url)
    section_raw = re.findall('<hr>(.+?)<hr>',course_url_resp.text)[0]
    sections = re.findall('<a href="(/webapps/blackboard/content/listContent.jsp?.+?)".+?">.+?">(.+?)</span>', section_raw) 
    return sections
  except Exception as inst:
    caller = str(inspect.stack(0)[1][3])
    inst = str(inst)
    print(caller+'\t'+inst)
    return []

# actually section can be directory info too
def get_item_from_section(path_prefix, section, sess):
  try:
    section_url, section_name = section
    print("--reading sections: {0}".format(section_name))
    mkdir(path_prefix)
    if(blackboard_url not in section_url):
      section_url = blackboard_url+section_url
    course_section_resp = sess.get(section_url)
    directories = re.findall('<a href="(/webapps/blackboard/content/listContent.jsp?.+?)"><span style=".+?">(.+?)</span>', course_section_resp.text)
    files = re.findall('<a href="(/bbcswebdav.+?)".+?">.+?">(.+)</span>', course_section_resp.text)
    """ files
    <a href="/bbcswebdav/pid-2238145-dt-content-rid-8465171_1/xid-8465171_1" onClick="this.href='/webapps/blackboard/execute/content/file?cmd=view&content_id=_2238145_1&course_id=_87673_1'">
      <span style="color:#000000;">lesson 11</span>
    </a>
    """
    files2 = re.findall('<a href="(/bbcswebdav.+?)".+?">.+?">(.+)[^</span>]</a>', course_section_resp.text)
    """ files2
    <a href="/bbcswebdav/pid-2233230-dt-content-rid-8062745_1/xid-8062745_1" target="_blank">
      <img src="https://d1e7kr0efngifs.cloudfront.net/3400.1.0-rel.35+67d71b7/images/ci/ng/cal_year_event.gif" alt="File">
      &nbsp;第十課閱讀材料 (徐復觀).pdf
    </a>
    """
    time.sleep(SLEEP_TIME)
    return (directories, (files+files2)) # [(directory_url, directory_name), (file_url, file_name)]
  except Exception as inst:
    caller = str(inspect.stack(0)[1][3])
    inst = str(inst)
    print(caller+'\t'+inst)
    return ([],[])

def download_files(path_prefix, files, sess):
  for f in files:
    file_url, file_name = f
    download_file(file_url, path_prefix, sess)

def download_item_from_directories(path_prefix, directories, sess, depth):
  try:
    if(depth<=0):
      return
    for directory in directories:
      directory_url, directory_title = directory
      new_prefix = os.path.join(path_prefix, directory_title)
      next_directories, files = get_item_from_section(new_prefix, directory, sess)
      download_files(new_prefix, files, sess)
      download_item_from_directories(new_prefix, next_directories, sess, depth-1)
  except Exception as inst:
    caller = str(inspect.stack(0)[1][3])
    inst = str(inst)
    print(caller+'\t'+inst)

# def main():
print("If you think the program has stuck, feel free to press ctrl+C to stop it")
print("This blackboard notes crawler make no warranty of any kind")
print("please press enter to continue")
raw_input()
cnt=0
while(1):
  cnt+=1
  username = raw_input("Your sid/ sid{0}: ".format(email_suffix))
  password = getpass()
  login_page_url, sess = init_bb_session()
  if(email_suffix not in username):
    username = username+email_suffix
  sess = login(username, password, login_page_url, sess)
  if(sess):
    break
  if(cnt>=3):
    print("Wrong login for 3 times, byebye")
mkdir(FOLDER_PREFIX)
userid = get_userid(sess)
course_infos = get_courses(userid, sess)

for course_info in course_infos:
  course_name = course_info[2]
  sections = get_course_sections(course_info, sess)
  if(os.path.exists(os.path.join(FOLDER_PREFIX, course_name))):
    while(1):
      download = raw_input("folder exists for {0}, download anyway? (y/n)".format(course_name))
      if(download.lower() == 'y'):
        break
      elif(download.lower() == 'n'):
        sections=[]
        break
      else:
        print("Please input only y or n!")
  for section in sections:
    section_title = section[1]
    path_prefix = os.path.join(FOLDER_PREFIX, course_name, section_title)
    directories, files = get_item_from_section(path_prefix, section, sess)
    download_item_from_directories(path_prefix, directories, sess, MAX_DEPTH)
    download_files(path_prefix, files, sess)
    time.sleep(SLEEP_TIME)

