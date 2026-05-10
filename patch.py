import sys, re
with open('api.py', 'r', encoding='utf-8') as f:
    content = f.read()

part1 = '    # Latest report date\n    rpt = conn.execute("SELECT report_date FROM reports WHERE id = ?", (rid,)).fetchone()\n    report_date = rpt[\'report_date\'] if rpt else \'\''

part1_new = '    # Latest report date and source_file_name for project name extraction\n    rpt = conn.execute("SELECT report_date, source_file_name FROM reports WHERE id = ?", (rid,)).fetchone()\n    report_date = rpt[\'report_date\'] if rpt else \'\'\n    \n    project_name = \'M60 EVT REL\'\n    if rpt and rpt[\'source_file_name\']:\n        import re\n        m = re.match(r\'^(.*?)\s*Daily Report_\', rpt[\'source_file_name\'], re.IGNORECASE)\n        if m:\n            project_name = m.group(1).upper()'

part2 = '    return jsonify({\n        \'report_date\': report_date,'

part2_new = '    return jsonify({\n        \'project_name\': project_name,\n        \'report_date\': report_date,'

content = content.replace(part1, part1_new).replace(part2, part2_new)

with open('api.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Patched api.py')
