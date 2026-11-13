"""Run with a display: python tests/gui_smoke.py (from app folder)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tempfile
from unittest.mock import patch
from types import SimpleNamespace
from app import App, ASSIGNMENTS

with tempfile.TemporaryDirectory() as d:
    db=Path(d)/'gui.sqlite3'
    app=App(db)
    app.update()
    for tab,a in zip(app.tabs,ASSIGNMENTS):
        app.nametowidget(tab.winfo_parent()).select(tab); app.update()
        p=Path('resources')/(a['title']+' Key.sql')
        assert app.store.import_file(a['id'],p,len(a['questions']))
        tab.refresh_files()
        tab.files.selection_set(tab.files.get_children()[0])
        app.update()
        assert tab.sid is not None and tab.number==1
        assert 'Suggested: 2' in tab.hints.get('1.0','end')
        assert tab.files.bind('<Double-1>')
        # Double click opens the clicked original using the Windows association.
        x,y,w,h=tab.files.bbox(str(tab.sid))
        with patch('app.sys.platform','win32'), patch('app.os.startfile',create=True) as launch:
            tab.open_clicked_file(SimpleNamespace(x=x+10,y=y+h//2))
            launch.assert_called_once_with(str(p.resolve()))
            launch.reset_mock()
            tab.open_clicked_file(SimpleNamespace(x=x+10,y=5))
            launch.assert_not_called()
        tab.score.set('2'); tab.score_changed(); app.update()
        tab.feedback.insert('end','Reviewed correct.')
        app.update(); tab.flush()
        tab.next_question(); app.update()
        assert tab.number==2
        tab.questions.selection_set('1'); app.update()
        assert tab.score.get()=='2'
        assert tab.feedback.get('1.0','end-1c')=='Reviewed correct.'
        tab.query.insert('end','\nSELECT 999;')
        app.update(); tab.flush()
        assert tab.score.get()==''
        assert tab.app.store.db.execute('SELECT score FROM answers WHERE submission=? AND number=1',(tab.sid,)).fetchone()[0]==''
        # Manual mapping from original source to current question.
        tab.source.tag_add('sel','1.0','1.20')
        with patch('app.messagebox.askyesno',return_value=True): tab.assign_selection()
        app.update()
        assert tab.query.get('1.0','end-1c')==tab.source.get('1.0','1.20')
    app.close()
    app=App(db); app.update()
    assert all(len(tab.files.get_children())==1 for tab in app.tabs)
    app.close()
print('GUI smoke passed: four tabs, selection, hints, score/feedback persistence, query invalidation, remapping, double-click opening and reopen.')
