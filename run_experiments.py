import os
import re
import subprocess
import matplotlib.pyplot as plt
import random
import numpy as np

MARKERS = ['o', '^', 's', '*', 'x', '+', 'd']
COLORS = [(99,0,169), (204,73,117), (189,55,82), (252,140,90), (75,116,178), (144,190,224), (0,0,0)]
COLORS = np.array(COLORS)
COLORS = COLORS / 255

AC = 0
FDR = 0
THARRY = 1
DHARRY = 2
TNEOHARRY = 3
DNEOHARRY = 4

LIT_NUM = 0
MATCH_RATE = 1
THROUGHPUT = 2
FALSE_POSITIVE = 3

def run_unit(lit_set, input_data, build_dir):
    print("Run on {} {} {}".format(lit_set, input_data, build_dir))
    command = "taskset -c 17 {} -c {} -e {} -n 10 -N".format(build_dir + "/bin/hsbench", input_data, lit_set)

    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode == 0:
        return result.stdout
    else:
        print("Command Execute Error!")
        print("Command: {}".format(command))
        print("Error: {}".format(result.stderr))
        assert False

def parse_bench_result(bench_out):
    matches = re.findall(r'\((\d+.\d+) matches/kilobyte\)', bench_out)
    assert len(matches) == 1
    match_rate = int(float(matches[0]) * 1024)

    matches = re.findall(r'Mean throughput \(overall\):\s+(\d{1,3}(,\d{3})*\.\d+)', bench_out)
    assert len(matches) == 1
    throughput = float(matches[0][0].replace(',', ''))

    matches = re.findall(r'Expression count:\s+(\d{1,3}(,\d{3})*)', bench_out)
    assert len(matches) == 1
    lit_num = int(matches[0][0].replace(',', ''))
    
    return lit_num, match_rate, throughput

def parse_time_breakdown_result(unit_out):
    matches = re.findall(r'\((\d+.\d+) matches/kilobyte\)', unit_out)
    assert len(matches) == 1
    match_rate = int(float(matches[0]) * 1024)

    matches = re.findall(r'Expression count:\s+(\d{1,3}(,\d{3})*)', unit_out)
    assert len(matches) == 1
    lit_num = int(matches[0][0].replace(',', ''))

    matches = re.findall(r'Time spent confirming', unit_out)
    if len(matches) == 0:
        matches = re.findall(r'Time spent scanning:\s+(\d+.\d+)', unit_out)
        assert len(matches) == 1
        time = int(float(matches[0]) * 1000000)
        return lit_num, match_rate, time
    
    matches = re.findall(r'Time spent scanning:\s+(\d+.\d+)', unit_out)
    assert len(matches) == 1
    total_time = float(matches[0]) * 1000000

    matches = re.findall(r'Time spent confirming:\s+(\d+.\d+)', unit_out)
    assert len(matches) == 1
    confirm_time = float(matches[0]) * 1000000

    return lit_num, match_rate, (total_time - confirm_time) / confirm_time
    

def run_bench_group(lit_set_dir, input_data, build_dirs):
    """跑一组规则集+corpus

    Args:
        lit_set_dir (_type_): _description_
        input_data (_type_): _description_
        build_dirs (_type_): _description_

    Returns:
        [
            [(lit_num, match_rate, throughput, fp_num), (lit_num, match_rate, throughput, fp_num),...],
            [(lit_num, match_rate, throughput, fp_num), (lit_num, match_rate, throughput, fp_num),...],
            [(lit_num, match_rate, throughput, fp_num), (lit_num, match_rate, throughput, fp_num),...],
            ......
        ]
    """
    res = [[] for i in range(len(build_dirs))]

    for root, dirs, files in os.walk(lit_set_dir):
        files = sorted(files, key=lambda x: int(re.findall(r'-(\d+)\.lits', x)[0]))
        for file in files:
            file_path = os.path.join(root, file)
            for idx, build_dir in enumerate(build_dirs):
                res[idx].append(parse_bench_result(run_unit(file_path, input_data, build_dir)))
    
    return res

def run_time_breakdown_group(lit_set_dir, input_data, build_dirs):
    """_summary_

    Args:
        lit_set_dir (_type_): _description_
        input_data (_type_): _description_
        build_dirs (_type_): _description_

    Returns:
        [
            [(lit_num, match_rate, total_time), (lit_num, match_rate, total_time),...],
            [(lit_num, match_rate, time_ratio), (lit_num, match_rate, time_ratio),...],
            [(lit_num, match_rate, total_time), (lit_num, match_rate, total_time),...],
            [(lit_num, match_rate, time_ratio), (lit_num, match_rate, time_ratio),...]
            ......
        ]
    """
    res = [[] for i in range(len(build_dirs))]

    for root, dirs, files in os.walk(lit_set_dir):
        files = sorted(files, key=lambda x: int(re.findall(r'-(\d+)\.lits', x)[0]))
        for file in files:
            file_path = os.path.join(root, file)
            for idx, build_dir in enumerate(build_dirs):
                res[idx].append(parse_time_breakdown_result(run_unit(file_path, input_data, build_dir)))
    
    return res

