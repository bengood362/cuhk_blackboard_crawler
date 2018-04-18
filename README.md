# cuhk_blackboard_crawler

Normally it can be run with `python blackboard_crawler.py`, but I haven't tested on Linux/ Windows yet.

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
Q: Why is there are some empty folders?  
A: Because the lecturer/ tutor/ professor has opened the course but haven't put any materials inside  