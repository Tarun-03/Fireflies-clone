"""Maintain search projections and temporal/reference invariants."""

from alembic import op

revision = "b13d2f984f6a"
down_revision = "af0016f7371b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE VIRTUAL TABLE search_documents_fts USING fts5(text, conten"
        "t='search_documents', content_rowid='id', tokenize='unicode61')"
    )
    op.execute(
        "CREATE TRIGGER search_insert AFTER INSERT ON search_documents BEG"
        "IN INSERT INTO search_documents_fts(rowid,text) VALUES(new.id,new"
        ".text); END"
    )
    op.execute(
        "CREATE TRIGGER search_delete AFTER DELETE ON search_documents BEG"
        "IN INSERT INTO search_documents_fts(search_documents_fts,rowid,te"
        "xt) VALUES('delete',old.id,old.text); END"
    )
    op.execute(
        "CREATE TRIGGER search_update AFTER UPDATE OF text ON search_docum"
        "ents BEGIN INSERT INTO search_documents_fts(search_documents_fts,"
        "rowid,text) VALUES('delete',old.id,old.text); INSERT INTO search_"
        "documents_fts(rowid,text) VALUES(new.id,new.text); END"
    )
    op.execute(
        "CREATE TRIGGER meeting_search_insert AFTER INSERT ON meetings BEG"
        "IN INSERT INTO search_documents(public_id,workspace_id,meeting_id"
        ",kind,text) VALUES(new.id,new.workspace_id,new.id,'title',new.tit"
        "le); END"
    )
    op.execute(
        "CREATE TRIGGER meeting_search_update AFTER UPDATE OF title ON mee"
        "tings BEGIN UPDATE search_documents SET text=new.title WHERE publ"
        "ic_id=new.id AND kind='title'; END"
    )
    op.execute(
        "CREATE TRIGGER segment_search_insert AFTER INSERT ON transcript_s"
        "egments BEGIN INSERT INTO search_documents(public_id,workspace_id"
        ",meeting_id,segment_id,kind,text) VALUES(new.public_id,new.worksp"
        "ace_id,new.meeting_id,new.public_id,'transcript',new.text); END"
    )
    op.execute(
        "CREATE TRIGGER segment_search_update AFTER UPDATE OF text ON tran"
        "script_segments BEGIN UPDATE search_documents SET text=new.text W"
        "HERE public_id=new.public_id AND kind='transcript'; END"
    )
    op.execute(
        "CREATE TRIGGER segment_cleanup BEFORE DELETE ON transcript_segmen"
        "ts BEGIN\nDELETE FROM comments WHERE segment_id=old.public_id;\nDEL"
        "ETE FROM highlights WHERE segment_id=old.public_id;\nDELETE FROM s"
        "earch_documents WHERE segment_id=old.public_id;\nUPDATE summary_po"
        "ints SET source_segment_id=NULL WHERE source_segment_id=old.publi"
        "c_id;\nUPDATE action_items SET source_segment_id=NULL WHERE source"
        "_segment_id=old.public_id;\nUPDATE chat_citations SET segment_id=N"
        "ULL WHERE segment_id=old.public_id;\nEND"
    )
    op.execute(
        "CREATE TRIGGER meeting_cleanup BEFORE DELETE ON meetings BEGIN UP"
        "DATE activity_events SET meeting_id=NULL, text='A meeting was del"
        "eted' WHERE meeting_id=old.id; END"
    )
    op.execute(
        "CREATE TRIGGER meeting_duration_update BEFORE UPDATE OF duration_"
        "ms ON meetings WHEN EXISTS(SELECT 1 FROM transcript_segments WHER"
        "E meeting_id=old.id AND end_ms>new.duration_ms) OR EXISTS(SELECT "
        "1 FROM chapters WHERE meeting_id=old.id AND end_ms>new.duration_m"
        "s) OR EXISTS(SELECT 1 FROM soundbites WHERE meeting_id=old.id AND"
        " end_ms>new.duration_ms) BEGIN SELECT RAISE(ABORT,'duration trunc"
        "ates content'); END"
    )
    op.execute(
        "CREATE TRIGGER segment_highlight_update BEFORE UPDATE OF text ON "
        "transcript_segments WHEN EXISTS(SELECT 1 FROM highlights WHERE se"
        "gment_id=old.public_id AND (end_offset>length(new.text) OR select"
        "ed_text<>substr(new.text,start_offset+1,end_offset-start_offset))"
        ") BEGIN SELECT RAISE(ABORT,'highlight requires explicit invalidat"
        "ion'); END"
    )
    op.execute(
        "CREATE TRIGGER transcript_segments_bounds_insert BEFORE INSERT ON"
        " transcript_segments WHEN new.end_ms>(SELECT duration_ms FROM mee"
        "tings WHERE id=new.meeting_id AND workspace_id=new.workspace_id) "
        "BEGIN SELECT RAISE(ABORT,'interval exceeds duration'); END"
    )
    op.execute(
        "CREATE TRIGGER transcript_segments_bounds_update BEFORE UPDATE ON"
        " transcript_segments WHEN new.end_ms>(SELECT duration_ms FROM mee"
        "tings WHERE id=new.meeting_id AND workspace_id=new.workspace_id) "
        "BEGIN SELECT RAISE(ABORT,'interval exceeds duration'); END"
    )
    op.execute(
        "CREATE TRIGGER chapters_bounds_insert BEFORE INSERT ON chapters W"
        "HEN new.end_ms>(SELECT duration_ms FROM meetings WHERE id=new.mee"
        "ting_id AND workspace_id=new.workspace_id) BEGIN SELECT RAISE(ABO"
        "RT,'interval exceeds duration'); END"
    )
    op.execute(
        "CREATE TRIGGER chapters_bounds_update BEFORE UPDATE ON chapters W"
        "HEN new.end_ms>(SELECT duration_ms FROM meetings WHERE id=new.mee"
        "ting_id AND workspace_id=new.workspace_id) BEGIN SELECT RAISE(ABO"
        "RT,'interval exceeds duration'); END"
    )
    op.execute(
        "CREATE TRIGGER soundbites_bounds_insert BEFORE INSERT ON soundbit"
        "es WHEN new.end_ms>(SELECT duration_ms FROM meetings WHERE id=new"
        ".meeting_id AND workspace_id=new.workspace_id) BEGIN SELECT RAISE"
        "(ABORT,'interval exceeds duration'); END"
    )
    op.execute(
        "CREATE TRIGGER soundbites_bounds_update BEFORE UPDATE ON soundbit"
        "es WHEN new.end_ms>(SELECT duration_ms FROM meetings WHERE id=new"
        ".meeting_id AND workspace_id=new.workspace_id) BEGIN SELECT RAISE"
        "(ABORT,'interval exceeds duration'); END"
    )
    op.execute(
        "CREATE TRIGGER highlight_text_insert BEFORE INSERT ON highlights "
        "WHEN new.end_offset>(SELECT length(text) FROM transcript_segments"
        " WHERE public_id=new.segment_id) OR new.selected_text<>(SELECT su"
        "bstr(text,new.start_offset+1,new.end_offset-new.start_offset) FRO"
        "M transcript_segments WHERE public_id=new.segment_id) BEGIN SELEC"
        "T RAISE(ABORT,'highlight does not match text'); END"
    )
    op.execute(
        "CREATE TRIGGER highlight_text_update BEFORE UPDATE ON highlights "
        "WHEN new.end_offset>(SELECT length(text) FROM transcript_segments"
        " WHERE public_id=new.segment_id) OR new.selected_text<>(SELECT su"
        "bstr(text,new.start_offset+1,new.end_offset-new.start_offset) FRO"
        "M transcript_segments WHERE public_id=new.segment_id) BEGIN SELEC"
        "T RAISE(ABORT,'highlight does not match text'); END"
    )
    op.execute(
        "INSERT INTO search_documents(public_id,workspace_id,meeting_id,ki"
        "nd,text) SELECT id,workspace_id,id,'title',title FROM meetings"
    )
    op.execute(
        "INSERT INTO search_documents(public_id,workspace_id,meeting_id,se"
        "gment_id,kind,text) SELECT public_id,workspace_id,meeting_id,publ"
        "ic_id,'transcript',text FROM transcript_segments"
    )
    op.execute("INSERT INTO search_documents_fts(search_documents_fts) VALUES('rebuild')")


def downgrade() -> None:
    op.execute("DROP TRIGGER highlight_text_update")
    op.execute("DROP TRIGGER highlight_text_insert")
    op.execute("DROP TRIGGER soundbites_bounds_update")
    op.execute("DROP TRIGGER soundbites_bounds_insert")
    op.execute("DROP TRIGGER chapters_bounds_update")
    op.execute("DROP TRIGGER chapters_bounds_insert")
    op.execute("DROP TRIGGER transcript_segments_bounds_update")
    op.execute("DROP TRIGGER transcript_segments_bounds_insert")
    op.execute("DROP TRIGGER segment_highlight_update")
    op.execute("DROP TRIGGER meeting_duration_update")
    op.execute("DROP TRIGGER meeting_cleanup")
    op.execute("DROP TRIGGER segment_cleanup")
    op.execute("DROP TRIGGER segment_search_update")
    op.execute("DROP TRIGGER segment_search_insert")
    op.execute("DROP TRIGGER meeting_search_update")
    op.execute("DROP TRIGGER meeting_search_insert")
    op.execute("DROP TRIGGER search_update")
    op.execute("DROP TRIGGER search_delete")
    op.execute("DROP TRIGGER search_insert")
    op.execute("DROP TABLE search_documents_fts")