def draw_bench_group(bench_group_result, file_name, format):
    fig, ax1 = plt.subplots()
    ax1.set_xlabel("# Rules")
    ax1.set_ylabel("Throughput (Gbit/s)")
    labels = ["FDR", "Harry", "NeoHarry"]

    fdr = [a / 1000 for a in bench_group_result[2]]
    tharry = bench_group_result[3]
    dharry = bench_group_result[4]
    harry = [max(a, b) / 1000 for a, b in zip(tharry, dharry)]
    tneoharry = bench_group_result[5]
    dneoharry = bench_group_result[6]
    neoharry = [max(a, b) / 1000 for a, b in zip(tneoharry, dneoharry)]    
    targets = [fdr, harry, neoharry]

    x = bench_group_result[0]
    for i in range(len(targets)):
        ax1.plot(x, targets[i], color = COLORS[i * 2], marker=MARKERS[i], linestyle='-', label=labels[i])
    
    ax2 = ax1.twinx()
    ax2.set_ylabel("# Matches/Mbytes")

    ax2.plot(x, bench_group_result[1], color = COLORS[-1], marker=MARKERS[-1], linestyle='-', label="Match Rate")

    ax1.legend(loc="upper right", ncol=3, bbox_to_anchor=(1, 1.15))
    ax2.legend(loc="upper left", bbox_to_anchor=(0, 1.15))

    ax2.set_ylim(0, 120)

    plt.savefig(file_name)

def draw_time_breakdown_group(res, file_name, format):
    n = len(res[0]) - 2
    xticks = res[0][0:n]

    fdr_frontend = [res[2][i] * (res[3][i] / (res[3][i] + 1)) / 1000 for i in range(n)]
    fdr_backend = [res[2][i] / 1000 - fdr_frontend[i] for i in range(n)]

    tneoharry = [(res[4][i], res[5][i]) for i in range(n)]
    dneoharry = [(res[6][i], res[7][i]) for i in range(n)]
    neoharry = [tneoharry[i] if tneoharry[i][0] < dneoharry[i][0] else dneoharry[i] for i in range(n)]

    neoharry_frontend = [neoharry[i][0] * (neoharry[i][1] / (neoharry[i][1] + 1)) / 1000 for i in range(n)]
    neoharry_backend = [neoharry[i][0] / 1000 - neoharry_frontend[i] for i in range(n)]

    tharry = [(res[8][i], res[9][i]) for i in range(n)]
    dharry = [(res[10][i], res[11][i]) for i in range(n)]
    harry = [tharry[i] if tharry[i][0] < dharry[i][0] else dharry[i] for i in range(n)]

    harry_frontend = [harry[i][0] * (harry[i][1] / (harry[i][1] + 1)) / 1000 for i in range(n)]
    harry_backend = [harry[i][0] / 1000 - harry_frontend[i] for i in range(n)]

    width = 100

    x1 = [i - width for i in xticks]
    x2 = [i for i in xticks]
    x3 = [i + width for i in xticks]

    plt.bar(x1, fdr_frontend, width=width, color=COLORS[0], label="FDR Shift-Or Match")
    plt.bar(x1, fdr_backend, width=width, color=COLORS[1], bottom=fdr_frontend, label="FDR Exact Match")
    plt.bar(x2, harry_frontend, width=width, color=COLORS[2], label="Harry Shift-Or Match")
    plt.bar(x2, harry_backend, width=width, color=COLORS[3], bottom=harry_frontend, label="Harry Exact Match")
    plt.bar(x3, neoharry_frontend, width=width, color=COLORS[4], label="NeoHarry Shift-Or Match")
    plt.bar(x3, neoharry_backend, width=width, color=COLORS[5], bottom=neoharry_frontend, label="NeoHarry Exact Match")

    plt.xlabel("# Rules")
    plt.ylabel("Run Time (milliseconds)")

    plt.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.15))

    plt.tight_layout()

    plt.savefig(file_name)

def norm_bench_group_result(result):
    """_summary_

    Args:
        result (_type_): _description_
        [
            [(lit_num, match_rate, throughput, fp_num), (lit_num, match_rate, throughput, fp_num),...],
            [(lit_num, match_rate, throughput, fp_num), (lit_num, match_rate, throughput, fp_num),...],
            [(lit_num, match_rate, throughput, fp_num), (lit_num, match_rate, throughput, fp_num),...],
            ......
        ]

    Returns:
        [
            [lit_num, lit_num, lit_num,...],
            [match_rate, match_rate, match_rate,...],
            [ac_tp, ac_tp, ac_tp,...],
            [fdr_tp, fdr_tp, fdr_tp,...],
            ......
            [ac_fp, ac_fp, ac_fp,...],
            [fdr_fp, fdr_fp, fdr_fp...],
            ......
        ]
    """
    res = []
    res.append([x[LIT_NUM] for x in result[FDR]])
    res.append([x[MATCH_RATE] for x in result[FDR]])

    # Add throughput rows
    for item in result:
        res.append([x[THROUGHPUT] for x in item])
    
    # Add false positive rows
    if len(result[0][0]) > 3:
        for item in result:
            res.append([x[FALSE_POSITIVE] for x in item])
    
    return res

