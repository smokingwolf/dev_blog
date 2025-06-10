# 開発ブログ 自動ビルド

このプロジェクトでは、Markdown形式の記事を `source/` ディレクトリ内に保存します。  
目的は、これらの記事を `dev_blog/` フォルダ内に静的なHTMLサイトとして変換することです。

## MarkdownからHTMLへの変換について

ビルドスクリプト `scripts/build.py` が `source/*.md` を読み取り、
`dev_blog/` 以下に月別・カテゴリ別の HTML を生成します。

実装が完了すると、以下のコマンドでローカルにてスクリプトを実行できるようになります：

```bash
python scripts/build.py
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

The provided build script converts `source/*.md` into monthly archives
(`dev_blog/archive/YYYY/MM.html`), category pages under
`dev_blog/category/`, and an index page showing the latest posts.

Once implemented, you will be able to run the script locally:

```bash
python scripts/build.py
```

Running the build script lets you preview the site locally. Existing files in
`dev_blog/` will be replaced during each build.

## Planned GitHub Actions workflow

A future GitHub Actions workflow will automate the build process on every push
to the main branch. The action will run the conversion script and commit the
resulting HTML so the blog stays up to date.
