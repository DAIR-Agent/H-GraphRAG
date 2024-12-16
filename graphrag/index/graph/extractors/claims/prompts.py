# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""A file containing prompts definition."""

CLAIM_EXTRACTION_PROMPT = """
-目标活动-
你是一名智能助手，帮助人类分析师分析文本文件中针对某些实体的声明。

-目标-
根据一个可能与此活动相关的文本文件、实体规范和声明描述，提取所有符合实体规范的实体以及所有针对这些实体的声明。

-步骤-
1. 提取所有符合预定义实体规范的命名实体。实体规范可以是实体名称列表或实体类型列表。
2. 对于步骤1中识别的每个实体，提取与该实体相关的所有声明。声明必须符合指定的声明描述，并且该实体应为声明的主体。
对于每个声明，提取以下信息：
- 主体：声明的主体实体名称，使用大写。主体实体是声明中描述行为的执行者，必须是步骤1中识别的命名实体之一。
- 客体：声明的客体实体名称，使用大写。客体实体是报告/处理或受到声明中描述的行为影响的实体。如果客体实体未知，则使用**未知**。
- 声明类型：声明的整体类别，使用大写。应以可跨多个文本输入重复的方式命名，以便类似声明共享相同的声明类型。
- 声明状态：**真**、**假** 或 **存疑**。“真”表示声明已确认，“假”表示声明被发现是错误的，“存疑”表示声明尚未验证。
- 声明描述：详细描述解释声明的理由，包括所有相关证据和参考资料。
- 声明日期：声明作出的期间（开始日期、结束日期）。开始日期和结束日期都应采用ISO-8601格式。如果声明是在单一日期作出，则开始日期和结束日期应相同。如果日期未知，返回**未知**。
- 声明来源文本：列出原始文本中与声明相关的所有引用。

将每个声明格式化为 (<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<claim_start_date>{tuple_delimiter}<claim_end_date>{tuple_delimiter}<claim_description>{tuple_delimiter}<claim_source>)

3. 以英文返回步骤1和步骤2中识别的所有声明，使用**{record_delimiter}**作为列表分隔符。

4. 完成时，输出{completion_delimiter}

-示例-
示例1:
实体规范：组织
声明描述：与实体相关的红色警告信号
文本：根据2022年1月10日的一篇文章，公司甲因参与多个由政府机构乙发布的公开招标而涉嫌围标被罚款。该公司由个人丙拥有，个人丙在2015年涉嫌参与腐败活动。
输出：

(公司甲{tuple_delimiter}政府机构乙{tuple_delimiter}反竞争行为{tuple_delimiter}真{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}公司甲被发现有反竞争行为，因为依据2022年1月10日发表的文章，公司甲参与多个由政府机构乙发布的公开招标而涉嫌围标被罚款{tuple_delimiter}根据2022年1月10日的一篇文章，公司甲因参与多个由政府机构乙发布的公开招标而涉嫌围标被罚款。)
{completion_delimiter}

示例2:
实体规范：公司甲, 个人丙
声明描述：与实体相关的红色警告信号
文本：根据2022年1月10日的一篇文章，公司甲因参与多个由政府机构乙发布的公开招标而涉嫌围标被罚款。该公司由个人丙拥有，个人丙在2015年涉嫌参与腐败活动。
输出：

(公司甲{tuple_delimiter}政府机构乙{tuple_delimiter}反竞争行为{tuple_delimiter}真{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}2022-01-10T00:00:00{tuple_delimiter}公司甲被发现有反竞争行为，因为依据2022年1月10日发表的文章，公司甲参与多个由政府机构乙发布的公开招标而涉嫌围标被罚款{tuple_delimiter}根据2022年1月10日的一篇文章，公司甲因参与多个由政府机构乙发布的公开招标而涉嫌围标被罚款。)
{record_delimiter}
(个人丙{tuple_delimiter}未知{tuple_delimiter}贪污{tuple_delimiter}存疑{tuple_delimiter}2015-01-01T00:00:00{tuple_delimiter}2015-12-30T00:00:00{tuple_delimiter}个人丙在2015年涉嫌参与腐败活动{tuple_delimiter}该公司由个人丙拥有，个人丙在2015年涉嫌参与腐败活动。)
{completion_delimiter}

-实际数据-
请根据以下输入提供答案。
实体规范：{entity_specs}
声明描述：{claim_description}
文本：{input_text}
输出："""


CONTINUE_PROMPT = "请不要使用你的内置知识来回答这个问题。请只从我给定的文本中提取实体，提取出的实体必须在我的实际数据的文本中出现，否则不要输出。同一个实体只提取一次，不要重复。请确保你的回答中不要有重复的信息。在上一次抽取中很多实体缺失。 把他们用同样的格式加在下面:\n"
LOOP_PROMPT = "请不要使用你的内置知识来回答这个问题。请只从我给定的文本中提取实体，提取出的实体必须在我的实际数据的文本中出现，否则不要输出。同一个实体只提取一次，不要重复。请确保你的回答中不要有重复的信息。似乎很多实体依然缺失.  回答 是 | 否 仍有应该被添加的实体。\n"
