# cuhk_blackboard_crawler

Whenever you want to stop the crawler, press CTRL+C.

## Warranty disclaimer

Unless required by applicable law or agreed to in writing, Licensor provides the Work (and each Contributor provides its Contributions) on an AS IS BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including, without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A PARTICULAR PURPOSE. You are solely responsible for determining the appropriateness of using or redistributing the Work and assume any risks associated with Your exercise of permissions under this License.

## Windows

1. Install python 2.7 from [Here](https://www.python.org/downloads/release/python-2714/), if you are using 64 bit please select Windows x86-64 MSI installer, or else please select Windows x86 MSI installer.
2. During the installation process, please tick "Add python to the PATH", <b>unless you know what you are doing</b>.
3. Press the green button: [Clone or Download], download as zip, and unzip it to somewhere.
4. open the somewhere folder, and hold shift and right click, open CMD at this folder.
5. type `pip install requests` and `python blackboard_crawler.py`.
6. type in your username and password according to instruction, I am not able to receive your username & password using this script.

## OSX

1. Install python 2.7 
2. `pip install requests`
3. `python blackboard_crawler.py`

## Linux

same as OSX

## Android/ iOS

never

## Contribution
* be patient
* increase the sleep time, so that we won't flood blackboard
* file some bugs under [issue](https://github.com/bengood362/cuhk_blackboard_crawler/issues)
* email me of some possible security problem
* create a deployment guideline for non-programmer
* PR any improvement
* test in more environment

## (Possibly) updates
* read file headers(course->section->directories/files->directories/files...) first, instead of read and write together
* GUI & exe for Windows user
* write to tmp_download file and rename later, so that keyboard interupt won't break the file writing
* use XML/ HTML parser instead of regular expression
* proper unit testing
* more reasonable time.sleep location

## FAQ

Tested environment:  

1. OSX & python2
2. ubuntu & python2
3. windows7 & python2

Q: Will you add old blackboard?  
A: No.  
Q: What if blackboard update and break the script?  
A: Maybe I will update it or maybe I won't.  
Q: What if my password leaked using this script?   
A: I will not compensate for any of your loss. No warranty of any kind is provided  
Q: What if ......?  
A: I am not responsible for any of your loss.  
Q: Why is there are some empty folders?  
A: Because the lecturer/ tutor/ professor has opened the course but haven't put any materials inside  