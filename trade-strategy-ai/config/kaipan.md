

```
通用参数说明：

Date	2026-04-16 #日期
DeviceID	4cac82ffc900bae65f51f73b756612a3911b7a7a # 设备id
Index	0 # 第一条数据的索引
PhoneOSNew	2 # 系统版本
Token	036ca9cad6e44ee4a585c22cb2c298ed # 用户token
UserID	3807176 # 用户id
VerSion	5.23.0.1 # 客户端版本
a	GetPMSL_PMLD # 接口名称
apiv	w44 # 接口版本
c	FuPanLa # 接口模块
st	20 # 分页大小

示例：
第一页： index = 0， st = 20
第二页： index = 20， st = 20
第三页： index = 40， st = 20

```

### 股票所属板块
```
GET

URL	https://apphwshhq.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&StockID=002726&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetFeaturedSection&apiv=w44&c=StockL2Data

**可不传参数: Token，UserID, DeviceID**

{
    "info": [
        [
            "801220", # 板块ID
            "食品饮料", # 板块名称
            -0.23,     # 涨跌幅
            "605388",  # 板块龙头 ID
            "均瑶健康", # 板块龙头名称
            10.05,    # 板块龙头涨跌幅
            0
        ],
        [
            "801412",
            "新零售",
            -0.25,
            "603031",
            "安孚科技",
            9.99,
            0
        ]
    ],
    "ttag": 0.002999999999999947,
    "errcode": "0"
}
```

### 题材详情
```
POST

URL	https://applhb.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&ID=261&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=InfoGet&apiv=w44&c=Theme

**可不传参数: Token，UserID, DeviceID**

{
    "ID": "261",  # 题材ID
    "Name": "华为海思概念", # 题材名称
    "BriefIntro": "华为海思是一家全球领先的Fabless半导体与器件设计公司，致力于为客户提供智能家庭、智慧城市及智能出行等泛智能终端芯片解决方案。产品覆盖智慧视觉、智慧IoT、智慧媒体、智慧交通及汽车电子、显示、手机终端、数据中心及光收发器等多个领域。", # 题材简介
    "ClassLayer": "3",
    "Desc": "",
    "PlateSwitch": "1",
    "StkSwitch": "2",
    "Introduction": "<p>华为海思的发展历程可以追溯到1991年，当时华为成立了ASIC设计中心，开始自主研发芯片。2004年，华为正式成立海思半导体有限公司，专注于半导体和集成电路设计。海思在芯片设计领域积累了丰富的经验，开发了多种芯片产品，包括用于智能设备的麒麟系列、数据中心的鲲鹏系列服务CPU、人工智能的Ascend（升腾）系列SoC、连接芯片（基站芯片天罡、终端芯片巴龙）以及其他专用芯片（视频监控、机顶盒芯片、物联网等芯片）。海思的芯片产品在国内外市场都有广泛应用，公司总部位于深圳，并在全球设有多个办事处和研究中心，拥有7000多名员工。海思已经建立了强大的IC设计和验证技术组合，开发了先进的EDA设计平台，并成功开发了200多种拥有自主知识产权的模型，申请了8000多项专利</p>", # 题材详情
    "CreateTime": "1723785234", # 创建时间
    "UpdateTime": "0", # 更新时间
    "Table": [ # 题材表格
        {
            "Level1": {  # 一级板块
                "ID": "2959",  # 板块ID
                "Name": "供应商服务商", # 板块名称
                "ZSCode": "0",
                "FirstShelveTime": "1723778301",
                "UpdateCacheTime": "0",
                "IsNew": 0, # 是否是新增
                "Stocks": [ # 板块下股票列表
                    {
                        "StockID": "603118", # 股票ID
                        "IsZz": "2", # 是否正宗
                        "IsHot": "1", # 是否热门
                        "Reason": "公司国产海思方案 WIFI 产品已成功获取客户项目，运营商直营业务部突破终端公司组网类新订单", # 原因
                        "FirstShelveTime": "1723778341", # 首次上架时间
                        "UpdateCacheTime": "1723778341", # 更新时间
                        "IsNew": 0, # 是否是新增
                        "prod_name": "共进股份", # 股票名称
                        "Hot": 11636 # 热度
                    }
                ]
            },
            "Level2": [ # 二级板块
                {
                    "ID": "2961",
                    "Name": "整机",
                    "ZSCode": "0",
                    "FirstShelveTime": "1723781360",
                    "UpdateCacheTime": "0",
                    "IsNew": 0,
                    "Stocks": [
                        {
                            "StockID": "600498",
                            "IsZz": "2",
                            "IsHot": "0",
                            "Reason": "公司旗下长江计算作为算力基础设施国家队，与昇腾合作发布了昇腾智造等“智”系列解决方案",
                            "FirstShelveTime": "1723781426",
                            "UpdateCacheTime": "1723781426",
                            "IsNew": 0,
                            "prod_name": "烽火通信",
                            "Hot": 8098
                        }
                    ]
                }
            ]
        },
        {
            "Level1": {
                "ID": "2960",
                "Name": "昇腾910C",
                "ZSCode": "0",
                "FirstShelveTime": "1723781360",
                "UpdateCacheTime": "0",
                "IsNew": 0,
                "Stocks": []
            },
            "Level2": [
                {
                    "ID": "2962",
                    "Name": "高速连接器",
                    "ZSCode": "0",
                    "FirstShelveTime": "1723781360",
                    "UpdateCacheTime": "0",
                    "IsNew": 0,
                    "Stocks": [
                        {
                            "StockID": "688629",
                            "IsZz": "2",
                            "IsHot": "0",
                            "Reason": "华为是公司的第一大客户，且华为占公司通讯类业务的比重超 60%，为其提供高速连接器",
                            "FirstShelveTime": "1723781457",
                            "UpdateCacheTime": "1723781457",
                            "IsNew": 0,
                            "prod_name": "华丰科技",
                            "Hot": 3767
                        }
                    ]
                }
            ]
        }
    ],
    "Stocks": [],
    "StockList": [
        {
            "StockID": "000062",
            "Tag": [
                {
                    "ID": "2957",
                    "Name": "经销商代理商",
                    "Reason": "公司是海思芯片全系列产品授权代理商。"
                }
            ],
            "prod_name": "深圳华强",
            "HotNum": 10428
        },
        {
            "StockID": "300041",
            "Tag": [
                {
                    "ID": "2958",
                    "Name": "合作商",
                    "Reason": "公司目前主要在芯片组装及封测部分进行产品开发和市场拓展；其中芯片封测是以海思合作为契机，尚处于小批量应用阶段"
                }
            ],
            "prod_name": "回天新材",
            "HotNum": 969
        }
    ],
    "IsNew": 0,
    "ZT": {
        "603118": [
            "1",
            "10.00",
            "1776409492"
        ]
    },
    "Power": 1,
    "Subscribe": 0,
    "IsGood": 0,
    "ComNum": 1395,
    "GoodNum": 1256,
    "errcode": "0",
    "t": 0.01566400000000001
}

```


### 市场情绪

```
GET

URL https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=ChangeStatistics&apiv=w44&c=HisHomeDingPan&st=1000

**可不传参数: Token，UserID, DeviceID**

{
	"info": [{
		"strong": "56", #情绪指标强度,
		"ztjs": "69",   #涨停家数
		"lbgd": "7",    #连板高度
		"Day": "2026-04-17", #日期
		"df_num": "3"  # 大幅回撤
	}, {
		"strong": "68",
		"ztjs": "79",
		"lbgd": "6",
		"Day": "2026-04-16",
		"df_num": "2"
	}, {
		"strong": "46",
		"ztjs": "57",
		"lbgd": "5",
		"Day": "2026-04-15",
		"df_num": "7"
	}],
	"tip": 温馨提示：情绪指标过高（75），短期有释放亏钱效应的风险；情绪指标过低（25），短线有反弹回暖需求；提示仅供参考,
	"ttag": 0.013094999999999996,
	"errcode": "0"
}
```

### 市场量能
```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=0&UserID=3807176&VerSion=5.23.0.1&a=MarketCapacity&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": {
		"last": "234167807",  #最新量单位:万
		"s_zrcs": "241523238", #昨日量单位:万
		"s_zrtj": "241523238",
		"s3_zrtj": "231643107", #三日量单位:万
		"yclnstr": "23417亿(-3.05%,缩量736亿)",
		"color": 2,
		"time": 1776519147,
        "date": "2026-04-16"
	},
	"ttag": 0.008885000000000032,
	"errcode": "0"
}

```

### 涨停表现
```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=ZhangTingExpression&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
"info": [71, 5, 1, 2, 10.8696, 12.5, 66.6667, 21.7822, 1.996, 3.034, 1.205, "\u9898\u6750\u5b58\u5728\u7092\u4f5c\u673a\u4f1a"],
"ttag": 0.0006789999999999852,
"errcode": "0"
}

info数组字段说明:
[0]	Integer	71 #涨停家数
[1]	Integer	5 #2连板家数
[2]	Integer	1 #3连板家数
[3]	Integer	2 #最高板数
[4]	Number	10.8696 #2板晋级率
[5]	Number	12.5 #3板晋级率
[6]	Number	66.6667 #最高板晋级率
[7]	Number	21.7822 #今日涨停破板率
[8]	Number	1.996  #昨日涨停表现
[9]	Number	3.034 #昨日连板表现
[10] Number	1.205 # 昨日破板表现
[11] String	题材存在炒作机会 #总结

```

### 指数数据

```
POST
URL	https://apphis.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetZsReal&apiv=w44&c=StockL2History

**可不传参数: Token，UserID, DeviceID**

{
	"StockList": [{
		"increase_rate": "0.70%", #涨幅
		"prod_name": "上证指数", #指数名称
		"increase_amount": "28.34", #涨幅点数
		"last_px": "4055.55", #最新点数
		"turnover": 976565489654, # 成交额
		"StockID": "SH000001" # 指数代码
	}, {
		"increase_rate": "2.05%",
		"prod_name": "深证成指",
		"increase_amount": "297.88",
		"last_px": "14796.30",
		"turnover": 1365112582861,
		"StockID": "SZ399001"
	}, {
		"increase_rate": "3.17%",
		"prod_name": "创业板指",
		"increase_amount": "111.31",
		"last_px": "3626.27",
		"turnover": 662253182539,
		"StockID": "SZ399006"
	}, {
		"increase_rate": "1.13%",
		"prod_name": "科创50",
		"increase_amount": "15.91",
		"last_px": "1422.23",
		"turnover": 86332967075,
		"StockID": "SH000688"
	}],
	"ttag": 0.0006849999999999357,
	"errcode": "0"
}

```

### 大幅回撤

```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=SharpWithdrawal&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": [
		["301529", "福赛科技", 0.42, -16.2787, 115.82],
		["300051", "琏升科技", 0.69, -10.2222, 16.16]
	],
	"num": 2,
	"date": "2026-04-16",
	"ttag": 0.00638099999999997,
	"errcode": "0"
}

info数组字段说明:

[0]	String	301529 #股票代码
[1]	String	福赛科技 #股票名称
[2]	Number	0.42 #涨幅
[3]	Number	-16.2787 #回撤幅度
[4]	Number	115.82 # 价格

```

### 权重表现

