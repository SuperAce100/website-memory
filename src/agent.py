from typing import List
from pydantic import BaseModel
from browser import Browser

class Action(BaseModel):
    action: str
    args: dict[str, str]

class Agent:
    def __init__(self):
        self.browser = Browser()

    def _parse_action(self, action: Action):
        if action.action == "click":
            self.browser.click(action.args["index"])
        elif action.action == "input":
            self.browser.input_text(action.args["index"], action.args["text"])
        elif action.action == "scroll":
            self.browser.scroll(action.args["amount"])
        elif action.action == "wait":
            self.browser.wait(action.args["amount"])
        elif action.action == "search":
            self.browser.search(action.args["query"])
        elif action.action == "take_screenshot":
            self.browser.take_screenshot_with_selectors(action.args["path"])
        else:
            raise ValueError(f"Invalid action: {action.action}")

    def run(self):
        pass

def main():
    agent = Agent()
    agent.run()

if __name__ == "__main__":
    main()