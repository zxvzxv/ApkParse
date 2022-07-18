import re

### copy xml file from "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/res/res/values/public.xml"
### then use this script to update public_res_ids.py

xml_file = "./public.xml"
target_py = "./public_res_ids.py"

res = []
str_data = ""
pattern = re.compile(r'<public type="([a-zA-Z_.]+)" name="([a-zA-Z_.]+)" id="([0-9a-z]+)" */>')



with open(xml_file, 'r') as fr:
    s = fr.read()
    matchs = pattern.findall(s)
    for match in matchs:
        name = "_".join([match[0], match[1]]).replace(".","_")
        line = f'    {match[2]}: "{name}",'
        res.append(line)

str_data = "\n".join(res)

header = '''
# source code: https://cs.android.com/android/platform/superproject/+/master:frameworks/base/core/res/res/values/public.xml
# doc: https://developer.android.com/reference/android/R.attr

PUBLIC_RES_ID = {
'''

end = "\n}"

with open(target_py, "w") as fw:
    fw.write(header + str_data + end)