```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=WeightPerformance&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": {
		"SZ": [
			["881162", "通信服务", 3.8, "301382", "蜂助手", 15.69],
			["881113", "有色冶炼加工", 3.149, "600961", "株冶集团", 10.03],
			["881163", "计算机应用", 2.7599, "688227", "品高股份", 20]
		],
		"XD": [
			["881107", "油气开采及服务", -0.399, "603393", "新天然气", 2.72],
			["881155", "\u94f6\u884c", -0.3449, "601665", "\u9f50\u9c81\u94f6\u884c", 1.16],
			["881140", "\u5316\u5b66\u5236\u836f", -0.061, "002940", "\u6602\u5229\u5eb7", 10.01]
		]
	},
	"ttag": 0.006769000000000025,
	"errcode": "0"
}

info数组字段说明:
SZ: 上涨

[0]	String	881162 #板块代码
[1]	String	通信服务 #板块名称
[2]	Number	3.8 #涨幅
[3]	String	301382 #最热股票代码
[4]	String	蜂助手 # 最热股票名称
[5]	Number	15.69 # 最热股票涨幅

XD: 下跌
[0]	String	881107 #板块代码
[1]	String	油气开采及服务  #板块名称
[2]	Number	-0.399 #跌幅
[3]	String	603393 #最热股票代码
[4]	String	新天然气 # 最热股票名称
[5]	Number	2.72 # 最热股票涨幅

```

### 涨跌停数

```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetZDTCount&apiv=w44&c=FuPanLa

**可不传参数: Token，UserID, DeviceID**

{
	"ZT": "79", #涨停数
	"DT": "1", #跌停数
	"ttag": 0.006491999999999998,
	"errcode": "0"
}
```



### 盘面亮点
```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetPMSL_PMLD&apiv=w44&c=FuPanLa&st=20

**可不传参数: Token，UserID, DeviceID**

{
	"List": [{
		"StockList": [
			["002726", "\u9f99\u5927\u7f8e\u98df"]
		],
		"TimeMin": 1776302700,
		"TagID": 13,
		"ZSCode": "801464",
		"ZSName": "\u519c\u4e1a",
		"TagShuXing": 2,
		"TagName": "T\u5b57\u677f",
		"Detail": "\u519c\u4e1a\u9f99\u5927\u7f8e\u98dfT\u5b57\u677f\u9996\u677f\u6da8\u505c"
	}, {
		"StockList": [
			["603629", "\u5229\u901a\u7535\u5b50"]
		],
		"TimeMin": 1776308580,
		"TagID": 24,
		"ZSCode": "801807",
		"ZSName": "\u7b97\u529b",
		"TagShuXing": 2,
		"TagName": "\u8d8b\u52bf\u65b0\u9ad8",
		"Detail": "\u7b97\u529b\u5229\u901a\u7535\u5b50\u76d8\u4e2d\u89e6\u53ca\u6da8\u505c"
	}],
	"date": "2026-04-16",
	"Time": 1776524062,
	"ttag": 0.007132000000000027,
	"errcode": "0"
}

# List数组字段说明:

List	Array
[0]	Object
StockList	Array # 股票列表
[0]	Array
[0]	String	002726 # 股票代码
[1]	String	龙大美食 # 股票名称
TimeMin	Integer	1776302700 # 时间戳
TagID	Integer	13 # 标签ID
ZSCode	String	801464 # 板块代码
ZSName	String	农业 # 板块名称
TagShuXing	Integer	2 # 标签属性
TagName	String	T字板 # 标签名称
Detail	String	农业龙大美食T字板首板涨停 # 说明

```

### 大幅回撤

```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetPMSL_KQXY&apiv=w44&c=FuPanLa&st=20

**可不传参数: Token，UserID, DeviceID**

{
	"date": "2026-04-17",
	"Time": 1776522520,
	"List": [
		["301666", "C\u5927\u666e\u5fae", "-5.34%", -12.97, "", 1, "\u5b58\u50a8\u3001\u6b21\u65b0\u80a1"],
		["688148", "\u82b3\u6e90\u80a1\u4efd", "-0.95%", -13.52, "", 1, "\u56fa\u6001\u7535\u6c60\u3001\u6c7d\u8f66\u96f6\u90e8\u4ef6"],
		["688485", "\u4e5d\u5dde\u4e00\u8f68", "0.42%", -12.26, "", 1, "\u82af\u7247\u3001\u5e76\u8d2d\u91cd\u7ec4"]
	],
	"ttag": 0.0012600000000000389,
	"errcode": "0"
}

# List数组字段说明:
List	Array
[0]	Array

[0]	String	301666 # 股票代码
[1]	String	C大普微 # 股票名称
[2]	String	-5.34% # 涨幅
[3]	Number	-12.97 # 回撤幅度
[4]	String
[5]	Integer	1
[6]	String	存储、次新股 # 板块名称

```

### 涨停信息

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetZhangTingTianTi&apiv=w44&c=FuPanLa

**可不传参数: Token，UserID, DeviceID**

{
	"StockList": [
		["002580", "\u5723\u9633\u80a1\u4efd", 6, 1776303444, "801807", "\u7b97\u529b", 0, 1, 20, 9663901824, 36273385216],
		["002297", "\u535a\u4e91\u65b0\u6750", 4, 1776302700, "801571", "\u4e00\u5b63\u62a5\u589e\u957f", 0, 1, 5, 7134659834, 5557268840],
		["002990", "\u76db\u89c6\u79d1\u6280", 3, 1776303879, "801807", "\u7b97\u529b", 0, 1, 20, 3984836476, 36273385216],
		["002468", "\u7533\u901a\u5feb\u9012", 2, 1776303234, "801571", "\u4e00\u5b63\u62a5\u589e\u957f", 0, 1, 5, 10652870916, 5557268840],
		["603687", "\u5927\u80dc\u8fbe", 2, 1776303116, "801250", "\u5e76\u8d2d\u91cd\u7ec4", 0, 1, 3, 5504331672, 4191526367],
		["002033", "\u4e3d\u6c5f\u80a1\u4efd", 2, 1776316146, "801330", "\u65c5\u6e38", 0, 1, 2, 3289386725, 1852110670],
		["600683", "\u4eac\u6295\u53d1\u5c55", 2, 1776303065, "801676", "\u5730\u4ea7\u94fe", 0, 0, 1, 3570533201, 261611125]
	],
	"ZhuShuList": [
		["801807", "\u7b97\u529b", 20, 36273385216, "000815,000967,002008,002421,002580,002757,002771,002929,002990,300798,301396,600156,600284,600666,601778,603220,603322,603985,688227,688668"],
		["801004", "\u9502\u7535\u6c60", 9, 10101847565, "000546,000762,001203,002213,002263,002850,002859,301148,603032"],
		["801571", "\u4e00\u5b63\u62a5\u589e\u957f", 5, 5557268840, "000570,002297,002468,600768,603906"],
		["801159", "\u673a\u5668\u4eba\u6982\u5ff5", 5, 2814763774, "002062,002209,301603,603897,603920"]
	],
	"Date": "2026-04-16",
	"ttag": 0.12112299999999998,
	"errcode": "0"
}

# StockList数组字段说明:
StockList	Array
[0]	Array
[0]	String	002580 # 股票代码
[1]	String	圣阳股份 # 股票名称
[2]	Integer	6 # 连板数
[3]	Integer	1776303444 # 涨停时间
[4]	String	801807 # 板块代码
[5]	String	算力 # 板块名称
[6]	Integer	0 #
[7]	Integer	1
[8]	Integer	20 # 板块涨停数
[9]	Long	9663901824
[10]	Long	36273385216 # 板块成交额


# 所属板块信息

ZhuShuList	Array
[0]	Array
[0]	String	801807 # 板块代码
[1]	String	算力 # 板块名称
[2]	Integer	20 # 板块涨停数
[3]	Long	36273385216 # 板块成交额: 元
[4]	String	000815,000967,002008,002421,002580,002757,002771,002929,002990,300798,301396,600156,600284,600666,601778,603220,603322,603985,688227,688668 # 板块内涨停股票代码

```

### 龙虎榜动向

```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetYTFP_LHBDX&apiv=w44&c=FuPanLa

**可不传参数: Token，UserID, DeviceID**

{
	"List": [{
		"BName": "\u7ae0\u76df\u4e3b",
		"BID": 41,
		"Buy": [{
			"Sto": "000967",
			"StoN": "\u76c8\u5cf0\u73af\u5883",
			"Money": 114520000,
			"Three": 1
		}],
		"Sell": [{
			"Sto": "000967",
			"StoN": "\u76c8\u5cf0\u73af\u5883",
			"Money": -30756200,
			"Three": 1
		}]
	}, {
		"BName": "\u65b9\u65b0\u4fa0",
		"BID": 54,
		"Buy": [{
			"Sto": "300088",
			"StoN": "\u957f\u4fe1\u79d1\u6280",
			"Money": 195483000,
			"Three": 0
		}],
		"Sell": []
	}, {
		"BName": "\u5f90\u6653",
		"BID": 67,
		"Buy": [{
			"Sto": "301396",
			"StoN": "\u5b8f\u666f\u79d1\u6280",
			"Money": 94744500,
			"Three": 0
		}],
		"Sell": []
	}, {
		"BName": "\u4e0a\u5858\u8def",
		"BID": 64,
		"Sell": [{
			"Sto": "002124",
			"StoN": "\u5929\u90a6\u98df\u54c1",
			"Money": -20701400,
			"Three": 0
		}],
		"Buy": []
	}, {
		"BName": "\u91d1\u5f00\u5927\u9053",
		"BID": 9,
		"Buy": [{
			"Sto": "301666",
			"StoN": "N\u5927\u666e\u5fae",
			"Money": 355048000,
			"Three": 0
		}],
		"Sell": []
	}],
	"Date": "2026-04-16",
	"Time": 1776524067,
	"ttag": 0.0072409999999999974,
	"errcode": "0"
}

# List数据结构说明:

[1]	Object
BName	String	章盟主 # 名称
BID	Integer	41 # ID
Buy	Array	 # 买入
[0]	Object
Sto	String	000967 # 股票代码
StoN	String	盈峰环境 # 股票名称
Money	Integer	114520000 # 金额：万
Three	Integer	1 # 是否是3日榜
Sell	Array  # 卖出
[0]	Object
Sto	String	000967 # 股票代码
StoN	String	盈峰环境 # 股票名称
Money	Integer	-30756200 # 金额：万
Three	Integer	1 # 是否是3日榜
```

### 涨停原因

```

POST

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetPlateInfo_w38&apiv=w44&c=HisLimitResumption&st=20

**可不传参数: Token，UserID, DeviceID**

{
	"nums": {
		"SZJS": 4065,
		"XDJS": 1003,
		"ZT": 79,
		"DT": 1,
		"ZBL": 21.7822,
		"yestRase": 1.996
	},
	"list": [{
		"ZSCode": "801070",
		"ZSName": "\u5149\u4f0f",
		"TCExplain": "",
		"GroupStr": "",
		"StockList": [
			["002333", "\u7f57\u666e\u65af\u91d1", 0, "", 0, 0, 1776319068, 0, 9528065, "\u9996\u677f", 1, "\u5206\u5e03\u5f0f\u5149\u4f0f\u3001\u57fa\u7840\u5efa\u8bbe", 110355427, 377858516, 28.91, 1357767755, "\u5206\u5e03\u5f0f\u5149\u4f0f", "\u5206\u5e03\u5f0f\u5149\u4f0f+\u91d1\u5c5e\u94dd\uff1b1. \u5206\u5e03\u5f0f\u5149\u4f0f\uff1a\u516c\u53f8\u751f\u4ea7\u7684\u94dd\u578b\u6750\u53ef\u5e94\u7528\u4e8e\u5149\u4f0f\u7ec4\u4ef6\u8fb9\u6846\u548c\u652f\u67b6\r\n\r\n2. \u91d1\u5c5e\u94dd\uff1a\u516c\u53f8\u4e3b\u8981\u4e1a\u52a1\u4e3a\u65b0\u578b\u94dd\u5408\u91d1\u94f8\u68d2\u6750\u6599\u3001\u94dd\u5408\u91d1\u578b\u6750\u3001\u94dd\u5408\u91d1\u7cfb\u7edf\u95e8\u7a97\u7684\u7814\u53d1\u3001\u8bbe\u8ba1\u3001\u751f\u4ea7\u548c\u9500\u552e\uff1b\u56f4\u7ed5\u667a\u6167\u57ce\u5e02\u5f00\u5c55\u7684\u5efa\u7b51\u667a\u80fd\u5316\u65bd\u5de5\u7b49\u76f8\u5173\u4e1a\u52a1\u3002", 0],
			["002613", "\u5317\u73bb\u80a1\u4efd", 0, "", 0, 0, 1776305232, 0, 85205896, "\u9996\u677f", 1, "\u5149\u4f0f\u73bb\u7483\u3001\u6d88\u8d39\u7535\u5b50", 117809925, 336346232, 14.05, 2446791357, "\u5149\u4f0f\u73bb\u7483", "\u5149\u4f0f(\u5149\u4f0f\u73bb\u7483)\uff1b\u516c\u53f8\u751f\u4ea7\u7684\u8fde\u7eed\u94a2\u5316\u8bbe\u5907\u4e3b\u8981\u7528\u4e8e\u5149\u4f0f\u4ea7\u54c1\u9762\u677f\u73bb\u7483\u7684\u751f\u4ea7\u3002", 0]
		],
		"num": 2
	}],
	"date": "2026-04-16",
	"ttag": 0.08092100000000002,
	"errcode": "0"
}

