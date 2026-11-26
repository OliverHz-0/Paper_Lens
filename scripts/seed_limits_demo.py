"""Seed rich, beginner-friendly demo analysis, auto-fetched resources, and pre-traced citations for limits-2025."""

from __future__ import annotations

import json
import time
from pathlib import Path

PAPER_DIR = Path(__file__).resolve().parent.parent / "data" / "papers" / "limits-2025"


def build_resources() -> dict:
    return {
        "fetched_at": int(time.time()),
        "github": [
            {
                "repo": "MedinaLab2016/MAD1-Machine-Learning",
                "url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning",
                "status": "fetched",
                "fetched_at": int(time.time()),
                "description": "LIMITS AI-guided antimicrobial peptide discovery pipeline (Random Forest, Neural Network, Genetic Algorithm & PCA scripts in R) + training (n=88) and testing (n=22) datasets.",
                "language": "R",
                "default_branch": "main",
                "files": [
                    {"name": "README.md", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning/blob/main/README.md"},
                    {"name": "Automation File (DBAASP scraper)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                    {"name": "Central File (main GA loop)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                    {"name": "Modeling RF (RandomForest)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                    {"name": "Modeling NN (Neuralnet RPROP)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                    {"name": "Mutation File (crossover & point mutation)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                    {"name": "PCA File (post hoc analysis)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                    {"name": "Training & Testing Data (n=88 / n=22)", "type": "file", "html_url": "https://github.com/MedinaLab2016/MAD1-Machine-Learning"},
                ],
                "readme_excerpt": (
                    "# MAD1-Machine-Learning (LIMITS Workflow)\n\n"
                    "Contains automated R programs for Random Forest (RF) and Artificial Neural Network (NN) "
                    "prediction of antitubercular host defense peptides coupled with a Genetic Algorithm (GA), "
                    "plus Principal Component Analysis (PCA) scripts.\n\n"
                    "Core components:\n"
                    "- Automation File: uploads candidate sequences to DBAASP property calculator and exports Excel features\n"
                    "- Modeling NN / Modeling RF: trained on 110 peptides × 13 biophysical features\n"
                    "- Mutation File: runs crossover (rate=50) and point mutation (rate=0.025) to generate 100 candidates/gen\n"
                    "- Central File: orchestrates all functions in a multi-generation loop (run last)\n"
                ),
            }
        ],
        "doi_meta": {
            "doi": "10.1021/acs.biomac.5c00244",
            "doi_url": "https://doi.org/10.1021/acs.biomac.5c00244",
            "si_landing_url": "https://pubs.acs.org/doi/suppl/10.1021/acs.biomac.5c00244",
            "status": "fetched",
            "journal": "Biomacromolecules",
            "published_date": "2025-05-01",
            "publisher": "American Chemical Society (ACS)",
            "open_access_pdf": "https://pubs.acs.org/doi/10.1021/acs.biomac.5c00244",
            "note": "本文采用 CC-BY-NC-ND 4.0 开放获取协议发表于 ACS Biomacromolecules 2025, 26, 3167–3179。",
        },
        "supporting_info": {
            "available": True,
            "url": "https://pubs.acs.org/doi/suppl/10.1021/acs.biomac.5c00244",
            "note": (
                "免费获取的 Supporting Information (PDF) 包含：\n"
                "• Supplementary Table 1：MAD2.1–MAD5.5 全部 20 条 AI 设计肽的完整氨基酸序列及 LC-MS 纯度（≥90%）\n"
                "• Supplementary Figures 1–9：训练集序列 Logo、理化多样性分布、交叉/突变率优化曲线、PR/ROC 曲线、29 条外部验证集误差图、NPN 外膜通透性实验（S8）与人红细胞溶血曲线（S9）\n"
                "• Supplementary Tables 2–5：非结核分枝杆菌活性与杀菌动力学统计学 P 值检验"
            ),
        },
        "web_tools": [
            {
                "name": "DBAASP Property Calculator（多肽理化特征在线计算器）",
                "url": "https://dbaasp.org/tools?page=property-calculation",
                "desc": "论文自动化脚本每代调用该服务器，基于 Moon–Fleming 标度批量计算 12 项生物物理性质。",
            },
            {
                "name": "WebLogo 3（氨基酸序列频率图工具）",
                "url": "https://weblogo.berkeley.edu/logo.cgi",
                "desc": "用于绘制 Figure 4h 的 13 肽各位点氨基酸出现概率，揭示『镜像三明治』序列规律。",
            },
            {
                "name": "AntiTbPdb（抗结核多肽专业数据库）",
                "url": "https://webs.iiitd.edu.in/raghava/antitbpdb/",
                "desc": "论文训练集另一半数据及 29 条外部盲测验证集的来源数据库（Ref 11）。",
            },
        ],
    }


def build_ref_cache() -> dict:
    now = int(time.time())
    curated = {
        "1": {
            "title": "Designing antimicrobial peptides: form follows function",
            "authors": "Fjell, C. D.; Hiss, J. A.; Hancock, R. E.; Schneider, G.",
            "venue": "Nature Reviews Drug Discovery",
            "year": 2012,
            "doi": "10.1038/nrd3591",
            "url": "https://doi.org/10.1038/nrd3591",
            "plain_summary": "抗菌肽（AMP）领域的里程碑综述，系统总结了多肽『结构决定功能』的设计原则，以及其进入临床时面临的毒性与合成成本障碍。",
            "why_cited": "在引言第一段用来背书两个基本事实：① 抗菌肽通过多靶点破膜很难诱发耐药；② 传统试错优化极其耗时耗钱。",
        },
        "2": {
            "title": "Antibiotic-resistant bacteria show widespread collateral sensitivity to antimicrobial peptides",
            "authors": "Lázár, V.; Martins, A.; Spohn, R. et al. / Mookherjee, N. et al.",
            "venue": "Nature Microbiology (2018) & Nature Reviews Drug Discovery (2020)",
            "year": 2018,
            "doi": "10.1038/s41564-018-0164-0",
            "url": "https://doi.org/10.1038/s41564-018-0164-0",
            "plain_summary": "发现一个极妙的现象：细菌为了抵抗传统小分子抗生素而突变细胞膜后，反而对抗菌肽变得更脆弱（协同敏感性）。",
            "why_cited": "强有力地论证了为什么 HDP 是对抗泛耐药超级细菌的天然克星。",
        },
        "4": {
            "title": "Machine learning for antimicrobial peptide identification and design",
            "authors": "Wan, F.; Wong, F.; Collins, J. J.; de la Fuente-Nunez, C.",
            "venue": "Nature Reviews Bioengineering",
            "year": 2024,
            "doi": "10.1038/s44222-024-00152-x",
            "url": "https://doi.org/10.1038/s44222-024-00152-x",
            "plain_summary": "2024 年顶级综述（另有同条目 4c Cell 2024 全球宏基因组挖掘工作），全面盘点深度学习与大模型如何加速抗菌肽发现。",
            "why_cited": "树立当今『大数据 AI 挖掘抗菌肽』的前沿标杆，顺势反衬出这些大模型对非 ESKAPE 稀缺数据病原体束手无策的痛点。",
        },
        "7": {
            "title": "Deep learning improves antimicrobial peptide recognition",
            "authors": "Veltri, D.; Kamath, U.; Shehu, A.",
            "venue": "Bioinformatics",
            "year": 2018,
            "doi": "10.1093/bioinformatics/bty179",
            "url": "https://doi.org/10.1093/bioinformatics/bty179",
            "plain_summary": "提出著名的 AMP Scanner 深度神经网，并证明即使把 20 种氨基酸简化为 9 类（约简字母表），依然能准确识别抗菌肽。",
            "why_cited": "说明前人也在尝试缩小多肽搜索空间，但仍离不开数千条序列的大数据集。",
        },
        "10": {
            "title": "Pathogen-specific antimicrobials engineered de novo through membrane-protein biomimicry",
            "authors": "Simonson, A. W.; Mongia, A. S.; Aronson, M. R. ... Medina, S. H.",
            "venue": "Nature Biomedical Engineering",
            "year": 2021,
            "doi": "10.1038/s41551-021-00712-9",
            "url": "https://doi.org/10.1038/s41551-021-00712-9",
            "plain_summary": "【本文的直接前作！】通讯作者 Medina 团队仿照分枝杆菌外膜孔蛋白 MspA 的结构，从头人工设计了 13 肽 MAD1（KRWHWWRRHWVVW），通过『色氨酸拉链』选择性扎破结核菌外膜。",
            "why_cited": "全文最核心的基石文献！MAD1 就是本文 LIMITS 框架的先导模板（Template），Figure 2a 也直接改编自该文。",
        },
        "11": {
            "title": "AntiTbPdb: a knowledgebase of anti-tubercular peptides",
            "authors": "Usmani, S. S.; Kumar, R.; Kumar, V.; Singh, S.; Raghava, G. P.",
            "venue": "Database",
            "year": 2018,
            "doi": "10.1093/database/bay025",
            "url": "https://doi.org/10.1093/database/bay025",
            "plain_summary": "人工整理的全球首个抗结核/抗分枝杆菌多肽专属知识库，收录了经实验验证的多肽序列、化学修饰与抑菌浓度数据。",
            "why_cited": "为本文贡献了约一半训练数据，并提供了 29 条完全独立的外部验证盲测肽。",
        },
        "13": {
            "title": "Targeting Mycobacterium tuberculosis and other microbial pathogens using improved synthetic antibacterial peptides",
            "authors": "Ramón-García, S.; Mikut, R.; Ng, C. ... Thompson, C. J.",
            "venue": "Antimicrobial Agents and Chemotherapy",
            "year": 2013,
            "doi": "10.1128/AAC.00175-13",
            "url": "https://doi.org/10.1128/AAC.00175-13",
            "plain_summary": "筛选出约 10 个氨基酸长的强效合成抗结核短肽（MIC < 10 μM），并最早用 PCA 分析发现抗结核肽偏爱高疏水、高色氨酸和赖氨酸。",
            "why_cited": "贡献了本文训练集约一半的多肽数据，也是本文后验 PCA 分析方法的先行者。",
        },
        "14": {
            "title": "Combining genetic algorithm with machine learning strategies for designing potent antimicrobial peptides",
            "authors": "Boone, K.; Wisdom, C.; Camarda, K.; Spencer, P.; Tamerler, C.",
            "venue": "BMC Bioinformatics",
            "year": 2021,
            "doi": "10.1186/s12859-021-04156-x",
            "url": "https://doi.org/10.1186/s12859-021-04156-x",
            "plain_summary": "率先把『遗传算法 + 可解释机器学习』结合起来定向进化抗菌肽，兼顾搜索效率与规律可解释性。",
            "why_cited": "启发了本文的数值编码与『GA + ML』混合进化架构设计。",
        },
        "15": {
            "title": "Side-chain hydrophobicity scale derived from transmembrane protein folding into lipid bilayers",
            "authors": "Moon, C. P.; Fleming, K. G.",
            "venue": "PNAS",
            "year": 2011,
            "doi": "10.1073/pnas.1103979108",
            "url": "https://doi.org/10.1073/pnas.1103979108",
            "plain_summary": "建立了首个在真实脂质双分子层中通过跨膜蛋白折叠实测出来的 20 种氨基酸疏水性标度（水→膜转移自由能）。",
            "why_cited": "本文计算 12 项生物物理特征的核心标尺——因为抗结核肽要钻进细菌油膜里，用跨膜实测标度比传统水-油分配标度准确得多。",
        },
        "18": {
            "title": "PeptX: Using Genetic Algorithms to optimize peptides for MHC binding",
            "authors": "Knapp, B.; Giczi, V.; Ribarics, R.; Schreiner, W.",
            "venue": "BMC Bioinformatics",
            "year": 2011,
            "doi": "10.1186/1471-2105-12-241",
            "url": "https://doi.org/10.1186/1471-2105-12-241",
            "plain_summary": "系统研究了用遗传算法优化多肽时的超参数选择，发现初始种子数量取训练集的 ~10% 时收敛最快。",
            "why_cited": "直接解释了为什么本文 LIMITS 第 0 代要选 10 条种子肽（≈ 110 条的 10%）。",
        },
        "21": {
            "title": "Efficient Measurement of Drug Interactions with DiaMOND (Diagonal Measurement of N-Way Drug Interactions)",
            "authors": "Van, N.; Degefu, Y. N.; Aldridge, B. B.",
            "venue": "Methods in Molecular Biology",
            "year": 2021,
            "doi": "10.1007/978-1-0716-1460-0_31",
            "url": "https://doi.org/10.1007/978-1-0716-1460-0_31",
            "plain_summary": "只需沿着剂量矩阵的对角线采样，就能用极少实验孔高效精确地测出多种抗结核药物联用是协同、相加还是拮抗。",
            "why_cited": "本文 Figure 5d 测定 4 条肽 × 6 种临床抗结核药（共 24 组配对）联用 FICI 的标准实验方法。",
        },
        "26": {
            "title": "Combinatorial alanine-scanning",
            "authors": "Morrison, K. L.; Weiss, G. A.",
            "venue": "Current Opinion in Chemical Biology",
            "year": 2001,
            "doi": "10.1016/S1367-5931(00)00178-2",
            "url": "https://doi.org/10.1016/S1367-5931(00)00178-2",
            "plain_summary": "丙氨酸（Ala）侧链只是一个小小的甲基，化学性质极惰性；把多肽每个位置逐一换成丙氨酸，就能像『逐个拔掉电路板电阻』一样测出谁是核心功能位点。",
            "why_cited": "解释 Figure 2c 用丙氨酸扫描锁定 MAD1 的 C 端色氨酸弹头的原理。",
        },
        "27": {
            "title": "Length Effects in Antimicrobial Peptides of the (RW)n Series",
            "authors": "Liu, Z.; Brady, A.; Young, A. ... Kallenbach, N. R.",
            "venue": "Antimicrobial Agents and Chemotherapy",
            "year": 2007,
            "doi": "10.1128/AAC.00827-06",
            "url": "https://doi.org/10.1128/AAC.00827-06",
            "plain_summary": "测试了精氨酸-色氨酸重复序列 (RW)n 的长度效应，证明对常规细菌而言 6 肽 (RW)3 就能起效且性价比最高，超过 10 个氨基酸不再带来额外抗菌收益。",
            "why_cited": "作为『常规细菌 6–10 aa 最优』的经典基准（也是 Ref 31），用来强力反衬本文发现的『抗结核肽偏爱 13 aa』是一个全新特例！",
        },
        "30": {
            "title": "The lexicon of antimicrobial peptides: a complete set of arginine and tryptophan sequences",
            "authors": "Clark, S.; Jowitt, T. A.; Harris, L. K.; Knight, C. G.; Dobson, C. B.",
            "venue": "Communications Biology",
            "year": 2021,
            "doi": "10.1038/s42003-021-02137-7",
            "url": "https://doi.org/10.1038/s42003-021-02137-7",
            "plain_summary": "穷举测试了精氨酸/色氨酸短肽库，发现最小活性长度仅 4 残基，对金葡菌最佳为 8 残基、对铜绿假单胞菌为 11 残基。",
            "why_cited": "进一步佐证普通革兰阳性/阴性菌不需要 13 肽这么长，凸显结核分枝杆菌 13-mer 现象的独特性。",
        },
        "33": {
            "title": "Disclosure of the mycobacterial outer membrane: cryo-electron tomography and vitreous sections reveal the lipid bilayer structure",
            "authors": "Hoffmann, C.; Leis, A.; Niederweis, M.; Plitzko, J. M.; Engelhardt, H.",
            "venue": "PNAS",
            "year": 2008,
            "doi": "10.1073/pnas.0709530105",
            "url": "https://doi.org/10.1073/pnas.0709530105",
            "plain_summary": "【决定性物证！】用冷冻电子断层扫描直接拍到了分枝杆菌外膜的真实双层结构，并精确测出这层富含分枝菌酸的厚装甲厚度约为 ~6 nm。",
            "why_cited": "直接解释了本文最震撼的机理发现：为什么 AI 偏偏钟情于 13 肽？因为 13 个氨基酸拉直大约 4.7–5.2 nm，刚好够『一箭穿透』这层 ~6 nm 的装甲！",
        },
        "34": {
            "title": "Metronidazole Lacks Activity against Mycobacterium tuberculosis in an In Vivo Hypoxic Granuloma Model of Latency",
            "authors": "Klinkenberg, L. G.; Sutherland, L. A.; Bishai, W. R.; Karakousis, P. C.",
            "venue": "Journal of Infectious Diseases",
            "year": 2008,
            "doi": "10.1086/589515",
            "url": "https://doi.org/10.1086/589515",
            "plain_summary": "证实厌氧药甲硝唑虽然在试管缺氧条件下能杀光休眠结核菌，但在活体动物肉芽肿里却完全失效——因为活体内的缺氧程度还不够极端，无法把甲硝唑化学激活。",
            "why_cited": "帮本文在 Figure 5c 完成神反转：虽然试管里甲硝唑曲线比多肽更低，但甲硝唑进不了活体临床；而本文多肽不依赖代谢/极端缺氧激活，才是真正有临床转化希望的休眠菌杀手！",
        },
    }
    out = {}
    for k, v in curated.items():
        out[k] = {
            "number": int(k),
            "status": "curated_verified",
            "source": "PaperLens 深度溯源库（可点右上角在线刷新）",
            "traced_at": now,
            **v,
        }
    return out


def build_analysis() -> dict:
    glossary = {
        "HDP": {
            "zh": "宿主防御肽（Host Defense Peptide）",
            "simple": "人体或动物天生自带的『微型蛋白质子弹』，一般只有 6–30 个氨基酸长，用来直接打穿入侵细菌的细胞膜。",
            "analogy": "就像边防巡逻队随身带的一次性『破门锤』，直接砸碎坏人的防盗门，而不是去撬精密门锁。",
            "in_paper": "本文要设计和优化的主角药物类型，目标是杀死耐药结核菌但不伤人体细胞。",
        },
        "Mtb": {
            "zh": "结核分枝杆菌（Mycobacterium tuberculosis）",
            "simple": "引起肺结核（TB）的罪魁祸首细菌。它全身裹着一层极厚、极油腻的蜡质装甲，普通抗生素很难钻进去。",
            "analogy": "相当于细菌界的『重装坦克』，不仅皮厚，被围困时还能『装死休眠』躲过常规炮火。",
            "in_paper": "本文要攻克的核心病原体（测试了强毒株 H37Rv、减毒株 H37Ra 等 4 种菌株）。",
        },
        "Mycomembrane": {
            "zh": "分枝菌酸外膜",
            "simple": "结核菌最外层特有的超厚脂质外壳（约 6 纳米厚），由长链脂肪酸（分枝菌酸）密密麻麻排成，是它耐药的核心护盾。",
            "analogy": "普通细菌穿的是薄雨衣，结核菌穿的是 6 毫米厚的防弹蜡甲。",
            "in_paper": "MAD1 模板和本文发现的『13 个氨基酸长度规律』全部围绕穿透这层 ~6 nm 外壳展开。",
        },
        "MIC": {
            "zh": "最低抑菌浓度（Minimum Inhibitory Concentration）",
            "simple": "能拦住细菌不再生长的最低药物浓度（单位 μM，微摩尔）。数字越小，说明药效越猛！",
            "analogy": "好比灭蚊剂：滴 5 滴就能放倒蚊子（MIC=5），肯定比滴 40 滴才管用（MIC=40）强得多。",
            "in_paper": "全文衡量抗结核战斗力的核心指标；为了画图直观，作者常取倒数 MIC⁻¹（越大越强）。",
        },
        "SI": {
            "zh": "选择性指数（Selectivity Index）",
            "simple": "计算公式 = 杀死其他无关细菌的浓度 ÷ 杀死结核菌的浓度。数字越大，说明它越『精准制导』、不误伤好细菌。",
            "analogy": "狙击枪 vs 散弹枪：SI=16 以上意味着专杀结核菌，对旁边 8 种普通细菌几乎零伤害。",
            "in_paper": "母肽 MAD1 的 SI 只有 2，而 AI 优化出的 MAD5.1/5.3 飙升到 >16（提升 8 倍以上）。",
        },
        "TI": {
            "zh": "毒性指数 / 安全治疗窗（Toxicity Index）",
            "simple": "计算公式 = 杀伤一半人体肺细胞的浓度(IC50) ÷ 杀死结核菌的浓度(MIC)。数字越大，对人越安全！",
            "analogy": "就像农药安全倍数：TI > 100 意味着药量放大 100 倍才会开始伤到人体肺细胞，非常安全。",
            "in_paper": "母肽 MAD1 的 TI 仅为 5（较危险），而 MAD5.1/5.3 达到 >100（安全性暴涨 20 倍以上）。",
        },
        "MAD1": {
            "zh": "先导模板肽（KRWHWWRRHWVVW）",
            "simple": "作者团队 2021 年人工设计的 13 个氨基酸短肽，靠模仿结核菌自己外膜上的通道蛋白来『以彼之道还施彼身』。",
            "analogy": "相当于汽车换代时的『第一代原型车』，能跑但油耗高、不够稳，本文用 AI 把它进化成超跑。",
            "in_paper": "整个 LIMITS 工作流的起点模板和性能对比基准线。",
        },
        "LIMITS": {
            "zh": "先导信息引导的治疗序列机器探询",
            "simple": "本文原创的小样本 AI 造药流水线：先靠湿实验摸清模板底细，再用『机器学习打分 + 遗传算法繁衍进化』在只有 ~100 条数据时也能挖出神药。",
            "analogy": "不需要看一万本菜谱，只要大厨先试吃出一道招牌菜的关键调料，再让 AI 围绕这几个调料快速杂交改良 50 代。",
            "in_paper": "全篇最核心的方法论创新。",
        },
        "ESKAPE": {
            "zh": "六大常见院内耐药菌群缩写",
            "simple": "指屎肠球菌、金葡菌、肺炎克雷伯菌等 6 种医院最常见、研究最多、公开抗菌肽数据最海量的细菌。",
            "analogy": "相当于互联网里的『热门大语种（英语/中文）』训练语料管够，而结核菌是『稀缺小语种』。",
            "in_paper": "用来解释为什么传统大数据 AI 模型在结核菌上玩不转。",
        },
        "Alanine Mutagenesis": {
            "zh": "丙氨酸扫描突变",
            "simple": "把一条多肽上的每个氨基酸轮流替换成最普通、最不起眼的『丙氨酸』，看替换哪一个会让药效暴跌。",
            "analogy": "想知道一台收音机里哪个零件最关键？把零件挨个拔掉换成普通导线，一拔就哑巴的那个就是核心芯片！",
            "in_paper": "Figure 2c 用它锁定了 MAD1 尾巴上第 10–13 位色氨酸区是『杀菌弹头』。",
        },
        "Biophysical Features": {
            "zh": "生物物理特征（13 维连续参数）",
            "simple": "不直接把氨基酸字母（如 K, R, W）喂给 AI，而是先算好这条肽带多少正电、有多怕水、有多长、多容易卷曲或抱团等 13 个物理数值。",
            "analogy": "挑篮球运动员时不死记名字拼音，而是直接看身高、臂展、弹跳、体重这 13 项硬核体测数据，小样本也能准得惊人。",
            "in_paper": "本文用 ~110 条极小数据就训出高准确率模型的关键法宝。",
        },
        "Genetic Algorithm (GA)": {
            "zh": "遗传算法",
            "simple": "模仿达尔文『物竞天择』的优化算法：挑最好的 10 条肽当爸妈，互相交换片段（交叉）并随机改几个字母（突变）生出 100 个娃，留最强 10 个再繁殖 50 代。",
            "analogy": "就像在电脑里开了 50 倍速的『赛马育种场』，几分钟就能把平庸基因杂交出冠军马。",
            "in_paper": "负责在 20¹³ 的天文数字序列空间里高效搜索新多肽。",
        },
        "Random Forest vs ANN": {
            "zh": "随机森林 vs 人工神经网络",
            "simple": "两种经典机器学习模型。随机森林像『几百位经验老道的老师傅投票』，稳但保守；神经网络像『层层抽象的脑回路』，更敢跨界脑补新结构。",
            "analogy": "老师傅（RF）擅长把老菜微调到极致（MAD2.2），脑洞画家（NN）直接发明了全新的聚精氨酸神菜（MAD5.1/5.3）。",
            "in_paper": "本文对比了两者的进化行为：RF 5 代内就锁死局部最优，NN 不断探索最终拿了全场 MVP。",
        },
        "PCA": {
            "zh": "主成分分析（Principal Component Analysis）",
            "simple": "把 13 个让人眼花缭乱的物理指标压缩成 2 个最核心的综合坐标轴（PC1 和 PC2），画在一张二维平面地图上看清规律。",
            "analogy": "就像把一座 3D 雕塑投影到一张照片上，一眼看出哪些好分子扎堆在哪两片高地。",
            "in_paper": "Figure 4 用它意外发现了两片高活性大陆：传统两亲区 vs 全新的『本征无序聚集区』。",
        },
        "Intrinsically Disordered": {
            "zh": "本征无序蛋白/肽（IDP）",
            "simple": "没有固定硬邦邦的螺旋造型，像煮熟的面条一样柔软多变、却容易互相抱团聚集的多肽。",
            "analogy": "传统认知以为武器必须是坚硬的『长矛（α-螺旋）』，AI 却提示柔软粘稠的『渔网（无序聚集肽）』也能缠死结核菌。",
            "in_paper": "Figure 4b/c 后验分析挖出的全新未探索区域（第二高活性簇）。",
        },
        "Persister / NRP Mtb": {
            "zh": "持留休眠菌（Non-Replicating Persister）",
            "simple": "当结核菌躲进人体免疫细胞内部、没吃没喝又缺氧时，它会主动关闭新陈代谢进入『冬眠』，让专门攻击分裂期细菌的传统抗生素彻底失灵。",
            "analogy": "坏人躲进防空洞断电装睡，靠追踪电力信号的导弹（异烟肼）全都打空，只有物理爆破手（HDP）能炸开防空洞。",
            "in_paper": "Figure 5b/c 证明 MAD2.2 等肽能有效清除饥饿与缺氧休眠结核菌，直击肺结核反复复发的临床死穴。",
        },
        "NPN Assay": {
            "zh": "NPN 外膜通透性荧光实验",
            "simple": "NPN 是一种平时不发光、但一旦钻进被捅破的细菌脂质膜就会大放荧光的染料。荧光越亮，说明细菌外壳破得越惨。",
            "analogy": "相当于往防盗门外面泼荧光粉：门如果被砸漏了，荧光粉渗进木缝里立刻亮起来。",
            "in_paper": "揭示了惊人分化：只有 MAD2.2 直接暴力破膜，而 MAD5.1/5.3 是『温柔非破膜』机制！",
        },
        "Hemolysis": {
            "zh": "溶血性（人红细胞破坏测试）",
            "simple": "把药物和人类新鲜红细胞混在一起，看红细胞会不会被扎破、把红色的血红蛋白漏出来。",
            "analogy": "判断这颗子弹打进血管后，会不会顺手把运输氧气的『红细胞快递车』全扎爆。",
            "in_paper": "MAD5.1/5.3 在有效浓度下零溶血，而暴力破膜的 MAD2.2 有中度溶血——完美对应它们的作用机制差异。",
        },
        "DiaMOND / FICI": {
            "zh": "对角线联合药敏法 / 分级抑菌浓度指数",
            "simple": "测两种药一起吃是『1+1 > 2（协同，FICI≤0.5）』、『1+1 = 2（相加，0.5<FICI≤1 或 <2）』还是『互相拆台（拮抗，FICI>2）』。",
            "analogy": "看看新研发的武林高手和老牌正规军并肩作战时，是配合默契还是互相绊脚。",
            "in_paper": "Figure 5d 测了 24 组配对，100% 都是友好的相加效应，零拮抗，其中 MAD5.1+贝达喹啉达 0.51 逼近强协同！",
        },
        "Poly-arginine Block": {
            "zh": "聚精氨酸模块（连续多个 R）",
            "simple": "精氨酸（R）是带强正电的氨基酸，几个 R 连在一起就像一块超强磁铁，能死死吸住带负电的细菌表面并帮助穿膜。",
            "analogy": "相当于在多肽正中央装了一块强力吸盘。",
            "in_paper": "高性能神经网络（12L, 5N）自发发明的新结构，造就了全场最佳的 MAD5 家族。",
        },
    }

    dimensions = [
        {
            "key": "background",
            "num": "01",
            "title": "研究背景",
            "subtitle": "为什么结核病需要 AI 设计宿主防御肽？现有 AI 又卡在哪？",
            "summary": "耐药肺结核（由结核分枝杆菌 Mtb 引起）是全球重大健康威胁。宿主防御肽（HDP）靠物理破坏细菌外膜起效，细菌极难产生耐药性；但天然 HDP 往往敌我不分（特异性差）、毒伤人体细胞，且无法靠细菌发酵廉价量产，传统试错优化极其烧钱。近年来 AI 虽已用于抗菌肽设计，但主流深度学习模型需要数千甚至上万条序列训练——这些大数据集几乎被常见院内菌（ESKAPE）垄断，而结核菌的数据极其稀缺；且很多 AI 只追杀菌力不管毒性，导致筛出的分子在临床前安全测试中折戟。",
            "beginner_analogy": "想象你要训练一位只靠『看图』就能设计防弹衣破甲弹的 AI 工程师：常规坦克（普通细菌）有上万份历史图纸随便练，但结核菌这种『特种蜡甲重坦』全网只有 100 份零散资料，普通大模型一上手就会严重偏科、甚至造出连友军（人体细胞）一起炸伤的危险武器。",
            "bullets": [
                "HDP（6–30 aa）物理破膜不易诱发耐药，但受困于【窄谱特异性差 + 宿主毒性高 + 化学合成昂贵】三大临床壁垒。",
                "现有 AI 抗菌肽模型（如 AMP Scanner、生成式大模型）高度依赖数千条数据，且严重偏向 ESKAPE 病原体，结核菌处于『数据荒漠』。",
                "传统 AI 筛选往往忽视选择性与安全性，导致体外强效但临床前毒理失败。",
            ],
            "slice_ids": ["S01", "S02", "S03", "S04"],
            "figure_ids": [],
        },
        {
            "key": "objective",
            "num": "02",
            "title": "研究目的",
            "subtitle": "如何用 ~100 条极小数据，挖出更强、更准、更安全的抗结核肽并看懂机理？",
            "summary": "作者提出核心设想：与其让 AI 在 20¹³ 种天文组合里从零盲猜，不如以课题组前期仿生设计的抗结核先导肽 MAD1 为模板（天然瞄准物理破坏分枝菌酸外膜），把问题约束为『宏观生物物理性质主导的破膜过程』，从而仅用约 100 条已知抗分枝杆菌多肽的小数据集，训练出既能大幅提升抗结核效价、又能把选择性与宿主安全性提升近一个数量级的 AI 挖掘工作流（LIMITS），并进一步通过后验分析打开黑箱，揭示抗结核多肽此前未知的构效物理定律。",
            "beginner_analogy": "既然只有 100 份资料，就别让 AI 死背『字母拼写（序列）』，而是先请老专家（MAD1 原型）划好重点：『打穿蜡甲靠的是身材尺寸、电量和疏水性，不是花哨的锁芯结构』——把任务从猜密码降维成调物理参数，小样本也能以小博大！",
            "bullets": [
                "方法目标：建立适用于数据稀缺病原体（~100 条数据）的 LIMITS 混合计算-实验挖掘框架。",
                "药学目标：产出在效价（MIC）、细菌选择性（SI）、肺细胞安全窗（TI）全面碾压母肽 MAD1，且能杀灭休眠持留菌、兼容临床抗生素的新候选肽。",
                "科学目标：通过后验分析提炼出可解释的『结构—功能—性能』生物物理新规律。",
            ],
            "slice_ids": ["S05", "S06", "S07"],
            "figure_ids": ["fig-1"],
        },
        {
            "key": "methods",
            "num": "03",
            "title": "使用了什么方法？",
            "subtitle": "LIMITS 四步闭环：先导突变扫描 + 13 维物理编码 + ML/GA 进化 + 后验反哺",
            "summary": "LIMITS 将湿实验先验与计算进化无缝串联：① 先对模板 MAD1（13 aa）做截短扫描（6 聚/9 聚体）与逐位丙氨酸扫描，实锤 13 aa 为最小活性长度、C 端色氨酸为杀菌弹头；② 搜集 110 条天然线性抗分枝杆菌肽（含 Mtb 及 3 种近亲分枝杆菌），用 Moon–Fleming 跨膜疏水标度通过 DBAASP 计算 13 维连续理化特征（替代 one-hot 编码）；③ 分别训练随机森林（RF）与多层前馈神经网络（ANN-RPROP）预测 MIC；④ 用遗传算法（种子 10 条、交叉率 50、突变率 0.025、每代生 100 条挑 Top 10）自动迭代 50 代挖掘最优序列。",
            "beginner_analogy": "就像打造冠军赛车的 4 步流水线：① 先把老款原型车拆一遍，确认『轴距必须 13 尺、尾翼不能少』；② 给 110 辆历史名车测出 13 项风阻/马力体检表；③ 训练两个 AI 评委（稳重老师傅 RF vs 脑洞大师 NN）；④ 开 50 轮虚拟杂交育种大赛，每轮自动淘汰差生、留下 Top 10 继续繁殖！",
            "bullets": [
                "湿实验先导降维（Fig 2）：6 聚/9 聚截短暴跌 >16 倍，A10–A13 丙氨酸突变掉活 5–10 倍 → 锁定 13 aa 长度与 C 端弹头。",
                "小样本数据集：110 条肽（88 训练 / 22 测试，5 折 CV），来自 Ramón-García (2013)、AntiTbPdb 与 MAD1。",
                "特征工程：12 项 DBAASP 跨膜物理参数 + 序列长度 = 13 维连续输入，彻底避开小样本 one-hot 过拟合。",
                "自动化进化：R 语言 GA 包 + 自动抓取 DBAASP 网页特征脚本，50 代每代评估 100 条新肽。",
            ],
            "slice_ids": ["S08", "S10", "S11", "S12", "S28", "S32", "S33", "S34"],
            "figure_ids": ["fig-1", "fig-2"],
        },
        {
            "key": "validation",
            "num": "04",
            "title": "怎么样验证的？",
            "subtitle": "双层计算体检（内部 CV + 29 条外部盲测）× 六维湿实验『终极考场』",
            "summary": "为了确保不是『电脑里自嗨』，作者设置了极其严苛的验证漏斗：计算层先用真实 vs 预测 R²、二分类混淆矩阵（阈值 10 μM）、PR/ROC 曲线及 29 条未见过的外部抗分枝杆菌肽做盲测，还故意保留预测表现差的 10L/4N NN 作为『低性能阴性对照』；湿实验层则通过微波固相合成 + HPLC 纯化（纯度 ≥90%）制备出 4 个家族共 20 条 AI 肽，依次接受 4 株结核菌 MIC、8 种非分枝杆菌脱靶反筛（算 SI）、人肺细胞 A549 毒性（算 TI）、人红细胞溶血、增殖/饥饿/缺氧三态杀菌动力学、NPN 破膜机理测定及 24 组 DiaMOND 抗生素联用测试！",
            "beginner_analogy": "光在模拟器里拿高分不算数！作者先把 20 条 AI 设计的分子全部真刀真枪合成出来，送进 6 关『魔鬼考场』：① 能不能干掉真毒结核菌？② 会不会误杀 8 种路人细菌？③ 伤不伤人体肺细胞？④ 会不会扎爆人红细胞？⑤ 能不能炸死『装死休眠』的老赖菌？⑥ 和医院现有的 6 种抗结核药一起吃会不会打架？",
            "bullets": [
                "计算四维体检（Fig 3）：回归 R² + 混淆矩阵 + PR/ROC 稳定性 + 29 条全新外部盲测（MSE < 0.2）。",
                "精妙的对照设计（Table 1）：对比 RF+MAD1种子（MAD2）、RF+随机种子（MAD3）、差 NN 对照（MAD4）、优 NN（MAD5）四组。",
                "临床拟真考场（Fig 5）：覆盖强毒株 H37Rv、营养饥饿与缺氧休眠持留菌、人红细胞溶血与 6 种临床药 DiaMOND 联用。",
            ],
            "slice_ids": ["S13", "S15", "S16", "S18", "S20", "S21", "S22", "S25", "S26", "S38", "S39"],
            "figure_ids": ["fig-3"],
        },
        {
            "key": "results",
            "num": "05",
            "title": "结果是怎么样？",
            "subtitle": "NN 产出安全王者 MAD5.1/5.3（TI>100），RF 产出休眠杀手 MAD2.2，PCA 挖出两大新规律",
            "summary": "结果不仅全面达成目标，还出现极具深度的反差亮点：① 综合指标王者是高性能 NN（12L, 5N）产出的 MAD5.1 与 MAD5.3——对强毒 H37Rv 的 MIC 降到 5 μM（比 MAD1 强 4 倍），对 8 种脱靶菌全 >80 μM（选择性 SI > 16，提升 >8 倍），对人肺细胞 IC50 > 500 μM（安全窗 TI > 100，提升 >20 倍）且零溶血！② 而在杀菌动力学与休眠菌考场中，RF 产出的 MAD2.2 夺魁——增殖期 7 天压菌 ~3 logs（媲美异烟肼），营养饥饿休眠菌 10 天杀灭 >2 logs（此时异烟肼完全失效），且 NPN 实验证实只有 MAD2.2 直接暴力破膜（代价是中度溶血），而 MAD5.1/5.3 走温和非破膜路线。③ 全部 24 组多肽+抗生素联用均呈相加效应（FICI 0.51–0.99，零拮抗）。④ PCA 后验分析揭示了『本征无序聚集簇』和『13 aa ≈ 6 nm 外膜厚度』两大物理规律！",
            "beginner_analogy": "最终跑出了两位性格迥异的超级英雄：神经网络教出来的『精准外科医生』MAD5.1/5.3，专杀结核菌、对人体肺和红细胞几乎零伤害，安全余量翻了 20 倍；随机森林教出来的『暴力破门手』MAD2.2，连装死冬眠的顽固结核菌都能 10 天干掉 99% 以上，但顺手会轻微擦伤红细胞——而且两派英雄和医院现有 6 种药都能完美组队，绝不内讧！",
            "bullets": [
                "MAD5.1 / MAD5.3（NN 12L,5N）：H37Rv MIC = 5 μM，SI > 16，A549 IC50 > 500 μM，TI > 100，零溶血，中央演化出全新『聚精氨酸块』。",
                "MAD2.2（RF + MAD1 种子）：唯一直接破膜（NPN 阳性），对增殖期（~3 log）与饥饿/缺氧休眠菌（>2 log）杀伤最猛，TI > 50，伴中度溶血。",
                "联用 100% 友好（Fig 5d）：全部 24 组 FICI ∈ [0.51, 0.99]，无拮抗；MAD5.1 + 贝达喹啉（0.51）逼近强协同！",
                "后验两大新大陆（Fig 4）：13 肽轴长 4.7–5.2 nm 精准匹配 ~6 nm 分枝菌酸外膜；另发现反传统的『无序聚集型』高活性预测簇。",
            ],
            "slice_ids": ["S40", "S42", "S45", "S46", "S47", "S49", "S52", "S53", "S55"],
            "figure_ids": ["table-1", "fig-4", "fig-5"],
        },
        {
            "key": "innovations",
            "num": "06",
            "title": "创新点与批判性审读",
            "subtitle": "六大核心突破 + 必须清醒看到的局限与论文细节瑕疵",
            "summary": "本文的真正含金量在于：它不仅做出了比母肽强一个数量级的抗结核候选肽，更示范了一套『小样本数据贫瘠领域的 AI 科学发现范式』——通过机制先验（MAD1 破膜）+ 物理表征（13 维连续参数）+ 进化搜索（GA）+ 黑箱反解（PCA），反过来让 AI 教给人类科学家以前没意识到的物理定律（13-mer 外膜厚度匹配、镜像对称基序、本征无序聚集新簇）。当然，作为概念验证阶段的工作，它也存在特征偏简（缺 3D 结构）、缺高质量阴性数据、无序簇尚未湿实验验证、缺乏体内动物实验等局限。",
            "beginner_analogy": "最厉害的不是 AI 帮你抽中了一张 SSR 卡，而是它在只有 100 张旧卡的寒酸条件下，不仅抽出了新卡，还顺手把『为什么 13 厘米长的钥匙刚好能捅开 6 纳米厚的防盗门』这个隐藏游戏机制给破解并教给了人类！",
            "bullets": [
                "范式创新：LIMITS 打破大数据垄断，~110 条数据即可在冷门高危病原体上高效定向进化。",
                "算法洞察：揭示树模型（RF 5代内锁死局部最优）与神经网络（NN 跨界探索发现中央聚精氨酸块）在小样本进化中的本质差异。",
                "机理发现①：首次提出 13-mer 长度渐近峰与 ~6 nm 分枝菌酸外膜厚度的物理尺寸匹配假说。",
                "机理发现②：打破『抗菌肽必须规则两亲螺旋』教条，指明『本征无序聚集态』与『镜像对称排布』新方向。",
            ],
            "slice_ids": ["S56", "S57", "S58", "S59"],
            "figure_ids": ["fig-4"],
        },
    ]

    workflow_steps = [
        {"step": "1", "title": "先导扫描降维", "desc": "对模板 MAD1 做截短+丙氨酸扫描，锁定 13 aa 与 C 端弹头"},
        {"step": "2", "title": "小样本物理编码", "desc": "110 条抗分枝杆菌肽转成 13 维跨膜理化特征，训 RF 与 NN"},
        {"step": "3", "title": "GA 50 代进化", "desc": "10 种子交叉突变生 100 候选，自动算特征并筛选 50 代"},
        {"step": "4", "title": "六维湿实验验证", "desc": "合成 20 条肽测 4 株 Mtb、8 脱靶菌、肺细胞、溶血、休眠菌与联用"},
        {"step": "5", "title": "后验机理反解", "desc": "PCA 与 WebLogo 发现 13-mer 外膜匹配律与无序聚集新大陆"},
    ]

    critical_notes = [
        "【作者自承局限 1】特征偏简：仅使用 DBAASP 的 13 维基础理化参数，尚未引入 AlphaFold 等 3D 构象、溶剂可及表面积（SASA）或多级自组装特征。",
        "【作者自承局限 2】阴性样本稀缺：文献天然偏向只报道『有效肽』，训练集缺乏非活性负样本，导致模型在特定序列区存在共同预测盲区，实测 MIC 与预测值并非严格线性一致。",
        "【未验证猜想】PCA 发现的『第二高活性簇（本征无序聚集型抗结核肽）』极其诱人，但本次合成的 21 条肽（Fig 4d 红点/黄点）全部落在传统第一簇，第二簇尚缺湿实验实锤。",
        "【21 天复燃现象】Fig 5a 增殖期杀菌曲线显示第 21 天所有单次给药组（含异烟肼和 4 条肽）菌量都回升至 10⁸，提示后续需评估蛋白酶稳定性与多次/联合给药方案，并推进体内动物实验。",
        "【精读细节核查】文中存在几处细微笔误：P3 培养基配方重复写了两次 L-leucine；P3 正文写缺氧甲硝唑 854 μM 而 Fig 5c 图例标为 584 μM；P5 正文写『8 个六聚体』而 Fig 2b 实际为 6 个六聚体 + 3 个九聚体；MAD2–5 具体序列未印在正文而在 Supporting Table 1。",
    ]

    figure_notes = {
        "fig-1": {
            "plain_summary": "全景展示 LIMITS 如何把『湿实验先验扫描（蓝）→ AI+遗传算法进化（绿）→ 体外实测（黄）→ 后验物理分析反哺（粉）』连成一个不断自我升级的闭环。",
            "how_to_read": "从左往右看：先看蓝色框如何缩小搜索范围，再看中间绿色框内的循环箭头（种子→突变交叉→算13个物理指标→RF/NN预测MIC→挑Top10回流），最后看右侧黄/粉框如何验证并把新知识反馈给模型。",
        },
        "fig-2": {
            "plain_summary": "交代模板肽 MAD1 的仿生由来（a），以及湿实验截短（b）和丙氨酸扫描（c）如何证明『完整 13 个氨基酸缺一不可，且尾巴最后 4 位是杀菌弹头』。",
            "how_to_read": "看表 b：MAD1 第一行仅需 2.5 μM 就能抑菌，截短成 6 聚体（MAD1.1–1.6）数值飙升到 40–>80（越大约差）；看柱状图 c：横轴 A1–A13 代表第几位被换成丙氨酸，柱子越高说明失去这个位置越致命——右端 A10–A13 突然拔高 5–10 倍，一目了然！",
        },
        "fig-3": {
            "plain_summary": "全方位对比随机森林（RF）和 4 种神经网络（NN）的预测准度（a）、分类准确率（b）以及 50 代遗传进化时的探索习性（c, d）。",
            "how_to_read": "a 图点越贴近斜线越准（RF R²=0.891 最高）；b 图蓝色对角线越大越好（RF 和 NN 12L,5N 准确率都达 94%）；最精彩的是底部 c vs d：c 图（RF）第 5 代起就变成一条平线（卡死在局部），d 图（NN 12L,5N）剧烈上下探索（敢于跳出舒适区找新骨架）！",
        },
        "table-1": {
            "plain_summary": "全文最硬核的成绩单！横向对比母肽 MAD1 与 4 组共 20 条 AI 肽在 4 株结核菌、8 种无关菌和人体肺细胞上的真实实验数据。",
            "how_to_read": "只盯最关键的 4 列就够了：① H37Rv（真毒结核菌，越小越强）；② 中间 Kp 到 Sm 共 8 列（无关细菌，越大越好，>80 代表零误伤）；③ SI（选择性，越大越好）；④ 最右列 TI（安全窗，越大越好）。直接看最底部 NN(12L,5N) 组的 MAD5.1 和 MAD5.3：H37Rv=5，SI>16，TI>100，全面碾压第一行母肽 MAD1（20, 2, 5）！",
        },
        "fig-4": {
            "plain_summary": "打开 AI 黑箱的后验大发现：>3000 条预测肽的生物物理地图（b–d）、13 肽神秘长度高峰（e–g）以及镜像对称序列模板（h）。",
            "how_to_read": "b 图越黄代表杀菌力越强，能看到左右两团亮黄色高地；对照 c 图箭头方向，左高地对应传统『净电荷+疏水矩』，右高地竟对应反传统的『聚集+无序』！d 图红点表明本次合成的全在左边，右边还是未开发的宝藏。e 图柱子在 13 处戛然而止，而 f 图训练集高峰在 9，证明 13 是 AI 自己悟出的外膜匹配长度！h 图字母越大代表该位置越偏爱这个氨基酸（蓝=正电，黑=疏水）。",
        },
        "fig-5": {
            "plain_summary": "模拟真实临床严酷环境的实战测试：增殖期（a）、营养饥饿休眠期（b）、缺氧休眠期（c）的动态杀菌曲线，以及与 6 种医院抗结核药联用的热图（d）。",
            "how_to_read": "a/b/c 纵轴是对数级活菌数（CFU/mL），曲线往下掉得越深说明杀菌越狠：注意 b 图绿线（MAD2.2）猛跌超 2 个数量级，而一线药异烟肼（浅蓝）和空白对照贴在一起完全失效！d 图热图看数字：所有 24 个格子的 FIC 分数都在 0.51–0.99 之间，全部是友好相加（无任何 >2 的拮抗），其中深紫色 0.51（MAD5.1+贝达喹啉）几乎达到强协同！",
        },
    }

    # Comprehensive 1:1 slice notes for all 60 slices (S01 - S60)
    slice_notes = {
        "S01": {
            "heading": "全文摘要与核心战报",
            "role": "全篇总纲：用极简篇幅交代研究痛点（序列空间大、AI 缺数据）、核心解法（LIMITS 约 100 条肽小样本工作流）、实测战果（效价/选择性/安全性近数量级提升）与后验机理发现（长度驱动）。",
            "plain_explanation": "一句话剧透：结核菌非常难缠，科学家想用 AI 设计杀菌短肽，但结核菌的训练数据太少了。本文发明了一套叫 LIMITS 的『小样本 AI 造药法』，只用 ~100 条数据就进化出了比原型强好几倍、更精准、更安全的新短肽，还意外发现『13 个氨基酸的长度』是捅穿结核菌外壳的隐藏密码！",
            "key_takeaways": ["仅用 ~100 条小数据运转 AI 工作流", "效价、选择性、安全性近一个数量级跃升", "后验发现序列长度是抗结核活性的关键隐形驱动力"],
            "terms": ["HDP", "LIMITS", "Mtb"],
        },
        "S02": {
            "heading": "背景①：为什么选 HDP？临床卡在哪？",
            "role": "引言第一段：先捧后抑——先确立 HDP 抗耐药的巨大临床潜力，再精准抛出其三大药学转化死穴（低特异性、宿主毒性、化学合成成本高）。",
            "plain_explanation": "动物天生自带一种叫 HDP 的短肽武器，几千年来细菌都没能对它产生广泛耐药——因为它靠物理砸门破膜，细菌想防住得同时大改好几种细胞壁零件，代价太高。但问题是天然 HDP 容易误伤人体细胞和好细菌，而且没法让大肠杆菌帮忙廉价发酵生产，只能昂贵地手工化学合成。",
            "key_takeaways": ["HDP 物理破膜使细菌突变耐药负担过高（Ref 1, 2）", "临床三大障碍：特异性差、脱靶毒性、化学合成昂贵"],
            "terms": ["HDP", "MIC"],
        },
        "S03": {
            "heading": "背景②：AI 辅助设计抗菌肽的兴起",
            "role": "引言第二段前半：顺接『合成筛选太慢太贵』的痛点，引出 AI（关系学习、深度神经网络、约简字母表等）正在掀起抗菌肽理性设计浪潮。",
            "plain_explanation": "既然手工试错太慢太贵，科学家自然想到请 AI 帮忙在电脑里先算好再合成。近年来确实有不少团队用深度神经网络筛出了强效抗菌肽，有的甚至把 20 种氨基酸简化成 9 类来缩小搜索范围。",
            "key_takeaways": ["AI 能从生物复杂性中挖掘全新序列骨架（Ref 4–8）", "约简字母表等技巧已用于压缩序列搜索空间"],
            "terms": ["HDP", "Random Forest vs ANN"],
        },
        "S04": {
            "heading": "核心痛点：大模型的数据饥渴与忽视安全",
            "role": "引言最关键的『挖坑段』：直击现有 AI 方法的两大致命短板（依赖数千条数据+只看 ESKAPE；只追杀菌不顾安全），为本文 LIMITS 登场铺平道路。",
            "plain_explanation": "但现有 AI 抗菌肽模型有个硬伤：太吃数据了！动辄要几千条训练序列，只有医院最常见的 ESKAPE 细菌才攒得出这么多数据，结核菌根本没有。更糟的是，很多 AI 只管挑杀菌最狠的，不管它会不会毒死人体细胞，结果做出来全卡死在临床前毒理测试里。",
            "key_takeaways": ["数千条大数据集仅限于 ESKAPE 病原体，结核菌极度数据稀缺", "忽视菌种特异性与宿主安全导致大量 AI 肽在毒理阶段折戟"],
            "terms": ["ESKAPE", "SI", "TI"],
        },
        "S05": {
            "heading": "破局亮相：提出 LIMITS 小样本工作流",
            "role": "引言转折段（Here, we...）：正式亮出本文解决方案 LIMITS——利用先导肽引导的特征选择，大幅降低所需数据集规模。",
            "plain_explanation": "针对上面的死局，我们开发并部署了一套新方法叫 LIMITS：不盲目喂大数据，而是先拿一条已知有效的『先导肽』做向导，精准挑出关键特征，把 AI 所需的数据量压到极小。",
            "key_takeaways": ["正式定义 LIMITS：Lead Informed Machine Interrogation of Therapeutic Sequences"],
            "terms": ["LIMITS", "HDP"],
        },
        "S06": {
            "heading": "研究目的与核心巧思：MAD1 模板 + 物理参数编码",
            "role": "阐述本文最核心的科学假设与主要成果预告：解释为什么以 MAD1 为模板、用理化参数替代序列编码能在 ~100 条小数据上跑通。",
            "plain_explanation": "我们把 LIMITS 用在肺结核元凶 Mtb 上，并以自己之前设计的 MAD1 肽做模板。妙就妙在 MAD1 是靠物理方式捅破结核菌油膜的——相比精密锁钥配对，物理破膜主要看电荷、疏水性等简单物理指标，所以只用 ~100 条肽的物理参数就能把 AI 训得很准，而且新生成的肽不仅杀菌、特异性、安全性翻倍飙升，还能对付休眠菌并和临床药联用！",
            "key_takeaways": ["MAD1 仿生自结核菌孔蛋白（Ref 10），锚定物理破膜机制", "用连续生物物理参数替代显式氨基酸序列，适配数据贫瘠场景", "子代肽效价/特异性/安全性提升达数量级，且对持留菌有效"],
            "terms": ["MAD1", "Mtb", "Mycomembrane", "Biophysical Features"],
        },
        "S07": {
            "heading": "结果预告：后验发现两大反常识规律",
            "role": "引言收官段：提前抛出本文超越『炼丹造药』的两大基础科学发现，拉高全篇学术立意。",
            "plain_explanation": "最后，我们把 AI 预测结果摊开做复盘分析，居然发现两个大惊喜：① 强效抗结核肽分成截然相反的两派——除了传统的正电螺旋派，还有一派竟然是『柔软无序、爱抱团』的未知新流派；② AI 强烈偏爱 13 个氨基酸的长度，算下来刚好和结核菌 6 纳米厚的外壳一般宽！",
            "key_takeaways": ["发现『本征无序聚集型』抗结核肽第二簇", "发现 13 肽轴长 ≈ 6 nm 分枝菌酸外膜厚度"],
            "terms": ["PCA", "Intrinsically Disordered", "Mycomembrane"],
        },
        "S08": {
            "heading": "方法①：110 条小样本库构建与 13 维理化特征",
            "role": "Methods 开篇：严格交代训练数据来源、筛选标准（自然残基、无非天然修饰）及 13 个输入特征的完整清单，确保研究可复现。",
            "plain_explanation": "我们从文献（Ramón-García 2013 和 AntiTbPdb 数据库）凑齐了 110 条长度 5–27 的天然短肽，为了扩充样本量，把对 3 种结核『近亲细菌』有效的肽也收了进来。然后不用字母直接喂 AI，而是用 Moon–Fleming 跨膜疏水标度算了 12 个物理指标，加上『肽链长度』一共 13 个数字作为 AI 的输入题库。",
            "key_takeaways": ["110 条线性天然肽（5–27 aa，MIC 1–400 μM）", "纳入 M. abscessus / M. bovis / M. smegmatis 扩充多样性", "12 项 Moon–Fleming/DBAASP 理化特征 + 长度 = 13 维特征"],
            "terms": ["Biophysical Features", "MIC"],
        },
        "S09": {
            "heading": "方法①续：序列熵热图与理化多样性分析",
            "role": "补充说明数据集质量体检工具（MetaLogo 计算位点变异熵及特征归一化多样性）。",
            "plain_explanation": "在开训之前，我们用 MetaLogo 工具检查了这 110 条肽在每个位置上氨基酸有多丰富、13 个物理指标分布够不够广，避免题库太单一导致 AI 偏科。",
            "key_takeaways": ["使用 MetaLogo 1.1.3 绘制序列 Logo 与位置熵热图", "对 13 项特征归一化后评估库多样性"],
            "terms": ["Biophysical Features"],
        },
        "S10": {
            "heading": "方法②：随机森林（RF）与神经网络（ANN）建模",
            "role": "交代两类核心监督学习回归模型的 R 语言实现细节、交叉验证策略（88 训练 / 22 测试，k=5）及网络结构搜索范围。",
            "plain_explanation": "我们在 R 语言里请了两位 AI 评委来预测多肽的抑菌浓度 MIC：一位是『随机森林（RF）』，5 折交叉验证平均误差 RMSE=0.20738，表现达标；另一位是『多层前馈神经网络（ANN，RPROP 算法）』，我们在 8–14 神经元、2–6 层的不同脑容量组合里做了系统筛选。",
            "key_takeaways": ["RandomForest 包：88 训练 / 22 测试，5 折 CV 平均 RMSE = 0.20738", "Neuralnet 包（RPROP）：网格交叉验证不同层数与神经元架构"],
            "terms": ["Random Forest vs ANN", "MIC"],
        },
        "S11": {
            "heading": "方法③：LIMITS 遗传算法进化引擎与开源仓",
            "role": "核心算法段：披露 GitHub 开源地址，详述遗传算法第 0 代种子规模（10 条 ≈ 10% 训练集）、交叉率（50）、点突变率（0.025）及每代产出 100 条候选肽的机制。",
            "plain_explanation": "这一段是 LIMITS 的发动机说明书（代码已开源到 GitHub）：第 0 代先挑 10 条种子肽（按前人经验取训练集的 10% 收敛最快），通过『片段互换（交叉率 50）』和『随机改字（点突变率 0.025）』每代生出 100 条多样化的新序列。",
            "key_takeaways": ["开源代码与数据：github.com/MedinaLab2016/MAD1-Machine-Learning", "种子=10（Ref 18）、交叉率=50、突变率=0.025 → 每代 100 候选"],
            "terms": ["LIMITS", "Genetic Algorithm (GA)"],
        },
        "S12": {
            "heading": "方法③续：全自动 DBAASP 特征抓取闭环",
            "role": "工程自动化亮点：说明代码如何把每代新生成的 100 条肽自动上传至 DBAASP 在线工具提取 13 项特征，再经 ML 选出 Top 10 进下一代循环。",
            "plain_explanation": "如果每代 100 条肽都要人工去网页算物理参数，50 代 5000 条能累死人。作者很聪明地写了自动化脚本，自动把候选序列传给 DBAASP 网站、抓回 Excel 物理表、喂给 AI 挑出最强的 10 条当下一代父母，全自动跑完循环。",
            "key_takeaways": ["自动化对接 dbaasp.org 批量提取 13 维特征", "Top 10 强效序列作为下一代种子迭代"],
            "terms": ["Biophysical Features", "Genetic Algorithm (GA)"],
        },
        "S13": {
            "heading": "方法④：模型评估指标（R²、混淆矩阵、PR/ROC）",
            "role": "交代如何严格评估 AI 模型——不仅看回归 R²，还以 MIC ≤ 10 μM 为界转为二分类，构建混淆矩阵与多阈值 PR 曲线。",
            "plain_explanation": "为了全方位给 AI 评委打分，我们既看预测值和真实值的直线贴合度（R²），又把 10 μM 设为『及格线』，统计它有没有把好肽漏掉（召回率）或者把烂肽误判成好肽（精确率）。",
            "key_takeaways": ["线性拟合真实 vs 预测 MIC⁻¹（R²）", "以 MIC ≤ 10 μM 划分活性/非活性，绘制 PR 曲线"],
            "terms": ["MIC", "Random Forest vs ANN"],
        },
        "S14": {
            "heading": "方法④续：ROC 曲线、PCA 与 WebLogo 工具",
            "role": "补充 ROC 曲线 AUC 计算、GraphPad Prism 主成分分析（PCA）及 WebLogo 3 序列图谱软件。",
            "plain_explanation": "接着用 GraphPad Prism 算了 ROC 曲线面积（AUC），并对神经网络预测出的海量序列做 PCA 降维画地图、用 WebLogo 画出每个位置最常出现的氨基酸字母。",
            "key_takeaways": ["PR/ROC AUC 评估分类稳健性", "Prism 10 做 PCA，WebLogo 3 做序列保守性图（Ref 19）"],
            "terms": ["PCA"],
        },
        "S15": {
            "heading": "方法⑤：29 条独立外部验证集构建",
            "role": "防过拟合关键步骤：从 AntiTbPdb 额外挑选 29 条未参与训练/测试的全新抗分枝杆菌线性肽，检验模型真正的『盲考』泛化能力。",
            "plain_explanation": "为了防止 AI 只是死记硬背了题库里的 110 道题，我们又从数据库里专门找了 29 道它从未见过的全新考题（涵盖 5 种分枝杆菌，MIC 跨度 0.01–300 μM）让每个模型盲考三次！",
            "key_takeaways": ["29 条完全独立的抗分枝杆菌线性肽做外部泛化测试（Ref 11）", "每组模型架构均做 3 次重复验证"],
            "terms": ["Mtb", "MIC"],
        },
        "S16": {
            "heading": "湿实验①：固相化学合成与 ≥90% 高纯度质控",
            "role": "交代 20 条 AI 肽的实体制备工艺（Fmoc 微波固相合成、半制备 HPLC 纯化、LC-MS 质谱确证），强调仅使用纯度 ≥90% 的样品进入生物实验。",
            "plain_explanation": "算出来的序列都是电脑里的字母，我们用自动化微波多肽合成仪把它们一颗颗氨基酸接成真药，再用液相色谱提纯、质谱验明正身——只有纯度达到 90% 以上才放行去做杀菌实验，确保数据绝不被杂质带偏。",
            "key_takeaways": ["Fmoc 固相微波合成 + 反相 C18 HPLC 纯化", "LC-MS 验证所有测试肽纯度 ≥ 90%（SI Table 1）"],
            "terms": ["HDP"],
        },
        "S17": {
            "heading": "湿实验②：多菌株培养条件（4 株结核菌 + 多种对照菌）",
            "role": "列出所有受试病原体（强毒 H37Rv、减毒 H37Ra、两株营养缺陷株及 8 种脱靶菌）的标准培养基与 CLSI 培养规范。",
            "plain_explanation": "把『考场里的细菌选手』全部养好：包括货真价实的强毒肺结核菌 H37Rv、实验室安全减毒版 H37Ra、以及大肠杆菌、MRSA 超级金葡菌等一大批用来测『会不会误伤路人』的非结核细菌。",
            "key_takeaways": ["遵循 CLSI 标准在 37°C 摇床培养", "覆盖 4 株 Mtb 菌株与多类革兰阳性/阴性对照菌"],
            "terms": ["Mtb", "ESKAPE"],
        },
        "S18": {
            "heading": "湿实验③：最低抑菌浓度（MIC）梯度稀释设计",
            "role": "说明 96 孔板 2 倍连续梯度稀释配药方案（最高 320 μM 起步，与菌液 1:1 混合）。",
            "plain_explanation": "怎么测 MIC？把多肽母液在 96 孔板里像『对半兑水』一样一格一格稀释成不同浓度，再往每个孔里倒进同样数量的细菌，看看最低浓到哪一格就能把细菌按住不长。",
            "key_takeaways": ["320 μM 母液 2 倍梯度稀释，三复孔，终体积 100 μL"],
            "terms": ["MIC"],
        },
        "S19": {
            "heading": "湿实验③续：不同细菌孵育时长与荧光/肉眼判读",
            "role": "因结核菌分裂极慢，需孵育 96 小时并用 mCherry 红色荧光定量判读 MIC50（重复 ≥3 个独立菌群，n≥9）。",
            "plain_explanation": "普通细菌 24 小时就能长满一盘，但结核菌是个超级慢性子，要养整整 4 天（96 小时）！我们给结核菌装了发光标签（mCherry），用酶标仪读荧光下降 50% 的浓度，且至少做 9 次重复取最稳定的结果。",
            "key_takeaways": ["Mtb 孵育 96 h、M. smegmatis 48 h、其他细菌 24 h", "至少 3 个独立菌群（n ≥ 9）确保高度可重复"],
            "terms": ["MIC", "Mtb"],
        },
        "S20": {
            "heading": "湿实验④：DiaMOND 药物联用相互作用测定",
            "role": "采用 Aldridge 课题组开发的 DiaMOND 方法测多肽与临床抗结核药联用的 FICI（<0.5 协同，0.5–1 相加，>2 拮抗）。",
            "plain_explanation": "临床治肺结核从来不是单打独斗，而是几种药一起吃。我们用高效的对角线法（DiaMOND）测试新多肽和医院常用抗结核药混在一起后，是互相帮忙还是互相拆台。",
            "key_takeaways": ["DiaMOND 剂量反应曲线拟合 Hill 方程计算 FICI（Ref 21, 22）", "分类标准：<0.5 协同、0.5–1 相加、>2 拮抗"],
            "terms": ["DiaMOND / FICI"],
        },
        "S21": {
            "heading": "湿实验⑤：三态杀菌动力学（增殖、缺氧、饥饿持留菌）",
            "role": "详述 21 天增殖期、厌氧箱 3 周诱导缺氧休眠期、PBST 14 天营养饥饿休眠期三种严酷细菌模型的构建与涂板计数（CFU）方案。",
            "plain_explanation": "光测停不停长（MIC）不够，还得看能不能真的把细菌『杀光』！我们专门造了三种状态的结核菌：正常活跃疯长的、关在无氧箱里憋了 3 周装死的、以及泡在清水缓冲液里饿了 14 天休眠的，每隔几天取样涂平板数活菌（CFU），一测就是 2–3 周！",
            "key_takeaways": ["增殖期 H37Rv（21 天，对照异烟肼）", "缺氧 NRP H37Ra（厌氧 3 周，对照异烟肼/甲硝唑）", "营养饥饿 NRP H37Rv（饥饿 14 天，对照异烟肼/莫西沙星）"],
            "terms": ["Persister / NRP Mtb", "Mtb"],
        },
        "S22": {
            "heading": "湿实验⑥：NPN 外膜通透性（破膜机制）检测",
            "role": "介绍用疏水荧光探针 NPN 测定 4 条核心肽（MAD2.2, 3.1, 5.1, 5.3）是否直接破坏结核菌外膜。",
            "plain_explanation": "怎么判断这几条多肽是不是靠『砸烂外膜』来杀菌？我们加入一种叫 NPN 的荧光侦探分子，如果细菌外壳被多肽捅破了，NPN 就会钻进膜缝隙里发出强光。",
            "key_takeaways": ["测试 0.1×–10× MIC 浓度下的 NPN 荧光摄取（Ref 10）", "以 PBS 为阴性对照、1% Triton X-100 强去垢剂为 100% 破膜阳性对照"],
            "terms": ["NPN Assay", "Mycomembrane"],
        },
        "S23": {
            "heading": "湿实验⑥续：NPN 混匀与瞬时荧光读数参数",
            "role": "补充 NPN 浓度（40 μM）、样本重复数（n=9）及激发/发射波长（350/420 nm）。",
            "plain_explanation": "把稀释好的结核菌和 NPN 染料混匀加进含多肽的孔板里，马上用仪器在 350/420 纳米波长下读荧光强度，共做 9 次平行重复。",
            "key_takeaways": ["OD600=0.2 菌液 + 40 μM NPN，n=9，Ex/Em = 350/420 nm"],
            "terms": ["NPN Assay"],
        },
        "S24": {
            "heading": "湿实验⑥续：外膜通透率计算公式",
            "role": "给出将原始荧光值归一化为 0%–100% 破膜百分比的标准公式。",
            "plain_explanation": "公式很简单：（加药后的荧光 − 没加药的背景荧光）÷（彻底溶解外壳的洗洁精对照荧光 − 背景荧光），就能算出多肽把细菌外膜破坏了百分之多少。",
            "key_takeaways": ["相对于 1% Triton X-100（100% 裂解）计算相对破膜率"],
            "terms": ["NPN Assay"],
        },
        "S25": {
            "heading": "湿实验⑦：人肺上皮细胞 A549 毒性（MTT 法）",
            "role": "选用与肺结核感染部位高度相关的人肺上皮细胞 A549，在 10–500 μM 超宽浓度下测 24 h 细胞存活率及 IC50（n=12）。",
            "plain_explanation": "肺结核长在肺里，所以必须拿人类肺细胞（A549）来测安全性！把多肽一路加到高达 500 μM 泡 24 小时，用 MTT 显色法看肺细胞还能活多少，算出让细胞死一半的浓度 IC50（越高越安全）。",
            "key_takeaways": ["A549 人肺细胞测试 10–500 μM（n=12）", "以 10% DMSO 为 100% 致死阳性对照，非线性拟合 IC50"],
            "terms": ["TI"],
        },
        "S26": {
            "heading": "湿实验⑧：健康人新鲜红细胞溶血实验",
            "role": "交代获 IRB 伦理批准后，采集 2 名健康志愿者的全血在 0.5–100 μM 范围测定红细胞溶血毒性（Ref 25）。",
            "plain_explanation": "除了肺细胞，药物进了身体还会碰到血液里的红细胞。我们合法合规地采了两位健康捐献者的新鲜血液，把 4 条明星肽加进去，检验它们会不会把红细胞扎破。",
            "key_takeaways": ["2 名健康供体新鲜全血（IRB 00012449 批准），0.5–100 μM"],
            "terms": ["Hemolysis"],
        },
        "S27": {
            "heading": "湿实验⑧续：红细胞洗涤、414 nm 吸光度与溶血率公式",
            "role": "补充 0.5% 红细胞悬液制备、37°C 孵育 1 h、414 nm 测游离血红蛋白吸光度及溶血率计算（n=24）。",
            "plain_explanation": "红细胞如果被扎破，里面的血红蛋白会漏到上清液里让液体变红。1 小时后离心取上清，在 414 纳米测红色深浅，和 1% Triton 洗洁精完全溶血对照一比，就算出溶血百分比（共 24 次重复）。",
            "key_takeaways": ["414 nm 检测游离血红蛋白，双供体总计 n=24"],
            "terms": ["Hemolysis"],
        },
        "S28": {
            "heading": "结果①：LIMITS 总体工作流的设计哲学（衔接 Fig 1）",
            "role": "Results 开篇：从原理高度阐释为什么必须先做『截短 + 丙氨酸扫描』再跑『遗传算法』，直接锚定 Figure 1。",
            "plain_explanation": "进入重头戏！我们为什么不直接开跑 AI？因为 13 个位置、每个位置 20 种氨基酸的组合多到像宇宙原子数一样恐怖。先拿 MAD1 做两轮体检（截短找底线 + 丙氨酸扫描找死穴），删掉废话、框定重点，再让遗传算法像自然选择一样一代代把优良基因传下去，小样本也能轻松起飞。",
            "key_takeaways": ["截短扫描确定最小活性长度；丙氨酸扫描锁定关键热点（Ref 26）", "遗传算法擅长在极小初始库和超大空间里做定向进化"],
            "terms": ["LIMITS", "Alanine Mutagenesis", "Genetic Algorithm (GA)"],
        },
        "S29": {
            "heading": "序列空间到底有多庞大？（20¹³ 天文数字）",
            "role": "紧接上段跨页句尾，用 13 肽拥有 20¹³ 种可能组合这一具体数字，具象化『非用 AI 进化不可』的紧迫性。",
            "plain_explanation": "随手算一笔账：仅仅 13 个氨基酸长度，就能拼出 20 的 13 次方（超过 8 万万亿）种不同多肽，全人类合成一万年也试不完，所以必须靠智能算法导航。",
            "key_takeaways": ["13 肽理论搜索空间 = 20¹³ ≈ 8.2 × 10¹⁶"],
            "terms": ["Genetic Algorithm (GA)"],
        },
        "S30": {
            "heading": "LIMITS 落地结核菌的完整闭环演示",
            "role": "概述 LIMITS 在 Mtb 上的全流程运转：跨菌种扩增训练集 → 物理参数预测 MIC → 多代交叉突变 → 多维体外实验 → 后验反哺。",
            "plain_explanation": "具体到结核菌项目，我们把 Mtb 和它三个常用的『替身亲戚』细菌的多肽数据合在一起训练，每代生出 100 条肽、算物理参数、打分留前 10 名循环演化，挑优合成测试后，再把实验和后验分析的新发现反哺给模型，形成越用越聪明的正反馈闭环。",
            "key_takeaways": ["纳入 3 种分枝杆菌替代株扩充训练多样性", "构建『计算预测 → 湿实验筛选 → 后验分析 → 反哺模型』正向闭环"],
            "terms": ["LIMITS", "Mtb", "Biophysical Features"],
        },
        "S31": {
            "heading": "正向反馈闭环说明",
            "role": "承接上段跨栏句尾，点明 LIMITS 不是一次性工具，而是可持续迭代进化的平台。",
            "plain_explanation": "每一轮真实细菌测试和复盘分析的结果，都能重新喂回模型数据库里，让下一代预测越来越准、特征越挑越精。",
            "key_takeaways": ["实验数据回流构成自我强化的正向反馈环"],
            "terms": ["LIMITS"],
        },
        "S32": {
            "heading": "结果②：MAD1 截短扫描——短了就不行！（Fig 2a–b）",
            "role": "用湿实验硬数据证明：常规 RW 肽只需 6 个氨基酸就能杀菌，但抗结核模板 MAD1 截短成 6 聚体活性暴跌 >16 倍，9 聚体也远不如完整 13 肽。",
            "plain_explanation": "先给模板 MAD1 做『瘦身测试』：按以前常规抗菌肽的经验，切出 6 个氨基酸（六聚体）就应该能杀菌了。但一测大跌眼镜——所有六聚体对结核菌的战斗力暴跌 16 倍以上！拉长到九聚体稍微好点，还是打不过完整的 13 肽 MAD1。说明结核菌对长度格外挑剔！",
            "key_takeaways": ["六聚体（MAD1.1–1.6）抗结核活性暴跌 >16 倍（Ref 27 常规规律在此失效）", "九聚体（MAD1.7–1.9）仅部分恢复，未能达到个位数 μM 效价"],
            "terms": ["MAD1", "MIC", "Mtb"],
        },
        "S33": {
            "heading": "结果②续：丙氨酸扫描锁定 C 端『杀菌弹头』（Fig 2c）",
            "role": "通过逐位丙氨酸突变揭示 MAD1 尾部 4 个 α-螺旋残基（尤其是第 13 位色氨酸）突变会导致活性骤降 5–10 倍。",
            "plain_explanation": "接着做『逐个拔零件测试』：把前面 1–9 位分别换成丙氨酸，杀菌力几乎没咋变；可一旦动了尾巴最后 4 位（特别是第 13 位色氨酸），药效立刻暴跌 5 到 10 倍！这说明尾巴这截就是直接杀菌的『导弹弹头』。",
            "key_takeaways": ["C 端 4 个 α-螺旋残基（A10–A13）突变导致 5–10 倍失活", "C 端富含色氨酸区代表抗分枝杆菌核心弹头"],
            "terms": ["Alanine Mutagenesis", "MAD1"],
        },
        "S34": {
            "heading": "结果②结论：头尾分工协作，13 aa 是最小完整单元",
            "role": "把 Fig 2b 与 2c 拼出完整机理拼图：单留 C 端弹头（MAD1.5/1.6）竟完全无效（>80 μM），证明 N 端负责锚定外膜、C 端负责破膜，完整 13 肽缺一不可。",
            "plain_explanation": "但神奇的是，如果把尾巴弹头单独切下来用（MAD1.5/1.6），竟然完全杀不死细菌！这就真相大白了：N 端（头部）虽然不直接炸膜，但它像火箭助推器一样负责把多肽抓牢在结核菌外壳上，再由 C 端（尾部）引爆破膜——所以完整的 13 个氨基酸一个都不能少！",
            "key_takeaways": ["N 端负责接触/锚定分枝杆菌外膜，C 端负责裂菌", "完整 13 aa 为最小活性序列，直接指导后续建模"],
            "terms": ["MAD1", "Mycomembrane"],
        },
        "S35": {
            "heading": "结果③：训练集序列特征与 13 维理化多样性体检",
            "role": "在展示模型成绩前，先透视 110 条训练数据的内部构成：典型的精氨酸/色氨酸交替两亲周期、中央疏水保守位点。",
            "plain_explanation": "开始看 AI 表现前，先给 110 条训练数据做个『体检』：和普通抗菌肽类似，它们大多是带正电的精氨酸（R）和怕水的色氨酸（W）交替排布，而且正中央普遍藏着一个疏水氨基酸。",
            "key_takeaways": ["训练集呈现典型的正电/疏水交替周期（R/W 富集）", "限定 13 项由先导研究挑出的关键生物物理特征"],
            "terms": ["Biophysical Features"],
        },
        "S36": {
            "heading": "数据集隐藏线索：阴性样本少 & 长度集中在 9–13 aa",
            "role": "客观交代训练集的统计分布特点（缺低活性负样本；92% 长度落在 9–13 aa），并提前埋下伏笔：『长度不只是合成偏爱，更是抗结核活性的隐藏关键』。",
            "plain_explanation": "体检发现两个特点：一是文献里大家通常只发『有效肽』，所以无效反面教材很少；二是虽然长度跨度 5–27，但 92% 都落在 9–13 个氨基酸里。别以为这只是图合成省事——后面分析会证明长度对杀结核菌超级关键！",
            "key_takeaways": ["除 MIC 和长度外，其余 11 项物理特征覆盖度很广（SI Fig 2）", "92% 样本在 9–13 aa，埋下后验长度定律的伏笔"],
            "terms": ["MIC", "Biophysical Features"],
        },
        "S37": {
            "heading": "超参数预优化过渡段",
            "role": "简短过渡句：引出遗传算子（突变/交叉率）经验优化及 Figure 3 的全面模型评测。",
            "plain_explanation": "正式上战场之前，我们先用实验调好了遗传算法里的交叉率和突变率，然后全面考评各个机器学习模型的成绩。",
            "key_takeaways": ["遗传算子超参数经经验优化（SI Fig 3）"],
            "terms": ["Genetic Algorithm (GA)"],
        },
        "S38": {
            "heading": "结果③核心：五大模型 R²、混淆矩阵与 PR/ROC 全面PK（Fig 3a–b）",
            "role": "详细解读 Figure 3a–b 与 SI Fig 4–5：对比 RF 与 4 种 NN，揪出 10L/4N 和 14L/6N 的早期高假阳性缺陷，锁定 RF 与 12L/5N NN 为两大优胜选手。",
            "plain_explanation": "五大模型同台竞技结果出炉！回归拟合上随机森林（R²=0.891）最高；但看 10 μM 二分类体检，RF 和『12 层 5 神经元』神经网络双双拿下 94% 准确率，而且 12L/5N 神经网络的 PR 曲线最稳、假阳性最少！反观 10L/4N 和 14L/6N 神经网络一开始就爱乱报假警（ROC AUC ≤ 0.900），被当场抓包。",
            "key_takeaways": ["全部模型 0.69 < R² < 0.90，证明 13 维物理特征抓住了抗结核趋势", "RF（Acc 94%, Recall 98%）与 NN 12L/5N（Acc 94%, Prec 95%, Spec 94%）最优秀", "12L/5N NN 预测波动最小，稳定性优于 RF"],
            "terms": ["Random Forest vs ANN", "MIC"],
        },
        "S39": {
            "heading": "外部 29 肽盲测 & 关键发现：RF 锁死局部 vs NN 全局探索（Fig 3c–d）",
            "role": "全篇算法部分最精彩的一段！用外部 29 肽盲测确认泛化性，保留差模型 10L/4N 作对照，并揭示 RF 5 代内陷局部最优 vs NN 持续随机全局探索的根本差异。",
            "plain_explanation": "拉到 29 条全新盲测肽上一考，除了 10L/4N 差生外，大家误差都低于 0.2 顺利过关！接着让它们跑 50 代遗传进化，神奇的画面出现了：随机森林不到 5 代就一头扎进死胡同卡死不动了（Fig 3c）；而 12L/5N 神经网络却像充满好奇心的探险家，不断跌落又爬上新高（Fig 3d），真正探索了广阔的新序列领地！",
            "key_takeaways": ["外部 29 肽验证：除 10L/4N 外均 <0.2 MSE，但暴露共同预测盲区", "携带 RF、12L/5N NN 进湿实验，并故意带 10L/4N NN 当差生对照", "RF <5 代锁死局部最优；12L/5N NN 具备强全局探索力"],
            "terms": ["Random Forest vs ANN", "Genetic Algorithm (GA)"],
        },
        "S40": {
            "heading": "结果④：第一组 MAD2（RF + MAD1 种子）湿实验启动（Table 1）",
            "role": "正式转入实体多肽湿实验验证！从 RF+MAD1 种子的进化池中兼顾效价与多样性挑出 5 条肽（MAD2.1–2.5）。",
            "plain_explanation": "纸上谈兵结束，真药上场！第一轮我们拿 10 份母肽 MAD1 当种子喂给随机森林，从 50 代结果里挑出 5 条既强又各具特色的候选肽（MAD2 家族）合成实测。",
            "key_takeaways": ["RF + 10 份 MAD1 种子 → 优选 5 条（MAD2.1–2.5）进入合成"],
            "terms": ["MAD1", "Random Forest vs ANN"],
        },
        "S41": {
            "heading": "MAD2 家族抗菌战绩：全保 C 端色氨酸，靠分枝菌酸外膜起效",
            "role": "报告 MAD2 家族对 4 株 Mtb（5–40 μM）及两种富含分枝菌酸的非结核菌的实测 MIC，进一步印证色氨酸弹头与外膜互作机理。",
            "plain_explanation": "有意思的是，AI 进化出的 5 条 MAD2 肽不约而同全都保留了尾巴末端的色氨酸（再次验证之前丙氨酸扫描没看走眼）！它们对 4 株结核菌都能在 5–40 μM 起效，而且对同样穿『分枝菌酸蜡甲』的近亲细菌也管用，说明依然瞄准的是那层油膜。",
            "key_takeaways": ["MAD2 全员保留 C 端 W，呼应 Fig 2c 丙氨酸扫描结论", "对 4 株 Mtb（含强毒 H37Rv）MIC 为 5–40 μM"],
            "terms": ["Mtb", "MIC", "Mycomembrane"],
        },
        "S42": {
            "heading": "MAD2 家族特异性（SI）与人肺细胞安全性（TI）评估",
            "role": "用 8 种非分枝杆菌反筛算选择性指数 SI，用人肺细胞 A549 测毒性指数 TI——MAD2.2 成为首轮黑马。",
            "plain_explanation": "接着考它们『会不会误伤好人』：拿去测 8 种普通细菌（大肠杆菌、MRSA 等）和人体肺细胞 A549。结果 MAD2.2 表现亮眼：对强毒结核菌只要 10 μM，对无关菌几乎无害（SI 翻倍到 4），安全窗一路飙升！",
            "key_takeaways": ["反筛 8 种非分枝杆菌建立 SI = MIC_Off / MIC_H37Rv", "MAD2.2 是 MAD2 组唯一实现 SI 翻倍（4 vs 2）的候选肽"],
            "terms": ["SI", "TI", "ESKAPE"],
        },
        "S43": {
            "heading": "MAD2.2 与 MAD2.5 安全性突破（IC50 > 500 μM）",
            "role": "承接上段报出 MAD2.2（TI > 50）和 MAD2.5（TI > 25）的超高人肺细胞安全余量。",
            "plain_explanation": "MAD2.2 和 MAD2.5 加到 500 μM 超高浓度都伤不到一半的人体肺细胞！算下来 MAD2.2 的安全窗 TI 超过 50，直接比母肽 MAD1（TI=5）安全了 10 倍以上！",
            "key_takeaways": ["MAD2.2：A549 IC50 > 500 μM，TI > 50（较 MAD1 提升 10×）"],
            "terms": ["TI"],
        },
        "S44": {
            "heading": "第二组 MAD3（RF + 随机种子）：换种子救不了随机森林",
            "role": "控制变量实验：只把 RF 的初始种子从 MAD1 换成训练集随机肽，结果 MAD3.2–3.5 反而全面倒退（仅 MAD3.1 尚可），证明瓶颈在 RF 模型本身而非种子。",
            "plain_explanation": "为了搞清楚『随机森林卡死是不是因为只喂了 MAD1 一种种子』，我们改用随机挑选的多样种子重跑 RF 得到 MAD3 家族。结果这批肽虽然长相大变（两正两疏水周期重复），但战斗力和安全性反而不如上一组（只有 MAD3.1 表现不错）。结论：单靠换种子救不了保守的随机森林！",
            "key_takeaways": ["MAD3 呈『2 碱性(R/K) + 2 疏水(L/I)』重复周期", "MAD3.2–3.5 普遍弱于 MAD2，仅 MAD3.1 具 TI > 25", "证明随机森林框架本身存在外推天花板"],
            "terms": ["Random Forest vs ANN", "SI", "TI"],
        },
        "S45": {
            "heading": "第三/四组 MAD4 vs MAD5：差生 NN 对照 vs 优等生 NN（12L, 5N）",
            "role": "高潮对决！先用差生对照 10L/4N NN（MAD4 组）证实离线指标差确实产出平平，再引出优等生 12L/5N NN 产出的 MAD5 家族——全员演化出全新『中央聚精氨酸块』！",
            "plain_explanation": "终于轮到神经网络登场！先拿离线考试不及格的 10L/4N 当反面对照（MAD4 组），果然杀菌力平平；再看学霸 12L/5N 神经网络产出的 MAD5 家族——太惊艳了，这 5 条肽的正中央全都自发长出了一段以前从未见过的『聚精氨酸强正电模块』！",
            "key_takeaways": ["差生对照 MAD4（10L,4N）对 H37Rv 仅中等活性（10–40 μM），验证评估指标有效", "学霸 MAD5（12L,5N）全员演化出全新『中央聚精氨酸块』"],
            "terms": ["Random Forest vs ANN", "Poly-arginine Block"],
        },
        "S46": {
            "heading": "全场 MVP 诞生：MAD5.1 与 MAD5.3 全面碾压母肽！",
            "role": "报出全篇最耀眼的湿实验数字：MAD5.1/5.3 实现 H37Rv 5 μM、SI > 16、TI > 100，彻底证实 NN 版 LIMITS 能同时拿下效价、特异性与安全性。",
            "plain_explanation": "学霸交卷直接满分！MAD5 家族在杀菌、精准、安全三项全能横扫：明星分子 MAD5.1 和 MAD5.3 杀强毒结核菌只需 5 μM（比母肽强 4 倍），对 8 种无关菌全 >80 μM（精准度 SI > 16，翻了 8 倍多），对人肺细胞安全窗 TI > 100（暴涨 20 倍以上）！",
            "key_takeaways": ["MAD5.1 & MAD5.3：MIC_H37Rv = 5 μM，SI > 16，TI > 100", "神经网络版 LIMITS 成功兼顾强效、窄谱与超高生物相容性"],
            "terms": ["MIC", "SI", "TI", "Poly-arginine Block"],
        },
        "S47": {
            "heading": "结果⑤：后验 PCA 揭示两片截然相反的高活性大陆（Fig 4a–c）",
            "role": "打开 AI 黑箱！对 >3000 条神经网络高分预测肽做 PCA 降维，在经典『正电+疏水矩』区之外，意外发现反传统的『聚集+无序』第二簇。",
            "plain_explanation": "造出好药还不够，我们还想知道 AI 到底悟出了什么秘诀！把神经网络预测的 3000 多条高分肽画到一张二维物理地图（PCA）上，惊呆了：高活性分子竟分成两堆！左堆是教科书教的『高正电+双亲螺旋派』；右堆却完全反着来，全是『爱抱团、软塌塌无序构象』的分子——这可能是人类从未发现过的全新抗结核肽流派！",
            "key_takeaways": ["PCA 分析 >3000 条唯一预测序列，PC1+PC2 解释 >50% 方差", "第一簇：经典 NC、HM、pI 主导（Ref 29）", "第二簇：聚集倾向(AP)、疏水扭转(HT)、无序倾向(DP) 主导"],
            "terms": ["PCA", "Intrinsically Disordered", "Biophysical Features"],
        },
        "S48": {
            "heading": "未开发的宝藏：现有合成肽全在第一簇，第二簇待探索（Fig 4d）",
            "role": "把本次合成的 21 条肽投影回 PCA 空间，诚实指出它们全落在传统第一簇，为后续研究指明第二簇的巨大挖掘价值。",
            "plain_explanation": "我们把这次真刀真枪合成的 21 条肽（MAD1 和 MAD2–5）标在地图上，发现它们全落在左边的传统高地——这意味着右边那片『无序聚集高地』还是一座一铲子都没挖过的处女金矿！",
            "key_takeaways": ["MAD1 与 MAD2–5 全部落入经典第一簇（Fig 4d）", "无序结构簇（第二簇）是未来序列探索的肥沃新大陆"],
            "terms": ["PCA", "Intrinsically Disordered"],
        },
        "S49": {
            "heading": "结果⑤核心惊奇：13 肽长度极限 ≈ 6 nm 分枝菌酸外膜厚度！（Fig 4e–f）",
            "role": "全篇最具科学美感的物理发现！排除训练集众数（9 aa）偏倚后，用氨基酸轮廓长度（3.6–4.0 Å）算出 13 肽长 4.7–5.2 nm，精准匹配冷冻电镜测得的 ~6 nm 分枝菌酸外膜厚度（Ref 33）。",
            "plain_explanation": "复盘时还撞见一个反常识奇观：普通细菌 6–10 个氨基酸就够杀了，可我们的 AI 偏偏把高分肽齐刷刷卡在『13 个氨基酸』的峰顶，超过 13 反而不要！检查训练集发现众数是 9 不是 13，绝不是题库带偏的。一算物理尺寸瞬间破案：13 个氨基酸伸展约 4.7–5.2 纳米，刚好和冷冻电镜拍到的结核菌外膜厚度（~6 纳米）严丝合缝！而且长度对活性的权重甚至超过了电荷和疏水性！",
            "key_takeaways": ["普通 RW 肽最佳 6–10 aa（Ref 30, 31）；抗结核 AI 呈尖锐 13-mer 渐近峰", "训练集众数为 9 aa，排除数据偏倚", "13-mer 轴长 4.7–5.2 nm ≈ 冷冻电镜实测分枝菌酸外膜 ~6 nm（Ref 32, 33）"],
            "terms": ["Mycomembrane", "Biophysical Features"],
        },
        "S50": {
            "heading": "为什么超过 13 个氨基酸反而变差？热力学尾巴负担假说",
            "role": "给出『为什么 13 aa 是上限而非下限』的物理热力学解释：不够长穿不透膜，太长则多出一截暴露在外的尾巴造成热力学惩罚。",
            "plain_explanation": "怎么理解『刚好 13 最佳、太长反倒扣分』？就像用钉子钉 6 毫米厚的木板：钉子太短钉不穿；钉子太长，多出来的半截露在外面晃荡反而增加能量负担（热力学代价），拉低杀菌效率！",
            "key_takeaways": ["足够长才能跨膜破壁；超长暴露尾段产生热力学负担导致效价递减"],
            "terms": ["Mycomembrane"],
        },
        "S51": {
            "heading": "序列蓝图：非周期性的『镜像三明治』排布（Fig 4g–h）",
            "role": "辩证补充：长度不是唯一决定因素（Fig 4g 无单变量线性相关），还需配合独特的『中央正电核 + 两侧疏水翼 + 两端带电』镜像结构（Fig 4h）。",
            "plain_explanation": "当然，光凑够 13 个氨基酸还不行（Fig 4g 显示同样 13 肽有的强有的弱）。传统抗菌肽讲究疏水和正电严格一隔一排，但抗结核 13 肽竟偏爱对称的『三明治阵型』：正中央一团强正电（R/K），左右夹着疏水护法（L/F/I），最外两头再配上带电氨基酸！",
            "key_takeaways": ["两亲性、线性矩、倾斜角呈负相关——不要求严格螺旋周期", "WebLogo（Fig 4h）揭示『两端带电—侧翼疏水—中央碱性块』镜像构型"],
            "terms": ["Poly-arginine Block", "Biophysical Features"],
        },
        "S52": {
            "heading": "结果⑥：增殖期杀菌动力学 & 破膜 vs 非破膜机理分化（Fig 5a）",
            "role": "精选 4 条优胜肽（MAD2.2, 3.1, 5.1, 5.3）进入实战：MAD2.2 7 天压菌 ~3 logs 媲美异烟肼，而 NPN 实验意外揭开『仅 MAD2.2 破膜、其余走非裂解机制』的分化！",
            "plain_explanation": "挑出最强的 4 条肽进实战！在正常分裂的结核菌里，前 14 天 4 条肽都显著压制了细菌，其中 MAD2.2 最猛，7 天就把菌量打掉 99.9%（~3 logs），追平一线金标准药异烟肼！随后一测 NPN 破膜实验，大反转来了：居然只有 MAD2.2 靠砸穿外膜起效，另外三条（包括 MAD5.1/5.3）可能是『悄无声息钻进菌体内部』的非破膜高手！",
            "key_takeaways": ["4 条肽（MIC ≤ 20 μM, TI > 25）前 14 天均显著抑菌", "MAD2.2 第 7 天降菌 ~3 logs，持平一线药异烟肼", "NPN 实验（SI Fig S8）：仅 MAD2.2 破膜，MAD3.1/5.1/5.3 属非裂解机制"],
            "terms": ["NPN Assay", "Mtb"],
        },
        "S53": {
            "heading": "结果⑥重磅：横扫传统抗生素打不动的『休眠持留菌』（Fig 5b–c）",
            "role": "直击肺结核久治不愈的临床核心痛点：在营养饥饿和缺氧休眠模型中，一线药异烟肼完全失效、二线莫西沙星严重钝化，而 MAD2.2 等多肽实现 >2 log 强力清除！",
            "plain_explanation": "真正让肺结核要吃半年药还爱复发的，是躲在免疫细胞里断粮缺氧『装死冬眠』的休眠菌！实验一测果然如此：一线王牌异烟肼对饥饿休眠菌完全没辙，二线强药莫西沙星也大幅哑火。但我们的 AI 肽立大功了——MAD2.2 仅 10 天就把休眠菌干掉 99% 以上（>2 log），缺氧模型里它同样是多肽冠军！",
            "key_takeaways": ["营养饥饿休眠态：异烟肼完全失效，MAD2.2 10 天降菌 >2 logs", "缺氧休眠态：MAD2.2 同样为多肽最强（MAD5.3 7 天后无显著清除）"],
            "terms": ["Persister / NRP Mtb"],
        },
        "S54": {
            "heading": "临床转化神反转：为什么我们的肽比甲硝唑更有戏？（Ref 34）",
            "role": "精准回应 Fig 5c 中阳性对照甲硝唑体外清零的疑问：引用 Ref 34 指出甲硝唑在活体肉芽肿因缺氧不足而失效，反衬 HDP 不依赖代谢状态激活的独特体内潜力。",
            "plain_explanation": "有人看图 5c 可能会问：『那条蓝色的甲硝唑不是在试管里把缺氧菌杀光了吗？』妙就妙在这——前人研究（Ref 34）早已证明甲硝唑进了活体肺肉芽肿就彻底失灵，因为活体里没那么极端缺氧、激活不了它！而我们的多肽压根不管细菌呼不呼吸、睡没睡觉，才是真正有望清扫体内潜伏结核的种子选手！",
            "key_takeaways": ["甲硝唑依赖极端厌氧还原激活，在活体肉芽肿模型中失效（Ref 34）", "HDP 对细菌代谢/呼吸状态不敏感，有望清除体内潜伏灶"],
            "terms": ["Persister / NRP Mtb"],
        },
        "S55": {
            "heading": "临床转化终检：零溶血安全性 + 24 组临床抗生素 100% 友好联用（Fig 5d）",
            "role": "完成临床前最后两道关卡：人红细胞溶血评估（仅破膜派 MAD2.2 中度溶血，其余零溶血）与 6 种临床抗结核药 DiaMOND 联用（100% 相加、零拮抗）。",
            "plain_explanation": "最后两关临床安检：测人红细胞溶血，暴力破膜的 MAD2.2 有中度溶血，但温和派 MAD3.1、MAD5.1、MAD5.3 在治病浓度下对红细胞零伤害！再拿这 4 条肽和医院常用的 6 种抗结核药两两搭档（共 24 组），全部都是 1+1=2 的友好相加效应，没有任何一对互相打架——完全可以无缝加入现有抗结核鸡尾酒疗法！",
            "key_takeaways": ["MAD3.1/5.1/5.3 治疗浓度零溶血；MAD2.2 中度溶血（SI Fig S9）", "与异烟肼、利福平、乙胺丁醇、链霉素、贝达喹啉、莫西沙星 24 组全相加（0.5 < FIC < 2.0），无拮抗"],
            "terms": ["Hemolysis", "DiaMOND / FICI"],
        },
        "S56": {
            "heading": "结论①：回顾小样本抗结核肽的数据困境",
            "role": "Conclusions 首段：呼应引言，再次点出非 ESKAPE 病原体与化学合成成本造成的大数据瓶颈。",
            "plain_explanation": "收尾总结第一段：AI 和生成大模型在大数据领域威力无穷，但抗菌肽不能靠发酵量产、大家又都扎堆研究 ESKAPE 常见菌，导致结核菌这类重要病原体根本攒不出大数据集。",
            "key_takeaways": ["重申非 ESKAPE 病原体高质量生物活性数据极度匮乏的行业现状"],
            "terms": ["ESKAPE", "HDP"],
        },
        "S57": {
            "heading": "结论②：LIMITS 的核心解法与四轮筛选成果",
            "role": "提炼 LIMITS 的方法论精髓（先导模板 + ML/GA + 连续理化特征替代 one-hot），并坦诚承认小样本下预测值与实测 MIC 并非完全一致，但四轮筛选已收获显著飞跃。",
            "plain_explanation": "LIMITS 靠『先导模板引路 + 连续物理参数代替字母编码 + 机器学习配遗传算法』巧妙跨过了小数据门槛。作者也很实诚：小样本下算出来的 MIC 和实测并非百发百中，但跑完四轮筛选还是稳稳拿下了比母肽全面升级的新候选药。",
            "key_takeaways": ["连续物理特征替代 one-hot 编码是小样本奏效的关键", "诚实指出实测 MIC 与预测存在偏差，但四轮筛选显著超越 MAD1"],
            "terms": ["LIMITS", "Biophysical Features"],
        },
        "S58": {
            "heading": "结论③：直面当前局限——特征尚简（仅 13 维）",
            "role": "科学严谨的局限性剖析：指出目前仅用 DBAASP 13 维基础理化特征是为了在概念验证阶段压缩空间、加快速度。",
            "plain_explanation": "作者主动亮出短板：现阶段只用了 13 个基础物理指标，模型还比较简单，主要是为了先快速跑通概念验证。",
            "key_takeaways": ["仅纳入 13 项基础理化特征以约束首轮概念验证空间"],
            "terms": ["Biophysical Features"],
        },
        "S59": {
            "heading": "结论④：未来升级路线——引入 3D 结构预测与高质量阴性数据",
            "role": "展望下一代 LIMITS：加入溶剂可及表面积（SASA）、3D 结构预测（捕捉多级自组装）及可靠阴性数据集以消除预测盲区。",
            "plain_explanation": "下一步怎么升级？团队正在把计算机 3D 结构预测、表面积和多级自组装特征加进模型，同时补齐高质量的『无效反面教材（阴性数据集）』来填平预测盲区，让 LIMITS 去探索更多人类未知的构效新大陆。",
            "key_takeaways": ["正在整合 in silico 3D 结构预测与 SASA 等高阶特征", "补齐高质量阴性数据集是消除预测盲区的关键下一步"],
            "terms": ["LIMITS", "Intrinsically Disordered"],
        },
        "S60": {
            "heading": "补充材料（Supporting Information）官方入口",
            "role": "指引读者免费获取完整 SI PDF（含 MAD2–MAD5 全部氨基酸序列、纯度、PR/ROC/外部验证图、NPN 与溶血原始数据）。",
            "plain_explanation": "这篇论文的完整补充材料在 ACS 官网免费开放，里面藏着正文没印出来的 20 条新肽完整序列（Supplementary Table 1）、破膜和溶血曲线原图——你可以直接在右侧『关联资源』面板点击直达！",
            "key_takeaways": ["ACS 官方免费提供完整 SI PDF（含全部候选肽序列与统计检验表）"],
            "terms": ["HDP"],
        },
    }

    return {
        "mode": "llm_deep",
        "paper_title_zh": "基于先导肽信息引导的 AI 抗结核宿主防御肽挖掘",
        "one_sentence_tldr": "面对结核分枝杆菌训练数据极度稀缺（仅 ~110 条）的困境，作者提出 LIMITS 小样本『湿实验扫描 + 13 维理化编码 + ML/GA 进化』闭环，挖出效价强 4 倍、选择性高 8 倍、安全窗翻 20 倍的新型抗结核肽（MAD5.1/5.3）及休眠菌强杀手（MAD2.2），并揭示『13 肽 ≈ 6 nm 外膜厚度』与『本征无序聚集新簇』两大物理规律。",
        "beginner_hook": "没有生物背景也能秒懂：肺结核菌就像全身披着 6 纳米厚蜡质防弹衣的『重装坦克』，普通抗生素打不穿还怕它装死冬眠。由于全网针对它的有效短肽数据只有 100 条左右，传统大数据 AI 根本练不起来；本文巧妙地先拿一条原型破甲弹（MAD1）摸清物理要害，再用『13 项体检数据 + AI 评委 + 50 代赛马育种』，造出了既能专杀结核菌、又不伤人体肺和红细胞的超级短肽！",
        "workflow_steps": workflow_steps,
        "dimensions": dimensions,
        "critical_notes": critical_notes,
        "glossary": glossary,
        "figure_notes": figure_notes,
        "slice_notes": slice_notes,
    }


def main() -> None:
    PAPER_DIR.mkdir(parents=True, exist_ok=True)
    (PAPER_DIR / "resources.json").write_text(
        json.dumps(build_resources(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PAPER_DIR / "ref_cache.json").write_text(
        json.dumps(build_ref_cache(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (PAPER_DIR / "analysis.json").write_text(
        json.dumps(build_analysis(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Seeded rich demo bundle into {PAPER_DIR}")


if __name__ == "__main__":
    main()
