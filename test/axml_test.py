import os,sys

SELF_PATH = os.path.dirname(os.path.realpath(__file__))
ROOT_PATH = os.path.join(SELF_PATH, "../")
sys.path.append(ROOT_PATH)
from parser.zip_parser import ZipFile
from parser.res_parser import Axml, Arsc
from main import ApkFile

def test_axml_basic():
    zip_file = ZipFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    zip_file2 = ZipFile(os.path.join(SELF_PATH ,"apks/arsc_obf.apk"))

    axml_1 = zip_file.get_file(b"AndroidManifest.xml")
    axml_1 = Axml(axml_1)

    axml_2 = zip_file2.get_file(b"AndroidManifest.xml")
    axml_2 = Axml(axml_2)

    assert len(axml_2.get_xml_str()) == 32877
    assert len(axml_1.get_xml_str()) == 9904
    

def test_arsc_basic():
    res = []
    with open(os.path.join(SELF_PATH ,"apks/resources.arsc"),"rb") as fr:
        arsc = Arsc(fr.read())
        res = arsc.get_resources(0x7f010000)
    assert res[0][1] == "res/anim/abc_fade_in.xml"


def test_icon():
    apk = ApkFile(os.path.join(SELF_PATH ,"apks/normal.apk"))
    icon_file = apk.get_file(apk.get_icon().encode())
    assert len(icon_file) == 171658
    

if __name__ == "__main__":
    # test_axml_basic()
    test_arsc_basic()
    # test_icon()
