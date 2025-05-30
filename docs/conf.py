# SPDX-FileCopyrightText: 2021-2023 Univention GmbH
#
# SPDX-License-Identifier: AGPL-3.0-only

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import tomllib

sys.path.insert(0, os.path.abspath("../src"))


# -- Project information -----------------------------------------------------

project = "UCS@school ID Connector"
copyright = "2021, Univention GmbH"
author = "Univention GmbH"

# The full version, including alpha/beta/rc tags
with open("../src/pyproject.toml", "rb") as fp:
    version = tomllib.load(fp)["tool"]["poetry"]["version"]

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autosectionlabel",
    "sphinx_design",
    "sphinx_copybutton",
    "univention_sphinx_extension",
    "sphinxcontrib.spelling",
    "sphinxcontrib.bibtex",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.inkscapeconverter",
    "sphinx_inline_tabs",
    "sphinx.ext.autodoc",
    "sphinx_sitemap",
]

bibtex_bibfiles = ["bibliography.bib"]
bibtex_encoding = "utf-8"
bibtex_default_style = "unsrt"
bibtex_reference_style = "label"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "uv-architecture": ("https://docs.software-univention.de/architecture/5.0/en/", None),
    "uv-appcenter": ("https://docs.software-univention.de/app-center/5.0/en", None),
    "uv-developer-reference": ("https://docs.software-univention.de/developer-reference/5.0/en", None),
    "uv-manual": ("https://docs.software-univention.de/manual/5.0/en", None),
    "uv-ucsschool-import": ("https://docs.software-univention.de/ucsschool-import/5.0/de", None),
    "uv-ucsschool-kelvin-rest-api": (
        "https://docs.software-univention.de/ucsschool-kelvin-rest-api",
        None,
    ),
    "uv-ucsschool-manual": ("https://docs.software-univention.de/ucsschool-manual/5.0/de", None),
    "pluggy": ("https://pluggy.readthedocs.io/en/latest/", None),
}

language = "en"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    ".pytest_cache",
    "sphinx-univention/*",
    "README.md",
]

pygments_style = "sphinx"
# -- Options for HTML output -------------------------------------------------
html_show_copyright = False
html_show_sphinx = False
html_show_sourcelink = False

html_theme = "univention_sphinx_book_theme"

doc_basename = "ucsschool-id-connector"
html_theme_options = {
    "pdf_download_filename": f"{doc_basename}.pdf",
    "show_source_license": True,
    "typesense_search": True,
    "typesense_document": doc_basename,
    "typesense_document_version": "latest",
    "univention_matomo_tracking": True,
    "univention_docs_deployment": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["static"]

html_css_files = ["custom.css"]

myst_enable_extensions = [
    "colon_fence",
]

title = "ID Connector - UCS@school"

source_suffix = {
    ".rst": "restructuredtext",
}

copybutton_prompt_text = r"\$ |.+# |In \[\d*\]: |>>> |"
copybutton_prompt_is_regexp = True
copybutton_line_continuation_character = "\\"
copybutton_here_doc_delimiter = "EOT"

if "spelling" in sys.argv:
    spelling_lang = "en_US"
    spelling_show_suggestions = True
    spelling_warning = True
    spelling_word_list_filename = ["spelling_wordlist"]

root_doc = "index"

numfig = True

latex_engine = "lualatex"
latex_show_pagerefs = True
latex_show_urls = "footnote"
latex_documents = [(root_doc, f"{doc_basename}.tex", project, author, "manual", False)]
latex_elements = {
    "papersize": "a4paper",
}


linkcheck_allowed_redirects = {
    r"https://pytest\.org": r"https://docs\.pytest\.org/en/.*",
    r"https://help\.univention\.com/t/\d+": r"https://help\.univention\.com/t/[\w-]+/\d+",
}
# See Univention Sphinx Extension for its options.
# https://git.knut.univention.de/univention/documentation/univention_sphinx_extension
# Information about the feedback link.
univention_feedback = True
# Information about the license statement for the source files
univention_pdf_show_source_license = True

univention_doc_basename = doc_basename
html_baseurl = "https://docs.software-univention.de/ucsschool-id-connector/"
sitemap_url_scheme = "{link}"
