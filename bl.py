#!/usr/bin/env python3
"""backlinks管理工具：数据库 ↔ Excel 双向同步"""

import sqlite3
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from datetime import datetime
import sys

DB_PATH = 'backlinks.db'
EXCEL_PATH = 'backlinks.xlsx'

# 颜色
GREEN = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
YELLOW = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
RED = PatternFill(start_color='FCE4EC', end_color='FCE4EC', fill_type='solid')
BLUE = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def export():
    """数据库 → Excel"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取所有项目
    cursor.execute('SELECT DISTINCT project_name FROM submissions ORDER BY project_name')
    projects = [r[0] for r in cursor.fetchall()]

    # 获取所有站点
    cursor.execute('''SELECT id, site_name, site_url, site_type, category, weight, language
        FROM sites ORDER BY 
        CASE WHEN category IS NULL THEN 1 ELSE 0 END,
        category, weight DESC NULLS LAST''')
    sites = cursor.fetchall()

    # 获取所有提交记录
    cursor.execute('SELECT site_id, project_name, status FROM submissions')
    subs = {}
    for sid, proj, status in cursor.fetchall():
        subs[(sid, proj)] = status
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = '提交总表'

    headers = ['站点名称', '提交地址', '类型', '分类', '权重', '语言'] + list(projects)
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = BLUE
        cell.alignment = Alignment(horizontal='center')

    for row_idx, site in enumerate(sites, 2):
        sid, name, url, stype, cat, weight, lang = site
        ws.cell(row=row_idx, column=1, value=name or '')
        ws.cell(row=row_idx, column=2, value=url or '')
        ws.cell(row=row_idx, column=3, value=stype or '')
        ws.cell(row=row_idx, column=4, value=cat or '')
        ws.cell(row=row_idx, column=5, value=str(weight or ''))
        ws.cell(row=row_idx, column=6, value=lang or '')
        
        for proj_idx, proj in enumerate(projects):
            col = 7 + proj_idx
            status = subs.get((sid, proj), '')
            cell = ws.cell(row=row_idx, column=col, value=status)
            cell.alignment = Alignment(horizontal='center')
            if status == '已提交':
                cell.fill = GREEN
            elif status in ('需付费', '需登录'):
                cell.fill = YELLOW

    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 8
    ws.column_dimensions['F'].width = 10

    wb.save(EXCEL_PATH)
    print(f'✅ 导出成功: {EXCEL_PATH}')
    print(f'   站点: {len(sites)} 个, 项目: {len(projects)} 个')
    print(f'   编辑后运行: python3 bl.py import')

def import_from_excel():
    """Excel → 数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    # 第一行是表头
    headers = [cell.value for cell in ws[1]]
    projects = [h for h in headers[6:] if h]  # 第7列开始是项目

    # 从第2行开始
    updated = 0
    added = 0
    now_ts = now()

    for row in ws.iter_rows(min_row=2, values_only=True):
        site_url = str(row[1]).strip().lower() if row[1] else ''
        if not site_url:
            continue
        
        # 确保站点存在
        cursor.execute('INSERT OR IGNORE INTO sites (site_url, created_at) VALUES (?, ?)',
                      (site_url, now_ts))
        # 更新站点信息
        site_name = str(row[0]).strip() if row[0] else ''

        cursor.execute('''UPDATE sites SET site_name = ? WHERE site_url = ?''',
                      (site_name, site_url))
        if row[2]:
            cursor.execute('UPDATE sites SET site_type = ? WHERE site_url = ?', (row[2], site_url))
        if row[3]:
            cursor.execute('UPDATE sites SET category = ? WHERE site_url = ?', (row[3], site_url))
        if row[4]:
            cursor.execute('UPDATE sites SET weight = ? WHERE site_url = ?', (int(row[4]) if row[4] else None, site_url))
        if row[5]:
            cursor.execute('UPDATE sites SET language = ? WHERE site_url = ?', (row[5], site_url))
        
        cursor.execute('SELECT id FROM sites WHERE site_url = ?', (site_url,))
        site_id = cursor.fetchone()[0]
        
        # 处理每个项目的提交状态
        for proj_idx, proj in enumerate(projects):
            col = 6 + proj_idx
            status = str(row[col]).strip() if col < len(row) and row[col] else ''
            if status:
                cursor.execute('''
                    INSERT INTO submissions (site_id, project_name, status, updated_at) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(site_id, project_name) DO UPDATE SET status=?, updated_at=?
                ''', (site_id, proj, status, now_ts, status, now_ts))
                updated += 1
            else:
                cursor.execute('DELETE FROM submissions WHERE site_id=? AND project_name=?',
                              (site_id, proj))

    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM sites')
    sites_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM submissions')
    subs_count = cursor.fetchone()[0]
    conn.close()

    print(f'✅ 导入成功!')
    print(f'   更新/新增提交记录: {updated} 条')
    print(f'   数据库站点: {sites_count} 个, 提交记录: {subs_count} 条')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法:')
        print('  python3 bl.py export   → 数据库 → Excel')
        print('  python3 bl.py import   → Excel → 数据库')
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == 'export':
        export()
    elif cmd == 'import':
        import_from_excel()
    else:
        print('未知命令，使用: export 或 import')
