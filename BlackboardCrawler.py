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

# Only developer should change it?
class BCFlags(object):
  SLEEP_TIME=1
  MAX_DEPTH=2
  VERBOSE=True
  IGNORE_SAME=True
  # IGNORE_SAME: ignore same file

# Just a dict with support of middler & get/setattr
class BCPrefs(object):
  @staticmethod
  def default_dict():
    return {'folder_prefix': 'blackboard', 'blackboard_url': 'https://blackboard.cuhk.edu.hk', 'email_suffix': '@link.cuhk.edu.hk', 'folder_name_style': 'CC_ONLY'}
  no_verification = staticmethod(lambda x: True)
  url_check = staticmethod(lambda x: re.match('https?://', str(x)) is not None)
  email_check = staticmethod(lambda x: '@' in str(x))
  folder_style = ['CC_ONLY', 'FULL', 'TERM_AND_CC']
  folder_name_check = staticmethod(lambda x: x in BCPrefs.folder_style)
  test = lambda x: '@' in x
  keys = ['folder_prefix', 'blackboard_url', 'email_suffix', 'folder_name_style']
  prefs_dict = {}
  @staticmethod
  def get_option_vals(key):
    if(key is 'folder_name_style'):
      return BCPrefs.folder_style
    return []
  @staticmethod
  def get_pref_type(key):
    if(key is 'folder_prefix'):
      return 'text'
    elif(key is 'blackboard_url'):
      return 'text'
    elif(key is 'email_suffix'):
      return 'text'
    elif(key is 'folder_name_style'):
      return 'option'
    else:
      return 'text'
  def __init__(self):
    self['folder_prefix']='blackboard'
    self['blackboard_url']='https://blackboard.cuhk.edu.hk'
    self['email_suffix']='@link.cuhk.edu.hk'
    self['folder_name_style']='CC_ONLY'
  def __setitem__(self, key, value):
    if(key not in self.keys):
      # return (False,"{0} not found".format(key)) # Cannot return value in __setitem__...
      raise KeyError("{0} not found".format(key))
    if(key is 'blackboard_url' and not BCPrefs.url_check(value)):
      # return (False,"{0} is not a url".format(value))
      raise Exception("{0} is not a url".format(key))
    if(key is 'email_suffix' and not BCPrefs.email_check(value)):
      # return (False,"{0} is not a email".format(value))
      raise Exception("{0} is not a email".format(value))
    if(key is 'folder_name_style' and not BCPrefs.folder_name_check(value)):
      raise Exception("{0} is not a folder style setting".format(value))
    self.prefs_dict[key]=value
    # return (True,'')
  def __getitem__(self, key):
    return self.prefs_dict[key]
  def __delitem__(self, key):
    del self.prefs_dict[key]
  def __setattr__(self, key, value):
    self.__setitem__(key, value)
  def __getattr__(self, key):
    return self.prefs_dict[key]
  def __str__(self):
    return self.prefs_dict.__str__()
  def __repr__(self):
    return self.prefs_dict.__str__()

