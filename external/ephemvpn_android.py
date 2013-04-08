import sys
import os
import android

sys.path.append(os.getcwd()+'/libs')
droid = android.Android()

error = ''

try:
    import sys
    import argparse
    import getpass
    import os
    import time
    import datetime
    import math
    import ConfigParser
except ImportError, e:
    error += "import 1 failed\n"
    droid.log(e)

try:
    import parsedatetime
except ImportError, e:
    error += "import 2 failed\n"
    droid.log(e)

try:
    import ephemvpn
    from ephemvpn import configuration as config
    from ephemvpn import vpntypes, launch, configure
    from ephemvpn.timehelpers import readable_delta
except ImportError, e:
    error += "import 3 failed\n"
    droid.log(e)


if error == '':
    droid.makeToast("ephemvpn A OK !")
    droid.log("ephevpn A  OK!!")
else:
    droid.makeToast(error)
    droid.log(error)