# 字段说明

nums	Object  # 涨停信息
SZJS	Integer	4065 # 上涨家数
XDJS	Integer	1003 # 下跌家数
ZT	Integer	79 # 涨停家数
DT	Integer	1 # 跌停家数
ZBL	Number	21.7822 # 破板率 百分比
yestRase	Number	1.996 # 昨日涨停表现 百分比
list	Array
[0]	Object
ZSCode	String	801807 # 板块代码
ZSName	String	算力 # 板块名称
TCExplain	String
GroupStr	String
StockList	Array  # 涨停股票列表
[0]	Array
[0]	String	000815 # 股票代码
[1]	String	美利云 # 股票名称
[2]	Integer	0
[3]	String
[4]	Integer	0
[5]	Integer	0
[6]	Integer	1776303306 # 涨停时间
[7]	Integer	0
[8]	Integer	302714336
[9]	String	首板 # 连板状态
[10]	Integer	1  # 几板
[11]	String	算力、消费电子 # 概念
[12]	Integer	743354457
[13]	Integer	1689222895 # 成交额
[14]	Number	16.67
[15]	Long	10319749598
[16]	String	算力  # 涨停原因
[17]	String	算力；2026年3月4日投资者关系活动记录表，公司在稳定原有业务基础上，积极扩大业务规模。目前，E1、E3、C1已交付客户使用，IT功率约50MW；B1、B3和C3已完成土建、正在积极进行客户储备，110电站项目稳步建设中。公司目前已合作的重点客户有电信、美团、北龙超算、并行等。  # 涨停详细信息
[18]	Integer	0


```

### 板块涨停历史数据

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&ZSCode=801807&a=GetDatePlate&apiv=w44&c=HisLimitResumption&st=3

**可不传参数: Token，UserID, DeviceID**

{
	"list": [{
		"ZSName": "\u7b97\u529b",
		"TCExplain": "",
		"Date": "2026-04-17",
		"StockList": [
			["001400", "\u6c5f\u987a\u79d1\u6280", 0, "", 0, 0, 1776405516, 0, 57129812, "\u9996\u677f", 1, "\u6db2\u51b7\u3001\u7b97\u529b", 57735427, 505325943, 18.14, 2904000000, "\u6db2\u51b7", "\u6db2\u51b7+\u5546\u4e1a\u822a\u5929\uff1b1. \u6db2\u51b7\uff1a2026\u5e741\u67087\u65e5\u300a\u79d1\u521b\u677f\u65e5\u62a5\u300b\u8baf\uff0c\u77e5\u540d\u5206\u6790\u5e08\u90ed\u660e\u9324\u53d1\u6587\u79f0\uff0c\u82f1\u4f1f\u8fbeVR200 NVL72\u5c06\u5747\u91c7\u7528\u5fae\u901a\u9053\u51b7\u677f\uff0c\u5176\u51b7\u5374\u6db2\u6d41\u91cf\u6216\u589e\u52a0100%\u3002\u636e2025\u5e74\u534a\u5e74\u62a5\uff0c\u5728\u94dd\u578b\u6750\u6324\u538b\u6a21\u5177\u65b9\u9762\uff0c\u6c5f\u987a\u79d1\u6280\u4ea7\u54c1\u8986\u76d6\u4e86\u4ece\u76f4\u5f8450mm\u7684\u5fae\u901a\u9053\u6a21\u5177\u81f31,200mm\u7684\u5927\u89c4\u683c\u6a21\u5177\uff0c\u4ea7\u54c1\u54c1\u7c7b\u4e30\u5bcc\u30022025\u5e749\u670824\u65e5\u4e92\u52a8\u6613\uff1a\u6c5f\u5b87\u79d1\u6280\u4e3a\u516c\u53f855%\u63a7\u80a1\u7684\u5b50\u516c\u53f8\uff0c\u6210\u7acb\u4e8e25\u5e749\u670819\u65e5\uff0c\u76ee\u524d\u4e3b\u8981\u4ece\u4e8b\u7528\u4e8e\u670d\u52a1\u5668\u6db2\u51b7\u76f8\u5173\u76843D\u6253\u5370\u4ea7\u54c1\u7684\u7814\u53d1\u5de5\u4f5c\uff0c\u76ee\u524d\u5df2\u6709\u90e8\u5206\u6837\u54c1\u3002\r\n\r\n2. \u5546\u4e1a\u822a\u5929\uff1a2026\u5e741\u670813\u65e5\u4f01\u67e5\u67e5APP\u663e\u793a\uff0c\u8fd1\u65e5\uff0c\u4e5d\u5b87\u5efa\u6728\u7a7a\u5929\u79d1\u6280(\u4e0a\u6d77)\u6709\u9650\u516c\u53f8\u53d1\u751f\u5de5\u5546\u53d8\u66f4\uff0c\u65b0\u589e\u6c5f\u9634\u4e00\u5408\u4e59\u5df3\u521b\u4e1a\u6295\u8d44\u5408\u4f19\u4f01\u4e1a(\u6709\u9650\u5408\u4f19)\u7b49\u4e3a\u80a1\u4e1c\uff0c\u540e\u8005\u7531\u4e5d\u9f0e\u65b0\u6750\u53ca\u6c5f\u987a\u79d1\u6280\u7b49\u5171\u540c\u6301\u80a1\u3002\u4f01\u67e5\u67e5\u4fe1\u606f\u663e\u793a\uff0c\u8be5\u516c\u53f8\u6210\u7acb\u4e8e2022\u5e74\uff0c\u7ecf\u8425\u8303\u56f4\u5305\u542b\uff1a3d\u6253\u5370\u670d\u52a1\uff1b\u589e\u6750\u5236\u9020\u88c5\u5907\u9500\u552e\uff1b3d\u6253\u5370\u57fa\u7840\u6750\u6599\u9500\u552e\u7b49\u3002\u636e\u65e0\u9521\u9ad8\u65b0\u533a\uff0c\u4e5d\u5b87\u5efa\u6728\u603b\u90e8\u57fa\u5730\u5df2\u843d\u6237\u65e0\u9521\uff0c\u5df2\u670d\u52a1\u591a\u5bb6\u56fd\u5185\u5546\u4e1a\u822a\u5929\u5934\u90e8\u4f01\u4e1a\uff0c\u9879\u76ee\u5c06\u6253\u9020\u96c6DED\u91d1\u5c5e3d\u6253\u5370\u6280\u672f\u5f00\u53d1\u3001\u65b0\u6750\u6599\u3001\u53ca\u96f6\u90e8\u4ef6\u5236\u9020\u7b49\u4e3a\u4e00\u4f53\u7684\u5546\u4e1a\u822a\u5929\u603b\u90e8\u57fa\u5730\u3002", 0]
		],
		"num": 10
	}, {
		"ZSName": "\u7b97\u529b",
		"TCExplain": "",
		"Date": "2026-04-16",
		"StockList": [
			["000815", "\u7f8e\u5229\u4e91", 0, "", 0, 0, 1776303306, 0, 302714336, "\u9996\u677f", 1, "\u7b97\u529b\u3001\u6d88\u8d39\u7535\u5b50", 743354457, 1689222895, 16.67, 10319749598, "\u7b97\u529b", "\u7b97\u529b\uff1b2026\u5e743\u67084\u65e5\u6295\u8d44\u8005\u5173\u7cfb\u6d3b\u52a8\u8bb0\u5f55\u8868\uff0c\u516c\u53f8\u5728\u7a33\u5b9a\u539f\u6709\u4e1a\u52a1\u57fa\u7840\u4e0a\uff0c\u79ef\u6781\u6269\u5927\u4e1a\u52a1\u89c4\u6a21\u3002\u76ee\u524d\uff0cE1\u3001E3\u3001C1\u5df2\u4ea4\u4ed8\u5ba2\u6237\u4f7f\u7528\uff0cIT\u529f\u7387\u7ea650MW\uff1bB1\u3001B3\u548cC3\u5df2\u5b8c\u6210\u571f\u5efa\u3001\u6b63\u5728\u79ef\u6781\u8fdb\u884c\u5ba2\u6237\u50a8\u5907\uff0c110\u7535\u7ad9\u9879\u76ee\u7a33\u6b65\u5efa\u8bbe\u4e2d\u3002\u516c\u53f8\u76ee\u524d\u5df2\u5408\u4f5c\u7684\u91cd\u70b9\u5ba2\u6237\u6709\u7535\u4fe1\u3001\u7f8e\u56e2\u3001\u5317\u9f99\u8d85\u7b97\u3001\u5e76\u884c\u7b49\u3002", 0],
			["688668", "\u9f0e\u901a\u79d1\u6280", 0, "", 0, 0, 1776307720, 0, 133526784, "\u9996\u677f", 1, "\u6db2\u51b7\u3001\u7b97\u529b", 142780410, 2588415607, 17.72, 15403141147, "\u6db2\u51b7", "\u6db2\u51b7+\u4e00\u5b63\u62a5\u589e\u957f\uff1b1. \u6db2\u51b7\uff1a2026\u5e743\u670831\u65e5\u4e92\u52a8\u6613\uff1a\u516c\u53f8\u76ee\u524dI\/O\u8fde\u63a5\u5668112G\u4ea7\u54c1\uff0c\u4e3b\u8981\u914d\u5907\u98ce\u51b7\u6563\u70ed\u5668\uff0c224G\u4ea7\u54c1\u98ce\u51b7\u6563\u70ed\u5668\u548c\u6db2\u51b7\u6563\u70ed\u5668\u4e3b\u8981\u6839\u636e\u5ba2\u6237\u8ba2\u5355\u9700\u6c42\u914d\u5907\u3002\r\n\r\n2. \u4e00\u5b63\u62a5\u589e\u957f\uff1a4\u670815\u65e5\u665a\u516c\u544a\uff0c2026\u5e741-3\u6708\u5f52\u5c5e\u4e0a\u5e02\u516c\u53f8\u80a1\u4e1c\u7684\u51c0\u5229\u6da6\uff1a8032.74\u4e07\u5143\uff0c\u540c\u6bd4\u4e0a\u5e74\u589e\u957f\uff1a51.86%", 0]
		],
		"num": 20
	}],
	"ZSCode": "801807",
	"ZSName": "\u7b97\u529b",
	"ttag": 0.965114,
	"errcode": "0"
}

# 说明

list	Array
[0]	Object
ZSName	String	算力 # 板块名称
TCExplain	String
Date	String	2026-04-17 # 日期
num	Integer	10  # 涨停数量
StockList	Array	#  涨停股票列表
[0]	Array
[0]	String	001400 # 股票代码
[1]	String	江顺科技 # 股票名称
[2]	Integer	0
[3]	String
[4]	Integer	0
[5]	Integer	0
[6]	Integer	1776405516 # 涨停时间
[7]	Integer	0
[8]	Integer	57129812
[9]	String	首板  # 连板状态
[10]	Integer	1 # 几板
[11]	String	液冷、算力  # 概念
[12]	Integer	57735427
[13]	Integer	505325943 # 成交额
[14]	Number	18.14
[15]	Long	2904000000
[16]	String	液冷   # 涨停原因
[17]	String	液冷+商业航天；1. 液冷：2026年1月7日《科创板日报》讯，知名分析师郭明錤发文称，英伟达VR200 NVL72将均采用微通道冷板，其冷却液流量或增加100%。据2025年半年报，在铝型材挤压模具方面，江顺科技产品覆盖了从直径50mm的微通道模具至1,200mm的大规格模具，产品品类丰富。2025年9月24日互动易：江宇科技为公司55%控股的子公司，成立于25年9月19日，目前主要从事用于服务器液冷相关的3D打印产品的研发工作，目前已有部分样品。

2. 商业航天：2026年1月13日企查查APP显示，近日，九宇建木空天科技(上海)有限公司发生工商变更，新增江阴一合乙巳创业投资合伙企业(有限合伙)等为股东，后者由九鼎新材及江顺科技等共同持股。企查查信息显示，该公司成立于2022年，经营范围包含：3d打印服务；增材制造装备销售；3d打印基础材料销售等。据无锡高新区，九宇建木总部基地已落户无锡，已服务多家国内商业航天头部企业，项目将打造集DED金属3d打印技术开发、新材料、及零部件制造等为一体的商业航天总部基地。  # 涨停详细信息
[18]	Integer	0


```

