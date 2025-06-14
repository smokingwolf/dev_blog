# source_txt/内のfinal_letter.txtの日付を50日後に更新し続ける処理
#
# SmokingWOLFが更新を続けている間は最終記事が出てこないが、
# 更新停止後50日で出すようにするための処理
# (GitHubの自動更新が、ユーザーによる最後の直接更新から60日後にオフになるらしいため)

from datetime import datetime, timedelta

heartbeat_file = 'source_txt/final_letter.txt'

# 50日後の「00:00:00」形式で日時を作成
new_date = (datetime.now() + timedelta(days=0)).strftime('%Y-%m-%d') + ' 00:00:00'

with open(heartbeat_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(heartbeat_file, 'w', encoding='utf-8') as f:
    for line in lines:
        if line.startswith('DATE:'):
            f.write(f'DATE: {new_date}\n')
        else:
            f.write(line)
