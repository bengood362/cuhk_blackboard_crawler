import os
import uuid
import string

def directory_flatten(path):
  for c in '\\/:*?"<>|':
      path = path.replace(c, '-')
  return path

def mkdir(name):
  try:
    if(os.path.exists(name)):
      pass # dir exists
    else:
      os.mkdir(name)
    return name
  except Exception as inst:
    print(inst)
    dir_name = str(name)+str(uuid.uuid4().hex[:8])
    os.mkdir(dir_name)
    return dir_name

def title_print(self, s):
    s = '@ {0} @'.format(s)
    print('@'*len(s))
    print(s)
    print('@'*len(s))

def download_file(url, path, sess):
  try:
    if(blackboard_url not in url):
      url = blackboard_url+url
    resp = sess.get(url, stream=True)
    url = urllib2.urlparse.unquote(resp.url)
    if(platform == "darwin"):
      url = url.encode('latin1')
    print('{0} {1}'.format(path,url))
    local_filename = urllib2.urlparse.unquote(url.split('/')[-1])
    file_size = resp.headers['Content-Length']
    if(int(file_size)>=1024*1024*100):
      while(1):
        download = raw_input("The file {1} is around {0}MB, still download?(y/n)".format(int(file_size)/1024/1024, local_filename))
        if(download.lower() == 'y'):
          break
        elif(download.lower() == 'n'):
          return local_filename
        else:
          print("Please input only y or n!")
    # NOTE the stream=True parameter
    r = resp
    with open(os.path.join(path, local_filename.decode('utf-8')).encode('utf-8'), 'wb') as f:
      for chunk in r.iter_content(chunk_size=1024):
        if chunk: # filter out keep-alive new chunks
          f.write(chunk)
              #f.flush() commented by recommendation from J.F.Sebastian
    return local_filename
  except Exception as inst:
    caller = str(inspect.stack(0)[1][3])
    inst = str(inst)
    print(caller+'\t'+inst)
    return 'error'
