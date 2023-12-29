import re
import random
from collections import OrderedDict

def content_to_hex_str(content:str):
    print("content = {}".format(content))
    ret = ""
    i = 0
    while i < len(content):
        if content[i] == '|':
            # This is the first '|'.
            # Find the second '|'.
            j = i + 1
            while j < len(content) and content[j] != '|':
                j += 1
            assert content[j] == '|'
            # content[i+1:j] is hexadecimal
            ret += "\\x" + content[i+1:j].replace(' ', "\\x")
            i = j + 1
        else:
            ret += "\\x{:X}".format(ord(content[i]))
            i += 1
    return ret

def extract_content_from_rules(snort_rules_file):
    with open(snort_rules_file, 'r') as f:
        return list(OrderedDict.fromkeys(re.findall(r'content:"([^"]*)"', f.read())))

def convert_snort_rules_to_hs_lits(snort_rules_file, hs_lits_file):
    with open(hs_lits_file, 'w') as f:
        contents = extract_content_from_rules(snort_rules_file)
        for i, content in enumerate(extract_content_from_rules(snort_rules_file)):
            line_pattern = "{}:/{}/" if i == len(contents) - 1 else "{}:/{}/\n"
            f.write(line_pattern.format(i, content_to_hex_str(content)))

def scale_hs_lits(hs_lits_file, des_dir, lit_file_prefix, scale=[i * 100 for i in range(1, 31)]):
    with open(hs_lits_file, 'r') as f:
        lines = f.readlines()
        for sc in scale:
            with open("{}/{}-{}.lits".format(des_dir, lit_file_prefix, sc), 'w') as f_tmp:
                f_tmp.writelines(lines[:sc])

def filter_hs_lits(hs_lits_file1, hs_lits_file2, length):
    with open(hs_lits_file1, 'r') as f1, open(hs_lits_file2, 'w') as f2:
        num = 0
        for line in f1:
            if line.count('x') >= length:
                f2.write("{}:{}".format(num, line.split(':')[-1]))
                num += 1

def count_match(match_result_file):
    cnt = {}
    with open(match_result_file, 'r') as f:
        for line in f:
            if not line.startswith("Match @"):
                continue
            lit_id = int(line.split(' ')[-1])
            if cnt.get(lit_id) is None:
                cnt[lit_id] = 1
            else:
                cnt[lit_id] += 1
    return cnt

def pick_lits(cnt_dict, match_num_per_set, set_num):
    cnt_dict = dict(sorted(cnt_dict.items(), key=lambda item: item[1]))
    print(cnt_dict)
    items = list(cnt_dict.items())
    is_selected = [False for i in range(len(items))]

    # Find the fisrt item where item[1] > match_num_per_set
    pos = 0
    while pos < len(items) and items[pos][1] <= match_num_per_set:
        pos += 1
    
    lit_sets = []
    if pos < set_num:
        print("The number of rules that are matched less or equal to {} times is less than {}".format(match_num_per_set, set_num))
        print("Match Casees:")
        for id in cnt_dict:
            print("Literal {}: {} times".format(id, cnt_dict[id]))
            lit_sets.append([id])
        return lit_sets

    for i in range(pos - 1, pos - set_num - 1, -1):
        lit_set = [items[i][0]]
        is_selected[i] = True

        delta = match_num_per_set - items[i][1]
        if delta > 0:
            for j in range(0, i):
                if not is_selected[j] and items[j][1] == delta:
                    lit_set.append(items[j][0])
                    is_selected[j] = True
                    break
        lit_sets.append(lit_set)
    
    for ls in lit_sets:
        set_match_num = sum([cnt_dict[lit_id] for lit_id in ls])
        if set_match_num < match_num_per_set:
            for i in range(pos - set_num):
                if is_selected[i]:
                    continue
                if abs(set_match_num + items[i][1] - match_num_per_set) < abs(set_match_num - match_num_per_set):
                    ls.append(items[i][0])
                    set_match_num += items[i][1]
                    is_selected[i] = True
                else:
                    break
    
    return lit_sets

def pick_k_from_unmatched_lits(is_matched, is_selected, k, rdm=False):
    ret = []
    i = 0

    while k > 0 and i < len(is_matched):
        if rdm:
            i = random.randint(0, len(is_matched) - 1)
        if not is_matched[i] and not is_selected[i]:
            ret.append(i)
            is_selected[i] = True
            k -= 1
        if not rdm:
            i += 1

    return ret

def rearrange_hs_lits(hs_lits_file1, hs_lits_file2, lit_sets, chunk_size, matched_lits):
    """
    重新排列literals, 使得每个chunk都含有一个lit_set中的literals, 同时chunk中不含其他会匹配的literals
    """
    with open(hs_lits_file1, 'r') as f1, open(hs_lits_file2, 'w') as f2:
        lines = f1.readlines()
        num_literals = len(lines)
        is_matched = [False for i in range(num_literals)]
        is_selected = [False for i in range(num_literals)]
        for lit in matched_lits:
            is_matched[lit] = True
        rearranged_lits = []
        for ls in lit_sets:
            rearranged_lits.extend(ls)
            for lit in ls:
                is_selected[lit] = True
            rearranged_lits.extend(pick_k_from_unmatched_lits(is_matched, is_selected, chunk_size-len(ls), True))
        
        for i in range(num_literals):
            if not is_selected[i]:
                rearranged_lits.append(i)

        rearranged_lines = []
        for lit in rearranged_lits:
            rearranged_lines.append(lines[lit])
        f2.writelines(rearranged_lines)

def task_rearrange_lits(lits_file1, lits_file2, match_result, match_num_per_set, set_num):
    cnt_dict = count_match(match_result)
    lit_sets = pick_lits(cnt_dict, match_num_per_set, set_num)
    rearrange_hs_lits(lits_file1, lits_file2, lit_sets, 100, list(cnt_dict.keys()))

def task_print_cnt_dict(match_file):
    cnt_dict = count_match(match_file)
    cnt_dict = dict(sorted(cnt_dict.items(), key=lambda item: item[1]))
    for k in cnt_dict:
        print("Literal {}, {} times".format(k, cnt_dict[k]))
    lit_sets = pick_lits(cnt_dict, 1, 30)
    for ls in lit_sets:
        print("Lit set {} | Match num {}".format(ls, sum([cnt_dict[x] for x in ls])))

def task_scale_rearranged_lits(rearranged_lits_file, des_dir, prefix):
    scale_hs_lits(rearranged_lits_file, des_dir, prefix)

if __name__ == "__main__":
    # convert_snort_rules_to_hs_lits("./data/suricata-emerging-all.rules", "./data/suricata-emerging-all.lits")
    # filter_hs_lits("./data/suricata-emerging-all.lits", "./data/filtered-suricata-emerging-all.lits", 8)
    task_rearrange_lits("./data/filtered-suricata-emerging-all.lits", "./data/rearranged-filtered-suricata-emerging-all-fudan-80-30.lits", "./data/fudan-filtered-suricata-emerging-all-match-result", 80, 30)
    task_scale_rearranged_lits("./data/rearranged-filtered-suricata-emerging-all-fudan-80-30.lits", "./data/fudan-suricata-lit-sets/0.1", "suricata")
    # task_rearrange_lits("./data/filtered-suricata-emerging-all.lits", "./data/rearranged-filtered-suricata-emerging-all-ixia-429-30.lits", "./data/ixia-filtered-suricata-emerging-all-match-result", 429, 30)
    # task_scale_rearranged_lits("./data/rearranged-filtered-suricata-emerging-all-ixia-429-30.lits", "./data/ixia-suricata-lit-sets/0.1", "suricata")