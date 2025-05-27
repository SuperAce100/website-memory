# Use a pipeline as a high-level helper
import os
import time
from transformers import pipeline
from rich.console import Console

console = Console()

from ui_tars.action_parser import (
    parse_action_to_structure_output,
    parsing_response_to_pyautogui_code,
)
from ui_tars.prompt import COMPUTER_USE_DOUBAO

from browser import Browser

pipe = pipeline("image-text-to-text", model="ByteDance-Seed/UI-TARS-1.5-7B")


def ui_tars_call(messages):
    response = pipe(text=messages, max_new_tokens=1000)
    response_text = response[-1]["generated_text"][-1]["content"]
    original_image_width, original_image_height = 1920, 1080
    action = response_text.split("Action: ")[1]
    return action, response_text


def main():
    base_path = "../.data/screenshots"
    os.makedirs(base_path, exist_ok=True)

    messages = [
        {
            "role": "system",
            "content": [
                {
                    "type": "text",
                    "text": COMPUTER_USE_DOUBAO.format(
                        language="English",
                        instruction="Your task is to search for candy online",
                    ),
                },
            ],
        },
    ]

    browser = Browser()
    browser.goto_url("https://www.google.com")
    image = browser.take_screenshot(f"{base_path}/screenshot{time.time()}.png")
    messages += [
        {
            "role": "user",
            "content": [
                {"type": "image", "url": f"data:image/png;base64,{image}"},
            ],
        }
    ]

    ui_tars_call(messages)


if __name__ == "__main__":
    main()
