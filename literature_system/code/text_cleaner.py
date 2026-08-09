"""
文本清洗工具模块
- HTML 摘要清洗
- 日期标准化
- 作者机构标准化（基础）
"""
import re
import html
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import html2text


# ============ HTML 摘要清洗 ============

def clean_html_abstract(html_text: str) -> str:
    """
    清洗 HTML 格式的摘要文本
    
    Args:
        html_text: 包含 HTML 标签的摘要文本
        
    Returns:
        清洗后的纯文本摘要
    """
    if not html_text or not isinstance(html_text, str):
        return ""
    
    # 如果没有 HTML 标签，直接返回
    if '<' not in html_text:
        return html_text.strip()
    
    try:
        # 方法1: 使用 html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = True
        h.body_width = 0  # 不自动换行
        
        text = h.handle(html_text)
        text = text.strip()
        
        # 清理多余的空行
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    except Exception as e:
        # 方法2: 简单回退 - 使用正则去除标签
        try:
            # 去除 HTML 标签
            text = re.sub(r'<[^>]+>', '', html_text)
            # 解码 HTML 实体
            text = html.unescape(text)
            # 清理空白
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except:
            return html_text.strip()


def test_html_cleaning():
    """测试 HTML 清洗功能"""
    test_cases = [
        # 测试用例: (输入, 预期包含关键词)
        ('<p>This is a <b>test</b> abstract.</p>', 'test abstract'),
        ('<jats:p>This is a <jats:italic>research</jats:italic> paper.</jats:p>', 'research paper'),
        ('No HTML here', 'No HTML here'),
        ('&lt;script&gt;alert(1)&lt;/script&gt;', 'script'),  # HTML 实体
        ('<p>Multiple</p><p>Paragraphs</p>', 'Multiple Paragraphs'),
    ]
    
    print("HTML 摘要清洗测试")
    print("=" * 60)
    for html_input, expected in test_cases:
        result = clean_html_abstract(html_input)
        status = "✓" if expected.lower() in result.lower() else "✗"
        print(f"{status} 输入: {html_input[:50]}")
        print(f"  输出: {result[:50]}")
        print()


# ============ 日期标准化 ============

DATE_PATTERNS = [
    # ISO 格式
    (r'^(\d{4})-(\d{2})-(\d{2})$', '%Y-%m-%d'),          # 2024-01-15
    (r'^(\d{4})/(\d{2})/(\d{2})$', '%Y/%m/%d'),          # 2024/01/15
    
    # 美式格式
    (r'^(\d{2})/(\d{2})/(\d{4})$', '%m/%d/%Y'),          # 01/15/2024
    (r'^(\d{2})-(\d{2})-(\d{4})$', '%m-%d-%Y'),          # 01-15-2024
    
    # 年月格式
    (r'^(\d{4})-(\d{2})$', '%Y-%m'),                     # 2024-01
    (r'^(\d{4})/(\d{2})$', '%Y/%m'),                    # 2024/01
    (r'^(\d{4})$', '%Y'),                                 # 2024
    
    # 文字月份
    (r'^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})$', '%d %b %Y'),  # 15 Jan 2024
    (r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})$', '%b %Y'),                # Jan 2024
    (r'^(\d{4})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*$', '%Y %b'),                 # 2024 Jan
]

# 英文月份映射
MONTH_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}


