"""SQL Assignment Reviewer - standard-library-only Windows desktop app."""
from pathlib import Path
import csv
import json
import os
import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from engine import read_document, extract_answers, assess

BASE = Path(__file__).resolve().parent
ASSIGNMENTS = json.loads((BASE / 'resources' / 'assignments.json').read_text(encoding='utf-8'))


def data_directory():
    root = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share'))
    p = root / 'SQLAssignmentReviewer'
    p.mkdir(parents=True, exist_ok=True)
    return p


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY, assignment TEXT NOT NULL, path TEXT NOT NULL,
            name TEXT NOT NULL, source TEXT NOT NULL, warning TEXT NOT NULL,
            images INTEGER NOT NULL DEFAULT 0, UNIQUE(assignment,path));
        CREATE TABLE IF NOT EXISTS answers (
            submission INTEGER NOT NULL REFERENCES submissions(id), number INTEGER NOT NULL,
            query TEXT NOT NULL, score TEXT NOT NULL DEFAULT '', feedback TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(submission,number));
        ''')
        self.db.execute('PRAGMA foreign_keys=ON')

    def import_file(self, assignment, path, count):
        path = str(Path(path).resolve())
        if self.db.execute('SELECT id FROM submissions WHERE assignment=? AND path=?', (assignment,path)).fetchone():
            return False
        doc = read_document(path)
        answers, warning = extract_answers(doc.text, count)
        if not doc.text.strip():
            warning = 'No readable body text. This may be an image-only submission. Open the Word file to inspect it; OCR is not included.'
        with self.db:
            cur = self.db.execute('INSERT INTO submissions(assignment,path,name,source,warning,images) VALUES(?,?,?,?,?,?)', (assignment,path,Path(path).name,doc.text,warning,doc.images))
            for n in range(1,count+1):
                self.db.execute('INSERT INTO answers(submission,number,query) VALUES(?,?,?)', (cur.lastrowid,n,answers.get(n,'')))
        return True

    def save(self, sid, number, query, score, feedback):
        with self.db:
            self.db.execute('UPDATE answers SET query=?,score=?,feedback=? WHERE submission=? AND number=?', (query,score,feedback,sid,number))

    def remove(self, sid):
        with self.db:
            self.db.execute('DELETE FROM answers WHERE submission=?', (sid,))
            self.db.execute('DELETE FROM submissions WHERE id=?', (sid,))


def text_area(parent, height=10, readonly=False):
    frame = ttk.Frame(parent)
    text = tk.Text(frame, wrap='word', height=height, undo=not readonly,
                   font=('Consolas', 10), padx=8, pady=6)
    scroll = ttk.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    text.pack(fill='both', expand=True)
    if readonly:
        text.configure(state='disabled')
    return frame, text


def replace(text, value, readonly=False):
    text.configure(state='normal')
    text.delete('1.0','end')
    text.insert('1.0',value)
    text.edit_modified(False)
    if readonly:
        text.configure(state='disabled')


class AssignmentTab(ttk.Frame):
    def __init__(self, parent, app, assignment):
        super().__init__(parent, padding=10)
        self.app, self.a = app, assignment
        self.sid = self.number = None
        self.loading = False
        self.pending = None
        self.score = tk.StringVar()
        self.summary = tk.StringVar(value='Import student submissions to begin.')
        bar = ttk.Frame(self)
        bar.pack(fill='x', pady=(0,8))
        for label, command in [('Add files',self.add_files),('Load folder',self.add_folder),('Remove selected',self.remove),('Export grades',self.export)]:
            ttk.Button(bar,text=label,command=command).pack(side='left',padx=(0,6))
        self.recursive = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar,text='Include subfolders',variable=self.recursive).pack(side='left')
        ttk.Label(self,textvariable=self.summary).pack(fill='x',pady=(0,5))
        pane = ttk.Panedwindow(self,orient='horizontal')
        pane.pack(fill='both',expand=True)
        left = ttk.Frame(pane); pane.add(left,weight=1)
        ttk.Label(left,text='Submission files',font=('Segoe UI',11,'bold')).pack(anchor='w')
        file_frame = ttk.Frame(left); file_frame.pack(fill='both',expand=True)
        self.files = ttk.Treeview(file_frame,columns=('name','progress'),show='headings',selectmode='browse',height=8)
        self.files.heading('name',text='File'); self.files.heading('progress',text='Reviewed')
        self.files.column('name',width=215); self.files.column('progress',width=70,stretch=False)
        fs = ttk.Scrollbar(file_frame,command=self.files.yview); self.files.configure(yscrollcommand=fs.set)
        fs.pack(side='right',fill='y'); self.files.pack(fill='both',expand=True)
        self.files.bind('<<TreeviewSelect>>',self.select_file)
        self.files.bind('<Double-1>',self.open_clicked_file)
        ttk.Label(left,text='Questions',font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(10,0))
        self.questions = ttk.Treeview(left,columns=('q','suggested','final'),show='headings',height=10,selectmode='browse')
        for c,label,w in [('q','Question',75),('suggested','Suggested',80),('final','Final',65)]:
            self.questions.heading(c,text=label); self.questions.column(c,width=w,stretch=True)
        self.questions.pack(fill='both',expand=True)
        self.questions.bind('<<TreeviewSelect>>',self.select_question)
        right=ttk.Frame(pane); pane.add(right,weight=4)
        self.warning=tk.StringVar(value='All processing is local. SQL is never executed.')
        ttk.Label(right,textvariable=self.warning,wraplength=850,foreground='#854d0e').pack(fill='x',pady=(0,8))
        self.prompt=tk.StringVar(value='Choose a submission and question.')
        ttk.Label(right,textvariable=self.prompt,wraplength=850,font=('Segoe UI',11,'bold')).pack(fill='x',pady=(0,8))
        self.book=ttk.Notebook(right); self.book.pack(fill='both',expand=True)
        review=ttk.Frame(self.book,padding=6); self.book.add(review,text='Review answer')
        ttk.Label(review,text='Student SQL - editable; changes save locally').pack(anchor='w')
        f,self.query=text_area(review,9); f.pack(fill='both',expand=True)
        self.query.bind('<<Modified>>',self.edited)
        row=ttk.Frame(review); row.pack(fill='x',pady=8)
        ttk.Label(row,text='Final mark:').pack(side='left')
        scorebox=ttk.Combobox(row,textvariable=self.score,values=('','0','1','2'),state='readonly',width=6)
        scorebox.pack(side='left',padx=8); scorebox.bind('<<ComboboxSelected>>',self.score_changed)
        ttk.Button(row,text='Save / refresh hints',command=self.save_refresh).pack(side='left',padx=5)
        ttk.Button(row,text='Save & next question',command=self.next_question).pack(side='left',padx=5)
        ttk.Label(review,text='Instructor feedback').pack(anchor='w')
        f,self.feedback=text_area(review,3); f.pack(fill='x'); self.feedback.bind('<<Modified>>',self.edited)
        ttk.Label(review,text='Offline hints - suggested marks require instructor review').pack(anchor='w',pady=(8,0))
        f,self.hints=text_area(review,6,True); f.pack(fill='both',expand=True)
        f,self.key=text_area(self.book,15,True); self.book.add(f,text='Reference solution')
        source_frame=ttk.Frame(self.book,padding=5); self.book.add(source_frame,text='Source text / remap')
        ttk.Label(source_frame,text='Select SQL below, then assign it to the current question. Images require opening the original document.').pack(anchor='w')
        tools=ttk.Frame(source_frame); tools.pack(fill='x',pady=5)
        ttk.Button(tools,text='Assign selected text to question',command=self.assign_selection).pack(side='left',padx=3)
        ttk.Button(tools,text='Open original document',command=self.open_original).pack(side='left',padx=3)
        f,self.source=text_area(source_frame,20,True); f.pack(fill='both',expand=True)
        f,instructions=text_area(self.book,20,True); self.book.add(f,text='Assignment instructions')
        replace(instructions,assignment['instructions'],True)
        rubric=ttk.Frame(self.book,padding=15); self.book.add(rubric,text='Rubric & limits')
        ttk.Label(rubric,justify='left',wraplength=750,text=(
            'FINAL MARKS\n0 - Incorrect or missing (verify the source first).\n1 - Partially correct; explain what earns credit.\n2 - Correct; valid alternative solutions are accepted by instructor review.\n\n'
            'SUGGESTIONS\n2 - Text matches the key after conservative normalization.\n1 - Different text: placeholder for review, not proof of partial credit.\n0 - No extracted SQL: may be a matching failure rather than a missing answer.\n\n'
            'No SQL is executed. No internet or AI service is used. Pattern hints cannot establish syntax, logical equivalence, joins, output columns, or correctness. Screenshots are not read and receive no automatic marks.\n\n'
            'Verify the extracted question mapping. Read the reference and source. Choose a final mark manually and add feedback. Only final marks count toward totals. Export leaves totals blank until every question has a final mark.\n\n' + assignment.get('note',''))).pack(anchor='nw')
        self.refresh_files()

    def refresh_files(self):
        selected=str(self.sid) if self.sid else None
        rows=self.app.store.db.execute('''SELECT s.id,s.name,COUNT(CASE WHEN a.score != '' THEN 1 END) reviewed
            FROM submissions s LEFT JOIN answers a ON a.submission=s.id
            WHERE s.assignment=? GROUP BY s.id ORDER BY s.name COLLATE NOCASE''',(self.a['id'],)).fetchall()
        for item in self.files.get_children(): self.files.delete(item)
        for r in rows:
            self.files.insert('', 'end',iid=str(r['id']),values=(r['name'],f"{r['reviewed']}/{len(self.a['questions'])}"))
        if selected and self.files.exists(selected): self.files.selection_set(selected)
        self.summary.set(f"{len(rows)} file(s) | {len(self.a['questions'])} questions | maximum {2*len(self.a['questions'])} marks | saved automatically")

    def add_files(self):
        paths=filedialog.askopenfilenames(title='Select student submissions',filetypes=[('Supported submissions','*.docx *.sql *.txt'),('Word documents','*.docx'),('All files','*.*')])
        self.import_paths(paths)

    def add_folder(self):
        directory=filedialog.askdirectory(title='Choose folder containing student submissions')
        if not directory: return
        folder=Path(directory)
        try:
            paths=sorted(p for p in (folder.rglob('*') if self.recursive.get() else folder.iterdir()) if p.is_file() and p.suffix.lower() in ('.docx','.sql','.txt') and not p.name.startswith('~$'))
        except OSError as e:
            messagebox.showerror('Cannot read folder',str(e)); return
        self.import_paths(paths)

    def import_paths(self, paths):
        self.flush(); errors=[]; added=skipped=0
        for path in paths:
            if Path(path).name.startswith('~$'): continue
            try:
                if self.app.store.import_file(self.a['id'],path,len(self.a['questions'])): added+=1
                else: skipped+=1
            except Exception as e: errors.append(f'{Path(path).name}: {e}')
        self.refresh_files()
        if paths:
            messagebox.showinfo('Import complete',f'{added} imported. {skipped} already present (existing reviews preserved).\n'+ ('\n'.join(errors) if errors else 'Verify question matches before marking.'))
        if not self.sid and self.files.get_children(): self.files.selection_set(self.files.get_children()[0])

    def select_file(self,event=None):
        selection=self.files.selection()
        if not selection or int(selection[0])==self.sid: return
        self.flush(); self.sid=int(selection[0]); self.number=None
        row=self.app.store.db.execute('SELECT * FROM submissions WHERE id=?',(self.sid,)).fetchone()
        self.warning.set(row['warning'] + f"  Embedded image objects: {row['images']} (not assessed).")
        replace(self.source,row['source'],True)
        self.refresh_questions()
        self.questions.selection_set('1')

    def refresh_questions(self):
        if not self.sid: return
        for item in self.questions.get_children(): self.questions.delete(item)
        for r in self.app.store.db.execute('SELECT * FROM answers WHERE submission=? ORDER BY number',(self.sid,)):
            q=self.a['questions'][r['number']-1]
            suggested,_=assess(self.a['id'],r['number'],r['query'],q['answer'])
            self.questions.insert('','end',iid=str(r['number']),values=(f"Q{r['number']}",suggested,r['score'] or '-'))
        if self.number: self.questions.selection_set(str(self.number))

    def select_question(self,event=None):
        selection=self.questions.selection()
        if not selection or int(selection[0])==self.number: return
        self.flush(); self.number=int(selection[0]); self.loading=True
        row=self.app.store.db.execute('SELECT * FROM answers WHERE submission=? AND number=?',(self.sid,self.number)).fetchone()
        q=self.a['questions'][self.number-1]
        self.prompt.set(f"Q{self.number}. {q['prompt']}")
        replace(self.query,row['query']); replace(self.feedback,row['feedback']); replace(self.key,q['answer'],True)
        self.score.set(row['score']); self.loading=False; self.update_hints()

    def edited(self,event):
        if not event.widget.edit_modified(): return
        event.widget.edit_modified(False)
        if self.loading or not self.sid or not self.number: return
        # A changed query invalidates any previously confirmed score.
        if event.widget is self.query: self.score.set('')
        if self.pending: self.after_cancel(self.pending)
        self.pending=self.after(500,self.save_refresh)

    def score_changed(self,event=None):
        self.flush(); self.refresh_files(); self.refresh_questions()

    def flush(self):
        if self.pending:
            self.after_cancel(self.pending); self.pending=None
        if self.sid and self.number and not self.loading:
            self.app.store.save(self.sid,self.number,self.query.get('1.0','end-1c'),self.score.get(),self.feedback.get('1.0','end-1c'))

    def update_hints(self):
        if not self.number: return
        suggestion,details=assess(self.a['id'],self.number,self.query.get('1.0','end-1c'),self.a['questions'][self.number-1]['answer'])
        replace(self.hints,f'Suggested: {suggestion}/2 (unconfirmed)\n'+details,True)

    def save_refresh(self):
        self.flush(); self.update_hints(); self.refresh_questions(); self.refresh_files()

    def next_question(self):
        if not self.number: return
        n=self.number; self.save_refresh()
        if n<len(self.a['questions']): self.questions.selection_set(str(n+1))

    def assign_selection(self):
        if not self.sid or not self.number: return
        try: selection=self.source.get('sel.first','sel.last')
        except tk.TclError:
            messagebox.showinfo('Select SQL first','Highlight a query in the Source text tab, then assign it.'); return
        if self.query.get('1.0','end-1c').strip() and not messagebox.askyesno('Replace extracted SQL?',f'Replace Q{self.number} SQL and clear its final mark?'): return
        replace(self.query,selection); self.score.set(''); self.save_refresh(); self.book.select(0)

    def open_clicked_file(self,event):
        # Resolve the clicked row instead of trusting a previous selection.
        item=self.files.identify_row(event.y)
        if item and self.files.identify_region(event.x,event.y) in ('cell','tree'):
            self.files.selection_set(item)
            self.select_file()
            self.open_original()
        return 'break'

    def open_original(self):
        if not self.sid: return
        path=self.app.store.db.execute('SELECT path FROM submissions WHERE id=?',(self.sid,)).fetchone()['path']
        if not Path(path).exists(): messagebox.showerror('File missing','The original document has moved. Extracted text is still saved.'); return
        if sys.platform=='win32':
            try: os.startfile(path)
            except OSError as e: messagebox.showerror('Cannot open document',str(e))
        else: messagebox.showinfo('Original document',path)

    def remove(self):
        if not self.sid: return
        if not messagebox.askyesno('Remove from review?','Remove this imported copy and its saved marks? The original file is kept.'): return
        self.flush(); self.app.store.remove(self.sid); self.sid=self.number=None
        for widget in (self.query,self.feedback): replace(widget,'')
        for widget in (self.source,self.key,self.hints): replace(widget,'',True)
        self.score.set(''); self.prompt.set('Choose a submission and question.'); self.warning.set('All processing is local.')
        for item in self.questions.get_children(): self.questions.delete(item)
        self.refresh_files()

    def export(self):
        self.flush()
        path=filedialog.asksaveasfilename(title='Export final marks',defaultextension='.csv',initialfile=f"Assignment_{self.a['id']}_grades.csv",filetypes=[('CSV','*.csv')])
        if not path: return
        try:
            export_csv(self.app.store,self.a,path)
        except OSError as e: messagebox.showerror('Export failed',str(e)); return
        messagebox.showinfo('Export saved','Final marks exported. Unreviewed questions and incomplete totals are blank. Suggested marks are excluded.')


def safe_cell(value):
    # Prevent spreadsheet formula injection from filenames and instructor text.
    s=str(value)
    return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s


def export_csv(store, assignment, path):
    count=len(assignment['questions'])
    with open(path,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f)
        w.writerow(['File']+[f'Q{i} / 2' for i in range(1,count+1)]+['Reviewed','Total','Maximum','Status']+[f'Q{i} feedback' for i in range(1,count+1)])
        for sub in store.db.execute('SELECT * FROM submissions WHERE assignment=? ORDER BY name',(assignment['id'],)):
            rows=store.db.execute('SELECT * FROM answers WHERE submission=? ORDER BY number',(sub['id'],)).fetchall()
            marks=[r['score'] for r in rows]; reviewed=sum(m!='' for m in marks)
            total=sum(int(m) for m in marks) if reviewed==count else ''
            w.writerow([safe_cell(sub['name'])]+marks+[f'{reviewed}/{count}',total,count*2,'Complete' if reviewed==count else 'Needs review']+[safe_cell(r['feedback']) for r in rows])


class App(tk.Tk):
    def __init__(self, dbpath=None):
        super().__init__()
        self.title('SQL Assignment Reviewer | Offline')
        self.geometry('1350x900'); self.minsize(1050,720)
        style=ttk.Style(self)
        if 'vista' in style.theme_names(): style.theme_use('vista')
        elif 'clam' in style.theme_names(): style.theme_use('clam')
        style.configure('TButton',padding=(9,5)); style.configure('Treeview',rowheight=26)
        style.configure('TNotebook.Tab',padding=(18,8))
        ttk.Label(self,text='SQL Assignment Reviewer',font=('Segoe UI',19,'bold'),padding=(15,10)).pack(anchor='w')
        ttk.Label(self,text='OFFLINE  |  No AI service  |  No query execution  |  Final marks confirmed by you',padding=(15,0,15,10)).pack(anchor='w')
        self.store=Store(dbpath or data_directory()/'reviews.sqlite3')
        book=ttk.Notebook(self); book.pack(fill='both',expand=True,padx=10)
        self.tabs=[]
        for a in ASSIGNMENTS:
            tab=AssignmentTab(book,self,a); self.tabs.append(tab); book.add(tab,text=a['title'])
        ttk.Label(self,text=f"Saved locally: {dbpath or data_directory()/'reviews.sqlite3'}",padding=8).pack(anchor='w')
        self.protocol('WM_DELETE_WINDOW',self.close)

    def close(self):
        for tab in self.tabs: tab.flush()
        self.store.db.close(); self.destroy()


if __name__=='__main__':
    try:
        App().mainloop()
    except Exception:
        import traceback
        log=data_directory()/'error.log'
        log.write_text(traceback.format_exc(),encoding='utf-8')
        messagebox.showerror('SQL Reviewer error',f'Could not run the app. Details saved to:\n{log}')
        raise
