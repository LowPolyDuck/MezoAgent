def load_plugins(plugin_names):
    """
    Dynamically load tools from each plugin specified by name.
    Each plugin folder must define a get_tools() function in its __init__.py.
    """
    tools = []
    for name in plugin_names:
        module = __import__(f"plugins.{name}", fromlist=["get_tools"])
        tools.extend(module.get_tools())
    return tools