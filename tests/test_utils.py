import os
import sys
sys.path.append('..')
from utils import *


def test_content_to_hex_str():
    assert content_to_hex_str("2|00|") == "\\x32\\x00"

def test_extract_content_from_rules():
    res = extract_content_from_rules("./data/test_extract_content_from_rules.rules")
    assert len(res) == 2
    assert res[0] == "2|00 00 00 06 00 00 00|Drives|24 00|"
    assert res[1] == "qazwsx.hsq"

def test_convert_snort_rules_to_hs_lits():
    convert_snort_rules_to_hs_lits("./data/test_convert_snort_rules_to_hs_lits.rules", "./data/tmp.out")
    with open("./data/test_convert_snort_rules_to_hs_lits.out", 'r') as f1, open("./data/tmp.out", 'r') as f2:
         assert f1.read() == f2.read()
    os.remove("./data/tmp.out")
    