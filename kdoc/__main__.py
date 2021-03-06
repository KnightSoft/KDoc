from kdoc.processor import Processor

import sys
import pprint
import os
import re
import json
import yaml

from jinja2 import Template, Environment, PackageLoader, Markup
from markdown import markdown
from functools import partial

p = Processor()
link_re = re.compile('\[\[\w+\]\]')

category_filename = lambda category: category.lower().replace(" ", "_").replace("/", "_") + ".html"

def safe_markdown(text):
    return Markup(markdown(text))

def safe_links(text):
    new_text = text

    for match in link_re.findall(text):
        func_name = str(match.strip('[]'))
        if func_name not in p.lookup_table:
            new_text = new_text.replace(match, Markup('<span class="deadlink">%s</span>' % func_name))
            continue

        category = p.lookup_table[func_name]
        new_text = new_text.replace(match, Markup('<a href="%s#%s">%s</a>' % (category_filename(category), func_name, func_name)))

    return new_text

def github_link(user, commit, path, line):
    repo = path.split("/")[0]
    path = '/'.join(path.split("/")[1:])

    return "https://github.com/%s/%s/blob/%s/%s#L%d" % (user, repo, commit, path, line)

# TODO: Refactor this
kos_github_link = partial(github_link, "KnightOS")

env = Environment(loader=PackageLoader("kdoc", "templates"))
env.filters['markdown'] = safe_markdown
env.filters['links'] = safe_links
env.filters['json'] = json.dumps
env.filters['file'] = category_filename

env.globals['kos_github_link'] = kos_github_link

if __name__ == '__main__':
    categories = sys.argv[1]
    with open(categories) as f:
        categories = yaml.load(f.read())['categories']

    commit = sys.argv[2]

    for f in sys.argv[3:]:
        p.add(f)

    p.process()

    f_count = len(p.functions)
    if f_count:
        pp = pprint.PrettyPrinter(indent=4)
        print "There are %d functions." % f_count
        print "---"
    else:
        sys.exit(0)

    template = env.get_template("category.html")

    try:
        os.mkdir("html")
    except: pass

    for category, items in p.category_table.items():
        kw = {
            'name': category,
            'items': sorted(items, key=lambda item: item.name),
            'categories': sorted(categories.items()),
            'commit': commit,
        }

        if category in categories:
            category_info = categories[category]
            if category_info and 'summary' in category_info:
                kw['summary'] = category_info['summary']
        else:
            print "WARNING: %s not in categories.yaml." % category

        content = template.render(**kw)

        with open(os.path.join("html", category_filename(category)), "w") as f:
            f.write(content)
            f.flush()

        print category, "written"

    with open(os.path.join("html", "data.json"), "w") as f:
        f.write(json.dumps(p.flatten()))
        f.flush()

    with open(os.path.join("html", "index.md"), "w") as f:
        template = env.get_template("categories.html")
        content = template.render(categories=sorted(categories.items()))

        f.write(content)
        f.flush()
