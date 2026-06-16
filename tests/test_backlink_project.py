import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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

    def test_optional_openpyxl_keeps_stats_command_available(self):
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
                    target_url TEXT,
                    comment_text TEXT,
                    comment_id TEXT,
                    result_reason TEXT,
                    UNIQUE(site_id, project_name)
                );
                INSERT INTO sites (site_url, site_type, weight, created_at) VALUES
                    ('https://example.com', 'blog_comment', 10, '2026-06-16 00:00:00');
                INSERT INTO submissions (site_id, project_name, status, updated_at)
                    VALUES (1, 'extractkeywords.com', '已提交', '2026-06-16 00:00:00');
                """
            )
            conn.commit()
            conn.close()

            proc = subprocess.run(
                [sys.executable, "backlink_db.py", "stats"],
                cwd=ROOT,
                env={**os.environ, "BACKLINKS_DB_PATH": str(db_path), "BACKLINKS_EXCEL_PATH": str(Path(tmpdir) / "backlinks.xlsx")},
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("数据库统计", proc.stdout)

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
            self.assertIn("target_url", sub_cols)
            self.assertIn("comment_text", sub_cols)
            self.assertIn("comment_id", sub_cols)
            self.assertIn("result_reason", sub_cols)
            self.assertIn("待确认", status_check)
            self.assertIn("需验证码", status_check)
            self.assertIn("已失效", status_check)
            self.assertIn("跳过", status_check)


if __name__ == "__main__":
    unittest.main()
