import requests, os, re

def find_dir(target):
    dir_list = []
    # rootdir = rootdir.replace('\\', '/')
    for path, subdirs, files in os.walk(os.path.expanduser("~")):
        path = path.replace('\\', '/')
        regex = re.compile(target)
        if regex.search(path):
            return path
        
def download_from_url(URL, location):
    response = requests.get(URL)
    open(location, "wb").write(response.content)