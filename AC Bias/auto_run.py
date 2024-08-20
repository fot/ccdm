"Testing"

import paramiko
import time
import os
import sys
from getpass import getpass, getuser
from selenium import webdriver


def ssh_session():
    "Open an ssh session, then execute command to start script"

    os.system("cls")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # this will automatically add the keys
    attempt = 1

    while True:

        if attempt <= 3:
            try:
                username = getuser()
                print(f"\nEntering SSH session on 131.142.113.13@{username}")
                print(f"  - Username: {username}")
                password = getpass("  - Password: ")
                ssh.connect("131.142.113.13", username=username, password=password)
                print("  - Connection successful!")
                break
            except paramiko.ssh_exception.AuthenticationException:
                print(f"Bad password, please try again! Attempt ({attempt}/3)")
                attempt += 1

        else:
            sys.exit("Too many failed attempts")

    print("""  - Starting "AC_BIAS_HIT_PERSISTANT.py" Tool...""")
    stdin, stdout, stderr = ssh.exec_command('/proj/sot/ska3/flight/bin/python '
                                            '/home/rhoover/python/Code/ccdm/AC\ Bias/'
                                            '"ac_bias_hit_persistent.py"')
    auto_open()
    ssh.exec_command(f"pkill -u {username}")


def auto_open():
    "Auto Open the generated file and refresh every 5 sec"

    url = "//noodle/FOT/engineering/ccdm/Tools/AC_BIAS/Output/ACBIAS_example.html"
    driver = webdriver.Chrome()
    driver.get(url)

    try:
        while True:
            time.sleep(5)
            driver.refresh()
            print("""Tool is running... (Enter "ctrl + c" to exit tool)""")
    except KeyboardInterrupt:
        print("Ending tool execution...")


ssh_session()
