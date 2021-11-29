This file is temporary, and needs to be deleted before releasing the documentation.

### Build and install:

```bash
  pip install sphinx livereload myst-parser sphinxcontrib-mermaid sphinx-toolbox sphinx-copybutton
  git clone git@git.knut.univention.de:univention/documentation/univention_sphinx_book_theme.git
  pip install -e  univention_sphinx_book_theme
```

### Run
```bash
  make html
  python liveserver.py
```
