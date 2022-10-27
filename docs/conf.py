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
# import os
import sys

# sys.path.insert(0, os.path.abspath("."))


# -- Project information -----------------------------------------------------

project = "UCS@school ID Connector"
copyright = "2021, univention"
author = "univention"

# The full version, including alpha/beta/rc tags
release = "2.2.4"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinxcontrib.mermaid",
    "sphinx.ext.autosectionlabel",
    "sphinx_toolbox.collapse",
    "sphinx_copybutton",
    "univention_sphinx_extension",
    "sphinxcontrib.spelling",
    "sphinxcontrib.bibtex",
    "sphinx.ext.intersphinx",
]

bibtex_bibfiles = ["bibliography.bib"]
bibtex_encoding = "utf-8"
bibtex_default_style = "unsrt"
bibtex_reference_style = "label"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.8", None),
    "uv-appcenter": ("https://docs.software-univention.de/app-center/5.0/en", None),
    "uv-developer-reference": ("https://docs.software-univention.de/developer-reference/5.0/en", None),
    "uv-manual": ("https://docs.software-univention.de/manual/5.0/en", None),
    "uv-ucsschool-import": ("https://docs.software-univention.de/ucsschool-import/5.0/de", None),
    "uv-ucsschool-kelvin-rest-api": ("https://docs.software-univention.de/ucsschool-kelvin-rest-api", None),
    "uv-ucsschool-manual": ("https://docs.software-univention.de/ucsschool-manual/5.0/de", None),
}

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# import stanford_theme
# html_theme = "stanford_theme"
# html_theme_path = [stanford_theme.get_html_theme_path()]

# html_theme = "sphinx_book_theme"

# html_theme = "sphinx-univention"
# html_theme_path = ["."]
html_last_updated_fmt = "%Y-%m-%d"
html_show_copyright = False
html_show_sphinx = False
html_show_sourcelink = False
# html_use_index = False

html_theme = "univention_sphinx_book_theme"

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

copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: | +"
copybutton_prompt_is_regexp = True

if "spelling" in sys.argv:
    spelling_lang = "en_US"
    spelling_show_suggestions = True
    spelling_warning = True
    spelling_word_list_filename = ["spelling_wordlist"]

linkcheck_allowed_redirects = {
    r"https://pytest\.org": r"https://docs\.pytest\.org/en/.*",
    r"https://help\.univention\.com/t/\d+": r"https://help\.univention\.com/t/[\w-]+/\d+",
}

# See Univention Sphinx Extension for its options and information about the
# feedback link.
# https://git.knut.univention.de/univention/documentation/univention_sphinx_extension
univention_feedback = True
univention_doc_basename = "ucsschool-id-connector"