### 法定节假日

```
POST

URL https://apphis.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetHoliday&apiv=w44&c=YiDongKanPan

**可不传参数: Token，UserID, DeviceID**

{
	"List": [ "2025-10-03", "2025-06-02", "2025-05-05", "2025-05-01", "2025-05-02", "2025-04-04", "2025-02-03", "2025-01-29", "2025-01-30", "2025-01-31", "2025-01-28", "2025-01-01", "2025-02-04", "2026-01-01", "2026-01-02", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-23", "2026-04-06", "2026-05-01", "2026-05-04", "2026-05-05", "2026-06-19", "2026-09-25", "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"],
	"ttag": 0.00031299999999999384,
	"errcode": "0"
}


```

### 大盘直播

```
POST


URL https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-15&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=ZhiBoContent&apiv=w44&c=HisConceptionPoint

**可不传参数: Token，UserID, DeviceID**


{
	"JHJJYD": ["", "", 0],
	"List": [{
		"ID": "88877",
		"UID": "182",
		"Time": 1776236400,
		"Comment": "\u4e09\u5927\u6307\u6570\u5168\u5929\u9707\u8361\u8d70\u5f31\uff0c\u521b\u4e1a\u677f\u6307\u6570\u8dcc\u8d85-1%\uff0c\u6536\u76d8\u4e24\u5e02\u603b\u6210\u4ea4\u8d852.4\u4e07\u4ebf\uff0c\u76f8\u8f83\u524d\u4e00\u4ea4\u6613\u65e5\u63a5\u8fd1\u6301\u5e73\uff0c\u4e0b\u8dcc\u4e2a\u80a1\u8d853000\u5bb6\u3002\u5e02\u573a\u5168\u5929\u5f31\u52bf\u8f6e\u52a8\uff0c\u533b\u836f\u677f\u5757\u76f8\u5bf9\u5f3a\u52bf\uff0c\u54c8\u836f\u80a1\u4efd\u4e8c\u8fde\u677f\uff0c\u745e\u5eb7\u533b\u836f\u3001\u9e6d\u71d5\u533b\u836f\u7b49\u591a\u80a1\u9996\u677f\uff0c\u7f8e\u8bfa\u534e\u521b\u8d8b\u52bf\u65b0\u9ad8\u3002\u7b97\u529b\u6982\u5ff5\u5723\u9633\u80a1\u4efd\u4e94\u8fde\u677f\uff0c\u4e2d\u5609\u535a\u521b\u516d\u5929\u4e94\u677f\uff0c\u5965\u5c3c\u7535\u5b5020cm\u4e8c\u8fde\u677f\u3002\u6b64\u5916\u5546\u4e1a\u822a\u5929\u822a\u5929\u5de5\u7a0b\u4e8c\u8fde\u677f\uff0c\u795e\u5251\u80a1\u4efd\u6da8\u505c\u521b\u8d8b\u52bf\u65b0\u9ad8\u3002\u53e6\u6709\u57fa\u7840\u5efa\u8bbe\u3001\u667a\u80fd\u7535\u7f51\u3001\u82af\u7247\uff08\u56fd\u4ea7\u7b97\u529b\uff09\u7b49\u5feb\u901f\u8f6e\u52a8\u3002AI\u786c\u4ef6\u5206\u5316\u8d70\u5f31\uff0c\u534e\u76db\u660c\u53cd\u590d\u5f00\u677f\uff0c\u5b8f\u548c\u79d1\u6280\u3001\u5251\u6865\u79d1\u6280\u70b8\u677f\uff0c\u6743\u91cd\u4e2d\u9645\u65ed\u521b\u7b49\u591a\u80a1\u9707\u8361\u56de\u843d\u3002\u77ed\u7ebf\u60c5\u7eea\u5206\u5316\uff0c\u9ad8\u4f4d\u80a1\u5723\u9633\u80a1\u4efd\u4e94\u8fde\u677f\uff0c\u957f\u6e90\u4e1c\u8c37\u3001\u4e2d\u5609\u535a\u521b\u516d\u5929\u4e94\u677f\uff0c\u4f46\u6709\u534e\u8fdc\u63a7\u80a1\u5929\u5730\u677f\u3002\uff08\u8be5\u5185\u5bb9\u7531AI\u5927\u6a21\u578b\u6839\u636e\u884c\u60c5\u81ea\u52a8\u751f\u6210\uff09",
		"Type": "0",
		"PlateCode": "",
		"PlateName": "",
		"PlateJE": "",
		"PlateZDF": "",
		"Interpretation": "",
		"IsChart": "0",
		"ThemeInfo": [],
		"ShareData": {
			"ZDTJ": "1",
			"ZDTJ_info": {
				"0": "99",
				"1": "730",
				"2": "395",
				"3": "211",
				"4": "113",
				"5": "49",
				"6": "56",
				"7": "26",
				"8": "21",
				"9": "12",
				"10": "21",
				"-1": "1209",
				"-2": "1240",
				"-3": "520",
				"-4": "214",
				"-5": "100",
				"-6": "45",
				"-7": "21",
				"-8": "9",
				"-9": "9",
				"-10": "5",
				"DT": "14",
				"ZT": "68",
				"SJDT": "8",
				"SJZT": "57",
				"SZJS": "1702",
				"XDJS": "3386"
			},
			"LNT": "0",
			"LNT_info": 1776236400
		},
		"UserName": "Livermore",
		"Image": "https:\/\/appresi.longhuvip.com\/uploadImg\/adv\/ArticleImage\/1727336533_456.png",
		"Stock": [
			["600664", "\u54c8\u836f\u80a1\u4efd", 9.9],
			["002589", "\u745e\u5eb7\u533b\u836f", 10.12],
			["603538", "\u7f8e\u8bfa\u534e  ", 8.91],
			["002580", "\u5723\u9633\u80a1\u4efd", 10.01],
			["000889", "\u4e2d\u5609\u535a\u521b", 9.98],
			["301189", "\u5965\u5c3c\u7535\u5b50", 20],
			["603698", "\u822a\u5929\u5de5\u7a0b", 9.99],
			["002361", "\u795e\u5251\u80a1\u4efd", 10.03],
			["002980", "\u534e\u76db\u660c", 9.98],
			["603256", "\u5b8f\u548c\u79d1\u6280", 4.15],
			["603083", "\u5251\u6865\u79d1\u6280", 4.29],
			["300308", "\u4e2d\u9645\u65ed\u521b", 0.9],
			["603950", "\u957f\u6e90\u4e1c\u8c37", 10],
			["600743", "\u534e\u8fdc\u63a7\u80a1", -9.97]
		],
		"DisStock": [
			["600664", "\u54c8\u836f\u80a1\u4efd"],
			["002589", "\u745e\u5eb7\u533b\u836f"],
			["002788", "\u9e6d\u71d5\u533b\u836f"],
			["603538", "\u7f8e\u8bfa\u534e"],
			["002580", "\u5723\u9633\u80a1\u4efd"],
			["000889", "\u4e2d\u5609\u535a\u521b"],
			["301189", "\u5965\u5c3c\u7535\u5b50"],
			["603698", "\u822a\u5929\u5de5\u7a0b"],
			["002361", "\u795e\u5251\u80a1\u4efd"],
			["002980", "\u534e\u76db\u660c"],
			["603256", "\u5b8f\u548c\u79d1\u6280"],
			["603083", "\u5251\u6865\u79d1\u6280"],
			["300308", "\u4e2d\u9645\u65ed\u521b"],
			["603950", "\u957f\u6e90\u4e1c\u8c37"],
			["600743", "\u534e\u8fdc\u63a7\u80a1"]
		],
		"ThemeClassInfo": [],
		"styleIndex": [],
		"BoomReason": ""
	}, {
		"ID": "88866",
		"UID": "204",
		"Time": 1776216300,
		"Comment": "\u5e76\u8d2d\u91cd\u7ec4\u5927\u80dc\u8fbe\u9996\u677f\u6da8\u505c\uff08\u8be5\u5185\u5bb9\u7531AI\u5927\u6a21\u578b\u6839\u636e\u884c\u60c5\u81ea\u52a8\u751f\u6210\uff09",
		"Type": "0",
		"PlateCode": "",
		"PlateName": "",
		"PlateJE": "",
		"PlateZDF": "",
		"Interpretation": "",
		"IsChart": "0",
		"ThemeInfo": [],
		"ShareData": [],
		"UserName": "xmm",
		"Image": "",
		"Stock": [
			["603687", "\u5927\u80dc\u8fbe  ", 10]
		],
		"DisStock": [
			["603687", "\u5927\u80dc\u8fbe"]
		],
		"ThemeClassInfo": [],
		"styleIndex": [],
		"BoomReason": ""
	}, {
		"ID": "88841",
		"UID": "204",
		"Time": 1776215700,
		"Comment": "\u7ade\u4ef7\u770b\u9f99\u5934\uff1aAI\u786c\u4ef6\u534e\u76db\u660c\u3001\u6caa\u7535\u80a1\u4efd\uff1b\u7b97\u529b\u4e2d\u6052\u7535\u6c14\u3001\u5723\u9633\u80a1\u4efd\u3001\u534f\u521b\u6570\u636e\uff1b\u9502\u7535\u6c60\u7ef4\u79d1\u6280\u672f\u3001\u77f3\u5927\u80dc\u534e\uff1b\u82af\u7247\u6d77\u7279\u9ad8\u65b0\u3001\u5927\u4e3a\u80a1\u4efd\uff1b\u7b97\u7535\u534f\u540c\u534e\u7535\u8fbd\u80fd\uff08\u8be5\u5185\u5bb9\u7531AI\u5927\u6a21\u578b\u6839\u636e\u884c\u60c5\u81ea\u52a8\u751f\u6210\uff09",
		"Type": "0",
		"PlateCode": "",
		"PlateName": "",
		"PlateJE": "",
		"PlateZDF": "",
		"Interpretation": "",
		"IsChart": "0",
		"ThemeInfo": [],
		"ShareData": [],
		"UserName": "xmm",
		"Image": "",
		"Stock": [
			["002980", "\u534e\u76db\u660c", 9.98],
			["002463", "\u6caa\u7535\u80a1\u4efd", -4.88],
			["002364", "\u4e2d\u6052\u7535\u6c14", 2.14],
			["002580", "\u5723\u9633\u80a1\u4efd", 10.01],
			["300857", "\u534f\u521b\u6570\u636e", 12.46],
			["600152", "\u7ef4\u79d1\u6280\u672f", 1.51],
			["603026", "\u77f3\u5927\u80dc\u534e", 0.13],
			["002023", "\u6d77\u7279\u9ad8\u65b0", 3.25],
			["002213", "\u5927\u4e3a\u80a1\u4efd", -8.48],
			["600396", "\u534e\u7535\u8fbd\u80fd", 0.25]
		],
		"DisStock": [
			["002980", "\u534e\u76db\u660c"],
			["002463", "\u6caa\u7535\u80a1\u4efd"],
			["002364", "\u4e2d\u6052\u7535\u6c14"],
			["002580", "\u5723\u9633\u80a1\u4efd"],
			["300857", "\u534f\u521b\u6570\u636e"],
			["600152", "\u7ef4\u79d1\u6280\u672f"],
			["603026", "\u77f3\u5927\u80dc\u534e"],
			["002023", "\u6d77\u7279\u9ad8\u65b0"],
			["002213", "\u5927\u4e3a\u80a1\u4efd"],
			["600396", "\u534e\u7535\u8fbd\u80fd"]
		],
		"ThemeClassInfo": [],
		"styleIndex": [],
		"BoomReason": ""
	}],
	"Notice": "\u76f4\u64ad\u5373\u5c06\u5f00\u59cb\uff01\uff01\uff01",
	"Time": 1776355200,
	"Status": 0,
	"date": "2026-04-17",
	"ttag": 0.0026609999999999134,
	"errcode": "0"
}

# 数据说明
JHJJYD	Array
List	Array	# 详细信息
Notice	String	直播即将开始！！！
Time	Integer	1776355200 # 时间戳
Status	Integer	0
date	String	2026-04-17 # 日期
ttag	Number	0.0026609999999999134
errcode	String	0

# List数据说明

List	Array
[0]	Object
ID	String	88877 # ID
UID	String	182
Time	Integer	1776236400 # 时间戳
Comment	String	三大指数全天震荡走弱，创业板指数跌超-1%，收盘两市总成交超2.4万亿，相较前一交易日接近持平，下跌个股超3000家。市场全天弱势轮动，医药板块相对强势，哈药股份二连板，瑞康医药、鹭燕医药等多股首板，美诺华创趋势新高。算力概念圣阳股份五连板，中嘉博创六天五板，奥尼电子20cm二连板。此外商业航天航天工程二连板，神剑股份涨停创趋势新高。另有基础建设、智能电网、芯片（国产算力）等快速轮动。AI硬件分化走弱，华盛昌反复开板，宏和科技、剑桥科技炸板，权重中际旭创等多股震荡回落。短线情绪分化，高位股圣阳股份五连板，长源东谷、中嘉博创六天五板，但有华远控股天地板。（该内容由AI大模型根据行情自动生成） # 评论
Type	String	0
PlateCode	String
PlateName	String
PlateJE	String
PlateZDF	String
Interpretation	String
IsChart	String	0
ThemeInfo	Array
ShareData	Object	 # 股票数据
ZDTJ	String	1
ZDTJ_info	Object	 # 涨停统计信息
0	String	99       # 涨幅为0的股票数量
1	String	730      # 涨幅为1%的股票数量
2	String	395      # 涨幅为2%的股票数量
3	String	211      # 涨幅为3%的股票数量
4	String	113     # 涨幅为4%的股票数量
5	String	49      # 涨幅为5%的股票数量
6	String	56      # 涨幅为6%的股票数量
7	String	26      # 涨幅为7%的股票数量
8	String	21      # 涨幅为8%的股票数量
9	String	12      # 涨幅为9%的股票数量
10	String	21       # 涨幅>=10%的股票数量
-1	String	1209     # 跌幅为1%的股票数量
-2	String	1240     # 跌幅为2%的股票数量
-3	String	520      # 跌幅为3%的股票数量
-4	String	214     # 跌幅为4%的股票数量
-5	String	100    # 跌幅为5%的股票数量
-6	String	45   # 跌幅为6%的股票数量
-7	String	21  # 跌幅为7%的股票数量
-8	String	9   # 跌幅为8%的股票数量
-9	String	9    # 跌幅为9%的股票数量
-10	String	5       # 跌幅>=10%的股票数量
DT	String	14  # 当日跌停数量
ZT	String	68  # 当日涨停数量
SJDT	String	8 # 实际跌停数量
SJZT	String	57 # 实际涨停数量
SZJS	String	1702 # 上涨股票数量
XDJS	String	3386 # 下跌股票数量
LNT	String	0
LNT_info	Integer	1776236400 # 时间戳
UserName	String	Livermore
Image	String	https://appresi.longhuvip.com/uploadImg/adv/ArticleImage/1727336533_456.png
Stock	Array  # 重点股票列表
[0]	Array
[0]	String	600664 #股票代码
[1]	String	哈药股份 # 股票名称
[2]	Number	9.9 # 涨幅 %
DisStock	Array
ThemeClassInfo	Array
styleIndex	Array
BoomReason	String

```