def normalize_date(date_str: str) -> Optional[Dict[str, str]]:
    """
    将各种格式的日期标准化为统一格式
    
    Args:
        date_str: 原始日期字符串
        
    Returns:
        包含标准化日期信息的字典:
        {
            'original': 原始字符串,
            'standard': YYYY-MM-DD 格式,
            'year': 年份,
            'month': 月份,
            'day': 日期,
            'parsed': 是否成功解析
        }
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    
    result = {
        'original': date_str,
        'standard': None,
        'year': None,
        'month': None,
        'day': None,
        'parsed': False
    }
    
    # 尝试各种模式
    for pattern, fmt in DATE_PATTERNS:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                # 构建可解析的日期字符串
                if fmt == '%Y':
                    date_str_formatted = f"{groups[0]}-01-01"
                    dt = datetime.strptime(f"{groups[0]}-01-01", '%Y-%m-%d')
                elif fmt == '%b %Y':
                    month = MONTH_MAP.get(groups[0].lower()[:3], 1)
                    date_str_formatted = f"{groups[1]}-{month:02d}-01"
                    dt = datetime.strptime(date_str_formatted, '%Y-%m-%d')
                elif fmt == '%Y %b':
                    month = MONTH_MAP.get(groups[1].lower()[:3], 1)
                    date_str_formatted = f"{groups[0]}-{month:02d}-01"
                    dt = datetime.strptime(date_str_formatted, '%Y-%m-%d')
                else:
                    # 对于其他格式，直接用 strptime
                    date_str_formatted = date_str
                    dt = datetime.strptime(date_str, fmt)
                
                result['standard'] = dt.strftime('%Y-%m-%d')
                result['year'] = dt.year
                result['month'] = dt.month
                result['day'] = dt.day
                result['parsed'] = True
                return result
            except ValueError:
                continue
    
    # 无法解析，尝试提取年份
    year_match = re.search(r'(19|20)\d{2}', date_str)
    if year_match:
        result['year'] = int(year_match.group())
        result['standard'] = f"{result['year']}-00-00"  # 表示年份未知月份
        result['parsed'] = False  # 部分解析
    
    return result


def test_date_normalization():
    """测试日期标准化功能"""
    test_cases = [
        '2024-01-15',
        '2024/01/15',
        '01/15/2024',
        'Jan 2024',
        'January 2024',
        '2024 Jan',
        '2024',
        '2024-06',
        '15-Feb-2023',
        'invalid date',
        '1990',
    ]
    
    print("日期标准化测试")
    print("=" * 60)
    for date_input in test_cases:
        result = normalize_date(date_input)
        status = "✓" if result['parsed'] else "△"
        print(f"{status} 输入: {date_input}")
        print(f"  输出: {result['standard']}, 年: {result['year']}, 月: {result['month']}, 日: {result['day']}")
        print()


# ============ 作者机构标准化（基础） ============

def parse_author_string(author_str: str) -> List[Dict[str, str]]:
    """
    解析作者字符串为结构化数据
    
    Args:
        author_str: 作者字符串，JSON 格式或逗号分隔
        
    Returns:
        作者列表，每项包含 given, family, affiliation
    """
    if not author_str:
        return []
    
    authors = []
    
    # 如果是 JSON 格式
    if author_str.startswith('['):
        try:
            import json
            authors_list = json.loads(author_str)
            for a in authors_list:
                authors.append({
                    'given': a.get('given', ''),
                    'family': a.get('family', ''),
                    'affiliation': a.get('affiliation', ''),
                    'sequence': a.get('sequence', ''),
                })
            return authors
        except:
            pass
    
    # 逗号分隔的简单解析
    parts = author_str.split(',')
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        
        # 尝试分离 given 和 family name
        parts2 = part.split()
        if len(parts2) >= 2:
            authors.append({
                'given': ' '.join(parts2[:-1]),
                'family': parts2[-1],
                'affiliation': '',
                'sequence': 'first' if i == 0 else ('last' if i == len(parts) - 1 else 'middle'),
            })
        else:
            authors.append({
                'given': '',
                'family': part,
                'affiliation': '',
                'sequence': '',
            })
    
    return authors


def test_author_parsing():
    """测试作者解析功能"""
    test_cases = [
        '[{"given":"John","family":"Smith","affiliation":"MIT"}]',
        '[{"given":"Jane","family":"Doe"},{"given":"Bob","family":"Wilson"}]',
        'John Smith, Jane Doe',
        'Smith J, Doe J',
    ]
    
    print("作者解析测试")
    print("=" * 60)
    for author_input in test_cases:
        result = parse_author_string(author_input)
        print(f"输入: {author_input[:50]}")
        print(f"输出: {result}")
        print()


# ============ 主测试 ============

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("文本清洗工具测试")
    print("=" * 60 + "\n")
    
    test_html_cleaning()
    test_date_normalization()
    test_author_parsing()
