from typing import List
from pydantic import BaseModel
from browser import Browser
from models.uitars import ui_tars_call
from rich.console import Console

from ui_tars.prompt import COMPUTER_USE_DOUBAO


class Action(BaseModel):
    action: str
    args: dict[str, str]


class Agent:
    def __init__(self):
        self.browser = Browser()
        self.console = Console()

    def _parse_action(self, action: str) -> Action:
        """Parse UI-TARS action into our Action format."""
        if action.startswith("click"):
            # Extract x y from (x,y) format
            coords = action.split("start_box='")[1].split("'")[0]
            x, y = map(int, coords.strip("()").split(","))
            return Action(action="click", args={"x": str(x), "y": str(y)})
        elif action.startswith("left_double"):
            coords = action.split("start_box='")[1].split("'")[0]
            x, y = map(int, coords.strip("()").split(","))
            return Action(action="left_double", args={"x": str(x), "y": str(y)})
        elif action.startswith("right_single"):
            coords = action.split("start_box='")[1].split("'")[0]
            x, y = map(int, coords.strip("()").split(","))
            return Action(action="right_single", args={"x": str(x), "y": str(y)})
        elif action.startswith("drag"):
            start_coords = action.split("start_box='")[1].split("'")[0]
            end_coords = action.split("end_box='")[1].split("'")[0]
            start_x, start_y = map(int, start_coords.strip("()").split(","))
            end_x, end_y = map(int, end_coords.strip("()").split(","))
            return Action(
                action="drag",
                args={
                    "start_x": str(start_x),
                    "start_y": str(start_y),
                    "end_x": str(end_x),
                    "end_y": str(end_y),
                },
            )
        elif action.startswith("hotkey"):
            key = action.split("key='")[1].split("'")[0]
            return Action(action="hotkey", args={"key": key})
        elif action.startswith("type"):
            content = action.split("content='")[1].split("'")[0]
            return Action(action="type", args={"content": content})
        elif action.startswith("scroll"):
            coords = action.split("start_box='")[1].split("'")[0]
            direction = action.split("direction='")[1].split("'")[0]
            x, y = map(int, coords.strip("()").split(","))
            return Action(
                action="scroll", args={"x": str(x), "y": str(y), "direction": direction}
            )
        elif action.startswith("wait"):
            return Action(action="wait", args={})
        elif action.startswith("finished"):
            content = action.split("content='")[1].split("'")[0]
            return Action(action="finished", args={"content": content})
        else:
            raise ValueError(f"Invalid action: {action}")

    def _execute_action(self, action: Action):
        try:
            if action.action == "click":
                self.browser.click(int(action.args["x"]), int(action.args["y"]))
            elif action.action == "left_double":
                self.browser.left_double(int(action.args["x"]), int(action.args["y"]))
            elif action.action == "right_single":
                self.browser.right_single(int(action.args["x"]), int(action.args["y"]))
            elif action.action == "drag":
                self.browser.drag(
                    int(action.args["start_x"]),
                    int(action.args["start_y"]),
                    int(action.args["end_x"]),
                    int(action.args["end_y"]),
                )
            elif action.action == "hotkey":
                self.browser.hotkey(action.args["key"])
            elif action.action == "type":
                self.browser.type(action.args["content"])
            elif action.action == "scroll":
                self.browser.scroll(
                    int(action.args["x"]),
                    int(action.args["y"]),
                    action.args["direction"],
                )
            elif action.action == "wait":
                self.browser.wait()
            elif action.action == "finished":
                return action.args["content"]
            else:
                raise ValueError(f"Invalid action: {action.action}")
        except Exception as e:
            self.console.print(f"[red]Error:[/red] {e}")
            return False
        return True

    def run(self, task: str):
        iteration = 0
        all_messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": COMPUTER_USE_DOUBAO.format(
                            language="English", instruction=task
                        )
                        + "\n\n DO NOT REPEAT ACTIONS. If an action is not successful, try something else. If you've already clicked on something, don't click on it again, either try another action or do something else like typing.",
                    },
                ],
            },
        ]

        last_action_success = True
        while True:
            iteration += 1
            state = self.browser.get_state()

            for message in all_messages:
                if message["role"] == "user":
                    message["content"] = [
                        item for item in message["content"] if item["type"] != "image"
                    ]

            all_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "url": state.page_screenshot_base64,
                        },
                    ],
                }
            )
            action, response = ui_tars_call(all_messages)
            all_messages.append(
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": response}],
                }
            )

            print(response)
            action = self._parse_action(action)
            if action.action == "finished":
                return action.args["content"]
            last_action_success = self._execute_action(action)


def main():
    agent = Agent()
    agent.browser.goto_url("https://www.apple.com")
    result = agent.run(
        "Go to the Apple website and find me a case for my iPhone 15 Pro Max"
    )
    print(result)


if __name__ == "__main__":
    main()
