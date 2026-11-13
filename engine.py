"""Offline document extraction and conservative review hints. Never executes SQL."""
from dataclasses import dataclass
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
MAX_BYTES = 25 * 1024 * 1024

@dataclass
class Document:
    text: str
    images: int = 0


def read_document(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('File exceeds the 25 MB limit.')
    if path.suffix.lower() == '.docx':
        with zipfile.ZipFile(path) as z:
            if sum(i.file_size for i in z.infolist()) > 100 * 1024 * 1024:
                raise ValueError('Uncompressed document exceeds the 100 MB limit.')
            root = ET.fromstring(z.read('word/document.xml'))
            # Paragraph order includes text inside tables. Automatic Word numbering
            # is not converted to question IDs: it can number unrelated lists.
            lines = []
            for p in root.findall('.//w:p', NS):
                parts = []
                for e in p.iter():
                    if e.tag == '{%s}t' % NS['w']:
                        parts.append(e.text or '')
                    elif e.tag in ('{%s}br' % NS['w'], '{%s}cr' % NS['w']):
                        parts.append('\n')
                    elif e.tag == '{%s}tab' % NS['w']:
                        parts.append('\t')
                lines.append(''.join(parts))
            return Document('\n'.join(lines), len(root.findall('.//w:drawing', NS)) + len(root.findall('.//w:pict', NS)))
    if path.suffix.lower() not in ('.sql', '.txt'):
        raise ValueError('Supported formats: .docx, .sql, .txt. Save old .doc files as .docx in Word.')
    raw = path.read_bytes()
    for enc in ('utf-8-sig', 'utf-16', 'cp1252'):
        try:
            return Document(raw.decode(enc))
        except UnicodeError:
            pass
    raise ValueError('Cannot decode this text file.')


# Tokenizer preserves strings/identifiers while removing comments. This avoids
# changing literals such as USA, or treating comment text as SQL requirements.
TOKEN = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/|N?'(?:''|[^'])*'|\[(?:\]\]|[^\]])*\]|\"(?:\"\"|[^\"])*\"|@[\w]+|[\w]+|>=|<=|<>|!=|[^\s]", re.I)

def tokens(sql):
    result = []
    for m in TOKEN.finditer(sql):
        t = m.group()
        if t.startswith(('--', '/*')):
            continue
        if t.startswith("'") or t[:2].lower() == "n'":
            result.append(t)
        elif t.startswith('['):
            result.append(t[1:-1].replace(']]', ']').casefold())
        elif t.startswith('"'):
            result.append(t[1:-1].replace('""', '"').casefold())
        else:
            result.append(t.casefold())
    return result


def canonical(sql):
    ts = tokens(sql)
    while ts and ts[-1] in (';', 'go'):
        ts.pop()
    return ts

START = re.compile(r'(?im)^\s*(?:select\b|with\b|create\s+(?:or\s+alter\s+)?proc(?:edure)?\b|alter\s+proc(?:edure)?\b|declare\b|update\b|insert\b|delete\b|use\b|set\s+nocount\b)')
HEADING = re.compile(r'(?im)^\s*(?:--\s*)?(?:(?:question|query|answer|q)\s*#?\s*(\d{1,2})\s*(?:[.):\-]|$)?|(\d{1,2})\s*[.):\-])[^\n]*$')


