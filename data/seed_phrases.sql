-- 申论帮 - 示例好词好句数据

-- 开头类
INSERT INTO good_phrases (gid, content, category, tags, use_count, status, created_at) VALUES
('phrase_001', '当前，我国正处于实现中华民族伟大复兴的关键时期，...', '开头', '家国情怀,时代主题', 0, 'approved', datetime('now')),
('phrase_002', '基层治理是国家治理的基石。完善基层治理体系，对于...', '开头', '基层治理,治理体系', 0, 'approved', datetime('now')),
('phrase_003', '营商环境是企业生存发展的土壤。优化营商环境，就是...', '开头', '营商环境,企业发展', 0, 'approved', datetime('now')),
('phrase_004', '乡村振兴战略是新时代'三农'工作的总抓手。推进乡村全面振兴，必须...', '开头', '乡村振兴,三农', 0, 'approved', datetime('now')),
('phrase_005', '绿色发展是高质量发展的底色。坚持绿水青山就是金山银山理念，要...', '开头', '绿色发展,生态文明', 0, 'approved', datetime('now'));

-- 过渡类
INSERT INTO good_phrases (gid, content, category, tags, use_count, status, created_at) VALUES
('phrase_006', '然而，我们也要清醒认识到，...仍然存在不少问题。', '过渡', '问题导向', 0, 'approved', datetime('now')),
('phrase_007', '一方面，...；另一方面，...。二者相互交织，增添了问题的复杂性。', '过渡', '辩证分析', 0, 'approved', datetime('now')),
('phrase_008', '造成上述问题的原因是多方面的，既有客观因素，也有主观原因。', '过渡', '原因分析', 0, 'approved', datetime('now')),
('phrase_009', '综上所述，...。要解决这些问题，需要多方协同、久久为功。', '过渡', '总结过渡', 0, 'approved', datetime('now')),
('phrase_010', '对此，我们必须坚持问题导向，找准突破口，以点带面推动整体提升。', '过渡', '对策引出', 0, 'approved', datetime('now'));

-- 论证类
INSERT INTO good_phrases (gid, content, category, tags, use_count, status, created_at) VALUES
('phrase_011', '实践证明，...是实现...的根本途径。', '论证', '实践验证', 0, 'approved', datetime('now')),
('phrase_012', '从调研情况看，...已经取得了阶段性成效，但距离目标还有差距。', '论证', '调研分析', 0, 'approved', datetime('now')),
('phrase_013', '以某地为例，该地通过...，实现了...的良性循环，其经验值得借鉴。', '论证', '案例论证', 0, 'approved', datetime('now')),
('phrase_014', '数据显示，...，充分说明了...的重要性和必要性。', '论证', '数据支撑', 0, 'approved', datetime('now')),
('phrase_015', '正如某专家所言：'...'。这深刻揭示了...的内在规律。', '论证', '专家观点', 0, 'approved', datetime('now'));

-- 对策类
INSERT INTO good_phrases (gid, content, category, tags, use_count, status, created_at) VALUES
('phrase_016', '一是加强顶层设计，完善...制度体系。', '对策', '制度建设', 0, 'approved', datetime('now')),
('phrase_017', '二是强化要素保障，加大...投入力度。', '对策', '资源保障', 0, 'approved', datetime('now')),
('phrase_018', '三是创新工作方式，推动...数字化转型。', '对策', '数字赋能', 0, 'approved', datetime('now')),
('phrase_019', '四是注重人才培养，打造...专业队伍。', '对策', '人才建设', 0, 'approved', datetime('now')),
('phrase_020', '五是加强监督考核，确保...落地见效。', '对策', '监督考核', 0, 'approved', datetime('now'));

-- 结尾类
INSERT INTO good_phrases (gid, content, category, tags, use_count, status, created_at) VALUES
('phrase_021', '总之，...需要我们以更加坚定的信心、更加务实的作风、更加有力的举措，持续发力、久久为功。', '结尾', '总括收尾', 0, 'approved', datetime('now')),
('phrase_022', '站在新的历史起点上，我们要...，奋力谱写...新篇章。', '结尾', '展望未来', 0, 'approved', datetime('now')),
('phrase_023', '只要我们坚持...，就一定能够...，为实现...作出更大贡献。', '结尾', '信心表达', 0, 'approved', datetime('now')),
('phrase_024', '展望未来，...前景光明、使命光荣。我们要以...为契机，...。', '结尾', '使命担当', 0, 'approved', datetime('now')),
('phrase_025', '让我们以更加昂扬的斗志、更加扎实的作风，推动...迈上新台阶！', '结尾', '号召动员', 0, 'approved', datetime('now'));

-- 名言类
INSERT INTO good_phrases (gid, content, category, tags, use_count, status, created_at) VALUES
('phrase_026', '大道至简，实干为要。', '名言', '实干精神', 0, 'approved', datetime('now')),
('phrase_027', '民惟邦本，本固邦宁。', '名言', '以民为本', 0, 'approved', datetime('now')),
('phrase_028', '上下同欲者胜，风雨同舟者兴。', '名言', '团结奋进', 0, 'approved', datetime('now')),
('phrase_029', '不谋全局者，不足谋一域。', '名言', '全局观念', 0, 'approved', datetime('now')),
('phrase_030', '知行合一，止于至善。', '名言', '知行统一', 0, 'approved', datetime('now'));