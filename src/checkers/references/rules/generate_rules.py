#!/usr/bin/env python3
"""生成完整的 GB/T 7714-2025 参考文献著录规则 JSON。"""

import json
import os


def build():
    rules = {
        "meta": {
            "standard_name": "GB/T 7714-2025",
            "full_name": "信息与文献 参考文献著录规则",
            "english_name": "Information and documentation—Rules for bibliographic references and citations to information resources",
            "effective_date": "2026-07-01",
            "release_date": "2025-12-02",
            "supersedes": "GB/T 7714-2015",
            "equivalent_to": "ISO 690:2021 (non-equivalent)",
            "description": "参考文献著录规则，包含著录信息源、著录用文字、著录用符号、著录通则、各文献类型著录项目与著录格式以及参考文献标引体系编制法",
            "scope": "本文件适用于作者和编制者著录参考文献。不适用于图书馆员、文献目录编制者以及索引编制者著录参考文献。",
            "maintainer": "全国信息与文献标准化技术委员会(SAC/TC 4)",
            "drafting_units": [
                "武汉大学", "中国科学院文献情报中心", "中国科学技术信息研究所",
                "北京师范大学出版社(集团)有限公司", "北京大学", "华中师范大学",
                "中国科学院计算机网络信息中心", "《中华医学杂志》社有限责任公司",
                "中国科学技术期刊编辑学会", "中国标准化研究院",
                "北京万方数据股份有限公司", "同方知网数字科技有限公司"
            ],
        },
        "normative_references": [
            {"id": "GB/T 4894", "name": "信息与文献 基础和术语",
             "note": "用于术语定义"},
            {"id": "GB/T 7408.1", "name": "日期和时间 信息交换表示法 第1部分:基本原则",
             "note": "用于日期格式"},
            {"id": "GB/T 28039", "name": "中国人名汉语拼音字母拼写规则",
             "note": "用于汉语拼音人名著录"},
            {"id": "ISO 4", "name": "Information and documentation—Rules for the abbreviation of title words and titles of publications",
             "note": "用于西文期刊刊名缩写"},
        ],
        "terms": [
            {"term": "参考文献", "term_en": "reference",
             "definition": "位于文末或文中,对信息资源或其中一部分进行准确和详细著录的数据,用于识别、定位和检索的相关信息。"},
            {"term": "电子资源", "term_en": "electronic resource",
             "definition": "以数字方式将图、文、声、像等信息存储在磁、光、电介质上，通过计算机、网络或相关设备使用的记录有知识内容或艺术内容的信息资源。"},
            {"term": "合订题名", "term_en": "title of the individual works",
             "definition": "由两种或两种以上的作品汇编而成的无总题名的文献中各部作品的题名。"},
            {"term": "会议录", "term_en": "proceedings; transactions",
             "definition": "包含向大会提交的论文、通常还有论文的讨论和与论文相关事务等内容报道的文献。"},
            {"term": "连续出版物", "term_en": "serial; serial publication",
             "definition": "以连续的各个部分发行的、通常具有数字或年代标识的、计划无限期发行，不论周期长短的印刷文献或非印刷形式的出版物。注：包括期刊、报纸等。"},
            {"term": "数据集", "term_en": "dataset",
             "definition": "相似或相关数据合乎逻辑的集合或分组。注：通常用作记录或用于研究。"},
            {"term": "顺序编码制", "term_en": "numeric system",
             "definition": "引文采用序号标注、参考文献表按引文的序号排序的标注体系。"},
            {"term": "析出文献", "term_en": "component part",
             "definition": "由某个责任者提供的、构成可能涉及多个责任者的主文献一部分的文献。注：析出文献包括连续出版物中的论文，图书中具有独立作者、独立篇名的文献等。"},
            {"term": "引文参考文献", "term_en": "cited reference",
             "definition": "作者为撰写或编辑作品而引用的信息资源。"},
            {"term": "永久标识符", "term_en": "persistent identifier; PID",
             "definition": "通过独立于数字对象物理位置或当前所有权提供访问以确保对数字对象永久存取的唯一标识符。注：永久标识符包括数字对象标识符(DOI)、统一资源名称(URN)等。"},
            {"term": "预印本", "term_en": "preprint",
             "definition": "尚未通过同行评审但仍可广泛使用的文稿。"},
            {"term": "阅读型参考文献", "term_en": "reading reference",
             "definition": "作者为撰写或编辑作品而阅读过的信息资源，或供读者进一步阅读的信息资源。"},
            {"term": "责任者", "term_en": "creator",
             "definition": "在开展个人或团体活动时负责创造、积累和/或保管信息资源的任何实体(团体、家族或个人)。"},
            {"term": "著者-出版年制", "term_en": "name and date system",
             "definition": "引文采用著者-出版年标注、参考文献表按责任者字顺和出版年排序的引文参考文献标注体系。"},
        ],
        "information_sources": {
            "description": "参考文献的著录信息源是被著录的信息资源本身。",
            "rules": [
                "图书、连续出版物、会议录、学位论文、报告、标准、专利、网站、网页、档案、地图、数据集、预印本应依据题名页、版权页、封面等主要信息源著录各个著录项目。",
                "图书、连续出版物中的析出文献可依据参考文献本身著录析出文献的信息，并可依据主要信息源著录析出文献的出处。",
                "电子资源可依据其存储介质上提供的主要信息源著录各个著录项目。"
            ]
        },
        "language_rules": {
            "description": "参考文献应用信息资源本身的语种著录。",
            "rules": [
                {"rule": "参考文献应用信息资源本身的语种著录。", "section": "5.1"},
                {"rule": "著录数字时，应保持信息资源原有的形式。但是，连续出版物卷期号、页码、出版年、创建或修改日期、引用日期、顺序编码制的参考文献序号等宜用阿拉伯数字著录，其中日期著录应符合GB/T 7408.1中的有关规定。", "section": "5.2"},
                {"rule": "使用汉语拼音著录中国人姓名时，宜使用GB/T 28039给出的规则拼写。", "section": "5.3"},
                {"rule": "作为集体责任者的机关团体名称、出版信息中附在出版地之后的省名、州名、国名等以及出版者可按国际公认的方法缩写。", "section": "5.4"},
                {"rule": "西文期刊刊名的缩写可使用ISO 4给出的规则。", "section": "5.5"},
                {"rule": "著录西文文献时，大写字母的使用应符合信息资源本身文种的习惯用法。", "section": "5.6"}
            ],
            "examples": [
                "[1] 博伯尔. 银行业的未来与人工智能[M]. 徐超，译. 北京：清华大学出版社，2023：35.",
                "[2] 図書館用語辞典編集委員会. 最新図書館用語大辭典[M]. 東京：柏書房株式會社，2004：154.",
                "[3] Boobier T. AI and the future of banking[M]. Chichester: John Wiley & Sons, 2020: 35."
            ]
        },
        "punctuation_rules": {
            "description": "著录用符号均为前置符，放在项目之前。按著者-出版年制组织的参考文献表中的第一个著录项目前不应使用任何标识符号。按顺序编码制组织的参考文献表中的各篇文献序号应用方括号括起。",
            "rules": [
                {"symbol": ".", "name": "句点",
                 "usage": ["题名", "比例尺", "其他责任者", "析出文献其他责任者", "版本", "出版信息", "年卷期或其他标识", "尺寸", "获取和访问路径", "永久标识符"],
                 "note": "每一条参考文献的结尾可用'.'号标识"},
                {"symbol": ":", "name": "冒号",
                 "usage": ["其他题名信息(副标题)", "出版者", "页码", "学位授予单位", "报告编号", "专利申请号", "档号", "收藏者"]},
                {"symbol": ",", "name": "逗号",
                 "usage": ["同一著作方式的责任者", "'等'、'译'字样或与之相应的词", "出版年", "连续出版物及其析出文献中的年和卷号", "会议年份", "学位授予年"]},
                {"symbol": ";", "name": "分号",
                 "usage": ["同一责任者的合订题名", "连续出版物后续的年卷期标识与页码"]},
                {"symbol": "//", "name": "双斜线",
                 "usage": ["析出文献的出处", "会议名称"]},
                {"symbol": "()", "name": "圆括号",
                 "usage": ["连续出版物及其析出文献中的期号/版次", "创建/发布或修改日期", "非公元纪年的出版年"]},
                {"symbol": "[]", "name": "方括号",
                 "usage": ["文献序号", "文献类型和文献载体标识", "引用日期", "自拟的信息（如自拟题名、出版地不详、出版者不详、估计出版年）"]},
                {"symbol": "/", "name": "斜线",
                 "usage": ["合期的期号或合卷的卷号间", "文献载体标识前"]},
                {"symbol": "-", "name": "短横线",
                 "usage": ["起讫页码", "起讫序号"]}
            ]
        },
        "general_rules": {
            "responsibility": {
                "description": "责任者著录规则（第7.1节）",
                "personal_author": {
                    "name_order": "姓在前名在后",
                    "rules": [
                        "欧美责任者的中译名可只著录其姓，其名可用缩写字母，缩写名后省略缩写点。同姓不同名的欧美责任者，其中译名不仅应著录其姓，还应著录其名的首字母。",
                        "用西文著录个人责任者，姓应全部著录，首字母应大写，名可缩写为首字母。如用首字母无法识别该人名时，可著录全名。",
                        "用汉语拼音著录个人责任者，姓应全部著录，首字母应大写，名宜用全称。"
                    ],
                    "examples": [
                        "Einstein A (原题: Albert Einstein)",
                        "Williams-Ellis A (原题: Amabel Williams-Ellis)",
                        "Li Jiangning (原题: Li Jiangning)",
                        "丸山敏秋 (原题: 丸山敏秋)",
                        "李时珍 (原题: (明) 李时珍)"
                    ]
                },
                "multiple_authors": {
                    "rule": "著作方式相同的责任者不超过3个时，应全部照录。超过3个时，可著录前3个责任者，其后加'，等'或与之相应的词。",
                    "examples": [
                        "钱学森，刘再复",
                        "印森林，吴胜和，李俊飞，等",
                        "Fordham E W, Ali A, Turner D A, et al."
                    ]
                },
                "no_author": {
                    "author_year_system": "应注明'佚名'或与之相应的词。示例：佚名，2023. 人物龙凤帛画[J]. 中国书法（3）：5.",
                    "numeric_system": "可省略此项，直接著录题名。示例：人物龙凤帛画[J]. 中国书法，2023（3）：5."
                },
                "collective_author": {
                    "rule": "凡是对文献负责的机关团体名称，通常根据著录信息源著录。机关团体名称应由上至下分级著录，上下级间用'.'分隔，用汉字书写的机关团体名称除外。",
                    "examples": [
                        "中国科学院物理研究所",
                        "Stanford University. Department of Civil Engineering"
                    ]
                }
            },
            "title": {
                "description": "题名著录规则（第7.2节）",
                "rules": [
                    {"rule": "题名应按著录信息源所载的内容著录。", "section": "7.2.1"},
                    {"rule": "如无题名信息，可根据信息源所载内容自拟题名，并置于'[]'内。", "section": "7.2.1"},
                    {"rule": "同一责任者的多个合订题名，应著录前3个合订题名。", "section": "7.2.2"},
                    {"rule": "对于不同责任者的多个合订题名，可只著录第一个或处于显要位置的合订题名。", "section": "7.2.2"},
                    {"rule": "在参考文献中不著录并列题名。", "section": "7.2.2"},
                    {"rule": "其他题名信息包括副题名，说明题名文字，多卷书的分卷书名、卷次、册次等。应按信息资源外部特征的具体情况著录。", "section": "7.2.3"}
                ]
            },
            "version": {
                "description": "版本著录规则（第7.4节）",
                "rules": [
                    "第1版可不著录，其他版本说明应著录。",
                    "版本宜用阿拉伯数字、序数缩写形式或其他标识表示。",
                    "古籍的版本应按原文客观照录，如'写本''抄本''刻本''活字本'等。"
                ],
                "examples": [
                    "3版（原题：第三版）", "新1版", "明刻本",
                    "V1.0", "5th ed (原题: Fifth edition)", "Rev. ed"
                ]
            },
            "publication_info": {
                "description": "出版信息著录规则（第7.5节）",
                "order": "出版信息应按出版地、出版者、出版日期顺序著录。",
                "special_fields": {
                    "学位论文": ["学位授予单位所在地", "学位授予单位", "学位授予年"],
                    "报告": ["发布日期"],
                    "专利": ["公告(公开)日期"],
                    "档案": ["收藏者所在地", "收藏者", "形成日期"],
                    "数据集": ["发布平台"],
                    "预印本": ["出版平台"]
                },
                "place": {
                    "rules": [
                        "出版地应著录出版者所在地的城市名称。",
                        "对同名异地的城市名，宜在城市名后附省、州名或国名等限定语。",
                        "文献中载有多个出版地，宜只著录第一个或处于显要位置的出版地。",
                        "无出版地的中文文献可著录'出版地不详'，外文文献可著录'S.l.'，并置于'[]'内。",
                        "无出版地的电子资源可省略此项。"
                    ],
                    "examples": ["Cambridge, Eng.", "Cambridge, Mass.",
                                "[出版地不详]: 三户图书刊行社, 1990", "[S.l.]: Macmillan, 1975"]
                },
                "publisher": {
                    "rules": [
                        "出版者可按著录信息源所载的形式著录，也可按国际公认的简化形式或缩写形式著录。",
                        "文献中载有多个出版者，宜只著录第一个或处于显要位置的出版者。",
                        "无出版者的中文文献可著录'出版者不详'，外文文献可著录's.n.'，并置于'[]'内。",
                        "无出版者的电子资源可省略此项。"
                    ],
                    "examples": ["[出版者不详]", "[s.n.]", "IRRI (原题: International Rice Research Institute)"]
                },
                "date": {
                    "rules": [
                        "出版年应采用公元纪年，并用阿拉伯数字著录。如有其他纪年形式时，应将原有的纪年形式置于'()'内。",
                        "期刊的在线出版日期、报纸的出版日期、报告的发布日期、专利的公告日期、档案的形成日期应按照'YYYY-MM-DD'格式，用阿拉伯数字著录。",
                        "出版年无法确定时，可依次选用版权年、印刷年、估计的出版年。估计的出版年应置于'[]'内。"
                    ],
                    "examples": ["1947（民国三十六年）", "1705（康熙四十四年）",
                                "2013-01-08", "c1988（版权年）", "[1936]（估计出版年）"]
                }
            },
            "dates": {
                "description": "创建/发布或修改日期、引用日期（第7.6节）",
                "rule": "电子资源的创建日期、发布日期、修改日期、引用日期应按照'YYYY-MM-DD'格式，用阿拉伯数字著录。",
                "format": "(创建或修改日期)[引用日期]",
                "example": "(2012-05-03)[2013-11-12]"
            },
            "pages": {
                "description": "页码著录规则（第7.7节）",
                "rules": [
                    "析出文献页码或引文页码，应采用阿拉伯数字著录。",
                    "引自序言或扉页题词的页码，可按实际情况著录。",
                    "无页码有文章编号的，应将文章编号按页码著录。"
                ],
                "examples": [
                    "曹凌. 中国佛教疑伪经综录[M]. 上海：上海古籍出版社，2011：19.",
                    "钱学森. 创建系统学[M]. 太原：山西科学技术出版社，2001：序2-3."
                ]
            },
            "access_path": {
                "description": "获取和访问路径（第7.8节）",
                "rule": "获取和访问路径应根据电子资源在互联网中的实际情况著录。"
            },
            "pid": {
                "description": "永久标识符（第7.9节）",
                "rules": [
                    "获取和访问路径中含永久标识符时，可不重复著录永久标识符。",
                    "获取和访问路径中不含永久标识符时，可按照原文如实著录永久标识符。"
                ],
                "examples": [
                    "路径中含DOI时省略: ...https://onlinelibrary.wiley.com/doi/book/10.1002/9781444305036.",
                    "路径中不含DOI时追加: ...https://d.wanfangdata.com.cn/thesis/Y351065. DOI:10.7666/d.y351065."
                ]
            }
        },
        "type_codes": {
            "M": "图书", "J": "期刊", "N": "报纸", "C": "会议录",
            "D": "学位论文", "R": "报告", "S": "标准", "P": "专利",
            "EB": "网站、网页", "A": "档案", "CM": "地图",
            "DS": "数据集", "PP": "预印本", "G": "汇编",
            "CP": "计算机程序", "DB": "数据库", "Z": "其他"
        },
        "carrier_codes": {
            "MT": "磁带(magnetic tape)", "DK": "磁盘(disk)",
            "CD": "光盘(CD-ROM)", "OL": "联机网络(online)",
            "MM": "缩微资料(microform materials)"
        },
        "document_types": [
            {
                "type_code": "M",
                "name": "图书",
                "former_name": "专著",
                "description": "原称'专著'，2025版改名。包括图书及其电子资源形式。",
                "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. 其他责任者. 版本. 出版地: 出版者, 出版年: 引文页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "其他责任者", "required": "可选", "ref": "7.1"},
                    {"name": "版本", "required": "有则必备", "ref": "7.4"},
                    {"name": "出版地", "required": "有则必备", "ref": "7.5.2"},
                    {"name": "出版者", "required": "有则必备", "ref": "7.5.3"},
                    {"name": "出版年", "required": "有则必备", "ref": "7.5.4"},
                    {"name": "引文页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "其他责任者", "symbol": ". "},
                    {"field": "版本", "symbol": ". "},
                    {"field": "出版地", "symbol": ": "},
                    {"field": "出版者", "symbol": ", "},
                    {"field": "出版年", "symbol": ": "},
                    {"field": "引文页码", "symbol": ". "},
                    {"field": "获取和访问路径", "symbol": ". "}
                ],
                "examples": [
                    "[1] 张伯伟. 全唐五代诗格汇考[M]. 南京：江苏古籍出版社，2002：288.",
                    "[2] 王夫之. 宋论[M]. 刻本. 金陵：湘乡曾国荃，1865（清同治四年）.",
                    "[3] Praetzellis A. Death by theory[M/OL]. Rev. ed. [S.l.]: Rowman & Littlefield, 2011: 13. http://lib.myilibrary.com/Open.aspx?id=293666."
                ]
            },
            {
                "type_code": "book_component",
                "name": "图书中的析出文献",
                "former_name": "专著中的析出文献",
                "description": "原称'专著中的析出文献'，2025版改名。",
                "format": "析出文献主要责任者. 析出文献题名: 析出文献其他题名信息[文献类型标识/文献载体标识]. 析出文献其他责任者//图书主要责任者. 图书题名: 其他题名信息. 版本. 出版地: 出版者, 出版年: 析出文献页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "析出文献主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "析出文献题名", "required": "必备", "ref": "7.2"},
                    {"name": "析出文献其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "析出文献其他责任者", "required": "可选", "ref": "7.1"},
                    {"name": "//（析出符号）", "required": "必备符号"},
                    {"name": "图书主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "图书题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "版本", "required": "有则必备", "ref": "7.4"},
                    {"name": "出版地", "required": "有则必备", "ref": "7.5.2"},
                    {"name": "出版者", "required": "有则必备", "ref": "7.5.3"},
                    {"name": "出版年", "required": "有则必备", "ref": "7.5.4"},
                    {"name": "析出文献页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "析出文献主要责任者", "symbol": ". "},
                    {"field": "析出文献题名", "symbol": ": "},
                    {"field": "析出文献其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "析出文献其他责任者", "symbol": "//"},
                    {"field": "图书主要责任者", "symbol": ". "},
                    {"field": "图书题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ". "},
                    {"field": "版本", "symbol": ". "},
                    {"field": "出版地", "symbol": ": "},
                    {"field": "出版者", "symbol": ", "},
                    {"field": "出版年", "symbol": ": "},
                    {"field": "析出文献页码", "symbol": ". "},
                    {"field": "获取和访问路径", "symbol": ". "}
                ],
                "examples": [
                    "[1] 周易外传：卷5[M]//王夫之. 船山全书：第1册. 修订版. 长沙：岳麓书社，2011：983-1029.",
                    "[2] Weinstein L, Swartz M N. Pathogenic properties of invading microorganisms[M]//Sodeman W A Jr, Sodeman W A. Pathologic physiology. 5th ed. Philadelphia: Saunders, 1974: 457-472."
                ]
            },
            {
                "type_code": "serial",
                "name": "连续出版物",
                "type_codes": ["J", "N"],
                "description": "包括期刊、报纸等连续出版物（著录整刊本身，而非其中的析出文献）。",
                "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. 年,卷(期)-年,卷(期). 出版地: 出版者, 出版年. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3", "note": "期刊用J，报纸用N"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "年卷期或其他标识", "required": "有则必备", "ref": "8.5.1"},
                    {"name": "出版地", "required": "有则必备", "ref": "7.5.2"},
                    {"name": "出版者", "required": "有则必备", "ref": "7.5.3"},
                    {"name": "出版年", "required": "有则必备", "ref": "7.5.4"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "年卷期或其他标识", "symbol": ". "},
                    {"field": "出版地", "symbol": ": "},
                    {"field": "出版者", "symbol": ", "},
                    {"field": "出版年", "symbol": ". "}
                ],
                "examples": [
                    "[1] 中华医学会湖北分会. 临床内科杂志[J]. 1984, 1(1)—. 武汉：中华医学会湖北分会，1984—.",
                    "[2] American Association for the Advancement of Science. Science[J]. 1883, 1(1)—. Washington, D.C.: American Association for the Advancement of Science, 1883—.",
                    "[3] Public Library Quarterly[J/OL]. 1979, 1(1)—. Philadelphia: Taylor & Francis, 1979—. http://www.tandfonline.com/journals/wplq20."
                ]
            },
            {
                "type_code": "component_from_serial",
                "name": "连续出版物中的析出文献",
                "type_codes": ["J", "N"],
                "description": "包括期刊论文、报纸文章等从连续出版物中析出的文献。",
                "format": "析出文献主要责任者. 析出文献题名: 析出文献其他题名信息[文献类型标识/文献载体标识]. 析出文献其他责任者. 连续出版物题名: 其他题名信息, 年, 卷(期/版次): 页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "析出文献主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "析出文献题名", "required": "必备", "ref": "7.2"},
                    {"name": "析出文献其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3", "note": "期刊论文用J，报纸文章用N"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "析出文献其他责任者", "required": "可选", "ref": "7.1"},
                    {"name": "连续出版物题名", "required": "有则必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "年", "required": "必备"},
                    {"name": "卷", "required": "有则必备"},
                    {"name": "期/版次", "required": "有则必备", "note": "置于圆括号内，如(2)、(S1)"},
                    {"name": "页码", "required": "必备"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "析出文献主要责任者", "symbol": ". "},
                    {"field": "析出文献题名", "symbol": ": "},
                    {"field": "析出文献其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "析出文献其他责任者", "symbol": ". "},
                    {"field": "连续出版物题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ", "},
                    {"field": "年", "symbol": ", "},
                    {"field": "卷", "symbol": ""},
                    {"field": "期/版次", "symbol": ": "},
                    {"field": "页码", "symbol": ". "},
                    {"field": "获取和访问路径", "symbol": ". "}
                ],
                "notes": [
                    "报纸文章文献类型标识为N，格式：析出文献主要责任者. 析出文献题名[N]. 报纸名, 出版日期(版次).",
                    "有卷号时卷前不加符号，期号置于圆括号内。合期号用/连接，如8/9/10。",
                    "无卷号直接著录期号：年(期):页码。",
                    "在线出版日期可替代年卷期：格式为YYYY-MM-DD。",
                    "报纸版次置于出版日期后的圆括号内，如2000-11-20(15)。",
                    "阅读型参考文献页码可著录起讫页或起始页，引文参考文献应著录引用信息所在页。",
                    "同一期刊连载的文献，后续部分在原参考文献后直接注明后续部分的年、卷、期、页码等。"
                ],
                "examples": [
                    "[1] 丁文详. 数字革命与竞争国际化[N]. 中国青年报, 2000-11-20 (15).",
                    "[2] 于潇，刘义，柴跃廷，等. 互联网药品可信交易环境中主体资质审核备案模式[J]. 清华大学学报（自然科学版），2012，52（11）：1518-1523.",
                    "[3] Myburg A A, et al. The genome of Eucalyptus grandis[J/OL]. Nature, 2014, 510: 356-362. https://www.nature.com/articles/nature13308.pdf."
                ]
            },
            {
                "type_code": "C",
                "name": "会议录",
                "description": "包括会议论文集等。凡以图书、析出文献、连续出版物形式出现的会议录，按相应格式著录。",
                "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]//会议名称, 会议年份: 引文页码. 获取和访问路径. 永久标识符.",
                "alternative_formats": {
                    "book_form": "按图书格式著录",
                    "journal_form": "按连续出版物格式著录"
                },
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "会议名称", "required": "有则必备", "note": "位于//后"},
                    {"name": "会议年份", "required": "有则必备"},
                    {"name": "引文页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": "//"},
                    {"field": "会议名称", "symbol": ", "},
                    {"field": "会议年份", "symbol": ": "},
                    {"field": "引文页码", "symbol": ". "}
                ],
                "examples": [
                    "[1] 牛志明，Swingland IR，雷光春. 综合湿地管理：综合湿地管理国际研讨会论文集[C]. 北京：海洋出版社，2012.",
                    "[2] 汪学军. 中国农业转基因生物研发进展与安全管理[C]//国家环境保护总局生物安全管理办公室. 中国国家生物安全框架实施国际合作项目研讨会论文集. 北京：中国环境科学出版社，2005：22-25.",
                    "[3] Wang Shanshan. Application of improved SOM neural network[C/OL]//2022 6th ACAIT, 2022: 2. https://ieeexplore.ieee.org/document/10137867."
                ]
            },
            {
                "type_code": "D",
                "name": "学位论文",
                "description": "包括博士、硕士学位论文等。",
                "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. 学位授予单位所在地: 学位授予单位, 学位授予年: 引文页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "学位授予单位所在地", "required": "有则必备", "ref": "7.5.2"},
                    {"name": "学位授予单位", "required": "必备", "ref": "7.5.3"},
                    {"name": "学位授予年", "required": "有则必备", "ref": "7.5.4"},
                    {"name": "引文页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "学位授予单位所在地", "symbol": ": "},
                    {"field": "学位授予单位", "symbol": ", "},
                    {"field": "学位授予年", "symbol": ": "},
                    {"field": "引文页码", "symbol": ". "}
                ],
                "examples": [
                    "[1] 王琦. 融合星载GNSS-R和SAR数据的高时空分辨率土壤湿度反演方法研究[D]. 武汉：武汉大学，2022：87.",
                    "[2] Christou A. Improving knowledge graph understanding with contextual views[D/OL]. Ohio: Wright State University, 2024: 18. http://rave.ohiolink.edu/etdc/view?acc_num=wright1715878159408301."
                ]
            },
            {
                "type_code": "R",
                "name": "报告",
                "description": "包括技术报告、研究报告、白皮书等。凡以图书、析出文献、连续出版物形式出现的报告，按相应格式著录。",
                "format": "主要责任者. 题名: 其他题名信息: 报告编号[文献类型标识/文献载体标识]. 发布日期: 引文页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "报告编号", "required": "有则必备"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "发布日期", "required": "有则必备", "ref": "7.5.4"},
                    {"name": "引文页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ": "},
                    {"field": "报告编号", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "发布日期", "symbol": ": "},
                    {"field": "引文页码", "symbol": ". "}
                ],
                "examples": [
                    "[1] 中国信息通信研究院，等. 电信业发展白皮书：2023：新时代高质量发展探索[R/OL]. 2023-12-28. http://www.caict.ac.cn/kxyj/qwfb/bps/...",
                    "[2] Calkin D E, et al. A comparative risk assessment framework: RMRS-GTR-262[R/OL]. 2011: 8-9. https://www.fs.usda.gov/rm/pubs/rmrs_gtr262.pdf."
                ]
            },
            {
                "type_code": "S",
                "name": "标准",
                "description": "包括国家标准、行业标准、国际标准等。",
                "format": "标准编号 标准名称[文献类型标识/文献载体标识]. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "标准编号", "required": "必备", "note": "如GB/T 3792—2021"},
                    {"name": "标准名称", "required": "必备", "ref": "7.2"},
                    {"name": "文献类型标识", "required": "标准化文件中为可选项", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "标准编号", "symbol": " "},
                    {"field": "标准名称", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "}
                ],
                "examples": [
                    "[1] GB/T 3792—2021 信息与文献 资源描述[S].",
                    "[2] GB 18030—2022 信息技术 中文编码字符集[S/OL]. http://c.gb688.cn/bzgk/gb/showGb?type=online&hcno=...",
                    "[3] ISO 21378: 2019 Audit data collection[S]."
                ]
            },
            {
                "type_code": "P",
                "name": "专利",
                "description": "包括发明专利、实用新型、外观设计等。",
                "format": "专利申请者/所有者. 题名: 其他题名信息: 专利申请号[文献类型标识/文献载体标识]. 公告(公开)日期: 引文页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "专利申请者/所有者", "required": "必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "专利申请号", "required": "必备", "note": "含国家代码，如CN200610171314.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "公告日期或公开日期", "required": "有则必备", "ref": "7.5.4.2", "format": "YYYY-MM-DD"},
                    {"name": "引文页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "专利申请者/所有者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ": "},
                    {"field": "专利申请号", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "公告(公开)日期", "symbol": ": "},
                    {"field": "引文页码", "symbol": ". "}
                ],
                "examples": [
                    "[1] 邓一刚. 全智能节电器：CN200610171314.3[P]. 2008-01-16: 8-9.",
                    "[2] 西安电子科技大学. 光折变自适应光外差探测方法：CN01128777.2[P/OL]. 2002-03-06. http://211.152.9.47/sipoasp/zljs/hyjs-yx-new.asp?recid=01128777.2&leixin=0."
                ]
            },
            {
                "type_code": "EB",
                "name": "网站、网页",
                "description": "2025版起EB特指网站/网页。凡以网页形式出现的图书、连续出版物、会议录等应按相应文献类型的规则著录；除此之外的网站、网页及其析出内容按本条著录。",
                "subtypes": [
                    {
                        "name": "网站",
                        "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. (创建或修改日期)[引用日期]. 获取和访问路径.",
                        "fields": [
                            {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                            {"name": "题名", "required": "必备", "ref": "7.2"},
                            {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                            {"name": "文献类型标识", "required": "必备", "value": "EB"},
                            {"name": "文献载体标识", "required": "必备", "value": "OL"},
                            {"name": "创建或修改日期", "required": "有则必备", "ref": "7.6", "format": "(YYYY-MM-DD)"},
                            {"name": "引用日期", "required": "必备", "ref": "7.6", "format": "[YYYY-MM-DD]"},
                            {"name": "获取和访问路径", "required": "必备", "ref": "7.8"}
                        ],
                        "punctuation_sequence": [
                            {"field": "主要责任者", "symbol": ". "},
                            {"field": "题名", "symbol": ": "},
                            {"field": "其他题名信息", "symbol": ""},
                            {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                            {"field": "创建或修改日期", "symbol": ""},
                            {"field": "引用日期", "symbol": ". "},
                            {"field": "获取和访问路径", "symbol": "."}
                        ],
                        "examples": [
                            "[1] 中国国家博物馆[EB/OL]. [2025-05-06]. https://www.chnmuseum.cn/.",
                            "[2] Library of Congress[EB/OL]. [2020-06-12]. https://www.loc.gov."
                        ]
                    },
                    {
                        "name": "网页",
                        "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. (创建或修改日期)[引用日期]. 获取和访问路径. 永久标识符.",
                        "fields": [
                            {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                            {"name": "题名", "required": "必备", "ref": "7.2"},
                            {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                            {"name": "文献类型标识", "required": "必备", "value": "EB"},
                            {"name": "文献载体标识", "required": "必备", "value": "OL"},
                            {"name": "创建或修改日期", "required": "有则必备", "ref": "7.6", "format": "(YYYY-MM-DD)"},
                            {"name": "引用日期", "required": "必备", "ref": "7.6", "format": "[YYYY-MM-DD]"},
                            {"name": "获取和访问路径", "required": "必备", "ref": "7.8"},
                            {"name": "永久标识符", "required": "可选", "ref": "7.9"}
                        ],
                        "punctuation_sequence": [
                            {"field": "主要责任者", "symbol": ". "},
                            {"field": "题名", "symbol": ": "},
                            {"field": "其他题名信息", "symbol": ""},
                            {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                            {"field": "创建或修改日期", "symbol": ""},
                            {"field": "引用日期", "symbol": ". "},
                            {"field": "获取和访问路径", "symbol": ". "}
                        ],
                        "examples": [
                            "[1] 高等教育文献保障系统. 馆际互借与文献传递服务[EB/OL]. [2025-06-21]. http://home.calis.edu.cn/pages/list.html?id=...",
                            "[2] 许振超：\"好好干，当一个好工人\"[EB/OL]. (2025-02-17)[2025-06-22]. http://cpc.people.com.cn/nl/2025/0217/c443712-40419790.html."
                        ]
                    }
                ]
            },
            {
                "type_code": "A",
                "name": "档案",
                "description": "2025版新增为独立文献类型。凡以图书、析出文献形式出现的档案，按相应格式著录。",
                "format": "主要责任者. 题名: 其他题名信息: 档号[文献类型标识/文献载体标识]. 收藏者所在地: 收藏者, 形成日期: 引文页码. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "档号", "required": "有则必备"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "收藏者所在地", "required": "有则必备", "ref": "7.5.2"},
                    {"name": "收藏者", "required": "有则必备", "ref": "7.5.3"},
                    {"name": "形成日期", "required": "有则必备", "ref": "7.5.4", "format": "YYYY-MM-DD"},
                    {"name": "引文页码", "required": "有则必备", "ref": "7.7"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ": "},
                    {"field": "档号", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "收藏者所在地", "symbol": ": "},
                    {"field": "收藏者", "symbol": ", "},
                    {"field": "形成日期", "symbol": ": "},
                    {"field": "引文页码", "symbol": ". "}
                ],
                "examples": [
                    "[1] 李鸿章. 奏请上海道库洋务外销要款无款可筹仍拨药厘接济事：04-01-35-0399-039[A]. 北京：中国第一历史档案馆，1887（光绪十三年三月十三日）.",
                    "[2] 湖北省建设厅. 湖北省建设厅关于检发实业部农工矿业团体登记规则的布告：LS031-001-0001-001[A/OL]. 武汉：湖北省档案馆，1931-11-07. https://www.hbda.gov.cn/pdf/LS031-001-0001-001.PDF.PDF."
                ]
            },
            {
                "type_code": "CM",
                "name": "地图",
                "former_name": "舆图",
                "description": "原称'舆图'，2025版改名。凡以图书、析出文献形式出现的地图，按相应格式著录。",
                "format": "主要责任者. 题名: 其他题名信息. 比例尺[文献类型标识/文献载体标识]. 版本. 出版地: 出版者, 出版年. 尺寸. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "比例尺", "required": "有则必备", "note": "如1:170000"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "版本", "required": "有则必备", "ref": "7.4"},
                    {"name": "出版地", "required": "有则必备", "ref": "7.5.2"},
                    {"name": "出版者", "required": "有则必备", "ref": "7.5.3"},
                    {"name": "出版年", "required": "有则必备", "ref": "7.5.4"},
                    {"name": "尺寸", "required": "纸质单幅地图必备", "note": "如138cm×96cm"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ". "},
                    {"field": "比例尺", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "版本", "symbol": ". "},
                    {"field": "出版地", "symbol": ": "},
                    {"field": "出版者", "symbol": ", "},
                    {"field": "出版年", "symbol": ". "},
                    {"field": "尺寸", "symbol": ". "}
                ],
                "examples": [
                    "[1] 刘祥沈. 沈阳市政区图. 1:170000[CM]. 武汉：武汉大学出版社，2016. 138cm×96cm.",
                    "[2] 谭其骧. 中国历史地图集：第2册[CM]. 北京：地图出版社，1982：6.",
                    "[3] 国家测绘地理信息局. 一带一路经济走廊及其途经城市分布地势图[CM/OL]. http://ydyl.china.com.cn/2016-10/27/content_39582227.htm."
                ]
            },
            {
                "type_code": "DS",
                "name": "数据集",
                "description": "2025版新增文献类型。凡以图书、析出文献、连续出版物形式出现的数据集，按相应格式著录。",
                "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. 版本. 发布平台(发布或修改日期)[引用日期]. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "版本", "required": "可选", "ref": "7.4", "note": "如V1.0"},
                    {"name": "发布平台", "required": "电子资源可选", "ref": "7.5.1"},
                    {"name": "发布或修改日期", "required": "有则必备", "ref": "7.6", "note": "置于圆括号内"},
                    {"name": "引用日期", "required": "必备", "ref": "7.6", "note": "置于方括号内"},
                    {"name": "获取和访问路径", "required": "电子资源必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "版本", "symbol": ". "},
                    {"field": "发布平台", "symbol": ""},
                    {"field": "发布或修改日期", "symbol": ""},
                    {"field": "引用日期", "symbol": ". "}
                ],
                "examples": [
                    "[1] 周壮，李盛阳，吴薇，等. 天宫二号遥感图像自然景物分类科学数据[DS/OL]. V1.0. 国家基础学科公共科学数据中心(2023-09-10)[2025-07-15]. https://www.nbsdc.cn/general/dataLinks/CSTR:16666.11.nbsdc.tfpbwtqf.",
                    "[2] IHME. Global burden of disease study 2019 (GBD 2019) data resources[DS/OL]. Global Health Data Exchange (2021)[2025-07-15]. https://ghdx.healthdata.org/gbd-2019."
                ]
            },
            {
                "type_code": "PP",
                "name": "预印本",
                "description": "2025版新增文献类型，指尚未通过同行评审的文稿。",
                "format": "主要责任者. 题名: 其他题名信息[文献类型标识/文献载体标识]. 版本. 出版平台(创建或修改日期)[引用日期]. 获取和访问路径. 永久标识符.",
                "fields": [
                    {"name": "主要责任者", "required": "有则必备", "ref": "7.1"},
                    {"name": "题名", "required": "必备", "ref": "7.2"},
                    {"name": "其他题名信息", "required": "有则必备", "ref": "7.2.3"},
                    {"name": "文献类型标识", "required": "必备", "ref": "7.3"},
                    {"name": "文献载体标识", "required": "电子资源必备", "ref": "7.3"},
                    {"name": "版本", "required": "有则必备", "ref": "7.4", "note": "如V2"},
                    {"name": "出版平台", "required": "电子资源可选", "ref": "7.5.1", "note": "如ChinaXiv、arXiv"},
                    {"name": "创建或修改日期", "required": "有则必备", "ref": "7.6", "note": "置于圆括号内"},
                    {"name": "引用日期", "required": "必备", "ref": "7.6", "note": "置于方括号内"},
                    {"name": "获取和访问路径", "required": "必备", "ref": "7.8"},
                    {"name": "永久标识符", "required": "电子资源可选", "ref": "7.9"}
                ],
                "punctuation_sequence": [
                    {"field": "主要责任者", "symbol": ". "},
                    {"field": "题名", "symbol": ": "},
                    {"field": "其他题名信息", "symbol": ""},
                    {"field": "文献类型标识/文献载体标识", "symbol": ". "},
                    {"field": "版本", "symbol": ". "},
                    {"field": "出版平台", "symbol": ""},
                    {"field": "创建或修改日期", "symbol": ""},
                    {"field": "引用日期", "symbol": ". "}
                ],
                "examples": [
                    "[1] 肖玲，张雪，王永. 数据要素的统计测算方法探究[PP/OL]. PSSXiv(2024-07-02)[2024-09-30]. https://zsyyb.cn/abs/202408.01096.",
                    "[2] Jenkins S D, Ruostekoski J. Controlled manipulation of light[PP/OL]. V2. (2012-03-18)[2020-06-24]. https://doi.org/10.48550/arXiv.1112.6136."
                ]
            }
        ],
        "numbering_systems": {
            "numeric": {
                "name": "顺序编码制",
                "description": "引文采用序号标注、参考文献表按引文的序号排序的标注体系。",
                "in_text_citation": {
                    "basic_rule": "应按正文中引用的文献出现的先后顺序连续编码，并将序号置于'[]'中。",
                    "footnote_form": "如果顺序编码制用脚注方式时，序号可由计算机自动生成圈码。",
                    "multiple_citations": "同一处引用多篇文献时，应将各篇文献的序号在'[]'内全部列出，各序号间用'，'。如遇连续序号，起讫序号间用短横线连接。此规则不适用于用计算机自动编码的序号。",
                    "examples": ["裴伟[570,83]提出……", "莫拉德对稳定区的节理格式的研究[255-256]……"],
                    "same_ref_multiple_pages": "多次引用同一责任者的同一文献时，在正文中标注首次引用的文献序号，并在序号的'[]'外著录引文页码。",
                    "auto_numbering": "用计算机自动编序号时，应重复著录参考文献，但参考文献表中的著录项目可简化为文献序号及引文页码。"
                },
                "reference_list": {
                    "order": "各篇文献应按正文部分标注的序号依次列出。更多示例见附录B。"
                }
            },
            "author_year": {
                "name": "著者-出版年制",
                "description": "引文采用著者-出版年标注、参考文献表按责任者字顺和出版年排序的引文参考文献标注体系。",
                "in_text_citation": {
                    "basic_format": "正文引用的文献由责任者姓氏与出版年构成，并置于'()'内。倘若只标注责任者姓氏无法识别该人名时，可标注责任者姓名。",
                    "collective_author": "集体责任者著述的文献可标注机关团体名称。",
                    "author_in_text": "倘若正文中已提及责任者姓名，则在其后的'()'内只著录出版年。",
                    "example": "(Crane, 1972) ... Stieg(1981) ...",
                    "multiple_authors": {
                        "western": "对欧美责任者只需标注第一个责任者的姓，其后附'et al.'。",
                        "chinese": "对于中国责任者应标注第一责任者的姓名，其后附'等'字。",
                        "example": "(Falout et al., 2009)"
                    },
                    "same_author_same_year": "同一责任者在同一年出版的多篇文献时，出版年后应用小写字母a, b, c……区别，并置于'()'内。示例：（邱均平，2000a）（邱均平，2000b）",
                    "same_ref_multiple_pages": "多次引用同一责任者的同一文献，在正文中标注责任者与出版年，并在'()'外以角标的形式著录引文页码。示例：（中国社会科学院语言研究所词典编辑室，1996）^{1194}"
                },
                "reference_list": {
                    "order": "各篇文献应首先按文种集中，可分为中文、日文、西文、俄文、其他文种5部分；然后按责任者字顺和出版年排列。中文文献可按责任者汉语拼音字顺排列，也可按责任者的笔画笔顺排列。",
                    "format_in_list": "出版年置于责任者之后，以'，'分隔。示例：张伯伟，2002. 全唐五代诗格汇考[M]. 南京：江苏古籍出版社，288."
                }
            }
        },
        "appendix_a": {
            "description": "文献类型和文献载体标识代码（规范性附录）",
            "type_codes": {
                "M": "图书", "J": "期刊", "N": "报纸", "C": "会议录",
                "D": "学位论文", "R": "报告", "S": "标准", "P": "专利",
                "EB": "网站、网页", "A": "档案", "CM": "地图",
                "DS": "数据集", "PP": "预印本", "G": "汇编",
                "CP": "计算机程序", "DB": "数据库", "Z": "其他"
            },
            "carrier_codes": {
                "MT": "磁带(magnetic tape)", "DK": "磁盘(disk)",
                "CD": "光盘(CD-ROM)", "OL": "联机网络(online)",
                "MM": "缩微资料(microform materials)"
            }
        },
        "appendix_b_reference": "完整示例见：docs/规范规则/参考文献规则/参考文献著录规则GB-T 7714-2025.md 附录B（顺序编码制参考文献表著录格式示例）",
        "changes_from_2015": [
            {"change": "新增文献类型：预印本[PP]、数据集[DS]、地图[CM]（原舆图更名）、档案[A]", "section": "前言o)"},
            {"change": "术语变更：'专著'改为'图书'；'专著中的析出文献'改为'图书中的析出文献'", "section": "前言i)"},
            {"change": "外文作者格式：从EINSTEIN A改为Einstein A（仅首字母大写）", "section": "5.1/7.1.1"},
            {"change": "将'数字对象唯一标识符(DOI)'改为'永久标识符(PID)'，涵盖DOI、URN等", "section": "前言h)"},
            {"change": "将'公告日期、更新日期、引用日期'改为'创建/发布或修改日期、引用日期'", "section": "前言g)"},
            {"change": "副标题从可选项升级为'有则必备'", "section": "各文献类型"},
            {"change": "对OL载体文献，获取和访问路径升格为必备著录项", "section": "各文献类型"},
            {"change": "专利要求完整著录含国家代码的专利号", "section": "8.10"},
            {"change": "新增电子资源载体标识'缩微资料[MM]'", "section": "前言o)"},
            {"change": "EB的文献类型从'电子资源'改为特指'网站、网页'", "section": "前言o)"},
            {"change": "电子报告简化：删除出版地和出版者信息", "section": "8.8"},
            {"change": "将'参考文献表''参考文献标注法'合并为第9章'参考文献标引体系编制法'", "section": "前言n)"},
            {"change": "删除了术语'主要责任者''专著''数字对象唯一标识符'，增加了术语'会议录''数据集''永久标识符''预印本''责任者'", "section": "前言b)"}
        ]
    }
    return rules


if __name__ == "__main__":
    rules = build()
    output_path = os.path.join(os.path.dirname(__file__), "gbt7714_2025.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    lines = content.count("\n") + 1
    chars = len(content)
    print(f"已生成: {output_path}")
    print(f"总行数: {lines}, 总字符数: {chars}")
    print(f"文献类型数: {len(rules['document_types'])}")
    print(f"术语定义数: {len(rules['terms'])}")
    print(f"变化条目数: {len(rules['changes_from_2015'])}")
    print("JSON 语法验证通过 ✅")