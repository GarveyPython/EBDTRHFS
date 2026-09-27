import json
import numpy as np


# 读取基准算例
def read(path):
    with open(path, 'r') as f:
        inst_d = json.load(f)
    PT = np.array(inst_d["PT"])  # 第一层次的加工时间
    PT1 = np.array(inst_d["PT1"])  # 第二层次的加工时间
    Ms = np.array(inst_d["M"])  # 各工厂各阶段的并行机数
    S = PT.shape[0]  # 总工站数
    Routes = np.array(list(range(S)) + [S - 2, S - 1] + list(range(S)) + [S - 2, S - 1])  # 生成各工件的工艺路线(机器号)
    return Ms, PT, PT1, S, Routes
