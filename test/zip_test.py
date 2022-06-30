import os,sys

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.join(SELF_PATH, "../")
sys.path.append(ROOT_PATH)
from parser.zip_parser import ZipFile

def test_basic():
    zip_file = ZipFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    # print(zip_file.ecd.__dict__)
    assert zip_file.ecd.central_dir_size == 48722
    assert len(zip_file.cds) == 532
    

def test_get_file():
    zip_file = ZipFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    res = zip_file.get_file(b"AndroidManifest.xml")
    assert len(res) == 22528


if __name__ == "__main__":
    test_basic()