### 新高趋势

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&GroupID=ALL&Index=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetDayNewHigh_W28&apiv=w44&c=StockNewHigh&st=2000

**可不传参数: Token，UserID, DeviceID**

{
	"x": ["20200102_412_138_0", "20200103_429_84_0"]
	"ttag": 0.002949000000000007,
	"errcode": "0"
}

# x数据说明
[0]	String	20200102_412_138_0 # 日期_总新高数量_当日新高数量_0


```

### 百日新高，按板块

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&IsAll=0&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=0_0_0_0_0&UserID=3807176&VerSion=5.23.0.1&a=GroupStock_W28&apiv=w44&c=StockNewHigh&st=20

**可不传参数: Token，UserID, DeviceID**


{
	"GroupList": [{
		"List": [
			["300866", "\u5b89\u514b\u521b\u65b0", 120.68, 7.89, "\u50a8\u80fd\u3001\u4fbf\u643a\u5f0f\u50a8\u80fd", 1517063039, 72383693, 534340639, -461956946, 25826238239, 64703661000, 1, "801178", "\u50a8\u80fd", 6.02],
			["300693", "\u76db\u5f18\u80a1\u4efd", 50.96, 2.12, "PCS\u8bbe\u5907\u3001\u5de5\u5546\u4e1a\u50a8\u80fd", 1185832723, 107282505, 433660640, -326378135, 13037633846, 15940075140, 1, "801178", "\u50a8\u80fd", 9.09],
			["301186", "\u8d85\u8fbe\u88c5\u5907", 66.8, 1.94, "\u6c7d\u8f66\u96f6\u90e8\u4ef6\u3001\u6d88\u8d39\u7535\u5b50", 282281446, 5566824, 68549396, -62982572, 1915737821, 5380723500, 0, "801178", "\u50a8\u80fd", 14.87],
			["003043", "\u534e\u4e9a\u667a\u80fd", 54.25, -0.51, "\u50a8\u80fd\u3001\u82af\u7247", 190186973, 8526333, 21501011, -12974678, 3191961120, 7260354101, 0, "801178", "\u50a8\u80fd", 5.92]
		],
		"GroupName": "\u50a8\u80fd",
		"GroupID": 801178,
		"GroupArticle": 0
	}, {
		"List": [
			["000573", "\u7ca4\u5b8f\u8fdc\uff21", 4.96, 5.31, "\u6709\u8272\u91d1\u5c5e\u3001\u623f\u5730\u4ea7", 212307029, 14324479, 51928851, -37604372, 2507836994, 3165871796, 0, "801676", "\u5730\u4ea7\u94fe", 8.61],
			["600234", "\u79d1\u65b0\u53d1\u5c55", 18.11, 1.97, "\u88c5\u4fee\u5bb6\u5177\u3001\u5730\u4ea7\u94fe", 98745492, -4373601, 17038949, -21412550, 2517377927, 4754254821, 0, "801676", "\u5730\u4ea7\u94fe", 4.01],
			["600639", "\u6d66\u4e1c\u91d1\u6865", 11.22, 0.9, "\u623f\u5730\u4ea7\u3001\u5e74\u62a5\u589e\u957f", 97192306, -7058137, 14897909, -21956046, 3322662117, 12593472659, 0, "801676", "\u5730\u4ea7\u94fe", 2.94]
		],
		"GroupName": "\u5730\u4ea7\u94fe",
		"GroupID": 801676,
		"GroupArticle": 0
	}],
	"GroupCount": 37,
	"GroupID": 801676,
	"Date": "2026-04-16",
	"ttag": 0.04555300000000001,
	"errcode": "0"
}

# 数据说明
GroupList	Array   # 板块列表
GroupCount	Integer	37  # 板块数量
GroupID	Integer	801676  # 最后一个板块ID
Date	String	2026-04-16  # 日期
ttag	Number	0.04555300000000001
errcode	String	0

# GroupList数据说明
GroupList	Array
[0]	Object
GroupName	String	通信 # 板块名称
GroupID	Integer	801660 # 板块代码
GroupArticle	Integer	0
List	Array
[0]	Array
[0]	String	301603  # 股票代码
[1]	String	乔锋智能 # 股票名称
[2]	Number	90.41 # 股票价格
[3]	Integer	20  # 当日涨幅
[4]	String	机器人概念、通信 # 所属版本
[5]	Integer	1066272322 # 当日成交额
[6]	Integer	135431216  # 主力净额
[7]	Integer	615813824  # 主力买入金额
[8]	Integer	-480382608 # 主力卖出金额
[9]	Long	3411395325 # 实际流通额
[10]	Long	10917911600 # 总市值
[11]	Integer	1       # 是否是新增 取值1,0
[12]	String	801660  # 板块代码
[13]	String	通信  # 板块名称
[14]	Number	32.64 # 实际换手率 32.64%



```

### 区间统计 按板块

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

DEnd=2026-04-17&DStart=2026-04-13&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=9&UserID=3807176&VerSion=5.23.0.1&a=GetInterviewsByDateZS&apiv=w44&c=StockLineData&st=20

**可不传参数: Token，UserID, DeviceID**

{
	"Count": 267,
	"ttag": 0.002910999999999997,
	"errcode": "0",
    List": [
		["801807", "\u7b97\u529b", 4.76, 378614525172, -366078599270, 12535925902, 4125320278796, 22309429235264, 3, 1, 11328022884, 44450.4]
    ]
}

# 数据说明
Count: 所有数据个数
List: 数据列表

List:
[0]	Array
[0]	String	801807  # 板块代码
[1]	String	算力 # 板块名称
[2]	Number	4.76 # 区间涨幅
[3]	Long	378614525172 # 区间主力买入
[4]	Long	-366078599270 # 区间主力卖出
[5]	Long	12535925902 # 区间净额
[6]	Long	4125320278796 # 区间成交额
[7]	Long	22309429235264 # 流通市值
[8]	Integer	3 # 净流入天数
[9]	Integer	1
[10]	Long	11328022884
[11]	Number	44450.4 # 区间强度


