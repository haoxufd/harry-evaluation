import sys
sys.path.append('..')
from run_experiments import *

def test_pasre_bench_result():
    with open("./data/test_parse_bench_result.bench_out", 'r') as f:
        lit_num, match_rate, throughput = parse_bench_result(f.read())
        assert lit_num == 3000
        assert match_rate == 0.991
        assert throughput == 2928.04