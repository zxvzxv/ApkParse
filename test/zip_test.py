import os,sys

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.join(SELF_PATH, "../")
sys.path.append(ROOT_PATH)
from parser.zip_parser import ZipFile

def test_basic():
    zip_file = ZipFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    zip_file2 = ZipFile(os.path.join(SELF_PATH ,"apks/mix.apk"))
    assert zip_file2.ecd.central_dir_size == 3107415
    assert len(zip_file2.cds) == 46901
    assert zip_file.ecd.central_dir_size == 48722
    assert len(zip_file.cds) == 532
    

def test_get_file():
    zip_file = ZipFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    zip_file2 = ZipFile(os.path.join(SELF_PATH ,"apks/mix.apk"))
    res = zip_file.get_file(b"AndroidManifest.xml")
    res2 = zip_file2.get_file(b"AndroidManifest.xml")
    assert len(res) == 22528
    assert len(res2) == 64104


if __name__ == "__main__":
    test_get_file()
