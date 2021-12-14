This file is temporary, and needs to be deleted before releasing the documentation.

### Build and install:

```bash
  pip install sphinx livereload myst-parser sphinxcontrib-mermaid sphinx-toolbox sphinx-copybutton
  mkdir -p ~/tmp
  # do the following if you trust nissedals cert, otherwise download in your browser
  curl -k -o ~/tmp/ucs-root-ca.crt https://nissedal.knut.univention.de/ucs-root-ca.crt
  cp /etc/ssl/certs/ca-certificates.crt ~/tmp
  cat ~/tmp/ucs-root-ca.crt >> ~/tmp/ca-certificates.crt
  pip install --cert ~/tmp/ca-certificates.crt --extra-index-url https://git.knut.univention.de/api/v4/projects/529/packages/pypi/simple univention-sphinx-book-theme

```

### Run
```bash
  make html
  python liveserver.py
```


# Install 2

```bash

```
