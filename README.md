# 開発ブログ 自動ビルド

このプロジェクトでは、Markdown形式の記事を `source/` ディレクトリ内に保存します。  
目的は、これらの記事を `dev_blog/` フォルダ内に静的なHTMLサイトとして変換することです。

## MarkdownからHTMLへの変換について

最終的には、変換処理を行うビルドスクリプトが用意される予定です。  
このスクリプトは `source/*.md` の各ファイルを読み取り、それと同じ名前のHTMLファイルを `dev_blog/` フォルダ内に出力いたします。

実装が完了すると、以下のコマンドでローカルにてスクリプトを実行できるようになります：

```bash
python build.py  # source/ から Markdown を読み取り、dev_blog/ に HTML を出力します
```

ビルドスクリプトを実行することで、サイトをローカルでプレビューすることが可能になります。  
なお、`dev_blog/` 内の既存ファイルは、ビルドのたびに上書きされますのでご注意ください。

## 今後のGitHub Actionsによる自動化ワークフロー

将来的には、GitHub Actionsを用いたワークフローにより、mainブランチへのpushごとに自動的にビルド処理を行う予定です。  
このアクションは変換スクリプトを実行し、生成されたHTMLをコミットすることで、ブログが常に最新の状態に保たれるようになります。

---


# Dev Blog AutoBuild

This project stores Markdown posts in the `source/` directory. The goal is to
convert these posts into a static HTML site inside `dev_blog/`.

## Converting Markdown to HTML

A build script will eventually handle the conversion. It will read each
`source/*.md` file and write a corresponding HTML file with the same name under
`dev_blog/`.

Once implemented, you will be able to run the script locally:

```bash
python build.py  # reads Markdown from source/ and outputs HTML to dev_blog/
```

Running the build script lets you preview the site locally. Existing files in
`dev_blog/` will be replaced during each build.

## Planned GitHub Actions workflow

A future GitHub Actions workflow will automate the build process on every push
to the main branch. The action will run the conversion script and commit the
resulting HTML so the blog stays up to date.
