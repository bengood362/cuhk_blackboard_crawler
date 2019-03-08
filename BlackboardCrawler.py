#!coding: utf-8
import json
import time
import requests
import urllib.request as urllib2
import traceback
import re
import os
import uuid # in case the error happens
from getpass import getpass
# import xml.etree.ElementTree as ET
# XML parser is not used because the fucking &ndash;
import inspect # debugging purpose
import string
from sys import platform, stdout
from utils import mkdir, directory_flatten, title_print

# Course data: https://blackboard.cuhk.edu.hk/learn/api/public/v1/courses/_117025_1
# Course contents: https://blackboard.cuhk.edu.hk/learn/api/public/v1/courses/_117025_1/contents
# Courses for user: https://blackboard.cuhk.edu.hk/learn/api/public/v1/users/_225417_1/courses

class AuthenticationException(Exception):
  pass

def map_l(*args):
  return list(map(*args))

def reduce(lambda_expression, input_arr):
  if(len(input_arr) > 1):
    t = input_arr[0]
    for val in input_arr[1:]:
      t = lambda_expression(t, val)
    return t

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
  def BCP_default_dict():
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
  def BCP_get_option_vals(key):
    if(key is 'folder_name_style'):
      return BCPrefs.folder_style
    return []
  @staticmethod
  def BCP_get_pref_type(key):
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
    parent
  ):
    self.username = username
    self.password = password
    self.parent = parent

  def BC_updatePrefs(self, key, value):
    self.prefs[key]=value

  def BC_log(self, s, t=0, coding='utf-8'):
    if(self.flags.VERBOSE or t!=0):
      curframe = inspect.currentframe()
      calframe = inspect.getouterframes(curframe, 2)
      caller = calframe[1][3]
      self.parent.log('{0}:{1}'.format(caller, s))

  # return True/ False
  def BC_login(self):
    self._BC_init_bb_session()
    self._BC_login()
    self.userid = self._BC_get_bb_userid()
    mkdir(self.prefs.folder_prefix)

  # return list of courses
  # [course_id, course_code, display_name]
  def BC_get_courses(self):
    if(not self.userid):
      raise AuthenticationException("Not logged in.")
    self.BC_log("getting courses...")

    courses_info = []
    courses_resp = self.sess.get("{0}/learn/api/public/v1/users/{1}/courses".format(self.prefs.blackboard_url, self.userid))
    courses = courses_resp.json().get('results', [])
    course_ids = map(lambda x: (x.get('courseId', "NO COURSE ID"), x.get('availability', {})), courses)
    for course_id, availability in course_ids:
      if(availability.get('available', "Disabled") == "Yes"):
        course_resp = self.sess.get("{0}/learn/api/public/v1/courses/{1}".format(self.prefs.blackboard_url, course_id))
        course_info = course_resp.json()
        if(course_info.get('availability',{}).get('available', 'No') == "Yes"):
          course_id = course_info.get('id', "NO ID")
          course_code = course_info.get('courseId', "NO COURSE CODE")
          display_name = course_info.get('name', "NO NAME")
          course_code = course_code.split('-')[1] if len(course_code.split('-'))>=2 else course_code
          courses_info.append((course_id, course_code, display_name))
    # for course in courses:
    #   if(course['course']['isAvailable']):
    #     content_id = course['id']
    #     course_id = course['course']['id']
    #     course_code = course['course']['courseId']
    #     display_name = course['course']['displayName']
    #     courses_info.append((course_id, course_code, display_name))
    self.BC_log("finish getting courses...")
    courses_info = sorted(courses_info, key=lambda x: '0' if not x[2][0].isdigit() else x[2], reverse=True)
    return courses_info #[course_id, course_code, course_name]

  # download courses
  def BC_download(self, selected_courses_info):
    # Un-enumerate it
    selected_courses_info = map_l(lambda x: x[1], selected_courses_info)
    self._BC_download(selected_courses_info)

  def BC_get_metadata_from_file(self, file_name):
    try:
      if(not os.path.isfile(file_name)):
        return {'size': -1}
      size = os.path.getsize(file_name)
    except Exception as inst:
      self.log(traceback.format_exc())
      self.BC_log('err: {0}'.format(inst))
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

  def BC_file_same(self, file_name, file_size):
    if(not self.flags.IGNORE_SAME):
      return False
    metadata_file = self.BC_get_metadata_from_file(file_name)
    # DEBUG: return True if size same, return False if not
    # self.log(metadata_file)
    # self.log(file_size)
    metadata_file['size'] = int(metadata_file['size'])
    file_size = int(file_size)
    if(metadata_file['size']<0 or file_size<0):
      return False
    return (metadata_file['size'] == file_size)

  def BC_make_course_dir(self, course_info):
    course_id, course_code, course_name = course_info
    print("{0}; {1}; {2}".format(self.prefs.folder_prefix, course_code, os.path.join(self.prefs.folder_prefix, course_code)))
    #course_code: 2018R1-CSCI4180
    if(self.prefs.folder_name_style == 'CC_ONLY'):
      course_code = course_code.split('-')[1] if len(course_code.split('-'))>=2 else course_code
      if(not reduce(lambda x,y: x and y, map_l(lambda x: not x.isdigit(), course_code))):
        while(not course_code[-1].isdigit()):
          course_code = directory_flatten(course_code[:-1])
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_code))
    elif(self.prefs.folder_name_style == 'FULL'):
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_name))
    elif(self.prefs.folder_name_style == 'TERM_AND_CC'):
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_code))
    else:
      dir_name = mkdir(os.path.join(self.prefs.folder_prefix, course_code))
    return dir_name

  def _BC_download(self, courses_info):
    for course_info in courses_info:
      course_id, course_code, course_name = course_info
      sections = self._BC_get_course_sections(course_info)
      dirname = self.BC_make_course_dir(course_info)
      # Ask if the user want to continue download if the folder exists?
      for section in sections:
        section_title = directory_flatten(section[1])
        # print '---------------------'
        # print dirname, section_title, os.path.join(dirname, section_title)
        # print '---------------------'
        path_prefix = os.path.join(dirname, section_title)
        directories, files = self._BC_get_item_from_section(path_prefix, section)
        self._BC_download_item_from_directories(path_prefix, directories, self.flags.MAX_DEPTH)
        self._BC_download_files(path_prefix, files)
        time.sleep(self.flags.SLEEP_TIME)

  def _BC_download_file(self, url, path):
    if(self.prefs.blackboard_url not in url):
      url = self.prefs.blackboard_url+url
    resp = self.sess.get(url, stream=True)
    headers = resp.headers
    url = urllib2.unquote(resp.url)
    if(platform == "darwin"):
      url = url.encode('latin1')
    self.BC_log('path: {0}'.format(path))
    self.BC_log('url: {0}'.format(url))
    self.BC_log("header: {0}".format(resp.headers))
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
    final_local_filename = local_filename_unquoted
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
    if(not self.BC_file_same(os.path.join(path, final_local_filename), file_size)):
      self.BC_log(u"Downloading {0}".format(final_local_filename))
      r = resp
      with open(os.path.join(path, final_local_filename), 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
          if chunk: # filter out keep-alive new chunks
            f.write(chunk)
            f.flush()
            #f.flush() commented by recommendation from J.F.Sebastian
    else:
      self.BC_log(u'File are found to be same: {0}'.format(final_local_filename))
    return final_local_filename

  def _BC_download_files(self, path_prefix, files):
    self.BC_log(repr(files))
    for f in files:
      file_url, file_name = f
      self.BC_log('url: {0} {1}'.format(file_url, file_name))
      self._BC_download_file(file_url, path_prefix)

  def _BC_download_item_from_directories(self, path_prefix, directories, depth):
    if(depth<=0):
      return
    for directory in directories:
      directory_url, directory_title = directory
      directory_title = directory_flatten(directory_title[:64])
      self.BC_log(u'reading: {0} {1}'.format(directory_url, directory_title))
      new_prefix = os.path.join(path_prefix, directory_title)
      next_directories, files = self._BC_get_item_from_section(new_prefix, directory)
      self._BC_download_files(new_prefix, files)
      self._BC_download_item_from_directories(new_prefix, next_directories, depth-1)

  def _BC_get_item_from_section(self, path_prefix, section):
    section_url, section_name = section
    section_name = section_name[:64]
    self.BC_log('----reading sections: {0}'.format(section_name))
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

  def _BC_get_course_sections(self, course_info):
    course_id, course_code, course_name = course_info
    self.BC_log('reading course: {0}'.format(course_name))
    course_url = "{1}/webapps/blackboard/execute/courseMain?course_id={0}".format(course_id, self.prefs.blackboard_url)
    course_url_resp = self.sess.get(course_url)
    print(course_url)
    print(course_url_resp.text)
    section_raw = re.findall('<hr>(.+?)<hr>',course_url_resp.text)[0]
    sections = re.findall('<a href="(/webapps/blackboard/content/listContent.jsp?.+?)".+?">.+?">(.+?)</span>', section_raw)
    return sections

  def _BC_init_bb_session(self):
    sess = requests.session()
    # fake header, otherwise they wont care
    sess.headers['User-Agent']='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
    # go to starting page
    blackboard_main_resp = sess.get(self.prefs.blackboard_url)
    next_url_1 = re.findall('url=(.+)', blackboard_main_resp.text)[0]
    # redirected to login page
    next_url_1 = urllib2.unquote(next_url_1)
    login_page_resp = sess.get(next_url_1)
    self.login_page_url = login_page_resp.url
    self.sess = sess

  def _BC_login(self):
    if '@' not in self.username:
      self.username = self.username + self.prefs.email_suffix
    form_auth_payload={
      'UserName': self.username,
      'Password': self.password,
      'AuthMethod': "FormsAuthentication"
    }
    self.BC_log("logging in...")
    logging_in_resp = self.sess.post(self.login_page_url, data=form_auth_payload)
    time.sleep(self.flags.SLEEP_TIME)
    next_url_3 = re.findall('action="(.+?)">',logging_in_resp.text)[0]
    SAMLResponse = re.findall('name="SAMLResponse" value="(.+?)" />',logging_in_resp.text)[0]
    resp4 = self.sess.post(next_url_3, data = {'SAMLResponse': SAMLResponse})
    time.sleep(self.flags.SLEEP_TIME)
    self.BC_log("logged in...")

  def _BC_get_bb_userid(self):
    course_url = '{0}/ultra/course'.format(self.prefs.blackboard_url)
    course_resp = self.sess.get(course_url)
    userid = re.findall('"id":"(.+?)"', course_resp.text)[0]
    return userid

  def BC_set_auth(self, u, p):
    self.username = u
    self.password = p

  def BC_setFlags():
    pass
