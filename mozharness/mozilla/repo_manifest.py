"""
Module for handling repo style XML manifests
"""
import xml.dom.minidom
import os


def load_manifest(filename):
    """
    Loads manifest from `filename`
    Processes any <include name="..." /> nodes
    """
    doc = xml.dom.minidom.parse(filename)
    # Find all <include> nodes
    for i in doc.getElementsByTagName('include'):
        p = i.parentNode

        # The name attribute is relative to where the original manifest lives
        inc_filename = i.getAttribute('name')
        inc_filename = os.path.join(os.path.dirname(filename), inc_filename)

        # Parse the included file
        inc_doc = load_manifest(inc_filename).documentElement
        # For all the child nodes in the included manifest, insert into our
        # manifest just before the include node
        # We operate on a copy of childNodes because when we reparent `c`, the
        # list of childNodes is modified.
        for c in inc_doc.childNodes[:]:
            p.insertBefore(c, i)
        # Now we can remove the include node
        p.removeChild(i)

    return doc


def rewrite_remotes(manifest, mapping_func, force_all=True):
    """
    Rewrite manifest remotes in place
    Returns the same manifest, with the remotes transformed by mapping_func
    mapping_func should return a modified remote node, or None if no changes
    are required
    If force_all is True, then it is an error for mapping_func to return None;
    a ValueError is raised in this case
    """
    for r in manifest.getElementsByTagName('remote'):
        m = mapping_func(r)
        if not m:
            if force_all:
                raise ValueError("Wasn't able to map %s" % r.toxml())
            continue

        r.parentNode.replaceChild(m, r)


def add_project(manifest, name, path, remote=None, revision=None):
    """
    Adds a project to the manifest in place
    """

    project = manifest.createElement("project")
    project.setAttribute('name', name)
    project.setAttribute('path', path)
    if remote:
        project.setAttribute('remote', remote)
    if revision:
        project.setAttribute('revision', revision)

    manifest.documentElement.appendChild(project)


def remove_project(manifest, name):
    """
    Removes a project from manifest
    """
    node = get_project(manifest, name)
    if node:
        node.parentNode.removeChild(node)
    return node


def get_project(manifest, name):
    """
    Gets a project node from the manifest by name
    """
    for node in manifest.getElementsByTagName('project'):
        if node.getAttribute('name') == name:
            return node

def get_remote(manifest, name):
    for node in manifest.getElementsByTagName('remote'):
        if node.getAttribute('name') == name:
            return node