```
### 区间统计 按股票

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

DEnd=2026-04-17&DStart=2026-04-08&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&FilterBJS=1&Index=0&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=2&UserID=3807176&VerSion=5.23.0.1&a=GetInterviewsByDateStock&apiv=w44&c=StockLineData&st=20

**可不传参数: Token，UserID, DeviceID**

{
	"Count": 5193,
	"ttag": 0.0035439999999999916,
	"errcode": "0",
    {
	"List": [
		["002580", "\u5723\u9633\u80a1\u4efd", 30.58, 90.06, 7265739404, -7176973197, 88766207, 272.797, 19903514654, 10630292007, "\u6db2\u51b7\u3001\u7b97\u529b", 1, "\u6e38\u8d44", 5, 655231040, 0]
    }
}

# 数据说明
Count: 所有数据个数
List: 数据列表

List:
[0]	Array
[0]	String	002580  # 股票代码
[1]	String	圣阳股份 # 股票名称
[2]	Number	30.58
[3]	Number	90.06  # 区间涨幅
[4]	Long	7265739404 # 区间主力买入
[5]	Long	-7176973197 # 区间主力卖出
[6]	Integer	88766207 # 区间净额
[7]	Number	272.797 # 区间换手率
[8]	Long	19903514654 # 区间成交额
[9]	Long	10630292007 # 实际流通市值
[10]	String	液冷、算力 # 所属板块
[11]	Integer	1 #是否融资融券
[12]	String	游资 # 主力类型
[13]	Integer	5 # 净流入天数
[14]	Integer	655231040
[15]	Integer	0

```

### 板块强度

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=1&UserID=3807176&VerSion=5.23.0.1&ZSType=7&a=RealRankingInfo&apiv=w44&c=ZhiShuRanking&st=20

**可不传参数: Token，UserID, DeviceID**

{
    "Time": 1776534425,
	"Count": 20,
	"Day": ["2026-04-16"],
	"Min": "0925",
	"Max": "1500",
	"MinDay": "2019-12-23",
	"Title": ["\u7b2c\u56db\u5b63\u5ea6\u673a\u6784\u589e\u4ed3", "2025\u5e74\u5e73\u5747PE", "2026\u5e74\u5e73\u5747PE"],
	"list_soninfo": [],
	"list_son": [],
	"ttag": 0.0040050000000000086,
	"errcode": "0",
	"list": [
		["801807", "\u7b97\u529b", 16745, 2.384, 0.659, 842988298724, 13137561494, 93705977142, -80568415648, 1.135, 22005970401760, 2.15, 6068170000, 27389759880032, 54999750285, 73.8018, 67.0754, 16745, 2.384]
    ]
}
list数据说明：

[0]	Array

[0]	String	801807  # 板块代码
[1]	String	算力 # 板块名称
[2]	Number	16745 # 板块强度
[3]	Number	2.384 # 板块涨幅
[4]	Number	0.659 # 板块涨速
[5]	Long	842988298724 # 板块成交额
[6]	Long	13137561494  #主力净额
[7]	Long	93705977142 # 主力买入金额
[8]	Long	-80568415648 # 主力卖出金额
[9]	Number	1.135 # 量比
[10]	Long	22005970401760 # 板块总市值
[11]	Number	2.15 # 区间涨幅
[12]	Long	6068170000  # 3000w大单净额
[13]	Long	27389759880032 # 板块总市值
[14]	Long	54999750285  # 第四季度机构增仓
[15]	Number	73.8018  # 2025年PE
[16]	Number	67.0754  # 2026年PE
[17]	Number	16745 # 板块强度
[18]	Number	2.384 # 板块涨幅

```

### 行业涨幅

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=2&UserID=3807176&VerSion=5.23.0.1&ZSType=4&a=RealRankingInfo&apiv=w44&c=ZhiShuRanking&st=20

**可不传参数: Token，UserID, DeviceID**

{
    "Time": 1776534429,
	"Count": 20,
	"Day": ["2026-04-16"],
	"Min": "0925",
	"Max": "1500",
	"MinDay": "2017-10-12",
	"Title": ["\u7b2c\u56db\u5b63\u5ea6\u673a\u6784\u589e\u4ed3", "2025\u5e74\u5e73\u5747PE", "2026\u5e74\u5e73\u5747PE"],
	"list_soninfo": [],
	"list_son": [],
	"ttag": 0.029415999999999998,
	"errcode": "0",
    list": [
		["881267", "\u80fd\u6e90\u91d1\u5c5e", 398, 3.985, -0.076, 32993292338, 1961472704, 13568474026, -11607001322, 1.126, 492241402424, 3.32, 792387000, 605562622227, 0, 0, 0, 3.985, 3.985]
    ]
}
list数据说明：

[0]	Array

[0]	String	881267  # 板块代码
[1]	String	能源金属 # 板块名称
[2]	Integer	398 # 板块强度
[3]	Number	3.985 # 涨幅 %
[4]	Number	-0.076 # 涨速 %
[5]	Long	32993292338 # 板块成交额
[6]	Integer	1961472704 # 主力净额
[7]	Long	13568474026  # 主力买入金额
[8]	Long	-11607001322 # 主力卖出金额
[9]	Number	1.126  # 量比
[10]	Long	492241402424 # 流通市值
[11]	Number	3.32 # 区间涨幅
[12]	Integer	792387000 # 3000w大单净额
[13]	Long	605562622227 # 板块总市值
[14]	Integer	0 # 第四季度机构增仓
[15]	Integer	0 # 2025年PE
[16]	Integer	0 # 2026年PE
[17]	Number	3.985 # 板块涨幅
[18]	Number	3.985 # 板块涨幅

```

### 地区涨幅

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=2&UserID=3807176&VerSion=5.23.0.1&ZSType=6&a=RealRankingInfo&apiv=w44&c=ZhiShuRanking&st=20

**可不传参数: Token，UserID, DeviceID**

{
	"Time": 1776534430,
	"Count": 20,
	"Day": ["2026-04-16"],
	"Min": "0925",
	"Max": "1500",
	"MinDay": "2017-10-12",
	"Title": ["\u7b2c\u56db\u5b63\u5ea6\u673a\u6784\u589e\u4ed3", "2025\u5e74\u5e73\u5747PE", "2026\u5e74\u5e73\u5747PE"],
	"list_soninfo": [],
	"list_son": [],
	"ttag": 0.015270000000000006,
	"errcode": "0",
    "list": [
		["801764", "\u897f\u85cf\u81ea\u6cbb\u533a", 677, 2.152, 0, 10769896135, 354081209, 1225385738, -871304529, 1.206, 293276511119, 2.03, 200396000, 330049415433, 92547571, 133.702, 40.6283, 2.152, 2.152]
    ]
}

list数据说明：

[0]	Array

[0]	String	801764 # 板块代码
[1]	String	西藏自治区 # 板块名称
[2]	Integer	677 # 板块强度
[3]	Number	2.152  # 涨幅 %
[4]	Integer	0   # 涨速 %
[5]	Long	10769896135 # 板块成交额
[6]	Integer	354081209  # 主力净额
[7]	Integer	1225385738  # 主力买入金额
[8]	Integer	-871304529 # 主力卖出金额
[9]	Number	1.206       # 量比
[10]	Long	293276511119 # 流通市值
[11]	Number	2.03        # 区间涨幅
[12]	Integer	200396000 # 3000w大单净额
[13]	Long	330049415433 # 板块总市值
[14]	Integer	92547571 # 第四季度机构增仓
[15]	Number	133.702 # 2025年PE
[16]	Number	40.6283 # 2026年PE
[17]	Number	2.152 # 板块涨幅
[18]	Number	2.152 #  板块涨幅

```

### 复盘榜

```
POST

URL	https://apphwshhq.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetRQZ_Data&apiv=w44&c=Index

**可不传参数: Token，UserID, DeviceID**

{
	"List": ["002580", "002297", "601778", "002361"],
    "ttag": 0.0009789999999999521,
	"errcode": "0"
}


```


### 龙虎榜
```
POST
URL	https://applhb.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOSNew=2&Time=2026-04-16&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=GetStockList&apiv=w44&c=LongHuBang&st=300

**可不传参数: Token，UserID, DeviceID**

{
    "Time": "2026-04-16",  # 日期
    "UserType": 0,
    "list": [   # 龙虎榜列表
        {
            "ID": "002361", # 股票代码
            "Name": "神剑股份", # 股票名称
            "IncreaseAmount": "3.88%", # 涨幅
            "D3": "0",  # 是否是3日榜
            "BuyIn": "-225788624", # 净买入
            "JoinNum": 0,  # 关联营业部数量
            "Turnover": "8991980701", # 成交额
            "CircPrice": 15583708671.840002, # 流通价值
            "Amplitude": "15.32",  # 振幅
            "TurnoverRatio": "58.33", # 换手率
            "Capitalization": 18316933502.940002 # 总市值
        },
        {
            "ID": "301666",
            "Name": "N大普微",
            "IncreaseAmount": "430.71%",
            "D3": "0",
            "BuyIn": "821664196",
            "JoinNum": 0,
            "Turnover": "4863699476",
            "CircPrice": 6484571680.650001,
            "Amplitude": "119.38",
            "TurnoverRatio": "82.94",
            "Capitalization": 106676710838
        }
    ],
    "DZJY": [
        "000657",
        "300798",
        "000967"
    ],
    "LikeCity": [],
    "T": [  # T 操作股票列表
        "688668", # 股票ID
        "688227"
    ],
    "TIcon": { # T 操作股票列表标签
        "600152": [ # 股票ID
            "量化基金" # 标签
        ],
        "600396": [
            "量化基金"
        ],
        "600719": [
            "量化基金"
        ]
    },
    "BIcon": { # Buy 操作股票列表标签
        "300088": [ # 股票ID
            "方新侠", # 标签
            "量化打板" # 标签
        ],
        "300736": [
            "量化打板"
        ]
    },
    "SIcon": { # Sell 操作股票列表标签
        "300736": [  # 股票ID
            "量化抢筹" # 标签
        ],
        "301636": [
            "量化基金"
        ]
    },
    "Status": {  # 股票状态
        "300027": "首板",
        "300736": "首板",
        "000967": "3天2板"
    },
    "fkgn": { # 风口概念列表
        "300027": { # 股票ID
            "801031": "文化传媒", # 概念ID : 概念名称
            "801032": "元宇宙",  # 概念ID : 概念名称
            "801059": "字节概念",
            "801085": "人工智能",
            "801095": "游戏",
            "801158": "网络直播",
            "801169": "VR/AR/MR",
            "801310": "浙江",
            "801439": "网红经济",
            "801452": "再融资",
            "801637": "文创产品",
            "801719": "腾讯概念",
            "801786": "影视院线",
            "801872": "谷子经济",
            "803024": "低价股"
        },
        "300736": {
            "801017": "苹果概念",
            "801034": "区块链",
            "801053": "零售",
            "801122": "壳资源",
            "801218": "华为概念",
            "801328": "消费电子",
            "801584": "数字经济",
            "801743": "北京市",
            "801787": "实控人变更"
        }
    },
    "kgSort": {
        "002634": [
            801566,
            801070,
            801273,
            801310,
            801123,
            801112,
            801256,
            801114,
            801313,
            803024
        ],
        "002650": [
            801220,
            801314,
            801635,
            801404,
            801651
        ]
    },
    "lb": {  # 连续进入龙虎榜次数
        "300344": 12,  # 股票ID : 次数
        "002361": 6,
        "002980": 2
    },
    "Total": 59, # 总数
    "Count": {
        "002361": 484910,
        "002491": 252615,
        "002634": 41465,
        "002650": 5335,
        "002980": 94005
    },
    "errcode": "0",
    "t": 0.003122999999999987
}


```

### 单一股票龙虎榜详细信息
```
POST

URL	https://applhb.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

c=Stock&a=GetNewOneStockInfo&Type=0&Time=2026-04-16&StockID=002361&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

**可不传参数: Token，UserID, DeviceID**

