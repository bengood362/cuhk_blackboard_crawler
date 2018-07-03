#!coding: utf-8
import json
import time
import requests
import urllib2
import re
import os
import uuid # in case the error happens
from getpass import getpass
# import xml.etree.ElementTree as ET
# XML parser is not used because the fucking &ndash;
import inspect # debugging purpose
import string
from sys import platform
from utils import mkdir

class AuthenticationException(Exception):
  pass

class BCFlags(object):
  SLEEP_TIME=0
  MAX_DEPTH=2
  FOLDER_PREFIX='blackboard'
  VERBOSE=True

class BCParams(object):
  pass

class BlackboardCrawler:
  flags = BCFlags()
  def __init__(
    self,
    username,
    password,
    blackboard_url="https://blackboard.cuhk.edu.hk",
    email_suffix='@link.cuhk.edu.hk'
  ):
    self.username = username
    self.password = password
    self.blackboard_url = blackboard_url
    self.email_suffix = email_suffix

  # return True/ False
  def login(self):
    self._init_bb_session()
    self._login()
    self.userid = self._get_bb_userid()
    mkdir(self.flags.FOLDER_PREFIX)

  # return list of courses
  # [course_id, course_code, display_name]
  def get_courses(self):
    if(not self.userid):
      raise AuthenticationException("Not logged in.")
    self.log("getting courses...")
    courses_resp = self.sess.get("{0}/learn/api/v1/users/{1}/memberships?expand=course.instructorsMembership,course.effectiveAvailability,course.permissions,courseRole&limit=10000&organization=false".format(self.blackboard_url, self.userid))
    courses = courses_resp.json()['results']
    courses_info = []
    for course in courses:
      if(course['course']['isAvailable']):
        content_id = course['id']
        course_id = course['course']['id']
        course_code = course['course']['courseId']
        display_name = course['course']['displayName']
        courses_info.append((course_id, course_code, display_name))
    self.log("finish getting courses...")
    return courses_info #[course_id, course_code, course_name]

  # download courses
  def download(self, selected_courses_info):
    # Un-enumerate it
    selected_courses_info = map(lambda x: x[1], selected_courses_info)
    self._download(selected_courses_info)

  def log(self, message):
    if(self.flags.VERBOSE):
      print (message)

  def _download(self, courses_info):
    for course_info in courses_info:
      course_id, course_code, course_name = course_info
      sections = self._get_course_sections(course_info)
      dir_name = mkdir(os.path.join(self.flags.FOLDER_PREFIX, course_name))
      # Ask if the user want to continue download if the folder exists?
      for section in sections:
        section_title = section[1]
        path_prefix = os.path.join(self.flags.FOLDER_PREFIX, course_name, section_title)
        directories, files = self._get_item_from_section(path_prefix, section)
        self._download_item_from_directories(path_prefix, directories, self.flags.MAX_DEPTH)
        self._download_files(path_prefix, files)
        time.sleep(self.flags.SLEEP_TIME)

  def _download_file(self, url, path):
    valid_chars = "-_.()\\/ %s%s" % (string.ascii_letters, string.digits)
    path = ''.join(c for c in path if c in valid_chars)
    if(self.blackboard_url not in url):
      url = self.blackboard_url+url
    resp = self.sess.get(url, stream=True)
    url = urllib2.urlparse.unquote(resp.url)
    if(platform == "darwin"):
      url = url.encode('latin1')
    self.log('{0} {1}'.format(path,url))
    local_filename = urllib2.urlparse.unquote(url.split('/')[-1])
    file_size = resp.headers['Content-Length']
    # if(int(file_size)>=1024*1024*100):
    #   while(1):
    #     download = raw_input("The file {1} is around {0}MB, still download?(y/n)".format(int(file_size)/1024/1024, local_filename))
    #     if(download.lower() == 'y'):
    #       break
    #     elif(download.lower() == 'n'):
    #       return local_filename
    #     else:
    #       print("Please input only y or n!")
    # NOTE the stream=True parameter
    r = resp
    with open(os.path.join(path, local_filename.decode('utf-8')), 'wb') as f:
      for chunk in r.iter_content(chunk_size=1024):
        if chunk: # filter out keep-alive new chunks
          f.write(chunk)
              #f.flush() commented by recommendation from J.F.Sebastian
    return local_filename

  def _download_files(self, path_prefix, files):
    for f in files:
      file_url, file_name = f
      self._download_file(file_url, path_prefix)

  def _download_item_from_directories(self, path_prefix, directories, depth):
    if(depth<=0):
      return
    for directory in directories:
      directory_url, directory_title = directory
      new_prefix = os.path.join(path_prefix, directory_title)
      next_directories, files = self._get_item_from_section(new_prefix, directory)
      self._download_files(new_prefix, files)
      self._download_item_from_directories(new_prefix, next_directories, depth-1)

  def _get_item_from_section(self, path_prefix, section):
    section_url, section_name = section
    self.log("--reading sections: {0}".format(section_name))
    dir_name = mkdir(path_prefix)
    # path_prefix = dir_name
    if(self.blackboard_url not in section_url):
      section_url = self.blackboard_url+section_url
    course_section_resp = self.sess.get(section_url)
    directories = re.findall('<a href="(/webapps/blackboard/content/listContent.jsp?.+?)"><span style=".+?">(.+?)</span>', course_section_resp.text)
    files = re.findall('<a href="(/bbcswebdav.+?)".+?">.+?">(.+)</span>', course_section_resp.text)
    """ files type 1
    <a href="/bbcswebdav/pid-2238145-dt-content-rid-8465171_1/xid-8465171_1" onClick="this.href='/webapps/blackboard/execute/content/file?cmd=view&content_id=_2238145_1&course_id=_87673_1'">
      <span style="color:#000000;">lesson 11</span>
    </a>
    """
    files2 = re.findall('<a href="(/bbcswebdav.+?)".+?">.+?">(.+)[^</span>]</a>', course_section_resp.text)
    """ files type 2
    <a href="/bbcswebdav/pid-2233230-dt-content-rid-8062745_1/xid-8062745_1" target="_blank">
      <img src="https://d1e7kr0efngifs.cloudfront.net/3400.1.0-rel.35+67d71b7/images/ci/ng/cal_year_event.gif" alt="File">
      &nbsp;第十課閱讀材料 (徐復觀).pdf
    </a>
    """
    time.sleep(self.flags.SLEEP_TIME)
    return (directories, (files+files2)) # [(directory_url, directory_name), (file_url, file_name)

  def _get_course_sections(self, course_info):
    course_id, course_code, course_name = course_info
    self.log("reading course: {0}".format(course_name))
    course_url = "{1}/webapps/blackboard/execute/courseMain?course_id={0}".format(course_id, self.blackboard_url)
    course_url_resp = self.sess.get(course_url)
    section_raw = re.findall('<hr>(.+?)<hr>',course_url_resp.text)[0]
    sections = re.findall('<a href="(/webapps/blackboard/content/listContent.jsp?.+?)".+?">.+?">(.+?)</span>', section_raw)
    return sections

  def _init_bb_session(self):
    sess = requests.session()
    # fake header, otherwise they wont care
    sess.headers['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
    # go to starting page
    blackboard_main_resp = sess.get(self.blackboard_url)
    next_url_1 = re.findall('url=(.+)', blackboard_main_resp.text)[0]
    # redirected to login page
    next_url_1 = urllib2.urlparse.unquote(next_url_1)
    login_page_resp = sess.get(next_url_1)
    self.login_page_url = login_page_resp.url
    self.sess = sess

  def _login(self):
    if '@' not in self.username:
      self.username = self.username + self.email_suffix
    form_auth_payload={
      'UserName': self.username,
      'Password': self.password,
      'AuthMethod': "FormsAuthentication"
    }
    self.log("logging in...")
    logging_in_resp = self.sess.post(self.login_page_url, data=form_auth_payload)
    time.sleep(self.flags.SLEEP_TIME)
    next_url_3 = re.findall('action="(.+?)">',logging_in_resp.text)[0]
    SAMLResponse = re.findall('name="SAMLResponse" value="(.+?)" />',logging_in_resp.text)[0]
    resp4 = self.sess.post(next_url_3, data = {'SAMLResponse': SAMLResponse})
    time.sleep(self.flags.SLEEP_TIME)
    self.log("logged in...")

  def _get_bb_userid(self):
    course_url = '{0}/ultra/course'.format(self.blackboard_url)
    course_resp = self.sess.get(course_url)
    userid = re.findall('"id":"(.+?)"', course_resp.text)[0]
    return userid

  def set_auth(self, u, p):
    self.username = u
    self.password = p

  def set_university(self, blackboard_url, email_suffix):
    self.blackboard_url = blackboard_url
    self.email_suffix = email_suffix

  def setFlags():
    pass