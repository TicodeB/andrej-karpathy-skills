import urllib.request


def upload_file(file_path, destination, opener=urllib.request.urlopen):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        response = opener(urllib.request.Request(destination, data=data, method='POST'))

        if response.status == 200:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False


def download_file( url, target, opener=urllib.request.urlopen ):
    # downlaod the file and save it
    response = opener(url)
    if response.status != 200 :
        return False
    f = open(target, "wb")
    f.write(response.read())
    f.close()
    return True
