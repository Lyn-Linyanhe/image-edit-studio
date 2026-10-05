"""Extract the embedded page to a file so node can syntax-check the script."""
import re
import sys

src = open("mask_edit_app.py", encoding="utf-8").read()
m = re.search(r'PAGE = r"""(.*?)"""', src, re.S)
page = m.group(1)
open("_page_extracted.html", "w", encoding="utf-8").write(page)

sc = re.search(r"<script>(.*?)</script>", page, re.S)
js = sc.group(1)
open("_page_extracted.js", "w", encoding="utf-8").write(js)
print("extracted html chars:", len(page), " js chars:", len(js))
print("js lines:", js.count("\n") + 1)