def norm_time_breakdown_group_result(result):
    """
    Args:
        result (_type_): [
            [(lit_num, match_rate, total_time), (lit_num, match_rate, total_time),...],
            [(lit_num, match_rate, time_ratio), (lit_num, match_rate, time_ratio),...],
            [(lit_num, match_rate, total_time), (lit_num, match_rate, total_time),...],
            [(lit_num, match_rate, time_ratio), (lit_num, match_rate, time_ratio),...]
            ......
        ]
    
    Returns:
        [
            
        ]
    """
    res = []
    res.append([x[0] for x in result[0]])
    res.append([x[1] for x in result[0]])

    for item in result:
        res.append([x[2] for x in item])
    
    return res

def save_bench_group(result, file_name):
    tmp_result = [[str(x) for x in y] for y in result]
    with open(file_name, 'w') as f:
        f.writelines([','.join(x) + '\n' for x in tmp_result])

def save_time_breakdown_group(result, file_name):
    tmp_result = [[str(x) for x in y] for y in result]
    with open(file_name, 'w') as f:
        f.writelines([','.join(x) + '\n' for x in tmp_result])

def str_to_type(x):
    if '.' in x:
        return float(x)
    if x == "None":
        return None
    return int(x)

def read_bench_group_result_from_file(file_name):
    res = []
    with open(file_name, 'r') as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.strip() == "":
                break
            res.append([str_to_type(x) for x in line.strip().split(',')])
    return res

def read_time_breakdown_result_from_file(file_name):
    res = []
    with open(file_name, 'r') as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if line.strip() == "":
                break
            res.append([str_to_type(x) for x in line.strip().split(',')])
    return res

def draw_bench_groups():
    groups = ["snort-ixia", "snort-fudan", "snort-random"]
    targets = [0, 1, 2]
    
    for target in targets:
        res = read_bench_group_result_from_file("./data/{}.res".format(groups[target]))
        draw_bench_group(res, "./data/figures/" + groups[target] + ".pdf", format="pdf")

def run_bench_groups():
    exps = [
    ("./data/ixia-snort-lit-sets/0.1", "./data/corpora/ixia-http-responses.db", "snort-ixia"),
    ("./data/fudan-snort-lit-sets/0.1", "./data/corpora/fudan1.db", "snort-fudan"),
    ("./data/random-snort-lit-sets", "./data/corpora/random-1500b.db", "snort-random")]

    targets = [0, 1, 2]

    build_dirs = ["/home/xuhao/ue2/build_fdr", 
                  "/home/xuhao/ue2/build_tharry", 
                  "/home/xuhao/ue2/build_dharry", 
                  "/home/xuhao/ue2/build_tneoharry", 
                  "/home/xuhao/ue2/build_dneoharry"]

    for target in targets:
        exp = exps[target]
        print("Run benchmark on {}".format(exp))
        res = norm_bench_group_result(run_bench_group(exp[0], exp[1], build_dirs))
        save_bench_group(res, "./data/{}.res".format(exp[2]))

def run_time_breakdown_groups():
    exps = [
    ("./data/fudan-snort-lit-sets/time-breakdown", "./data/corpora/fudan1.db", "snort-fudan-time")]

    targets = [0]

    build_dirs = ["/home/xuhao/ue2/build_fdr", 
                  "/home/xuhao/ue2/build_fdr_time", 
                  "/home/xuhao/ue2/build_tneoharry",
                  "/home/xuhao/ue2/build_tneoharry_time", 
                  "/home/xuhao/ue2/build_dneoharry",
                  "/home/xuhao/ue2/build_dneoharry_time", 
                  "/home/xuhao/ue2/build_tharry",
                  "/home/xuhao/ue2/build_tharry_time", 
                  "/home/xuhao/ue2/build_dharry",
                  "/home/xuhao/ue2/build_dharry_time"]

    for target in targets:
        exp = exps[target]
        print("Run time breakdown on {}".format(exp))
        res = norm_time_breakdown_group_result(run_time_breakdown_group(exp[0], exp[1], build_dirs))
        save_time_breakdown_group(res, "./data/{}.res".format(exp[2]))

if __name__ == "__main__":
    # run_time_breakdown_groups()
    res = read_time_breakdown_result_from_file("./data/snort-fudan-time.res")
    draw_time_breakdown_group(res, "./data/figures/snort-fudan-time.pdf", "pdf")
    draw_bench_groups()