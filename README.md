# ブログ 自動ビルド

このプロジェクトでは、あるTXT形式の原稿を `source_txt/` ディレクトリ内に保存すると
それらの記事を `docs/` フォルダ内に静的なHTMLサイトとして変換する自動ビルド機能が実装されてます。

## MarkdownからHTMLへの変換について

ビルドスクリプト `scripts/build.py` が `source/*.md` を読み取り、
`docs/` 以下に月別・カテゴリ別の HTML を生成します。
生成に使用する処理は以下のみです（ローカルでも実行可能です）。

```bash
python scripts/build.py
```

このビルドスクリプトを実行することで、サイトをローカルでプレビューすることが可能になります。  
なお、`docs/` 内の既存ファイルは、ビルドのたびに上書きされますのでご注意ください。

## GitHub Actionsによる自動化ワークフロー

GitHub Actionsを用いたワークフローにより、mainブランチへの「source_txt/」へのpushごとに自動的にビルド処理を行います。 
このアクションは変換スクリプトを実行し、生成されたHTMLをコミットすることで、ブログが常に最新の状態に保たれるようになります。

ブログ投稿者は「source_txt/」「source_img/」「source_js/」内のみ操作するようにしてください。

デザイン変更時は「design/」内を編集します（ただしその後に「source_txt」を更新して再ビルドを行うまで反映されません）

・「source_img/」内に画像がpushされた場合、「docs/image/」内にコピーされます。

・「source_js/」内に画像がpushされた場合、「docs/js/」内にコピーされます。

### scripts/build.pyについて

build.pyは「source_txt/に何かがプッシュされる」か「毎週土曜の明け方」のタイミングで実行されます。
実行されると、source_txt/内の全txtを使用してdocs/内に全期間・全カテゴリーのブログHTMLを生成します。

### scripts/heartbeat.pyについて

heartbeat.pyはsource_txt/にプッシュされるたびに実行され、source/txt/final_letter.txtの記事のDATE:を現在から50日後の日付に延ばします。
