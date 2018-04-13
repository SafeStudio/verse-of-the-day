import sys

import logging

log = logging.getLogger(__name__)
log.setLevel(level=logging.DEBUG)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
log.addHandler(out_hdlr)
