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
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# -- Project information -----------------------------------------------------

project = "Deephaven Python Plotting API"
copyright = "2021, Deephaven Data Labs"
author = "Deephaven Data Labs"

# The full version, including alpha/beta/rc tags
# release = '0.0.1'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
]


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Custom CSS files
html_css_files = ["custom.css"]

# Theme options
# see https://alabaster.readthedocs.io/en/latest/customization.html
# see https://github.com/bitprophet/alabaster/blob/master/alabaster/theme.conf
html_theme_options = {
    #'logo' : 'deephaven.png',
    #'logo_name' : 'Deephaven',
    "page_width": "80%",
    "sidebar_width": "35%",
}

# A boolean that decides whether module names are prepended to all object names (for object types where a “module” of some kind is defined), e.g. for py:function directives. Default is True.
add_module_names = False
# if we allow sphinx to generate type hints for signatures (default), it would make the generated doc cluttered and hard to read
autodoc_typehints = "none"
autoclass_content = "both"

#########################################################################################################################################################################


from deephaven_server import Server

s = Server(port=10000, jvm_args=["-Xmx1g"])
s.start()

import deephaven.plot.express

docs_title = "Deephaven Python plot API modules."
package_roots = [deephaven.plot.express]
package_excludes = ["._", "proto"]

import os
import shutil
import pkgutil


def glob_package_names(packages):
    rst = []

    for package in packages:
        rst.append(package.__name__)

        if hasattr(package, "__path__"):
            for importer, modname, ispkg in pkgutil.walk_packages(
                path=package.__path__,
                prefix=package.__name__ + ".",
                onerror=lambda x: None,
            ):
                rst.append(modname)

    return rst


def _add_package(tree, package):
    n = package[0]

    if n not in tree:
        tree[n] = {}

    if len(package) > 1:
        _add_package(tree[n], package[1:])


def package_tree(package_names):
    rst = {}
    for pn in package_names:
        spn = pn.split(".")
        _add_package(rst, spn)
    return rst


def make_rst_tree(package, tree):
    package_name = ".".join(package)

    if len(tree) == 0:
        toctree = ""
    else:
        toctree = ".. toctree::\n"
        for k in tree:
            p = package.copy()
            p.append(k)
            pn = ".".join(p)
            toctree += "%s%s <%s>\n" % (" " * 4, k, pn)

    rst = (
        "%s\n%s\n\n%s\n.. automodule:: %s\n    :members:\n    :no-undoc-members:\n    :show-inheritance:\n    :inherited-members:\n\n"
        % (package_name, "=" * len(package_name), toctree, package_name)
    )

    if len(package) > 0:
        filename = f"code/{package_name}.rst"

        with open(filename, "w") as file:
            file.write(rst)

    for k, v in tree.items():
        p = package.copy()
        p.append(k)
        make_rst_tree(p, v)

def make_rst_modules(docs_title, package_roots):
    rst = f"""
Python Modules
##############

{docs_title}

.. toctree::
    :glob:

"""

    for pr in package_roots:
        rst += "\n%s./code/%s" % (" " * 4, pr.__name__)

    filename = "modules.rst"

    with open(filename, "w") as file:
        file.write(rst)


def gen_sphinx_modules(docs_title, package_roots, package_excludes):
    pn = glob_package_names(package_roots)
    pn = [p for p in pn if not any(exclude in p for exclude in package_excludes)]
    pt = package_tree(pn)

    if os.path.exists("code"):
        shutil.rmtree("code")
    os.mkdir("code")

    make_rst_modules(docs_title, package_roots)
    make_rst_tree([], pt)


gen_sphinx_modules(docs_title, package_roots, package_excludes)