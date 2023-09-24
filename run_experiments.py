import os
import re
import subprocess
import matplotlib.pyplot as plt

MARKERS = ['o', '^', 's', '*', 'x']

def run_bench(lit_set, input_data, build_dir):
    command = "{} -c {} -e {} -n 1 -N".format(build_dir + "/bin/hsbench", input_data, lit_set)

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
    match_rate = float(matches[0])

    matches = re.findall(r'Mean throughput \(overall\):\s+(\d{1,3}(,\d{3})*\.\d+)', bench_out)
    assert len(matches) == 1
    throughput = float(matches[0][0].replace(',', ''))

    matches = re.findall(r'Expression count:\s+(\d{1,3}(,\d{3})*)', bench_out)
    assert len(matches) == 1
    lit_num = int(matches[0][0].replace(',', ''))

    return lit_num, match_rate, throughput

def run_bench_group(lit_set_dir, input_data, build_dirs):
    res = [[] for i in range(len(build_dirs))]

    for root, dirs, files in os.walk(lit_set_dir):
        files = sorted(files, key=lambda x: int(re.findall(r'-(\d+)\.lits', x)[0]))
        for file in files:
            file_path = os.path.join(root, file)
            for idx, build_dir in enumerate(build_dirs):
                res[idx].append(parse_bench_result(run_bench(file_path, input_data, build_dir)))
    
    return res

def draw_bench_group(bench_group_result):
    plt.figure()

    x = [x[0] for x in bench_group_result[0]]
    for i, res in enumerate(bench_group_result):
        y = [x[2] for x in res]
        plt.plot(x, y, marker=MARKERS[i], linestyle='-')

    plt.xlabel("Rule Num")
    plt.ylabel("Throughput(Mbit/s)")

    pdf_file = "./data/figures/alexa-snort.pdf"
    plt.savefig(pdf_file, format="pdf")

def task_run_alexa():
    lit_set_dir = "./data/alexa-snort-lit-sets"
    input_data = "./data/corpora/alexa-http-requests.db"
    build_dirs = ["/home/xuhao/ue2/build_fdr", "/home/xuhao/ue2/build_tharry", "/home/xuhao/ue2/build_dharry", "/home/xuhao/ue2/build_ac"]
    res = run_bench_group(lit_set_dir, input_data, build_dirs)
    draw_bench_group(res)

if __name__ == "__main__":
    task_run_alexa()
