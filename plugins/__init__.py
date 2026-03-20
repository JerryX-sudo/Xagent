"""Plugin directory for Xagent.

Users can add custom tools by creating .py files in ~/.xagent/plugins/
Each file should define a class that inherits from tools.base.BaseTool.

Example plugin (save as ~/.xagent/plugins/my_tool.py):

    from tools.base import BaseTool

    class MyTool(BaseTool):
        name = "my_tool"
        description = "Does something custom"
        parameters = {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input for the tool",
                },
            },
            "required": ["input"],
        }

        def run(self, **kwargs):
            return f"Result: {kwargs.get('input')}"
"""
