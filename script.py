import csv
import re
from pprint import pprint
from time import sleep

import requests
import speedtest
from collections import deque
import datetime

RESTART_MESSAGE = 'Restarting router'
RECENT_REBOOT_MESSAGE = 'Recently rebooted'

default_interval = 60 * 5  # 5 minutes
restart_interval = 60 * 10  # 10 minutes

session_key_regex = re.compile(r'url:"sky_rebootCPE\.cgi\?todo=reboot&sessionKey=(.*)",')

session_key_url = 'http://192.168.0.1/sky_rebootCPE.html'
reboot_url = 'http://192.168.0.1/sky_rebootCPE.cgi?todo=reboot&sessionKey=%s'
sky_auth = ('admin', 'qqQQ11!!')

def check_previous_result(result):
    print 'Taking a look at the previous result..'

    with open('results.csv', 'rb') as f:
        reader = csv.reader(f)
        tail = deque(reader, 1)[0]

        if tail:
            print('Previous result was:')
            print tail
            print 'Download: {} Mbps / Upload: {}Mbps'.format(
                float(tail[1]) / 1000000,
                float(tail[2]) / 1000000,
            )

            if tail[4] in [RESTART_MESSAGE, RECENT_REBOOT_MESSAGE]:
                print "The router was recently restarted, not doing it again."
                write_result(result, RECENT_REBOOT_MESSAGE)
                return default_interval

            if tail[1] == '0.0' and tail[2] == '0.0':
                print('Internet has been down for at least 5 minutes, restarting the router..')
                return restart_router(result)

    # If we made it here, the internet hasn't been download for long enough yet.
    write_result(result, 'Not restarting yet')

    # How long until the next event should be sent?
    return default_interval

def restart_router(result):
    write_result(result, RESTART_MESSAGE)

    key_response = requests.get(session_key_url, auth=sky_auth)
    session_key = session_key_regex.search(key_response.text)

    if session_key:
        session_key = session_key.group(1)
        restart_response = requests.post(reboot_url % session_key, auth=sky_auth)

    return restart_interval

def print_sleep(sleep_timer):
    while sleep_timer > 0:
        print '\rSleeping for {} more seconds.'.format(sleep_timer),
        sleep(1)
        sleep_timer -= 1

    return


def write_result(result, message=None):
    result['message'] = message or ''

    with open('results.csv', 'ab') as f:
        writer = csv.writer(f)
        writer.writerow([
            result['timestamp'],
            result['download'],
            result['upload'],
            result['ping'],
            result['message'],
        ])

def run_test():
    servers = [1234] # Milton Keynes

    try:
        s = speedtest.Speedtest()

        print 'Getting servers..'
        s.get_servers(servers)

        print 'Getting best server..'
        s.get_best_server()

        print "Running download test..."
        s.download()

        print "Running upload test..."
        s.upload(pre_allocate=False)

        results = s.results.dict()
        print 'Download: {} Mbps / Upload: {}Mbps'.format(
            results['download'] / 1000000,
            results['upload'] / 1000000,
        )
    except:
        print 'Failed to run speed test, internet is likely down.'
        results = {
            'download': 0.0,
            'upload': 0.0,
            'timestamp': '%sZ' % datetime.datetime.utcnow().isoformat(),
            'ping': '0'
        }

    if results['download'] == 0.0 and results['upload'] == 0.0:
        print 'I think the internet is down..'
        return check_previous_result(results)

    write_result(results, 'Test succeeded')

    # How long until the next event should be sent?
    return default_interval

def main():
    while True:
        print 'Running test..'
        sleep_timer = run_test()

        print 'Sleeping..'
        print_sleep(sleep_timer)

if __name__ == '__main__':
    main()
