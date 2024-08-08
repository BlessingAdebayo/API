# Developer Base Image



This image clones a git url passed by env variable.
Then, with additional checks on the mercor username and password it runs main.py inside that repository.

### Expected env vars:
- MERCOR_GIT_LINK
- MERCOR_SDK_USERNAME
- MERCOR_SDK_PASSWORD


