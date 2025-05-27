import base64
import json
import os
import random
import time
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
from PIL import Image

class BrowserState(BaseModel):
    page_url: str
    page_screenshot_base64: str

class Browser:
    def __init__(self):
        self.driver = sync_playwright().start().chromium.launch(headless=False)
        
        self.context = self.driver.new_context()
        self.active_page = self.context.new_page()
        self._element_selectors = []  # List of (selector, click_location) tuples

    def open_url(self, url):
        page = self.context.new_page()
        page.goto(url)
        self.active_page = page
        page.wait_for_load_state("networkidle")
        return page
    
    def click(self, index: int):
        """Click on an element specified by its index."""
        if index >= len(self._element_selectors):
            print(self._element_selectors)
            raise ValueError(f"No element found with index {index}")
        selector, click_location = self._element_selectors[index]
        if click_location:
            # Click at specific coordinates if available
            self.active_page.mouse.click(click_location['x'], click_location['y'])
        else:
            # Fallback to selector click
            self.active_page.click(selector)
        self.active_page.wait_for_load_state("networkidle")
        self.active_page.wait_for_timeout(1000)

    def input_text(self, index: int, text: str):
        """Input text into an element specified by its index."""
        if index >= len(self._element_selectors):
            print(self._element_selectors)
            raise ValueError(f"No element found with index {index}")
        selector, _ = self._element_selectors[index]
        self.active_page.fill(selector, text)
        self.active_page.wait_for_timeout(random.randint(200, 1000))
        self.active_page.keyboard.press("Enter")
        self.active_page.wait_for_load_state("networkidle")
        self.active_page.wait_for_timeout(1000)

    def scroll(self, amount: int = 500):
        """Scroll the page by the specified amount."""
        self.active_page.evaluate(f"window.scrollBy(0, {amount})")
        self.active_page.wait_for_load_state("networkidle")
        self.active_page.wait_for_timeout(1000)

    def wait(self, timeout: int = 5000):
        """Wait for the specified timeout in milliseconds."""
        self.active_page.wait_for_timeout(timeout)

    def back(self):
        """Navigate back to the previous page."""
        self.active_page.go_back()

    def search(self, query: str):
        """Jump to a search engine with the given query."""
        self.active_page.goto(f"https://www.google.com/search?q={query}")

    def take_screenshot(self, path: str):
        """Take a screenshot of the active page and save it to the specified path."""
        self.active_page.screenshot(path=path)

    def _get_web_element_rect(self, fix_color=True):
        """Get web elements and their bounding rectangles with numbered labels."""
        if fix_color:
            selected_function = "getFixedColor"
        else:
            selected_function = "getRandomColor"

        js_script = """
        (function() {
            function getRandomColor(index) {
                var letters = '0123456789ABCDEF';
                var color = '#';
                for (var i = 0; i < 6; i++) {
                    color += letters[Math.floor(Math.random() * 16)];
                }
                return color;
            }

            function getFixedColor(index) {
                return '#000000'
            }

            function getSelector(element) {
                if (element.id) {
                    return '#' + element.id;
                }
                if (element.getAttribute('name')) {
                    return `[name="${element.getAttribute('name')}"]`;
                }
                if (element.getAttribute('aria-label')) {
                    return `[aria-label="${element.getAttribute('aria-label')}"]`;
                }
                if (element.getAttribute('role')) {
                    return `[role="${element.getAttribute('role')}"]`;
                }
                if (element.classList && element.classList.length > 0) {
                    return '.' + Array.from(element.classList).join('.');
                }
                return element.tagName.toLowerCase();
            }

            let labels = [];
            var bodyRect = document.body.getBoundingClientRect();

            var items = Array.prototype.slice.call(
                document.querySelectorAll('*')
            ).map(function(element) {
                var vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
                var vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
                
                var rects = [...element.getClientRects()].filter(bb => {
                    var center_x = bb.left + bb.width / 2;
                    var center_y = bb.top + bb.height / 2;
                    var elAtCenter = document.elementFromPoint(center_x, center_y);

                    return elAtCenter === element || element.contains(elAtCenter) 
                }).map(bb => {
                    const rect = {
                        left: Math.max(0, bb.left),
                        top: Math.max(0, bb.top),
                        right: Math.min(vw, bb.right),
                        bottom: Math.min(vh, bb.bottom)
                    };
                    return {
                        ...rect,
                        width: rect.right - rect.left,
                        height: rect.bottom - rect.top
                    }
                });

                var area = rects.reduce((acc, rect) => acc + rect.width * rect.height, 0);

                return {
                    element: {
                        tagName: element.tagName,
                        type: element.type || '',
                        ariaLabel: element.getAttribute('aria-label') || '',
                        text: element.textContent.trim().replace(/\\s+/g, ' '),
                        isButton: element.tagName === 'BUTTON' || element.tagName === 'A' || element.getAttribute('role') === 'button',
                        isInput: element.tagName === 'INPUT' || element.tagName === 'TEXTAREA' || element.tagName === 'SELECT',
                        selector: getSelector(element)
                    },
                    include: 
                        (element.tagName === "INPUT" || element.tagName === "TEXTAREA" || element.tagName === "SELECT") ||
                        (element.tagName === "BUTTON" || element.tagName === "A" || (element.onclick != null) || window.getComputedStyle(element).cursor == "hello") || (element.getAttribute('role') === 'button') || (element.getAttribute('tabindex') === '0') || (element.getAttribute('role') === 'link') || (element.getAttribute('role') === 'menuitem'),
                    area,
                    rects,
                    clickLocation: rects.length > 0 ? {
                        x: rects[0].left + rects[0].width / 2,
                        y: rects[0].top + rects[0].height / 2
                    } : null
                };
            }).filter(item =>
                item.include && (item.area >= 20)
            );

            // Only keep inner clickable items
            const buttons = Array.from(document.querySelectorAll('button, a, input[type="button"], div[role="button"]'));
            const buttonTags = new Set(buttons.map(b => b.tagName));
            
            // Filter out elements that are inside buttons
            items = items.filter(x => !buttonTags.has(x.element.tagName) || x.element.isButton);

            // Filter out elements that are inside spans with role
            items = items.filter(x => 
                !(x.element.parentNode && 
                x.element.parentNode.tagName === 'SPAN' && 
                x.element.parentNode.children.length === 1 && 
                x.element.parentNode.getAttribute('role')));

            items.forEach(function(item, index) {
                item.rects.forEach((bbox) => {
                    newElement = document.createElement("div");
                    newElement.id = `browser-agent-element-${index}`;
                    var borderColor = COLOR_FUNCTION(index);
                    newElement.style.outline = `2px dashed ${borderColor}`;
                    newElement.style.position = "fixed";
                    newElement.style.left = bbox.left + "px";
                    newElement.style.top = bbox.top + "px";
                    newElement.style.width = bbox.width + "px";
                    newElement.style.height = bbox.height + "px";
                    newElement.style.pointerEvents = "none";
                    newElement.style.boxSizing = "border-box";
                    newElement.style.zIndex = 2147483647;
                    
                    var label = document.createElement("span");
                    label.textContent = index;
                    label.style.position = "absolute";
                    label.style.top = Math.max(-19, -bbox.top) + "px";
                    label.style.left = Math.min(Math.floor(bbox.width / 5), 2) + "px";
                    label.style.background = borderColor;
                    label.style.color = "white";
                    label.style.padding = "2px 4px";
                    label.style.fontSize = "12px";
                    label.style.borderRadius = "2px";
                    newElement.appendChild(label);
                    
                    document.body.appendChild(newElement);
                    labels.push(newElement);
                });
            });

            return [labels.map(l => l.id), items];
        })();
        """

        js_script = js_script.replace("COLOR_FUNCTION", selected_function)
        rects, items_raw = self.active_page.evaluate(js_script)
        
        # Store selectors and click locations for interaction
        self._element_selectors = [(item['element']['selector'], item['clickLocation']) for item in items_raw]

        return items_raw

    def take_screenshot_with_selectors(self, path: str):
        """Take a screenshot of the active page with all clickable elements highlighted and numbered."""
        items_raw = self._get_web_element_rect()
        self.active_page.screenshot(path=path)
        # Remove the rectangles after taking screenshot
        for i in range(len(items_raw)):
            self.active_page.evaluate(f"document.getElementById('browser-agent-element-{i}').remove()")
        
        # Convert image to base64
        with open(path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')


    def goto_url(self, url: str):
        self.active_page.goto(url)
        self.active_page.wait_for_load_state("networkidle")
        self.active_page.wait_for_timeout(1000)

    def get_state(self) -> BrowserState:
        self.active_page.wait_for_load_state("networkidle")
        self.active_page.wait_for_timeout(1000)

        return BrowserState(
            page_url=self.active_page.url,
            page_screenshot_base64=f"data:image/png;base64,{self.take_screenshot_with_selectors(f"../.data/screenshots/screenshot_{time.time()}.png")}"
        )

    def close(self):
        self.context.close()
        self.driver.close()

def main():
    base_path = "../.data/screenshots"
    os.makedirs(base_path, exist_ok=True)
    browser = Browser()
    browser.open_url("https://apple.com/iphone")
    browser.take_screenshot_with_selectors(f"{base_path}/screenshot.png")
    browser.wait(1000)
    browser.scroll(1000)
    browser.take_screenshot_with_selectors(f"{base_path}/screenshot.png")
    browser.wait(1000)
    browser.scroll(1000)
    browser.take_screenshot_with_selectors(f"{base_path}/screenshot.png")

if __name__ == "__main__":
    main()