def extract_answers(text, count):
    """Return candidates and a mapping warning. Never silently finalize matches."""
    heads = list(HEADING.finditer(text))
    valid = [h for h in heads if 1 <= int(h.group(1) or h.group(2)) <= count]
    if valid:
        answers = {}
        duplicate = False
        for i, h in enumerate(valid):
            number = int(h.group(1) or h.group(2))
            section = text[h.end():valid[i+1].start() if i+1<len(valid) else len(text)]
            # A query can start on the same line as its label.
            line = h.group()
            inline = None if line.lstrip().startswith('--') else re.search(r'\b(SELECT\s+(?:DISTINCT\s+)?[\w@*\[(]|WITH\s+\w+\s+AS\s*\(|CREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\b|ALTER\s+PROC(?:EDURE)?\b|DECLARE\s+@|UPDATE\s+\S+\s+SET\b|INSERT\s+(?:INTO\s+)?\S+\s*\(|DELETE\s+FROM\b)', line, re.I)
            if inline:
                section = line[inline.start():] + '\n' + section
            start = START.search(section)
            candidate = section[start.start():].strip() if start else ''
            if number in answers:
                duplicate = True
                answers[number] += '\n\n-- Duplicate question label: inspect source\n' + candidate
            else:
                answers[number] = candidate
        warning = 'Matched explicit question labels. Verify every match; trailing prose may be included.'
        if duplicate:
            warning += ' Duplicate labels found.'
        return answers, warning
    # SQL stored procedures and ordinary queries need different boundaries.
    starts = list(re.finditer(r'(?im)^\s*(?:create\s+(?:or\s+alter\s+)?|alter\s+)proc(?:edure)?\b', text))
    if starts:
        chunks = [text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)].strip() for i,m in enumerate(starts)]
    else:
        # Only a top-level SELECT at line start is a fallback boundary. Indented
        # nested SELECTs and multi-line CTEs are ambiguous: instructor must remap.
        starts = list(re.finditer(r'(?im)^(?:SELECT|WITH)\b', text))
        chunks = [text[m.start():starts[i+1].start() if i+1<len(starts) else len(text)].strip() for i,m in enumerate(starts)]
    if len(chunks) == count:
        return dict(enumerate(chunks,1)), 'Unnumbered answers assigned in document order. Check all matches, especially subqueries and CTEs.'
    return {}, f'Could not reliably match {count} questions (found {len(chunks)} possible blocks). Use Source text and assign selected text to each question. Blank candidates do NOT prove a missing submission.'


