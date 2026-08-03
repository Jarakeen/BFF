from pathlib import Path

class AIService:
    def __init__(self, bff_root: Path):
        self.bff_root = bff_root

    def load_brand_voice(self) -> str:
        return (
            self.bff_root
            / "80_Operations"
            / "AI Systems"
            / "Black Feather Foundry GPT"
            / "30_STREAMING"
        ).read_text(encoding="utf-8")

    def build_system_prompt(self) -> str:
        brand_voice = self.load_brand_voice()

        return f"""
{brand_voice}

You are writing for the Black Feather Foundry.

Write:
- Twitch stream titles
- Discord live notifications

Requirements:
- Maximum 140 characters
- Dry humor
- Clever, not loud
- Never use clickbait
- Never use ALL CAPS
- Don't invent events or personal details
- Sound like expedition reports or office memos when appropriate
"""

def build_user_prompt(
    self,
    activity: str,
    objective: str = "",
    boss: str = "",
) -> str:

    return f"""
Today's stream

Activity: {activity}

Objective: {objective}

Boss: {boss}

Generate:

- 10 Twitch titles
- 10 Discord live notifications

Maximum 140 characters each.
"""