{
	"Name": "神剑股份",   # 股票名称
	"ID": "002361",  # 股票代码
	"Time": "2026-04-16", # 日期
	"Group": {
		"Buy": [],
		"Sell": []
	},
	"KlineDay": { # 日K线数据
		"S": "2026-04-16",
		"E": "2026-04-16"
	},
	"OnTimeList": ["2026-04-17", "2026-04-16", "2026-04-15"], # 上榜日期
	"ToBusinessCount": 0, # 关联营业部数量
	"CurPrice": "19.26", # 当前价格
	"QuoteChange": "3.88%", # 涨跌幅
	"TurnoverRatio": "58.33", # 换手率
	"Circulation": "155.84", # 流通市值
	"BuyIn": -225788624, # 净买入额
	"List": [{  # 龙虎榜列表
		"SellList": [{ # 卖盘列表
			"ID": "816", # 席位ID
			"Name": "招商证券上海肇嘉浜路", # 席位名称
			"Day": "2026-04-16", # 日期
			"StockID": "002361", # 股票代码
			"ReasonType": "0", # 原因类型
			"Type": "2", # 类型
			"Buy": "7735345", # 买入额
			"Sell": "222126689", # 卖出额
			"PX": "1",  # 排名
			"LogID": "20260416002361021816", # 日志ID
			"AssocIcon": 0,
			"ExpendablesIcon": 0,
			"YouZiIcon": 0,  # 游资标签 如：一线游资
			"IsDY": 0,
			"UserGroupIcon": [],
			"GroupID": "",  # 分组ID
			"GroupIcon": [], # 分组标签（如"量化抢筹"）
			"UserGroupIconN": {}
		}],
		"BuyList": [{
			"ID": "8800",
			"Name": "深股通专用",
			"Day": "2026-04-16",
			"StockID": "002361",
			"ReasonType": "0",
			"Type": "1",
			"Buy": "209605039",
			"Sell": "67244930",
			"PX": "1",
			"LogID": "202604160023610118800",
			"AssocIcon": 0,
			"ExpendablesIcon": 0,
			"YouZiIcon": 0,
			"IsDY": 0,
			"UserGroupIcon": [],
			"GroupID": "",
			"GroupIcon": [],
			"UserGroupIconN": {}
		}],
		"UpReason": ["日振幅值达15%", "日换手率达20%"], # 上榜原因
		"BuyTotal": 651723160, # 买入总额
		"SellTotal": 877511784 # 卖出总额
	}],
	"DZJY": [],
	"lbnum": 6, # 连续进入龙虎榜次数
	"lbStart": 1,
	"Turnover": "8991980701", # 成交额
	"MoreTurnover": 19052692016, # 更多成交额
	"Arr": [0],
	"ytdbusin": {  # 昨日营业部数据
		"buy": { # 买入席位
			"8800": 5, # 席位ID : 排名 买5
			"3030": 3,
			"20865": 1
		},
		"sell": { # 卖出席位
			"8800": 2, # 席位ID : 排名 卖2
			"816": 1
		}
	},
	"tag": "lv2",
	"errcode": "0",
	"t": 0.0044359999999999955
}

```

### 早盘竞价

```
GET

URL	https://apphis.longhuvip.com/w1/api/index.php

#### 竞价总体信息

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=MorningBidding&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": {
		"tJJJE": "201.95亿",  # 今日竞价金额
		"lJJJE": "249.42亿", # 昨日竞价金额
		"ycln": "23417亿",  # 今日预测总成交
		"lln": "24152亿",  # 昨日预测总成交
		"tSZ": "4065",     # 今日上涨家数
		"tXD": "1003",     # 今日下跌家数
		"lSZ": "1702",     # 昨日上涨家数
		"lXD": "3386"      # 昨日下跌家数
	},
	"ttag": 0.007982999999999962,
	"errcode": "0"
}

#### 竞价数量

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=MorningBiddingNum&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": [
     189, # 涨停委买数
     196, # 撮合成交>2000w 的数量
      50, # 近期热门股
      61, # 主力净额大于1000万的数量
       2], #竞价砸盘数量
	"ttag": 0.011894999999999989,
	"errcode": "0"
}


 #### 涨停委买列表

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&PidType=0&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=4&UserID=3807176&VerSion=5.23.0.1&a=MorningBiddingList&apiv=w44&c=HisHomeDingPan&st=20


#### 撮合大于2000w的列表

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&PidType=1&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=10&UserID=3807176&VerSion=5.23.0.1&a=MorningBiddingList&apiv=w44&c=HisHomeDingPan&st=20


#### 近期热门股

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&PidType=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=5&UserID=3807176&VerSion=5.23.0.1&a=MorningBiddingList&apiv=w44&c=HisHomeDingPan&st=20


#### 主力净额大于1000万的列表

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&PidType=3&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=6&UserID=3807176&VerSion=5.23.0.1&a=MorningBiddingList&apiv=w44&c=HisHomeDingPan&st=20


#### 竞价砸盘列表

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=0&PhoneOSNew=2&PidType=4&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=5&UserID=3807176&VerSion=5.23.0.1&a=MorningBiddingList&apiv=w44&c=HisHomeDingPan&st=20

#### 返回值
{
    "info": [  # 涨停委买列表
        [
            "603920", # 股票代码
            "世运电路", # 股票名称
            0,
            10, # 实时涨幅
            2277793709, # 涨停委买额
            9.99813,  # 竞价涨幅
            103488085, # 竞价净额
            0.69, # 竞价换手
            163466462, # 竞价额
            259825698, # 20分后涨停委买
            0,         # 撮合成交额
            "机器人概念、通信", # 板块标签
            23849428062, # 实际流通
            471286258,
            793683715,
            -322397457,
            ""
        ],
        [
            "002297",
            "博云新材",
            0,
            9.99,
            854923752,
            9.98632,
            57761772,
            5.38,
            384126276,
            80253672,
            0,
            "商业航天、大飞机",
            7134659834,
            263923189,
            1442050165,
            -1178126976,
            ""
        ]
    ],
    "day": "2026-04-16", # 日期
    "time": 1776578057, # 时间戳
    "status": 1,
    "ttag": 0.011726999999999932,
    "errcode": "0"
}


```

### 板块竞价
```
POST
URL	https://apphis.longhuvip.com/w1/api/index.php

Day=20260416&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=0&UserID=3807176&VerSion=5.23.0.1&a=GetBKJJ_W36&apiv=w44&c=StockBidYiDong

{
    "List1": [  # 今日新增竞价异动列表
        [
            "801003", # 板块代码
            "5G", # 板块名称
            6.1, # 竞价爆量 6.1倍
            480121033, # 异动金额
            125,
            8199256 # 主力净额
        ],
        [
            "801012",
            "钢铁",
            4.3,
            145382846,
            14,
            -2067492
        ]
    ],
    "List2": [  # 昨日爆发板块延续异动
        [
            "801001",
            "芯片",
            20.8,
            2932086565,
            7080,
            -94192639
        ],
        [
            "801004",
            "锂电池",
            12.2,
            1530558681,
            "5G",
            6.1,
            480121033,
            125,
            8199256
        ],
        [
            "801012",
            "钢铁",
            4.3,
            145382846,
            14,
            -2067492
        ]
    ],
    "List3": [  # 其他异动板块
        [
            "801007",
            "房地产",
            8,
            238383753,
            1461,
            -47885630
        ]
    ],
    "Day": "2026-04-15", # 日期
    "State": 1,
    "ttag": 0.010110999999999981,
    "errcode": "0"
}

```

### 板块内股票竞价量比 > 800w

```

POST
URL	https://apphis.longhuvip.com/w1/api/index.php

Day=20260416&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&IsLB=0&IsZT=0&Isst=1&Order=1&PhoneOSNew=2&StockID=801660&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=1&UserID=3807176&VerSion=5.23.0.1&a=GetBKJJBL&apiv=w44&c=StockBidYiDong&filter=3&st=20

{
    "List": [
        [
            "603920", # 股票代码
            "世运电路", # 股票名称
            58.86, # 价格
            10, # 实时涨幅
            12.58, # 竞价量比
            163466462, # 竞价额
            10, #竞价涨幅
            103488085, # 竞价净额
            0.69, # 竞价换手
            23848048040, # 实际流通
            "机器人概念、通信", # 板块标签
            1,
            "",
            ""
        ],
        [
            "301377",
            "鼎泰高科",
            216.64,
            -0.3,
            4.21,
            21384000,
            1.24,
            -990000,
            0.14,
            15386639360,
            "英伟达概念、PCB设备",
            1,
            "",
            ""
        ]
    ],
    "State": 1,
    "Day": "2026-04-16",
    "ttag": 0.013986999999999972,
    "errcode": "0"
}

```

### 最强风口

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

c=StockFengKData&a=GetFengKListBest&Time=&Day=20260416&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

{
    "List": [
        [
            "600875", # 股票代码
            "东方电气", # 股票名称
            5469, # 强度
            "0",
            9.99, # 涨跌幅
            1567700924,
            1,
            0,
            3665100361,
            -2097399437,
            "燃气轮机、DeepSeek、人工智能、储能、年报增长、光伏、电气设备、智能电网、核电、风电、ChatGPT、火电灵活改造、业绩增长、新型工业化、工业互联网、风电整机厂商、电源、钒电池、成都市、四川省、氢燃料电池、乡村振兴、抽水蓄能、西藏水电站、氢能源、西部大开发、可控核聚变、水电、国有企业、电力、加氢站、央企", # 所属板块
            1776304440,   # 时间戳
            "燃气轮机、DeepSeek、人工智能、储能、年报增长、光伏、电气设备、智能电网、核电、风电" # 精选板块
        ],
        [
            "000070",
            "特发信息",
            5464,
            "0",
            10.01,
            1054641907,
            0,
            0,
            2212276943,
            -1157635036,
            "算力租赁、算力、数据中心、光纤概念、通信、人工智能、低空经济、军工、并购重组、深圳、光伏、商业航天、智能电网、物业服务、腾讯系AI 、盘古大模型、云计算、通感一体化、深圳国资、国资云、阿里巴巴概念、5G、数字经济、华为概念、数字能源、6G、智慧城市、广东省、传感器、军工信息化、轨道交通、高铁、创投、卫星导航、地产链、成飞概念、一带一路、蚂蚁概念、金融概念、大飞机、特高压、国有企业、电力、绿色电力",
            1776308520,
            "算力租赁、算力、数据中心、光纤概念、通信、人工智能、低空经济、军工、并购重组、深圳、光伏、商业航天、智能电网、物业服务"
        ]
    ],
    "Time": 1776580804, # 时间戳
    "Day": "2026-04-16", # 日期
    "JF": "40000",
    "State": 1,
    "Count": 30,
    "Tips": "",
    "ttag": 0.013891999999999998,
    "errcode": "0"
}

```

### 获取股票所属板块

```
POST
URL	https://apphwshhq.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

a=GetStockIDPlate&c=StockL2Data&StockID=600666&Type=1&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

**可不传参数: Token，UserID, DeviceID**

{
    "List": [
        [
            "801807", # 板块代码
            "算力", # 板块名称
            0.619, # 板块涨跌幅
        ],
        [
            "801328",
            "消费电子",
            1.338
        ],
        [
            "801199",
            "汽车零部件",
            1.019
        ],
        [
            "801574",
            "年报增长",
            0.466
		]
    ],
    "ttag": 0.0018700000000000383,
    "errcode": "0"
}

```

### 获取最新消息

