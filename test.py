import sys
from process_line import process_line
import logging, coloredlogs, verboselogs
coloredlogs.install(level=11,fmt='%(asctime)s - %(levelname)s - %(message)s')
filename = sys.argv[1]
rawfile = open(filename,'r')
pages = rawfile.read().split('\n')
for page in pages:
    process_line(page)

