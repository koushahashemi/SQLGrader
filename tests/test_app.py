import csv
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from engine import assess, canonical, extract_answers, read_document
from app import Store, export_csv, ASSIGNMENTS


class EngineTests(unittest.TestCase):
    def test_reference_roundtrip(self):
        for a in ASSIGNMENTS:
            raw=(Path('resources') / (a['title']+' Key.sql')).read_text(encoding='utf-8-sig')
            candidates,warning=extract_answers(raw,len(a['questions']))
            self.assertEqual(len(candidates),len(a['questions']))
            for q in a['questions']:
                self.assertEqual(assess(a['id'],q['number'],candidates[q['number']],q['answer'])[0],'2')

    def test_normalization_preserves_strings(self):
        self.assertEqual(canonical('SELECT COUNT(*) FROM [Orders]; -- note'),canonical('select count ( * ) from orders'))
        self.assertNotEqual(canonical("SELECT 'USA'"),canonical("SELECT 'usa'"))
        self.assertEqual(canonical("SELECT 'a--b', '/* literal */'"),['select',"'a--b'",',',"'/* literal */'"])
        self.assertNotEqual(canonical('SELECT 1; SELECT 2'),canonical('SELECT 1'))

    def test_alternative_remains_review(self):
        suggestion,detail=assess('9',4,"SELECT COALESCE(Region, 'Unknown') FROM Customers WHERE Country='USA'",ASSIGNMENTS[3]['questions'][3]['answer'])
        self.assertEqual(suggestion,'1')
        self.assertIn('NOT a finding',detail)
        self.assertIn('Seen: NULL handling',detail)

    def test_numbered_and_inline(self):
        found,_=extract_answers('Question 1: SELECT COUNT(*) FROM Orders;\nQuestion 2\nSELECT AVG(UnitPrice) FROM Products;',2)
        self.assertTrue(found[1].startswith('SELECT COUNT'))
        self.assertTrue(found[2].startswith('SELECT AVG'))

    def test_ambiguous_does_not_guess(self):
        found,w=extract_answers('SELECT 1;',10)
        self.assertEqual(found,{})
        self.assertIn('Could not reliably match',w)

    def test_duplicate_labels_flagged(self):
        found,w=extract_answers('Q1\nSELECT 1;\nQ1\nSELECT 2;',2)
        self.assertIn('Duplicate',w)
        self.assertIn('SELECT 2',found[1])

    def test_docx_tables_images_and_no_code_execution(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'submission.docx'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Q1</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>SELECT 1;</w:t><w:br/><w:t>-- note</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:drawing/></w:r></w:p></w:body></w:document>''')
            doc=read_document(p)
            self.assertIn('SELECT 1;\n-- note',doc.text)
            self.assertEqual(doc.images,1)

    def test_actual_instructions(self):
        for a in ASSIGNMENTS:
            doc=read_document(Path('resources')/(a['title']+'.docx'))
            self.assertIn('Questions',doc.text)
            self.assertIn(a['questions'][0]['prompt'],doc.text)


class PersistenceTests(unittest.TestCase):
    def test_import_save_reopen_export_and_remove(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'=student.sql'; p.write_text('Q1\nSELECT COUNT(*) FROM Orders;')
            db=root/'grades.db'; store=Store(db); a=ASSIGNMENTS[0]
            self.assertTrue(store.import_file('5',p,10))
            self.assertFalse(store.import_file('5',p,10))
            sid=store.db.execute('SELECT id FROM submissions').fetchone()[0]
            store.save(sid,1,'SELECT COUNT(*) FROM Orders;','2','=badformula')
            store.db.close(); store=Store(db)
            self.assertEqual(store.db.execute('SELECT score FROM answers WHERE number=1').fetchone()[0],'2')
            out=root/'export.csv'; export_csv(store,a,out)
            with out.open(encoding='utf-8-sig') as f: rows=list(csv.reader(f))
            self.assertTrue(rows[1][0].startswith("'="))
            self.assertEqual(rows[1][1],'2'); self.assertEqual(rows[1][2],'')
            self.assertEqual(rows[1][12],'') # incomplete total
            self.assertTrue(rows[1][15].startswith("'="))
            for n in range(2,11): store.save(sid,n,'SELECT 1','1','reviewed')
            export_csv(store,a,out)
            with out.open(encoding='utf-8-sig') as f: rows=list(csv.reader(f))
            self.assertEqual(rows[1][12],'11')
            store.remove(sid)
            self.assertEqual(store.db.execute('SELECT COUNT(*) FROM answers').fetchone()[0],0)
            self.assertTrue(p.exists()); store.db.close()

if __name__=='__main__': unittest.main()