```
POST

URL	https://applhb.longhuvip.com/w1/api/index.php

DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&PhoneOS=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&Version=5.23.0.1&a=AppNews&apiv=w44&c=UserInfo&st=1

**可不传参数: Token，UserID, DeviceID**

{
    "List": [
        {
            "Time": "1776580899",
            "Content": "【瑞达期货：预计一季度净利润同比增长135.64%-165.25%】瑞达期货发布业绩预告，依据上市公司公告预计2026年一季度净利润为1.91亿元-2.15亿元。业绩增长主要原因是期货市场成交量和成交额创新高，交投情绪高涨，交易活跃度提升，公司把握市场机会，资产管理及风险管理业务利润较上年同期大幅增长。注：公司Q1净利润预计1.91亿-2.15亿，2025年Q4净利润1.61亿，据此计算，Q1净利润预计增长变动18%-33%。",
            "ID": "31708",
            "URL": "",
            "Type": 23,
            "StockID": "002961",
            "StockName": "瑞达期货",
            "StockStr": "002961",
            "Param0": "11"
        }
    ],
    "errcode": "0",
    "t": 0.0025119999999999587
}

```


### 涨停表现
```
URL	https://apphis.longhuvip.com/w1/api/index.php

#### 涨跌停数

POST

Date=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=MarketStockZDNum&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": {
		"SJZT": "79", # 涨停数
		"SJDT": "1"  # 跌停数
	},
	"ttag": 0.006464000000000025,
	"errcode": "0"
}

#### 涨停板数量统计

GET

URL	Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=DailyLimitIndex&apiv=w44&c=HisHomeDingPan

**可不传参数: Token，UserID, DeviceID**

{
	"info": [71, 5, 1, 1, 1], # 一板数量, 二板数量, 三板数量, 四板数量, 更高板数量
	"ttag": 0.0004729999999999457,
	"errcode": "0"
}

#### 涨停板列表

GET

Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=0&PhoneOSNew=2&PidType=1&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=4&UserID=3807176&VerSion=5.23.0.1&a=DailyLimitPerformance&apiv=w44&c=HisHomeDingPan&st=1000

参数说明: PidType=1, 一板, PidType=2, 二板, PidType=3, 三板, PidType=4, 四板, PidType=5, 五板及以上

**可不传参数: Token，UserID, DeviceID**

{
    "info": [
        [
            [
                "002726", # 股票代码
                "龙大美食", # 股票名称
                0,
                "",
                1776302700, # 涨停时间
                "农业", # 涨停原因
                39182180, # 封单额
                275723072, # 最大封单
                91895163, #主力净额
                141993242, # 主力买入
                -50098079, # 主力卖出
                158897958, # 成交额
                "猪肉、农业", # 所属板块
                2351136421, # 流通市值
                6.76, #实际换手
                1,
                0, # 是否是回封
                1.52, #振幅
                "",  # 标签 如4天2板
                "801464", # 涨停板块
                1,
                3.62, # 价格
                10.03 # 涨跌幅
            ]
        ],
        "2026-04-16"
    ],
    "ttag": 0.0025600000000000067,
    "errcode": "0"
}

#### 破板个股

GET
Day=2026-04-16&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&PidType=1&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=5&UserID=3807176&VerSion=5.23.0.1&a=DailyLimitPerformance2&apiv=w44&c=HisHomeDingPan&st=1000

参数说明：
PidType=1, 今日首板破板个股,
PidType=2, 未涨停的昨日一板个股
PidType=3, 未涨停的昨日二板个股
PidType=4, 未涨停的昨日三板个股
PidType=5, 未涨停的昨日四板及以上个股

**可不传参数: Token，UserID, DeviceID**

{
    "info": [
        [
            [
                "301382", # 股票代码
                "蜂助手", # 股票名称
                0,
                "",
                40.49, # 价格
                15.69, # 涨跌幅
                "DeepSeek、人工智能", # 所属板块
                244740588, # 主力净额
                940356481, # 主力买入
                -100000000,
                158897958,
                -695615893, # 主力卖出
                2126573704, # 成交额
                6195717080, # 实际流通
                34.69, # 实际换手
                0,
                14.63, # 振幅
                "",
                1,
                764268608 #最大封单
            ]
        ],
        17  # 个数
    ],
    "ttag": 0.002458999999999989,
    "errcode": "0"
}

```

### 尾盘抢筹

```
URL	https://apphis.longhuvip.com/w1/api/index.php

Day=20260416&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a&Index=0&Order=1&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&Type=1&UserID=3807176&VerSion=5.23.0.1&a=GetWPQC&apiv=w44&c=StockBidYiDong&st=20

**可不传参数: Token，UserID, DeviceID**

{
    "List": [
        [
            "002384", # 股票代码
            "东山精密", # 股票名称
            "游资", # 标签
            1,  # 是否融资融券
            "光芯片、苹果概念", # 所属板块
            2.57, #涨跌幅
            11843400000, #成交额
            182656195162, # 实际流通市值
            6014487511, # 主力买
            -6261255927, # 主力卖
            -246768416, # 主力净额
            427181324, # 抢筹金额
            328182000, # 撮合成交
            0,
            0,
            0.62, # 抢筹幅度
            100 # 抢筹占比
        ]
    ],
    "State": 1,
    "Day": "2026-04-16",
    "ttag": 0.01568,
    "errcode": "0"
}

```

### 市场风口

```
POST

URL	https://apphis.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

#### 股票风口

c=StockFengKData&a=GetFengKList&Index=0&st=500&Order=17&Day=20260416&Time=1500&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

**可不传参数: Token，UserID, DeviceID**

{
    "List": [
        [
            "603777", # 股票代码
            "来伊份  ", # 股票名称
            "0",
            "-0.48", # 涨跌幅
            "2265698308",
            "103684465",
            "-138528691",
            "-34844226", # 主力净额
            "食品饮料,人造肉", # 风口概念
            "0",
            "游资", # 标签
            "食品饮料,人造肉", # 所属板块
            "1776303523"
        ],
        [
            "688818",
            "电科蓝天",
            "0",
            "-0.12",
            "8845094713",
            "390357726",
            "-536092881",
            "-145735155",
            "",
            "0",
            "",
            "",
            "1776303862"
        ]
    ],
    "Time": 1776584687,
    "Day": "2026-04-16",
    "Count": 546,
    "ttag": 0.0032059999999999866,
    "errcode": "0"
}

#### 概念风口

c=StockFengKData&a=GetFengKYDPlate&Day=20260416&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

**可不传参数: Token，UserID, DeviceID**

{
    "List": [
        [
            "锂电池", # 概念名称
            744.42 # 强度
        ],
        [
            "有色金属",
            433.05
        ],
        [
            "生物制品",
            -9.13
        ],
        [
            "房地产",
            -9.92
        ]
    ],
    "Day": "20260416",
    "Time": 1776584696,
    "ttag": 0.0008170000000000122,
    "errcode": "0"
}

```

### 游资动向
```
POST

URL	https://applhb.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

c=Index&a=YouZiDongXiangByList&Time=2026-04-16&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

**可不传参数: Token，UserID, DeviceID**

{
    "DongXiang": [
        {
            "Sort": "10000",
            "ID": "9", #游资ID
            "ShortName": "金开大道", # 游资简称
            "Time": "2026-04-16", # 日期
            "List": [
                {
                    "GInfo": [
                        "0:1:15490"
                    ],
                    "Slist": [  #股票列表
                        {
                            "SellList": [ # 卖出席位列表
                                {
                                    "ID": "14726", # 卖出席位ID
                                    "Name": "东方财富证券拉萨团结路第二", # 卖出席位名称
                                    "Day": "2026-04-16", # 日期
                                    "StockID": "301666", # 股票代码
                                    "ReasonType": "0",
                                    "Type": "2",
                                    "Buy": "33399745", # 买入金额
                                    "Sell": "21462281", # 卖出金额
                                    "PX": "1", # 排名
                                    "LogID": "2026041630166602114726",
                                    "AssocIcon": 0,
                                    "ExpendablesIcon": 0,
                                    "YouZiIcon": 0,
                                    "IsDY": 0,
                                    "UserGroupIcon": [],
                                    "GroupID": "",
                                    "GroupIcon": []
                                }
                            ],
                            "BuyList": [ # 买入席位列表
                                {
                                    "ID": "15490",
                                    "Name": "方正证券重庆金开大道",
                                    "Day": "2026-04-16",
                                    "StockID": "301666",
                                    "ReasonType": "0",
                                    "Type": "1",
                                    "Buy": "355048024",
                                    "Sell": "0",
                                    "PX": "1",
                                    "LogID": "2026041630166601115490",
                                    "AssocIcon": 0,
                                    "ExpendablesIcon": 0,
                                    "YouZiIcon": "2",
                                    "IsDY": 0,
                                    "UserGroupIcon": [],
                                    "GroupID": 9,
                                    "GroupIcon": [
                                        "金开大道"
                                    ]
                                }
                            ],
                            "UpReason": [ # 上榜理由
                                "无价格涨跌幅限制"
                            ],
                            "BuyTotal": 917611846, # 买入总金额
                            "SellTotal": 95947650 # 卖出总金额
                        }
                    ],
                    "Money": 355048024, # 金额
                    "ts": [
                        "355048024",
                        0
                    ],
                    "ID": 301666, # 股票代码
                    "Name": "N大普微", # 股票名称
                    "D3": 0,
                    "IncreaseAmount": "430.71%" # 涨跌幅
                }
            ],
            "IsReview": 0
        }
    ],
    "Time": "2026-04-16",
    "errcode": "0",
    "t": 0.005848000000000001
}
```

### 游资席位信息

```
POST

URL	https://applhb.longhuvip.com/w1/api/index.php?apiv=w44&PhoneOSNew=2&VerSion=5.23.0.1

c=BusinessGroup&a=GroupInfo&GID=7&UserID=3807176&Token=036ca9cad6e44ee4a585c22cb2c298ed&DeviceID=4cac82ffc900bae65f51f73b756612a3911b7a7a

**可不传参数: Token，UserID, DeviceID**

{
    "GID": 7, # ID
    "Info": "短线游资，擅长挖掘新题材并推动板块联动效应，交易中常出现盘中直线拉升同板块多只个股首板的操作，个股走势走弱后即进行卖出操作。", # 简介
    "ShortName": "成都系", # 简称
    "Total": 11,  # 席位总数
    "CertifiID": 0,
    "BusinessList": [
        {
            "ID": "10175", # 席位ID
            "Name": "宏信证券成都天府大道北段" # 席位名称
        },
        {
            "ID": "6609",
            "Name": "国联证券成都锦城大道"
        }
    ],
    "MsgList": [],
    "Time": 1776585566,
    "errcode": "0",
    "t": 0.005643999999999982
}
```



### 题材库搜索

```
POST

URL	https://applhb.longhuvip.com/w1/api/index.php

DeviceID=4dc508c4765c902e4ab538f195402bb23c9e24d2&PhoneOSNew=2&Token=036ca9cad6e44ee4a585c22cb2c298ed&UserID=3807176&VerSion=5.23.0.1&a=InfoSearch&apiv=w44&c=Theme&key=%E5%85%89

key = 搜索关键词


**可不传参数: Token，UserID, DeviceID**

{
    "List": [ # 主题材满足条件List
        {
            "ID": "9", # 题材ID
            "Name": "光刻机概念", # 题材名称
            "Desc": "", # 描述
            "CreateTime": "1698997269" # 创建时间
        },
        {
            "ID": "55",
            "Name": "激光雷达",
            "Desc": "",
            "CreateTime": "1700808643"
        }
    ],
    "SList": [ # 子题材满足条件List
        {
            "ID": "307",
            "Name": "大厂算力梳理",
            "LName": [          # 子题材名称列表
                "阿里系",
                "光模块"
            ],
            "LID": [   # 子题材ID列表
                "3438",
                "4217"
            ],
            "LIDNameMap": [ # 子题材ID和名称映射
                {
                    "ID": "3438",
                    "Name": "阿里系"
                },
                {
                    "ID": "4217",
                    "Name": "光模块"
                }
            ]
        }
    ],
    "errcode": "0",
    "t": 0.009297999999999973
}

```
