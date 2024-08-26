"Testing"

import paramiko
import time
import os
import sys
from getpass import getpass, getuser
from selenium import webdriver


def ssh_session():
    "Open an ssh session, then execute command to start script"

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
    ssh.exec_command('/proj/sot/ska3/flight/bin/python /home/rhoover/python/Code/ccdm/'
                     'AC\ Bias/components/"ac_bias_hit_persistent.py"')
    pid = get_pid()
    auto_open()
    print(f"  - Killing PID: {pid} on ssh session.")
    ssh.exec_command(f"kill {pid}")


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


def get_pid():
    "Get the PID of the script started on the ssh session"
    base_dir = "//noodle/GRETA/rhoover/python/Code/ccdm/AC Bias/components"

    while True:
        try:
            time.sleep(3) # Allow script startup time
            with open(f"{base_dir}/pid.txt", "r", encoding = "utf-8") as file:
                for line in file:
                    pid = str(line)
                break
        except FileNotFoundError:
            print("  - Error! PID not found yet, trying again in 1 sec...")
            time.sleep(1)

    os.remove(f"{base_dir}/pid.txt")
    print(f"  - PID: {pid} started on ssh session.")
    return pid


def main():
    "Main Execution"
    os.system("cls")
    print("---Welcome to the AC_BIAS_HIT_PERSISTENT Plotter Tool---")
    ssh_session()


main()
