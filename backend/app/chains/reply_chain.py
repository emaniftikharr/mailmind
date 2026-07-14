"""
LCEL chain: smart reply generation using email body + classification context.

Produces 2-3 reply variants with distinct intents (Accept / Decline / Propose,
etc.) and a `reply_needed` flag for emails that require no response.
Uses SystemMessage so JSON examples don't conflict with LangChain's template
variable parser.
"""
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import Runnable

from app.chains.base import get_groq_llm

MAX_INPUT_CHARS = 3_000

_SYSTEM = """\
You are a smart reply assistant. Given an email (and optional category/priority hints),
decide whether a reply is needed, then generate 2-3 reply variants with distinct intents.
Respond with valid JSON only — no prose, no markdown fences.

OUTPUT SCHEMA
{
  "reply_needed": <bool — false ONLY for automated notifications, shipping updates,
                  newsletters, receipts, or emails that explicitly say "no reply needed">,
  "variants": [
    {
      "label": <string — 1-4 words describing intent, e.g. "Accept", "Decline", "Clarify">,
      "tone":  <"formal" | "friendly" | "direct">,
      "text":  <string — complete reply body, newlines as \\n, signed "[Your Name]">
    }
  ]
}

TONE DEFINITIONS
- "formal"   — polished, professional, suitable for executives or external contacts
- "friendly" — warm and collegial, suitable for teammates or familiar contacts
- "direct"   — brief and to-the-point, no filler phrases

RULES
- Set reply_needed=false for: automated order confirmations, shipping notifications,
  newsletters, promotional emails, and messages that say "no action/reply required".
- Set reply_needed=true for everything else (even FYI updates worth acknowledging).
- When reply_needed=false, return variants=[].
- Generate 3 variants for meeting invites and binary decisions (Accept/Decline/Propose).
- Generate 2 variants for task requests and informational emails.
- Each variant must differ in INTENT, not just tone. Never generate two "Accept" variants.
- Assign tone based on content: formal for external/executive, friendly for teammates,
  direct when brevity is the clearest choice (e.g., short confirmations).
- Reply text: complete, ready-to-send, 2-5 sentences per variant.
- Open with sender's first name if visible; otherwise use "Hi,".
- Do NOT include a subject line — body only.
- Sign every reply with \\n\\n[Your Name]

EXAMPLES

Email:
[Category: meeting | Priority: normal]
Subject: Q3 Strategy Meeting - Thursday at 2 PM
From: sarah@company.com

Hi team, you are invited to the Q3 Strategy Meeting on Thursday, July 17 at 2 PM in Conference Room B. Please confirm your attendance by Wednesday.

Output: {"reply_needed":true,"variants":[{"label":"Accept","tone":"formal","text":"Hi Sarah,\\n\\nThank you for the invitation. I'll be attending the Q3 Strategy Meeting on Thursday, July 17 at 2 PM — looking forward to it.\\n\\n[Your Name]"},{"label":"Decline","tone":"formal","text":"Hi Sarah,\\n\\nThank you for the invite. Unfortunately I have a conflict on Thursday at 2 PM and won't be able to attend. Could someone share the notes afterwards?\\n\\nApologies for the inconvenience,\\n[Your Name]"},{"label":"Propose new time","tone":"friendly","text":"Hi Sarah,\\n\\nThanks for the invite! Thursday at 2 PM doesn't quite work for me — would there be flexibility to push it to 4 PM or move to Friday? Happy to make it work either way.\\n\\nBest,\\n[Your Name]"}]}

Email:
[Category: task | Priority: high]
Subject: Report due Friday
From: boss@company.com

Could you please have the Q2 performance report ready by Friday EOD? I need it for the board presentation on Monday.

Output: {"reply_needed":true,"variants":[{"label":"Confirm","tone":"direct","text":"Got it — I'll have the Q2 report ready by Friday EOD.\\n\\n[Your Name]"},{"label":"Need more time","tone":"formal","text":"Hi,\\n\\nI can have the report ready, but Friday EOD is tight given my current workload. Would Monday morning before the presentation work? I want to make sure the data is accurate.\\n\\nThanks,\\n[Your Name]"},{"label":"Clarify scope","tone":"friendly","text":"Hi,\\n\\nHappy to get this done by Friday! Quick question — should I include the regional breakdown and YoY comparisons, or just the top-line metrics? That'll help me prioritize.\\n\\nThanks,\\n[Your Name]"}]}

Email:
[Category: update | Priority: normal]
Subject: Server migration completed successfully
From: devops@company.com

Just a heads-up — the server migration completed successfully last night. No action needed. Logs are attached for reference.

Output: {"reply_needed":true,"variants":[{"label":"Acknowledge","tone":"direct","text":"Thanks for the update — glad the migration went smoothly!\\n\\n[Your Name]"},{"label":"Ask for details","tone":"friendly","text":"Great news! Any noticeable performance improvements so far? Would love to see some before/after metrics if you have them.\\n\\nThanks,\\n[Your Name]"}]}

Email:
[Category: invoice | Priority: normal]
Subject: Invoice #INV-2024-06 for June Services
From: billing@vendor.com

Dear Customer, please find attached your invoice for June 2024. Total amount due: $2,400. Payment is due by July 15.

Output: {"reply_needed":true,"variants":[{"label":"Confirm receipt","tone":"formal","text":"Hi,\\n\\nThank you for sending over invoice #INV-2024-06. I've received it and will process payment by July 15.\\n\\nBest regards,\\n[Your Name]"},{"label":"Query amount","tone":"formal","text":"Hi,\\n\\nThank you for the invoice. The total of $2,400 seems higher than our agreed rate — could you provide a breakdown of the line items so I can verify before processing?\\n\\nThank you,\\n[Your Name]"}]}

Email:
[Category: complaint | Priority: high]
Subject: Service outage - 3 hours and counting
From: client@enterprise.com

This is completely unacceptable. Our entire team has been locked out of your platform for three hours and we have a critical client presentation this afternoon. I expect an immediate resolution and a full explanation of what happened.

Output: {"reply_needed":true,"variants":[{"label":"Acknowledge + ETA","tone":"formal","text":"Hi,\\n\\nI sincerely apologize for the disruption — I fully understand the impact this has with your presentation today. I've escalated this as a P1 incident and our team is actively working on a resolution. I will personally send you a status update within the hour.\\n\\n[Your Name]"},{"label":"Escalate immediately","tone":"formal","text":"Hi,\\n\\nThank you for reaching out. This has been escalated to our senior engineering team as a critical incident. I will follow up within 30 minutes with an estimated resolution time and a full incident timeline.\\n\\nDeepest apologies for the disruption.\\n\\n[Your Name]"},{"label":"Request details to investigate","tone":"formal","text":"Hi,\\n\\nI'm very sorry for the disruption. To help our team investigate faster, could you confirm which specific features are affected and whether you're seeing any error messages? We're treating this as our top priority right now.\\n\\n[Your Name]"}]}

Email:
[Category: update | Priority: low]
Subject: Your order #ORD-8842 has shipped
From: noreply@store.com

Hi, your order #ORD-8842 has shipped and will arrive by Friday July 18. Track your shipment at store.com/track. No reply needed.

Output: {"reply_needed":false,"variants":[]}
"""

_prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=_SYSTEM),
    HumanMessagePromptTemplate.from_template("{email_text}"),
])

_chain: Runnable | None = None


def get_reply_chain() -> Runnable:
    global _chain
    if _chain is None:
        llm = get_groq_llm(temperature=0.15, max_tokens=900)
        _chain = (_prompt | llm | JsonOutputParser()).with_retry(
            stop_after_attempt=3,
        )
    return _chain
