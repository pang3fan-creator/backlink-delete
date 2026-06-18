import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MultiLanguageConstantsTests(unittest.TestCase):
    """Tests for Points 1-2: multi-language labels and success indicators."""

    def test_name_labels_include_french_portuguese(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        self.assertIn("Nom", backlink_submit.NAME_LABELS)
        self.assertIn("Nome", backlink_submit.NAME_LABELS)
        self.assertIn("Nombre", backlink_submit.NAME_LABELS)
        self.assertIn("Ihr Name", backlink_submit.NAME_LABELS)

    def test_email_labels_include_multilingual(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        self.assertIn("Courriel", backlink_submit.EMAIL_LABELS)
        self.assertIn("Correo electrónico", backlink_submit.EMAIL_LABELS)
        self.assertIn("Ihre E-Mail", backlink_submit.EMAIL_LABELS)
        self.assertIn("Adresse e-mail", backlink_submit.EMAIL_LABELS)

    def test_url_labels_include_multilingual(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        self.assertIn("Site web", backlink_submit.URL_LABELS)
        self.assertIn("Sitio web", backlink_submit.URL_LABELS)
        self.assertIn("Ihre Website", backlink_submit.URL_LABELS)
        self.assertIn("Sito web", backlink_submit.URL_LABELS)

    def test_comment_labels_include_multilingual(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        self.assertIn("Commentaire", backlink_submit.COMMENT_LABELS)
        self.assertIn("Comentário", backlink_submit.COMMENT_LABELS)
        self.assertIn("Comentario", backlink_submit.COMMENT_LABELS)
        self.assertIn("Kommentar", backlink_submit.COMMENT_LABELS)
        self.assertIn("Commento", backlink_submit.COMMENT_LABELS)

    def test_submit_texts_include_multilingual(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        self.assertIn("Publier le commentaire", backlink_submit.SUBMIT_TEXTS)
        self.assertIn("Publicar comentário", backlink_submit.SUBMIT_TEXTS)
        self.assertIn("Kommentar abschicken", backlink_submit.SUBMIT_TEXTS)
        self.assertIn("Pubblica il commento", backlink_submit.SUBMIT_TEXTS)

    def test_success_indicators_include_multilingual(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        indicators = backlink_submit.SUCCESS_INDICATORS
        self.assertIn("Votre commentaire attend modération", indicators)
        self.assertIn("Seu comentário aguarda moderação", indicators)
        self.assertIn("Su comentario está pendiente de moderación", indicators)
        self.assertIn("Ihr Kommentar wird geprüft", indicators)
        self.assertIn("Il tuo commento è in attesa di moderazione", indicators)

    def test_css_fallbacks_include_generic_name_selector(self):
        sys.path.insert(0, str(ROOT))
        import backlink_submit
        names = [fb["author"] for fb in backlink_submit.CSS_FALLBACKS]
        self.assertIn("input[name='author']", names)


class PrevalidateLabelCheckTests(unittest.TestCase):
    """Tests for Point 3: unified prevalidate/submit standard."""

    def test_check_site_result_keys_include_label_accessible(self):
        sys.path.insert(0, str(ROOT))
        import prevalidate
        # Test that check_site returns the new key for a non-existent URL
        result = prevalidate.check_site("https://this.does.not.exist.example")
        self.assertIn('label_accessible', result)

    def test_prevalidate_open_uses_automation_bypass_args(self):
        sys.path.insert(0, str(ROOT))
        import prevalidate

        calls = []

        def fake_open(url, timeout=25, proxy=None):
            calls.append((url, timeout, proxy))
            return -1, "", "timeout"

        saved = prevalidate.open_agent_browser
        try:
            prevalidate.open_agent_browser = fake_open
            prevalidate.check_site("https://example.com/post")
        finally:
            prevalidate.open_agent_browser = saved

        self.assertEqual(calls[0], ("https://example.com/post", 25, None))

    def test_prevalidate_apply_only_marks_hard_blockers_worth_zero(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common

        self.assertFalse(backlink_common.is_hard_worth_zero_reason("Login wall"))
        self.assertFalse(backlink_common.is_hard_worth_zero_reason("Captcha required"))
        self.assertFalse(backlink_common.is_hard_worth_zero_reason("Cloudflare challenge on page"))
        self.assertFalse(backlink_common.is_hard_worth_zero_reason("No comment form in DOM"))
        self.assertTrue(backlink_common.is_hard_worth_zero_reason("404 not found"))
        self.assertTrue(backlink_common.is_hard_worth_zero_reason("SSL error"))
        self.assertTrue(backlink_common.is_hard_worth_zero_reason("No Website/URL field in comment form"))

    def test_prepare_script_imports(self):
        """Verify backlink_prepare.py can be imported without error."""
        import importlib
        sys.path.insert(0, str(ROOT))
        spec = importlib.util.find_spec("backlink_prepare")
        self.assertIsNotNone(spec, "backlink_prepare.py should be importable")

    def test_prepare_and_prevalidate_use_shared_db_path(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common
        import backlink_prepare
        import prevalidate

        self.assertEqual(backlink_prepare.DB_PATH, backlink_common.DB_PATH)
        self.assertEqual(prevalidate.DB_PATH, backlink_common.DB_PATH)


class BacklinkProjectTests(unittest.TestCase):
    def test_common_statuses_include_new_workflow_states(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common

        self.assertIn("待确认", backlink_common.VALID_STATUSES)
        self.assertIn("需验证码", backlink_common.VALID_STATUSES)
        self.assertIn("已失效", backlink_common.VALID_STATUSES)
        self.assertIn("跳过", backlink_common.VALID_STATUSES)

    def test_agent_browser_tools_exported(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common

        self.assertTrue(callable(backlink_common.agent_browser_available))
        self.assertTrue(callable(backlink_common.get_agent_browser_proxy))
        self.assertTrue(callable(backlink_common.run_agent_browser))
        self.assertTrue(callable(backlink_common.close_agent_browser))
        self.assertTrue(callable(backlink_common.reset_agent_browser_daemon))

    def test_agent_browser_available_returns_bool(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common
        result = backlink_common.agent_browser_available()
        self.assertIsInstance(result, bool)

    def test_get_agent_browser_proxy_respects_env(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common

        with tempfile.TemporaryDirectory() as _:
            env_backup = os.environ.get("AGENT_BROWSER_PROXY")
            os.environ.pop("AGENT_BROWSER_PROXY", None)
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)

            try:
                self.assertIsNone(backlink_common.get_agent_browser_proxy())
                os.environ["AGENT_BROWSER_PROXY"] = "http://127.0.0.1:8118"
                self.assertEqual(backlink_common.get_agent_browser_proxy(), "http://127.0.0.1:8118")
            finally:
                os.environ.pop("AGENT_BROWSER_PROXY", None)
                if env_backup:
                    os.environ["AGENT_BROWSER_PROXY"] = env_backup
                else:
                    os.environ.pop("AGENT_BROWSER_PROXY", None)

    def test_submit_comment_no_agent_browser_returns_failure(self):
        sys.path.insert(0, str(ROOT))
        import backlink_common
        import backlink_submit
        import shutil as shutil_mod

        saved_which = shutil_mod.which
        try:
            shutil_mod.which = lambda x: None
            backlink_common._AGENT_BROWSER_PATH = None
            result = backlink_submit.submit_comment(
                "test-project",
                "https://test-site.com",
                "99999",
                "https://example.com/blog/post",
                "Test comment"
            )
            self.assertFalse(result["success"])
            self.assertEqual(result["status"], "失败")
            self.assertIn("未安装", result["error"])
        finally:
            shutil_mod.which = saved_which
            backlink_common._AGENT_BROWSER_PATH = None

    def test_backlink_db_stats_command_available_without_excel(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, site_type, weight, created_at)
                VALUES ('https://example.com', 'blog_comment', 10, '2026-06-18 00:00:00');
                INSERT INTO submissions (site_id, project_name, status, updated_at)
                VALUES (1, 'extractkeywords.com', '已提交', '2026-06-18 00:00:00');
                """
            )
            conn.commit()
            conn.close()

            proc = subprocess.run(
                [sys.executable, "backlink_db.py", "stats"],
                cwd=ROOT,
                env={**os.environ, "BACKLINKS_DB_PATH": str(db_path)},
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("数据库统计", proc.stdout)
            self.assertIn("extractkeywords.com", proc.stdout)

    def test_backlink_db_add_submission_records_manual_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, site_type, created_at)
                VALUES ('https://example.com/post', 'blog_comment', '2026-06-18 00:00:00');
                """
            )
            conn.commit()
            conn.close()

            proc = subprocess.run(
                [
                    sys.executable,
                    "backlink_db.py",
                    "add-submission",
                    "1",
                    "demo-project",
                    "已提交",
                    "--url",
                    "https://example.com/post",
                    "--submit-url",
                    "https://submit.example.com",
                    "--comment",
                    "Manual comment",
                    "--reason",
                    "手动提交成功",
                ],
                cwd=ROOT,
                env={**os.environ, "BACKLINKS_DB_PATH": str(db_path)},
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                """
                SELECT status, submit_url, target_url, comment_text, result_reason
                FROM submissions
                WHERE site_id = 1 AND project_name = 'demo-project'
                """
            ).fetchone()
            conn.close()

            self.assertEqual(
                row,
                (
                    "已提交",
                    "https://submit.example.com",
                    "https://example.com/post",
                    "Manual comment",
                    "手动提交成功",
                ),
            )

    def test_database_migration_adds_tracking_columns_and_statuses(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                """
            )
            conn.commit()
            conn.close()

            sys.path.insert(0, str(ROOT))
            import backlink_common

            backlink_common.migrate_database(db_path)

            conn = sqlite3.connect(db_path)
            site_cols = {row[1] for row in conn.execute("PRAGMA table_info(sites)")}
            sub_cols = {row[1] for row in conn.execute("PRAGMA table_info(submissions)")}
            status_check = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='submissions'"
            ).fetchone()[0]
            conn.close()

            self.assertIn("skip_reason", site_cols)
            self.assertIn("consecutive_failures", site_cols)
            self.assertIn("submit_url", sub_cols)
            self.assertIn("target_url", sub_cols)
            self.assertIn("comment_text", sub_cols)
            self.assertIn("comment_id", sub_cols)
            self.assertIn("result_reason", sub_cols)
            self.assertIn("待确认", status_check)
            self.assertIn("需验证码", status_check)
            self.assertIn("已失效", status_check)
            self.assertIn("跳过", status_check)

    def test_database_migration_creates_project_views(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, site_type, worth_submitting)
                VALUES ('https://example.com/post', 'blog_comment', 1);
                INSERT INTO submissions (site_id, project_name, status, updated_at)
                VALUES (1, 'heicpdf.to', '已提交', '2026-06-18 00:00:00');
                """
            )
            conn.commit()
            conn.close()

            sys.path.insert(0, str(ROOT))
            import backlink_common

            backlink_common.migrate_database(db_path)

            conn = sqlite3.connect(db_path)
            view = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view' AND name='view_heicpdf_to'"
            ).fetchone()
            row = conn.execute(
                "SELECT site_url, status FROM view_heicpdf_to WHERE site_id = 1"
            ).fetchone()
            conn.close()

            self.assertEqual(view, ("view_heicpdf_to",))
            self.assertEqual(row, ("https://example.com/post", "已提交"))

    def test_submit_comment_smoke_persists_submit_url_and_target_url(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, site_type, created_at)
                VALUES ('https://example.com/post', 'blog_comment', '2026-06-16 00:00:00');
                """
            )
            conn.commit()
            conn.close()

            proc = subprocess.run(
                [
                    sys.executable,
                    "backlink_submit.py",
                    "--project",
                    "demo-project",
                    "--submit-url",
                    "https://submit.example.com",
                    "--site-id",
                    "1",
                    "--url",
                    "https://example.com/post",
                    "--comment",
                    "Test comment",
                ],
                cwd=ROOT,
                env={**os.environ, "BACKLINKS_DB_PATH": str(db_path)},
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                """
                SELECT submit_url, target_url, comment_text
                FROM submissions
                WHERE site_id = 1 AND project_name = 'demo-project'
                """
            ).fetchone()
            conn.close()

            self.assertEqual(row, ("https://submit.example.com", "https://example.com/post", "Test comment"))

    def test_apply_site_worth_success_recovers_worth_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL,
                    skip_reason TEXT
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, worth_submitting, skip_reason)
                VALUES ('https://example.com/post', 0, 'old reason');
                """
            )
            conn.commit()
            conn.close()

            sys.path.insert(0, str(ROOT))
            import backlink_common
            import backlink_submit

            old_common_db = backlink_common.DB_PATH
            old_submit_db = backlink_submit.DB_PATH
            try:
                backlink_common.DB_PATH = db_path
                backlink_submit.DB_PATH = db_path
                backlink_submit.apply_site_worth_after_submission("1", True, "success_text: awaiting moderation")

                conn = sqlite3.connect(db_path)
                row = conn.execute(
                    "SELECT worth_submitting, skip_reason, consecutive_failures FROM sites WHERE id = 1"
                ).fetchone()
                conn.close()
            finally:
                backlink_common.DB_PATH = old_common_db
                backlink_submit.DB_PATH = old_submit_db

            self.assertEqual(row, (1, None, 0))

    def test_apply_site_worth_failure_keeps_worth_one_unless_hard_blocker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "backlinks.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_url TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    site_type TEXT,
                    weight INTEGER,
                    notes TEXT,
                    created_at TEXT,
                    worth_submitting INTEGER DEFAULT NULL,
                    skip_reason TEXT
                );
                CREATE TABLE submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    project_name TEXT NOT NULL,
                    status TEXT DEFAULT '已提交',
                    notes TEXT,
                    updated_at TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, worth_submitting, skip_reason)
                VALUES ('https://example.com/post', 1, NULL);
                """
            )
            conn.commit()
            conn.close()

            sys.path.insert(0, str(ROOT))
            import backlink_common
            import backlink_submit

            old_common_db = backlink_common.DB_PATH
            old_submit_db = backlink_submit.DB_PATH
            try:
                backlink_common.DB_PATH = db_path
                backlink_submit.DB_PATH = db_path
                backlink_submit.apply_site_worth_after_submission("1", False, "找不到评论表单")

                conn = sqlite3.connect(db_path)
                row = conn.execute(
                    "SELECT worth_submitting, skip_reason, consecutive_failures FROM sites WHERE id = 1"
                ).fetchone()
                conn.close()
            finally:
                backlink_common.DB_PATH = old_common_db
                backlink_submit.DB_PATH = old_submit_db

            self.assertEqual(row, (1, None, 1))


if __name__ == "__main__":
    unittest.main()
