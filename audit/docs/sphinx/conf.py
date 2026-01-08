# Configuration file for the Sphinx documentation builder.
# OSS Audit 2.0 API文档配置

import os
import sys
import pathlib

# Add the source directory to sys.path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

# -- Project information -----------------------------------------------------

project = 'OSS Audit 2.0'
copyright = '2024, OSS Audit Team'
author = 'OSS Audit Team'
version = '2.0.0'
release = '2.0.0'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary', 
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx_autodoc_typehints',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

html_title = "OSS Audit 2.0 API文档"
html_short_title = "OSS Audit 2.0"
html_logo = None  # Add logo path if available
html_favicon = None  # Add favicon path if available

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

# autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autodoc_typehints = 'description'
autodoc_mock_imports = []

# napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# autosummary settings
autosummary_generate = True
autosummary_imported_members = True

# intersphinx settings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'requests': ('https://requests.readthedocs.io/en/master', None),
    'pyyaml': ('https://pyyaml.org/wiki/PyYAMLDocumentation', None),
}

# todo extension settings
todo_include_todos = True

# coverage extension settings  
coverage_ignore_modules = [
    'tests.*',
    'setup',
    'conf',
]

# Type hints configuration
always_document_param_types = True
typehints_fully_qualified = False
typehints_document_rtype = True
typehints_use_signature = True
typehints_use_signature_return = True

# Custom CSS
def setup(app):
    app.add_css_file('custom.css')

# Language settings
language = 'zh_CN'
locale_dirs = ['locale/']
gettext_compact = False

# Source file suffix
source_suffix = {
    '.rst': None,
    '.md': 'markdown',
}

# Master document
master_doc = 'index'