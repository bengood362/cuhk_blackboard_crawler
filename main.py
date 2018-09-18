#!coding: utf-8
# main.py
from Tkinter import *
import BlackboardCrawler
import inspect

class Application(Frame):
  def initialize(self):
    self.login_button = Button(self)
    self.login_button['text'] = "Login"
    self.login_button['command'] = self.create_login
    self.login_button.pack(ipadx=10, ipady=10)
    self.option_button = Button(self)
    self.option_button['text'] = "Options"
    self.option_button['command'] = self.create_option
    self.option_button.pack(ipadx=10, ipady=10)
    self.debug_button = ''
    self.debug_button2 = ''
    self.blackboard_options_update = {'folder_prefix': 'blackboard', 'blackboard_url': 'https://blackboard.cuhk.edu.hk', 'email_suffix': '@link.cuhk.edu.hk'}
    # self.debug_button = Button(self)
    # self.debug_button['text'] = "Debug"
    # self.debug_button['command'] = lambda: self._prompt_yesno(title='I am a prompt', text='haha\nThis is line 2', attr='b')
    # self.debug_button.pack(ipadx=10, ipady=10)
    # self.debug_button2 = Button(self)
    # self.debug_button2['text'] = "Debug2"
    # self.debug_button2['command'] = lambda: self.print_attr('blackboard_options_update')
    # self.debug_button2.pack(ipadx=10, ipady=10)
    self.startup_buttons = [self.login_button, self.option_button, self.debug_button, self.debug_button2]

  def create_option(self):
    self._prompt_form(
      keys=BlackboardCrawler.BCPrefs.keys,
      default_vals=map(lambda x: self.blackboard_options_update[x], BlackboardCrawler.BCPrefs.keys),
      yes_handler=lambda result: setattr(self, 'blackboard_options_update', result)
    )
    print(self.blackboard_options_update)

  def create_login(self):
    def login(event=None):
      username = self.login_frame.username_entry.get()
      password = self.login_frame.password_entry.get()
      self.bc = BlackboardCrawler.BlackboardCrawler(username, password)
      for (key,val) in self.blackboard_options_update.items():
        self.bc.updatePrefs(key, val)
      self.login_popup = Toplevel()
      self.login_popup.geometry('200x100')
      self.login_popup.grab_set()
      self.login_popup.confirm_button = Button(self.login_popup)
      self.login_popup.confirm_button['text'] = 'Continue'
      self.login_popup.confirm_button['command'] = lambda: [self.login_popup.grab_release(), self.login_popup.destroy(), self.login_frame.destroy()]
      self.login_popup.message_label = Label(self.login_popup)
      self.login_popup.message_label.grid(row=0, column=0)
      self.login_popup.confirm_button.grid(row=1, column=0)
      try:
        self.bc.login()
        self.login_popup.title("Success")
        self.login_popup.message_label['text'] = "Login successfully"
        self.login_frame.destroy()
        self.login_success()
      except Exception as inst:
        self.log(inst)
        self.login_popup.title("Failed")
        self.login_popup.message_label['text'] = str(inst)
        self.login_unsuccess()

    self.login_frame = Toplevel(self)
    self.login_frame.title('Login')
    self.login_frame.geometry('400x300')

    self.login_frame.username_label = Label(self.login_frame)
    self.login_frame.password_label = Label(self.login_frame)
    self.login_frame.username_label['text'] = 'username: '
    self.login_frame.password_label['text'] = 'password: '

    self.login_frame.username_entry = Entry(self.login_frame)
    self.login_frame.password_entry = Entry(self.login_frame,show='*')

    self.login_frame.confirm_button = Button(self.login_frame)
    self.login_frame.cancel_button = Button(self.login_frame)
    self.login_frame.confirm_button['text'] = 'Login'
    self.login_frame.confirm_button['command'] = login
    self.login_frame.cancel_button['text'] = 'Cancel'
    self.login_frame.cancel_button['command'] = self.login_frame.destroy

    self.login_frame.username_label.grid(row=0)
    self.login_frame.password_label.grid(row=1)
    self.login_frame.username_entry.grid(row=0, column=1)
    self.login_frame.password_entry.grid(row=1, column=1)
    self.login_frame.confirm_button.grid(row=3, column=0)
    self.login_frame.cancel_button.grid(row=3, column=1)

    self.login_frame.bind("<Return>", login)

  def download_success(self):
    self._prompt(title="Success", text='Download successfully')

  def download_unsuccess(self, reason=''):
    self._prompt(title="Unsuccess", text='Download failed: {0}'.format(reason))

  def login_success(self):
    self.bc.log('login_success')
    for button in self.startup_buttons:
      if(button and isinstance(button,Button)):
        button.destroy()
    del self.startup_buttons
    self.show_courses()

  def show_courses(self):
    def download(event=None):
      self.bc.log("download clicked")
      course_download = filter(lambda (i, v): self.course_bool_var[i].get(), list(enumerate(self.courses)))
      try:
        self.bc.download(course_download)
        self.download_success()
      except Exception as inst:
        self.log(inst)
        self.download_unsuccess(inst)
    def select_all(event=None):
      self.bc.log("select all clicked")
      for cbv in self.course_bool_var:
        cbv.set(1)
    def select_this_sem(event=None):
      for i in range(len(self.course_label)):
        cl = self.course_label[i]
        text = cl['text']
        if('2018R1' in text):
          cbv = self.course_bool_var[i]
          cbv.set(1)
    self.master.geometry('1000x500')
    self.courses = self.bc.get_courses()
    self.course_checkbox = []
    self.course_label = []
    self.course_bool_var = []
    self.grid_columnconfigure(1, weight=0)
    self.grid_columnconfigure(1, weight=1)
    for i in range(len(self.courses)):
      self.bc.log('rendering {0}'.format(self.courses[i][2]))
      course = self.courses[i]
      (course_id, course_code, display_name) = course
      bool_var = BooleanVar()
      course_checkbox = Checkbutton(self, variable=bool_var)
      course_label = Label(self)
      self.course_checkbox.append(course_checkbox)
      self.course_label.append(course_label)
      self.course_bool_var.append(bool_var)
      course_label['text'] = display_name
      course_checkbox.grid(row=i, column=0, sticky=W, padx=5, columnspan=1)
      course_label.grid(row=i, column=1, sticky=W, padx=5, columnspan=1)
    self.download_button = Button(self)
    self.download_button['text'] = 'Download'
    self.download_button['command'] = download
    self.download_button.grid(row=(i+1), column=0)
    self.select_all_button = Button(self)
    self.select_all_button['text'] = 'Select All'
    self.select_all_button['command'] = select_all
    self.select_all_button.grid(row=(i+1), column=1)
    self.select_this_sem_button = Button(self)
    self.select_this_sem_button['text'] = 'Select this sem'
    self.select_this_sem_button['command'] = select_this_sem
    self.select_this_sem_button.grid(row=(i+1), column=2)

    self.bc.log('finish login_success')

  def login_unsuccess(self):
    self.bc.log('login_unsuccess')
    self._prompt(text="login unsuccessful")
    self.bc.log('finish login_unsuccess')

  def log(self, s, t=0, coding='utf-8'):
    VERBOSE = True if getattr(self,'bc') is None else self.bc.flags.VERBOSE
    if(VERBOSE or t!=0):
      curframe = inspect.currentframe()
      calframe = inspect.getouterframes(curframe, 2)
      caller = calframe[1][3]
      if(isinstance(s,unicode)):
        print u'{0}:{1}'.format(caller.decode(coding), s)
      else:
        print '{0}:{1}'.format(caller.decode(coding), s)

  def _prompt(self, geometry='200x100', title='Prompt', text='content'):
    self.prompt = Toplevel(self)
    self.prompt.geometry(geometry)
    self.prompt.title(title)

    self.prompt.text_label = Label(self.prompt)
    self.prompt.text_label['text'] = text

    self.prompt.confirm_button = Button(self.prompt)
    self.prompt.confirm_button['text'] = "OK"
    self.prompt.confirm_button['command'] = lambda: [self.prompt.grab_release(), self.prompt.destroy()]

    self.prompt.grab_set()
    self.prompt.text_label.pack(ipadx=10, ipady=10)
    self.prompt.confirm_button.pack()

  def _prompt_yesno(self, geometry='400x300', title='Prompt', text='content', yes_text='Yes', no_text='No', attr='last_choice'):
    self.prompt_yesno = Toplevel(self)
    self.prompt_yesno.geometry(geometry)
    self.prompt_yesno.title(title)

    self.prompt_yesno.text_label = Label(self.prompt_yesno)
    self.prompt_yesno.text_label['text'] = text

    self.prompt_yesno.yes_button = Button(self.prompt_yesno)
    self.prompt_yesno.yes_button['text'] = yes_text
    self.prompt_yesno.yes_button['command'] = lambda: [self.prompt_yesno.grab_release(), setattr(self,attr,1), self.prompt_yesno.destroy()]
    self.prompt_yesno.no_button = Button(self.prompt_yesno)
    self.prompt_yesno.no_button['text'] = no_text
    self.prompt_yesno.no_button['command'] = lambda: [self.prompt_yesno.grab_release(), setattr(self,attr,0), self.prompt_yesno.destroy()]

    self.prompt_yesno.grab_set()
    self.prompt_yesno.text_label.grid(row=0, columnspan = 2, ipadx=10, ipady=10)
    self.prompt_yesno.yes_button.grid(row=1, column=0)
    self.prompt_yesno.no_button.grid(row=1, column=1)

  def _prompt_form(self, geometry='400x300', title='Prompt Form', keys=['test1', 'test2'], default_vals=['test_val1', 'test_val2'], yes_text='Confirm', no_text='Cancel', yes_handler=None, no_handler=None):
    self.prompt_form = Toplevel(self)
    self.prompt_form.geometry(geometry)
    self.prompt_form.title(title)
    textlabels = []
    entries = []
    for i in range(len(keys)):
      key = keys[i]
      default_val = default_vals[i]
      tl = Label(self.prompt_form)
      tl['text'] = key
      en=Entry(self.prompt_form)
      en.insert(END, default_val)
      tl.grid(row=i, column=0)
      en.grid(row=i, column=1)
      textlabels.append(tl)
      entries.append(en)
    def get_result(keys, entries):
      result = {}
      for (key,en) in zip(keys, entries):
        result[key]=en.get()
      return result
    self.prompt_form.yes_button = Button(self.prompt_form)
    self.prompt_form.yes_button['text'] = yes_text
    self.prompt_form.yes_button['command'] = lambda: [self.prompt_form.grab_release(), yes_handler(get_result(keys, entries)) if yes_handler is not None else None, self.prompt_form.destroy()]
    self.prompt_form.no_button = Button(self.prompt_form)
    self.prompt_form.no_button['text'] = no_text
    self.prompt_form.no_button['command'] = lambda: [self.prompt_form.grab_release(), no_handler(get_result(keys, entries)) if no_handler is not None else None, self.prompt_form.destroy()]

    self.prompt_form.grab_set()
    self.prompt_form.yes_button.grid(row=i+1, column=0)
    self.prompt_form.no_button.grid(row=i+1, column=1)

  def print_attr(self, attr):
    print getattr(self, attr)

  def __init__(self, master):
    Frame.__init__(self, master)
    self.pack()
    self.initialize()

root = Tk()
root.title('Blackboard Crawler authored by Ben Chan')
root.geometry('600x400')
app = Application(master=root)
app.mainloop()
try:
  root.destroy()
except:
  pass