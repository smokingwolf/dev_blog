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
