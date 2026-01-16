import jinja2


TEMPLATE = "Text {{ variable }}"

environment = jinja2.Environment()
template = environment.from_string(TEMPLATE)
output = template.render(variable="demo")
assert output == "Text demo", f"got: {output}"
