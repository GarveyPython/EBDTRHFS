class BenchmarkModelValidator:
    # 考虑RE(可再生能源)、ESS和电网协同供电,ESS多余的电可以卖给电网
    def __init__(self, inst_path, F_num):
        self.F_num = F_num

        # Ms: shape为(S,), 各阶段并行机数目
        self.Ms, self.PT, self.PT1, self.S, self.Routes = read(inst_path)
        self.N = self.PT.shape[1]  # 工件数
        self.Archive = {"Sol": [], "Obj": [], "F_Obj": []}
        self.Proc_E1 = 60  # 制造阶段的单位加工能耗kwh
        self.Idle_E1 = 20  # 制造阶段的单位空转能耗kwh
        self.Proc_E2 = 30  # 检测-修复阶段的单位加工能耗kwh
        self.Idle_E2 = 10  # 检测-修复阶段的单位空转能耗kwh
        self.Threshold = 1000  # 各制造机器的役龄阈值(min)
        self.Main_T = 30  # 各机器每次维护的时长(检测阶段不维护)
        self.com_E = 3  # 单位车间辅助公共能耗(照明/除尘等)
        self.unit_Main_cost = 10  # 单位维护成本设为10
        self.Trans_k = 0.2  # 空转的役龄等效折算系数
        self.back_fac = 0.9  # 役龄回退因子
        self.Lub_L = 0.2  # 各制造机的润滑油使用量 0.2L
        self.Lub_serv_T = 600  # 润滑油的有效使用时间(min)
        self.Lub_CO2 = 2.85  # 润滑油的碳排放因子(kgCO2/L)
        self.E_CO2 = 0.6747  # 电能碳排放因子(KgCO2/kwh)
        self.EP = 24  # 能源周期
        self.ToU = [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.8, 0.8, 1.5, 1.5, 1.5, 1.5,
                    0.8, 0.8, 1.5, 1.5, 1.5, 0.8, 0.8, 0.8, 0.4, 0.4, 0.4, 0.4]  # 分时电价数据(0:00开始,时间间隔为1h)
        self.ToU_Sell = [0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.55, 0.55, 1.2, 1.2, 1.2, 1.2,
                         0.55, 0.55, 1.2, 1.2, 1.2, 0.55, 0.55, 0.55, 0.3, 0.3, 0.3, 0.3]  # 卖电的分时电价数据(0:00开始,时间间隔为1h)
        self.PV_main = 0.04  # PV光伏的单位(kwh)维护成本
        self.WT_main = 0.03  # WT风电的单位(kwh)维护成本
        self.ESS_in_out_cost = 0.0287  # ESS的单位充放电成本
        # =============== 设置不同规模的ESS配置验证算法 ==========================
        if self.N == 20:  # 小规模ESS验证
            self.ESS_init = 30  # ESS的初始容量,kwh
            self.ESS_min = 20  # ESS的最小剩余容量,kwh
            self.ESS_max = 90  # ESS的最大剩余容量,kwh
            self.ESS_Cp = 100  # ESS的额定容量,kwh
            self.ESS_lim = 25  # 每个调度时间步的充放电限制量即25%,kwh
        elif self.N == 50 or (self.N >= 100 and self.F_num >= 4):
            self.ESS_init = 300  # ESS的初始容量,kwh
            self.ESS_min = 150  # ESS的最小剩余容量,kwh
            self.ESS_max = 900  # ESS的最大剩余容量,kwh
            self.ESS_Cp = 1000  # ESS的额定容量,kwh
            self.ESS_lim = 250  # 每个调度时间步的充放电限制量即25%,kwh
        else:  # 算例的工厂配置较少,但工件任务量较高
            self.ESS_init = 500  # ESS的初始容量,kwh
            self.ESS_min = 200  # ESS的最小剩余容量,kwh
            self.ESS_max = 1350  # ESS的最大剩余容量,kwh
            self.ESS_Cp = 1500  # ESS的额定容量,kwh
            self.ESS_lim = 375  # 每个调度时间步的充放电限制量即25%,kwh

        self.CEP = 0.1  # 0.1CNY/kgCO2 100CNY/1ton Ref https://doi.org/10.1007/s12065-026-01144-z
        total_MT = self.PT[:-2] + self.PT1[:-2]  # 两个加工道次的总制造时间
        total_RT = 2 * (self.PT[-2:] + self.PT1[-2:])  # 重入2次
        # 这里根据任务量结合加工能耗, 确定政府激励机制发放的碳补贴配额 kgCO2, https://doi.org/10.1016/j.cor.2023.106360
        self.EA = (total_MT.sum() / 60 * self.Proc_E1 + total_RT.sum() / 60 * self.Proc_E2) * self.E_CO2 * 0.3  # 设置一个补贴比例
        df = pd.read_excel("dataset/PVWT.xlsx", header=None)
        self.PV_energy = df.iloc[:, 2].values.tolist()  # 一个周期的光伏发电量
        self.WT_energy = df.iloc[:, 1].values.tolist()  # 一个周期的风能发电量