class BlackboardCrawler:
  flags = BCFlags()
  prefs = BCPrefs()
  def __init__(
    self,
    username,
    password,
  ):
    self.username = username
    self.password = password

  def updatePrefs(self, key, value):
    self.prefs[key]=value

  def log(self, s, t=0, coding='utf-8'):
    if(self.flags.VERBOSE or t!=0):
      curframe = inspect.currentframe()
      calframe = inspect.getouterframes(curframe, 2)
      caller = calframe[1][3]
      if(isinstance(s,unicode)):
        print(u'{0}:{1}'.format(caller.decode(coding), s))
      else:
        print('{0}:{1}'.format(caller.decode(coding), s))

  def title_print(self, s):
    s = '@ {0} @'.format(s)
    print('@'*len(s))
    print(s)
    print('@'*len(s))

  # return True/ False
  def login(self):
    self._init_bb_session()
    self._login()
    self.userid = self._get_bb_userid()
    mkdir(self.prefs.folder_prefix)

  # return list of courses
  # [course_id, course_code, display_name]
  def get_courses(self):
    if(not self.userid):
      raise AuthenticationException("Not logged in.")
    self.log("getting courses...")
    courses_resp = self.sess.get("{0}/learn/api/v1/users/{1}/memberships?expand=course.instructorsMembership,course.effectiveAvailability,course.permissions,courseRole&limit=10000&organization=false".format(self.prefs.blackboard_url, self.userid))
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

  def get_metadata_from_file(self, file_name):
    try:
      if(not os.path.isfile(file_name)):
        return {'size': -1}
      size = os.path.getsize(file_name)
    except Exception as inst:
      self.log('err: {0}'.format(inst))
      return {'size': -1}
    return {'size': size}

  # def get_metadata_from_url(self, url):
  #   try:
  #     resp = self.sess.get(url)
  #     headers = resp.headers
  #     self.log("headers: {0}".format(headers))
  #     size = int(headers['Content-Length'])
  #   except Exception as inst:
  #     self.log('url: {0}'.format(url))
  #     self.log('err: {0}'.format(inst))
  #     return {'size': -1}
  #   return {'size': size}

  def file_same(self, file_name, file_size):
    if(not self.flags.IGNORE_SAME):
      return False
    metadata_file = self.get_metadata_from_file(file_name)
    # DEBUG: return True if size same, return False if not
    # self.log(metadata_file)
    # self.log(file_size)
    metadata_file['size'] = int(metadata_file['size'])
    file_size = int(file_size)
    if(metadata_file['size']<0 or file_size<0):
      return False
    return (metadata_file['size'] == file_size)

  def make_course_dir(self, course_info):
    course_id, course_code, course_name = course_info
    #course_code: 2018R1-CSCI4180
    if(self.prefs.folder_name_style == 'CC_ONLY'):
      course_code = course_code.split('-')[1]
      if(not reduce(lambda x,y: x and y, map(lambda x: not x.isdigit(), course_code))):
        while(not course_code[-1].isdigit()):
          course_code = course_code[:-1]
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_code))
    elif(self.prefs.folder_name_style == 'FULL'):
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_name))
    elif(self.prefs.folder_name_style == 'TERM_AND_CC'):
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_code))
    else:
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_code))
    return dir_name

  def _download(self, courses_info):
    for course_info in courses_info:
      course_id, course_code, course_name = course_info
      sections = self._get_course_sections(course_info)
      dirname = self.make_course_dir(course_info)
      # Ask if the user want to continue download if the folder exists?
      for section in sections:
        section_title = section[1]
        path_prefix = os.path.join(dirname, section_title)
        directories, files = self._get_item_from_section(path_prefix, section)
        self._download_item_from_directories(path_prefix, directories, self.flags.MAX_DEPTH)
        self._download_files(path_prefix, files)
        time.sleep(self.flags.SLEEP_TIME)

  def _download_file(self, url, path):
    valid_chars = "-_.()\\/ %s%s" % (string.ascii_letters, string.digits)
    path = ''.join(c for c in path if c in valid_chars)
    path = path.decode('utf-8')
    if(self.prefs.blackboard_url not in url):
      url = self.prefs.blackboard_url+url
    resp = self.sess.get(url, stream=True)
    headers = resp.headers
    url = urllib2.urlparse.unquote(resp.url)
    if(platform == "darwin"):
      url = url.encode('latin1')
    self.log('path: {0}'.format(path))
    self.log('url: {0}'.format(url))
    self.log("header: {0}".format(resp.headers))
    header_content = headers['Content-Disposition']
    # self.log('local_filename1: {0}'.format(repr(header_content)))
    coding, local_filename = re.findall("[*]=(.+)''(.+)", header_content)[0]
    # self.log('coding: {0}'.format(repr(coding)))
    # self.log('repr local_filename2: {0}'.format(repr(local_filename)))
    local_filename_unquoted = urllib2.unquote(local_filename)
    self.debug = local_filename_unquoted
    # self.log('local_filename3: {0}'.format(local_filename_unquoted))
    # self.log('str local_filename3: {0}'.format(str(local_filename_unquoted)))
    # self.log('repr local_filename3: {0}'.format(repr(local_filename_unquoted)))
    # self.log('type local_filename3: {0}'.format(type(local_filename_unquoted)))
    final_local_filename = local_filename_unquoted.decode(coding)
    # final_local_filename = local_filename_unquoted
    # self.log(u'local_filename4: {0}'.format(final_local_filename))
    # self.log(u'repr local_filename4: {0}'.format(repr(final_local_filename)))
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
    if(not self.file_same(os.path.join(path, final_local_filename), file_size)):
      self.log(u"Downloading {0}".format(final_local_filename))
      r = resp
      with open(os.path.join(path, final_local_filename), 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
          if chunk: # filter out keep-alive new chunks
            f.write(chunk)
            f.flush()
            #f.flush() commented by recommendation from J.F.Sebastian
    else:
      self.log(u'File are found to be same: {0}'.format(final_local_filename))
    return final_local_filename

  def _download_files(self, path_prefix, files):
    self.log(repr(files))
    for f in files:
      file_url, file_name = f
      if(isinstance(file_name,unicode)):
        self.log(u'url: {0} {1}'.format(file_url, file_name))
      else:
        self.log(u'url: {0} {1}'.format(file_url, file_name.decode('utf-8')))
      self._download_file(file_url, path_prefix)

  def _download_item_from_directories(self, path_prefix, directories, depth):
    if(depth<=0):
      return
    for directory in directories:
      directory_url, directory_title = directory
      self.log('reading: {0} {1}'.format(directory_url, directory_title))
      new_prefix = os.path.join(path_prefix, directory_title)
      next_directories, files = self._get_item_from_section(new_prefix, directory)
      self._download_files(new_prefix, files)
      self._download_item_from_directories(new_prefix, next_directories, depth-1)

  def _get_item_from_section(self, path_prefix, section):
    section_url, section_name = section
    self.log("----reading sections: {0}".format(section_name))
    dir_name = mkdir(path_prefix)
    # path_prefix = dir_name
    if(self.prefs.blackboard_url not in section_url):
      section_url = self.prefs.blackboard_url+section_url
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
    course_url = "{1}/webapps/blackboard/execute/courseMain?course_id={0}".format(course_id, self.prefs.blackboard_url)
    course_url_resp = self.sess.get(course_url)
    section_raw = re.findall('<hr>(.+?)<hr>',course_url_resp.text)[0]
    sections = re.findall('<a href="(/webapps/blackboard/content/listContent.jsp?.+?)".+?">.+?">(.+?)</span>', section_raw)
    return sections

  def _init_bb_session(self):
    sess = requests.session()
    # fake header, otherwise they wont care
    sess.headers['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
    # go to starting page
    blackboard_main_resp = sess.get(self.prefs.blackboard_url)
    next_url_1 = re.findall('url=(.+)', blackboard_main_resp.text)[0]
    # redirected to login page
    next_url_1 = urllib2.urlparse.unquote(next_url_1)
    login_page_resp = sess.get(next_url_1)
    self.login_page_url = login_page_resp.url
    self.sess = sess

  def _login(self):
    if '@' not in self.username:
      self.username = self.username + self.prefs.email_suffix
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
    course_url = '{0}/ultra/course'.format(self.prefs.blackboard_url)
    course_resp = self.sess.get(course_url)
    userid = re.findall('"id":"(.+?)"', course_resp.text)[0]
    return userid

  def set_auth(self, u, p):
    self.username = u
    self.password = p

  def setFlags():
    pass