# Hints are intentionally broad. Presence of a token is not proof of correctness.
RULES = {
 '5': [ [('COUNT',r'\bcount\s*\('),('Orders table',r'\borders\b')],
 [('AVG(UnitPrice)',r'\bavg\s*\([^)]*unitprice'),('Products table',r'\bproducts\b')],
 [('MIN and MAX',r'\bmin\s*\([\s\S]*\bmax\s*\('),('UnitPrice',r'\bunitprice\b')],
 [('SUM(Quantity)',r'\bsum\s*\([^)]*quantity'),('Order Details',r'order details')],
 [('SUM',r'\bsum\s*\('),('Price and quantity',r'unitprice[\s\S]*quantity|quantity[\s\S]*unitprice')],
 [('SUM',r'\bsum\s*\('),('GROUP BY',r'\bgroup by\b'),('ProductID',r'\bproductid\b')],
 [('COUNT',r'\bcount\s*\('),('GROUP BY',r'\bgroup by\b'),('CustomerID',r'\bcustomerid\b')],
 [('HAVING',r'\bhaving\b'),('COUNT',r'\bcount\s*\('),('Threshold > 5',r'>\s*5\b')],
 [('AVG',r'\bavg\s*\('),('Subquery SELECT',r'\([\s\S]*\bselect\b'),('Greater than',r'>')],
 [('ProductName',r'\bproductname\b'),('Price * stock',r'unitprice\s*\*\s*(?:\w+\s*\.\s*)?unitsinstock|unitsinstock\s*\*\s*(?:\w+\s*\.\s*)?unitprice')]],
 '7': [[('Customers and Orders',r'customers[\s\S]*orders|orders[\s\S]*customers'),('JOIN',r'\bjoin\b'),('CompanyName and OrderDate',r'companyname[\s\S]*orderdate|orderdate[\s\S]*companyname')],
 [('JOIN',r'\bjoin\b'),('Freight > 50',r'freight\s*>\s*50\b'),('CompanyName',r'\bcompanyname\b')],
 [('JOIN',r'\bjoin\b'),('CompanyName and OrderDate',r'companyname[\s\S]*orderdate|orderdate[\s\S]*companyname')],
 [('Customers',r'\bcustomers\b'),('Orders',r'\borders\b'),('Order Details',r'order details'),('Products',r'\bproducts\b')],
 [('ProductName',r'\bproductname\b'),('Quantity',r'\bquantity\b'),('JOIN',r'\bjoin\b')],
 [('ProductName',r'\bproductname\b'),('UnitPrice * UnitsInStock',r'unitprice[\s\S]*\*[\s\S]*unitsinstock|unitsinstock[\s\S]*\*[\s\S]*unitprice')],
 [('SUM',r'\bsum\s*\('),('GROUP BY',r'\bgroup by\b'),('CompanyName',r'\bcompanyname\b'),('Quantity and UnitPrice',r'quantity[\s\S]*unitprice|unitprice[\s\S]*quantity')],
 [('SUM(Quantity)',r'\bsum\s*\([^)]*quantity'),('HAVING',r'\bhaving\b'),('Threshold > 100',r'>\s*100\b')],
 [('OrderDate',r'\borderdate\b'),('1997 date boundary',r'1997'),('Date comparison',r'>')],
 [('Top ten / ranking',r'\btop\s*\(?\s*10\b|\bfetch\b|\brow_number\b|\brank\b'),('SUM',r'\bsum\s*\('),('Descending order',r'\bdesc\b')]],
 '8': [[('Stored procedure',r'\b(?:create|alter)\b[\s\S]*\bproc(?:edure)?\b'),('Products',r'\bproducts\b'),('Three requested columns',r'productname[\s\S]*unitprice[\s\S]*unitsinstock')],
 [('Stored procedure',r'\bproc(?:edure)?\b'),('Parameter',r'@'),('CustomerID filter',r'\bwhere\b[\s\S]*customerid'),('Order fields',r'orderid[\s\S]*orderdate[\s\S]*freight')],
 [('Stored procedure',r'\bproc(?:edure)?\b'),('Parameter',r'@'),('Category filter',r'\bwhere\b[\s\S]*categoryid'),('ProductName and UnitPrice',r'productname[\s\S]*unitprice')],
 [('UPDATE',r'\bupdate\b'),('Price SET',r'\bset\b[\s\S]*unitprice'),('ProductID filter',r'\bwhere\b[\s\S]*productid'),('Parameters',r'@')],
 [('Products insertion',r'\binsert\b[\s\S]*\bproducts\b'),('Order Details insertion',r'\binsert\b[\s\S]*order details'),('Order 11012',r'\b11012\b'),('Generated ID',r'\bscope_identity\b|\boutput\b[\s\S]*inserted'),('Parameters',r'@')]],
 '9': [[('CompanyName',r'companyname'),('UPPER',r'\bupper\s*\('),('LEN',r'\blen\s*\(')],
 [('OrderID and date',r'orderid[\s\S]*orderdate'),('Year expression',r'\byear\s*\(|\bdatepart\s*\('),('1997 filter',r'\bwhere\b[\s\S]*1997')],
 [('ProductName',r'productname'),('ROUND',r'\bround\s*\('),('Price > 20',r'unitprice\s*>\s*20\b')],
 [('CustomerID and CompanyName',r'customerid[\s\S]*companyname'),('NULL handling',r'\bisnull\s*\(|\bcoalesce\s*\(|\bcase\b'),('Unknown replacement',r"'Unknown'"),('USA filter',r"\bwhere\b[\s\S]*'USA'")],
 [('ProductName and UnitPrice',r'productname[\s\S]*unitprice'),('Price arithmetic',r'\*|\+'),('Descending order',r'\border by\b[\s\S]*\bdesc\b')]]
}


def assess(assignment, number, query, reference):
    if not canonical(query):
        return '0', 'No query extracted. Verify the source before marking it missing.'
    if canonical(query) == canonical(reference):
        return '2', 'Matches the supplied key after removing comments, formatting and identifier case. Still confirm question mapping; no SQL was executed.'
    # Join token text for patterns, retaining literals exactly.
    normalized = ' '.join(tokens(query))
    checks = RULES[assignment][number-1]
    lines = ['Provisional 1 = review needed, NOT a finding that this answer earns partial credit.',
             'Different SQL may be fully correct. These are text-pattern hints, not SQL validation.']
    for label, pattern in checks:
        found = bool(re.search(pattern, normalized, re.I))
        lines.append(('Seen: ' if found else 'Check manually: ') + label)
    lines.append('Inspect output columns, join conditions, filters, aggregation, syntax and alternative approaches before choosing 0/1/2.')
    return '1', '\n'.join(lines)
