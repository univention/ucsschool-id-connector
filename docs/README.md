<!--
SPDX-FileCopyrightText: 2021-2023 Univention GmbH

SPDX-License-Identifier: AGPL-3.0-only
-->

# Automatic built documentation

This documentation is automatically built and available at:

https://univention.gitpages.knut.univention.de/components/ucsschool-id-connector/


# Build and install of the documentation

```bash
  pip install sphinx livereload myst-parser sphinxcontrib-mermaid sphinx-toolbox sphinx-copybutton
  mkdir -p ~/tmp
  # do the following if you trust nissedals cert, otherwise download in your browser
  curl -k -o ~/tmp/ucs-root-ca.crt https://nissedal.knut.univention.de/ucs-root-ca.crt
  cp /etc/ssl/certs/ca-certificates.crt ~/tmp
  cat ~/tmp/ucs-root-ca.crt >> ~/tmp/ca-certificates.crt
  pip install --cert ~/tmp/ca-certificates.crt --extra-index-url https://git.knut.univention.de/api/v4/projects/529/packages/pypi/simple univention-sphinx-book-theme

```

# Run
```bash
  make html
  python liveserver.py
```


# Rerender the images using plantuml

In order to use `make plantuml` you need to have a recent version of plantuml on your path. It is
known to work with versions  > 1.2021.14. In order to get plantuml on your path you can create a
plantuml script with the following content in $HOME/bin::

    #!/bin/sh
    exec java -jar /PATH/TO/CURRENT/plantuml.jar "$@"
