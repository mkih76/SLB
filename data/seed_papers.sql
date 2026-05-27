-- 申论帮 - 示例试卷数据

-- 试卷1: 2024年国考申论（省部级）
INSERT INTO papers (pid, title, exam_type, year, difficulty, questions, heat, status, created_at) VALUES
('paper_2024_gwy_sbd', '2024年国家公务员录用考试申论（省部级）', '国考', 2024, 'hard',
'[{"qid": "q1", "stem": "请你根据给定资料，概括当前基层治理中存在的主要问题，并提出对策建议。", "material": ["材料一：某社区存在电动自行车上楼充电、楼道堆放杂物等安全隐患，居民多次反映但问题解决不彻底。", "材料二：某街道在开展老旧小区改造时，因施工方案与居民需求不匹配，导致居民集体投诉。", "材料三：某乡镇在推进数字政务建设中，存在重建设轻运维的问题，系统建成后使用率不高。"], "word_limit": 800},
{"qid": "q2", "stem": "给定资料中提到了某地在优化营商环境方面的创新举措，请你就其中一项进行详细分析，并说明其借鉴意义。", "material": ["材料四：某省推行'一网通办'改革，企业开办时间从原来的5个工作日压缩至1个工作日。", "材料五：某市建立'企业服务专员'制度，为重点企业提供一对一专属服务。", "材料六：某县设立'吐槽窗口'，专门收集企业对政府工作的意见建议。"], "word_limit": 1000}]',
0, 'published', datetime('now'));

-- 试卷2: 2024年省考申论（行政执法）
INSERT INTO papers (pid, title, exam_type, year, difficulty, questions, heat, status, created_at) VALUES
('paper_2024_sk_sxzz', '2024年各省公务员录用考试申论（行政执法类）', '省考', 2024, 'medium',
'[{"qid": "q1", "stem": "请根据给定资料，分析当前行政执法中存在的突出问题，并提出改进措施。", "material": ["材料一：某地城管执法人员在执法过程中存在态度粗暴、程序不规范等问题，引发群众不满。", "材料二：某市在综合行政执法改革后，部门间职责划分不清，导致推诿扯皮现象。", "材料三：部分地区行政执法装备不足，信息化水平较低。"], "word_limit": 800},
{"qid": "q2", "stem": "给定资料介绍了某地在推进规范执法方面的经验，请你就其中一项成功做法进行总结提炼。", "material": ["材料四：某市推行'柔性执法'，对轻微违法行为首违不罚。", "材料五：某省建立行政执法监督平台，实现全过程监管。", "材料六：某县开展'执法体验日'活动，邀请群众参与监督。"], "word_limit": 1000}]',
0, 'published', datetime('now'));

-- 试卷3: 2023年事业单位联考
INSERT INTO papers (pid, title, exam_type, year, difficulty, questions, heat, status, created_at) VALUES
('paper_2023_sydw', '2023年事业单位联考综合应用能力（E类）', '事业单位', 2023, 'medium',
'[{"qid": "q1", "stem": "请根据给定资料，谈谈如何提升基层公共服务水平。", "material": ["材料一：某社区养老服务中心设施齐全但利用率不高，居民反映服务内容单一。", "材料二：某地区推进'15分钟服务圈'建设，但部分服务项目尚未落地。", "材料三：基层公共服务人才短缺，专业化程度不高。"], "word_limit": 800}]',
0, 'published', datetime('now'));

-- 试卷4: 2023年国考申论（地市级）
INSERT INTO papers (pid, title, exam_type, year, difficulty, questions, heat, status, created_at) VALUES
('paper_2023_gwy_dsj', '2023年国家公务员录用考试申论（地市级）', '国考', 2023, 'medium',
'[{"qid": "q1", "stem": "请你根据给定资料，概括乡村振兴中产业兴旺的主要做法和成效。", "material": ["材料一：某村发展特色民宿产业，带动农副产品销售，农民收入显著增加。", "材料二：某乡镇引进农产品深加工企业，延长产业链，提高附加值。", "材料三：某县打造区域公共品牌，提升农产品市场竞争力。"], "word_limit": 800},
{"qid": "q2", "stem": "给定资料反映了乡村人才振兴中的一些问题，请你就如何吸引人才返乡提出建议。", "material": ["材料四：某地出台人才返乡优惠政策，但落地执行中存在偏差。", "材料五：返乡创业青年反映融资难、用地难问题突出。", "材料六：部分农村基础设施建设滞后，难以满足人才生活需求。"], "word_limit": 1000}]',
0, 'published', datetime('now'));

-- 更新试卷热度
UPDATE papers SET heat = (SELECT COUNT(*) FROM submissions WHERE submissions.pid = papers.pid) + RANDOM() % 10;