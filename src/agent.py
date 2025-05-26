from typing import List
from pydantic import BaseModel
from browser import Browser
from models.prompts import common_browser_system_prompt
from models.llms import llm_call_messages
from rich.console import Console

class Action(BaseModel):
    action: str
    args: dict[str, str]

class Agent:
    def __init__(self):
        self.browser = Browser()
        self.console = Console()

    def _parse_action(self, action: str) -> Action:
        reasoning_start = action.find("<reasoning>") + len("<reasoning>")
        reasoning_end = action.find("</reasoning>")
        reasoning = action[reasoning_start:reasoning_end].strip()
        self.console.print(f"[yellow]Reasoning:[/yellow] {reasoning}")

        action_type_start = action.find("<action_type>") + len("<action_type>")
        action_type_end = action.find("</action_type>")
        action_type = action[action_type_start:action_type_end].strip().lower()

        
        args = {}
        current_pos = 0
        while True:
            arg_start = action.find('<action_argument name="', current_pos)
            if arg_start == -1:
                break
                
            name_start = arg_start + len('<action_argument name="')
            name_end = action.find('">', name_start)
            arg_name = action[name_start:name_end]
            
            value_start = name_end + len('">')
            value_end = action.find('</action_argument>', value_start)
            arg_value = action[value_start:value_end].strip()
            
            args[arg_name] = arg_value
            current_pos = value_end + len('</action_argument>')
        
        self.console.print(f"[green]Action:[/green] {action_type} with args: {args}")
        return Action(action=action_type, args=args)

    def _execute_action(self, action: Action):
        try:
            if action.action == "click":
                self.browser.click(int(action.args["index"]))
            elif action.action == "input":
                self.browser.input_text(int(action.args["index"]), action.args["text"])
            elif action.action == "scroll":
                self.browser.scroll(int(action.args["amount"]))
            elif action.action == "wait":
                self.browser.wait(int(action.args["amount"]))
            elif action.action == "search":
                self.browser.search(action.args["query"])
            else:
                raise ValueError(f"Invalid action: {action.action}")
        except Exception as e:
            self.console.print(f"[red]Error:[/red] {e}")
            return False
        return True

    def run(self, task: str):
        iteration = 0
        all_messages = [{
            "role": "system",
            "content": common_browser_system_prompt
        }, {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"Your job is to complete the following task: {task}"
                }
            ]
        }]

        last_action_success = True
        while True:
            iteration += 1
            state = self.browser.get_state()
            all_messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": state.page_screenshot_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": f"Currently open page: {state.page_url} {'' if last_action_success else 'Last action failed, try again.'}"
                    }
                ]
            })
            response = llm_call_messages(all_messages, model="anthropic/claude-sonnet-4")
            action = self._parse_action(response)
            if action.action == "done":
                return action.args["result"]
            last_action_success = self._execute_action(action)


def main():
    agent = Agent()
    agent.browser.open_url("https://www.apple.com")
    result = agent.run("Compare the specs of the iPhone 15 Pro Max and the iPhone 15 Pro")
    print(result)

if __name__ == "__main__":
    main()