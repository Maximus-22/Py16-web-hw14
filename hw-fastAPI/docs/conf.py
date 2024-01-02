import sys
import os

print(sys.path)

# Додати шлях до кореневого каталогу проекту
sys.path.insert(0, os.path.abspath('..'))

# Затем добавьте путь к каталогу src (если это необходимо)
sys.path.insert(0, os.path.abspath('../src'))

project = 'Contacts project'
copyright = '2024, maximus22'
author = 'maximus22'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'pyramid'
html_static_path = ['_static']
