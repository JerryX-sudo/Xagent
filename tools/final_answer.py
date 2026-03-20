"""Final answer tool for Xagent."""

from typing import Any

from tools.base import BaseTool


class FinalAnswerTool(BaseTool):
    """Tool for providing the final answer to terminate the agent loop."""

    name = "final_answer"
    description = "Use this tool when you have completed the task and want to provide the final answer to the user. This will terminate the current agent loop."
    parameters = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The final answer or summary to present to the user",
            },
        },
        "required": ["answer"],
    }

    def run(self, **kwargs: Any) -> str:
        """Return the final answer."""
        answer = kwargs.get("answer", "")
        if not answer:
            return "Error: No answer provided"
        return answer
