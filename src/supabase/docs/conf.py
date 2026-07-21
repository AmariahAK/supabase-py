import supabase

project = "supabase-py"
version = supabase.__version__
release = version
copyright = (
    "2022, Anand Krishna, Daniel Reinón García, Joel Lee, "
    "Leynier Gutiérrez González, Andrew Smith"
)
author = (
    "Anand Krishna, Daniel Reinón García, Joel Lee, "
    "Leynier Gutiérrez González, Andrew Smith"
)

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.extlinks",
]

napoleon_google_docstring = True

autodoc_member_order = "bysource"
autodoc_class_signature = "separated"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = []
