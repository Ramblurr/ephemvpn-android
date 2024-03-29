#!/usr/bin/env python
"""Launches ephemeral VPNs on EC2

Your AWS credentials must be passed via the -a and -s arguments, or will be
read from ~/.ephemvpnrc (see ephemvpnrc.sample). By default it launches an
IPSEC vpn in Europe.

The supported VPNs config scripts auto generate as much config as possible,
but can be overriden with ~/.ephemvpnrc.

An identity file is not needed by every VPN type, but a keypair name is.
Just provide the name of the keypair with -I.
When using -i, if your identity file's file name minus the extension is not
the name of the key, then set -I too.

The running time can be expressed explicitly or with natural language.
Examples:

    -t 15:00           terminates at 3pm
    -t 1h              terminates one hour from launch
    -t 'next tuesday'  terminates next tuesday at midnight

"""
__LICENSE__ = """
Copyright (c) 2013 - Casey Link <unnamedrambler@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import logging as log

log.basicConfig(filename="/sdcard/ephemvpn.log", level=log.DEBUG)

import sys
import os
sys.path.append(os.getcwd()+'/libs')

import argparse
import getpass
import time
import datetime
import math
import ConfigParser
import parsedatetime

import ephemvpn
from ephemvpn import configuration as config
from ephemvpn import vpntypes, launch, configure
from ephemvpn.timehelpers import readable_delta


def confirm(prompt=None, resp=False):
    """prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.

    >>> confirm(prompt='Create Directory?', resp=True)
    Create Directory? [y]|n:
    True
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y:
    False
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: y
    True

    """

    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')
    else:
        prompt = '%s [%s]|%s: ' % (prompt, 'n', 'y')

    while True:
        ans = raw_input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print 'please enter y or n.'
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False

def _parse_conf(path):
    c = ConfigParser.ConfigParser()
    c.read([path])

    try:
        config.AWS_API_KEY = c.get('amazon', 'AWS_API_KEY')
        config.AWS_SECRET_KEY = c.get('amazon', 'AWS_SECRET_KEY')
        config.AWS_KEY_FILE= c.get('amazon', 'AWS_KEY_FILE')
        config.LOCAL_AWS_KEY_FILE = c.get('amazon', 'LOCAL_AWS_KEY_FILE')
    except ConfigParser.NoSectionError:
        pass

    return c

def _parse_running_time(running_time):
    cal               = parsedatetime.Calendar()
    shutdown_t,result = cal.parse(running_time)

    # thu feb 20 14:50:00 1997
    d_sec      = time.mktime(shutdown_t) - time.time()
    d_min      = int(math.ceil(d_sec)/60)

    return d_min, shutdown_t



def _confirm_time(shutdown_t):
    now               = datetime.datetime.now()
    # thu feb 20 14:50:00 1997
    nice_fmt   = '%a %b %d %H:%M %Y'
    human_date = time.strftime(nice_fmt, shutdown_t)
    fuzzy_date = readable_delta(now, shutdown_t)

    log.info("the vpn will be released into the ether %s after boot\n(probably around %s)" % (fuzzy_date,human_date))
    return confirm("proceed?", resp=False)

def _gen_config(path):
    if os.path.exists(path):
        log.error("Error: config file {} exists".format(path))
        return 1
    c = ConfigParser.ConfigParser()
    c.add_section('amazon')
    c.set('amazon', 'AWS_API_KEY', 'foo')
    c.set('amazon', 'AWS_SECRET_KEY', 'bar')
    c.set('amazon', 'AWS_KEY_FILE',  'name')
    c.set('amazon', 'LOCAL_AWS_KEY_FILE',  '~/.ssh/%(AWS_KEY_FILE)s.pem')
    with open(path, 'wb') as configfile:
        c.write(configfile)
    log.info("empty config created at {}".format(path))
    return 0


import android
droid = android.Android()

class AndroidHandler(log.StreamHandler):
    def emit(self, record):
        msg = self.format(record)
        droid.log(msg)

def _main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--region', choices=config.AMI_ID_BY_REGION.keys(), help="Where in the world to create the VPN (default: %(default)s)", default='eu-west-1')
    parser.add_argument('-v', '--vpn-type', choices=vpntypes.TYPES.keys(), help="The type of feed to fetch (default: %(default)s)", default='ipsec')
    parser.add_argument('-a', '--api-key', help="Your AWS API key")
    parser.add_argument('-s', '--secret-key', action='store_true', help="Prompts for your AWS secret key secret_key interactively (no echo)")
    parser.add_argument('-S', '--no-prompt-secret', help="Your AWS secret key will be read from the arguments")
    parser.add_argument('-i', '--identity-file', help="The path to your key pair (not required by all VPN types)")
    parser.add_argument('-I', '--key-name', help="The name of the keypair to use. ")
    parser.add_argument('-c', '--config', help="Path to alternate config file", default=os.path.expanduser('~/.ephemvpnrc'))
    parser.add_argument('-V', '--verbose', action='store_true', help="Be more verbose")
    parser.add_argument('-q', '--quiet', action='store_true', help="Output nothing. For non-interactive unattended launches, assumes yes to all questions")
    parser.add_argument('-t', '--running-time', help="The time at or after which the VPN will terminate itself (default: %(default)s)", default='1h')
    parser.add_argument('-G', '--generate-config', action='store_true', help='Path to create a config file at (recommended {})'.format(os.path.expanduser('~/.ephemvpnrc')))
    args = parser.parse_args()

    log.info(args)
    if args.generate_config:
        return _gen_config(args.generate_config)

    # parse config file
    cf = _parse_conf(args.config)
    secret_key = None
    if args.secret_key:
        secret_key = getpass.getpass()
    elif args.no_prompt_secret:
        secret_key = args.no_prompt_secret

    if args.api_key:
        config.AWS_API_KEY = args.api_key
    if secret_key:
        config.AWS_SECRET_KEY = secret_key

    if args.identity_file:
        config.LOCAL_AWS_KEY_FILE = args.identity_file
        if args.key_name:
            config.AWS_KEY_FILE = args.key_name
        else:
           name, ext = os.splitext(os.basename(args.identity_file))
           config.AWS_KEY_FILE = name
    elif args.key_name:
        config.AWS_KEY_FILE = name

    # sanity check
    print config.AWS_API_KEY
    if not config.AWS_API_KEY or not config.AWS_SECRET_KEY or not len(config.AWS_API_KEY) > 0 or not len(config.AWS_SECRET_KEY) > 0:
        log.info("AWS Credentials required")
        parser.print_usage()
        return 1

    if not config.AWS_KEY_FILE:
        log.info("AWS Keypair name required")
        parser.print_usage()
        return 1

    # calculate running time
    d_min, shutdown_t = _parse_running_time(args.running_time)

    # at scheduler doesn't support subminute periods
    if d_min < 1:
        log.error("Error:running time must be greater than one minute")
        return 1

    log.info("ephemvpn v{}".format(ephemvpn.__version__))
    log.info("summoning one {} vpn".format(args.vpn_type))
    if not args.quiet and not _confirm_time(shutdown_t):
        return 1

    config.AT_RUNNING_MINUTES = d_min

    try:
        vpn = vpntypes.VPN(args.vpn_type, cf, config.AT_RUNNING_MINUTES)
    except ValueError:
        log.error("this vpn type is broken")
        return 1

    if vpn.needs_post_configure() and not args.identity_file:
        log.error("vpn type {} requires sshing, so an identity file (private key) is required".format(args.vpn_type))
        parser.print_usage()
        return 1

    host = launch(vpn, args.region)
    if host is not None:
        configure(host, vpn)

    log.info("\nephemeral vpn summoned\n")

    info = vpn.human_readable_data()
    info['Hostname'] = host

    longest = max(map(len, info.keys()))
    fmt = "{0:>{width}}: {1}"
    for k,v in info.iteritems():
        log.info(fmt.format(k, v, width=longest))
    # a new line for aesthetics
    log.info('\n')
    return 0

if __name__ == '__main__':
    sys.exit(_main())
