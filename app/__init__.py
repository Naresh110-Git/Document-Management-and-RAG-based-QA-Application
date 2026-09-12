import os
import sys

# Allow `import app` from the workspace root, while keeping the actual implementation under backend/app.
# This shim enables editors and direct Python execution to resolve the package consistently.
ROOT_APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app"))
if ROOT_APP_PATH not in __path__:
    __path__.insert(0, ROOT_APP_PATH)

# Ensure the workspace root is visible when this package is imported indirectly.
ROOT_PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_PROJECT not in sys.path:
    sys.path.insert(0, ROOT_PROJECT)
