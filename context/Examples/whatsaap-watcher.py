# whatsapp_watcher.py
from playwright.sync_api import sync_playwright
from base_watcher import BaseWatcher
from pathlib import Path
import json

class WhatsAppWatcher(BaseWatcher):
    def __init__(self, vault_path: str, session_path: str):
        super().__init__(vault_path, check_interval=30)
        self.session_path = Path(session_path)
        self.keywords = ['urgent', 'asap', 'invoice', 'payment', 'help']
        
    def check_for_updates(self) -> list:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                self.session_path, headless=True
            )
            page = browser.pages[0]
            page.goto('https://web.whatsapp.com')
            page.wait_for_selector('[data-testid="chat-list"]')
            
            unread = page.query_selector_all('[aria-label*="unread"]')
            messages = []
            for chat in unread:
                text = chat.inner_text().lower()
                if any(kw in text for kw in self.keywords):
                    messages.append({'text': text, 'chat': chat.get_attribute('aria-label')})
            browser.close()
            return messages
    
    def create_action_file(self, item) -> Path:
        content = f'''---
type: whatsapp
chat: {item['chat']}
received: {datetime.now().isoformat()}
priority: high
status: pending
---
 
## Message Content
{item['text']}
 
## Suggested Actions
- [ ] Reply
- [ ] Escalate
'''
        filepath = self.needs_action / f'WHATSAPP_{hash(item["text"])}.md'
        filepath.write_text(content)
        return filepath