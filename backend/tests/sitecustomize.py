import os
import sys

# When test files are executed directly in editors, sys.path[0] is the tests folder.
# This file is auto-loaded by Python as sitecustomize when the tests directory is on sys.path.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
