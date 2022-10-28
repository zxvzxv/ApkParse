import os,sys

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.join(SELF_PATH, "../")
sys.path.append(ROOT_PATH)
from parser.zip_parser import ZipFile
from parser.res_parser import Axml, Arsc

def test_axml_basic():
    zip_file = ZipFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    zip_file2 = ZipFile(os.path.join(SELF_PATH ,"apks/arsc_obf.apk"))

    axml_1 = zip_file.get_file(b"AndroidManifest.xml")
    axml_1 = Axml(axml_1)

    axml_2 = zip_file2.get_file(b"AndroidManifest.xml")
    axml_2 = Axml(axml_2)

    string_encoding = axml_1.string_pool.is_utf8
    print(axml_2.get_xml_str())
    

def test_arsc_basic():
    with open(os.path.join(SELF_PATH ,"apks/resources.arsc"),"rb") as fr:
        arsc = Arsc(fr.read())
        arsc.get_resources(0x7f010000)


if __name__ == "__main__":
    test_arsc_basic()
