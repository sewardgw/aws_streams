
#PYTHONPATH=~/GitHub/aws_streams/python-lib/:PYTHONPATH bin/python ~/GitHub/aws_streams/python-bin/runner.py

from twitter import collector

if __name__ == '__main__':
    # import sys
    # print sys.path
    collector.run()
