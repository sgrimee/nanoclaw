# /clear Command Examples

## Basic Usage

### Example 1: Clear and Start Fresh

**Conversation:**
```
User: @Andy what's 2+2?
Andy: 2+2 = 4

User: @Andy tell me about that number
Andy: 4 is an even number, the first non-prime composite number...

User: @Andy /clear
Andy: ✅ Context cleared! Starting fresh conversation. All files and memory (CLAUDE.md, documents) are still accessible.

User: @Andy tell me about that number
Andy: I don't have context about which number you're referring to. Could you specify which number?
```

**What happened:** After `/clear`, the assistant has no memory of the "4" from earlier conversation.

---

### Example 2: Clear with Immediate Prompt

**Conversation:**
```
User: @Andy we were talking about Paris yesterday, remember?
Andy: Yes, we discussed Paris as a travel destination and...

User: @Andy /clear What's the capital of Germany?
Andy: The capital of Germany is Berlin.

User: @Andy what were we just talking about?
Andy: We were discussing Germany's capital, Berlin.
```

**What happened:** The `/clear` removed Paris context, then immediately processed the Germany question.

---

### Example 3: Preserving Files and Memory

**Setup:**
```bash
# Create a test file
echo "Project deadline: March 1st" > /workspace/group/project-notes.md
```

**Conversation:**
```
User: @Andy read project-notes.md
Andy: Your project deadline is March 1st.

User: @Andy when's my deadline?
Andy: March 1st, based on the project notes.

User: @Andy /clear

User: @Andy read project-notes.md
Andy: Your project deadline is March 1st.

User: @Andy when's my deadline?
Andy: I don't have context about a deadline. Could you clarify which deadline you're asking about?
```

**What happened:** The file remains accessible, but the conversation context about "your deadline" is lost.

---

### Example 4: Fixing Context Confusion

**Problem Scenario:**
```
User: @Andy schedule a meeting for tomorrow at 2pm
Andy: Meeting scheduled for Feb 22 at 2pm.

User: @Andy remind me about the presentation
Andy: Sure, I'll remind you about the presentation scheduled for tomorrow at 2pm.

User: @Andy what time is my dentist appointment?
Andy: Based on our earlier conversation, your appointment is at 2pm tomorrow.
```

**Wrong!** The assistant confused the meeting with a dentist appointment.

**Solution:**
```
User: @Andy /clear what time is my dentist appointment?
Andy: I don't have information about a dentist appointment. Could you provide more details or check your calendar?
```

**Much better!** Now the assistant doesn't make false assumptions.

---

### Example 5: Daily Workflow

**Morning:**
```
User: @Andy summarize my calendar for today
Andy: [provides morning summary]
```

**Evening (starting fresh):**
```
User: @Andy /clear summarize my calendar for tomorrow
Andy: [provides tomorrow's summary without referencing morning conversation]
```

**Benefit:** Each day starts with clean context, avoiding confusion between different days.

---

### Example 6: Task Switching

**Working on Email:**
```
User: @Andy help me draft an email to the client
Andy: [drafts email]

User: @Andy make it more formal
Andy: [revises email]
```

**Switching to Calendar:**
```
User: @Andy /clear what's on my calendar next week?
Andy: [provides calendar info without mentioning email]
```

**Benefit:** Clean separation between different tasks.

---

## Advanced Usage

### Example 7: Combined with File Operations

```
User: @Andy /clear Read the meeting notes from last week and create an action items list
```

The `/clear` ensures no old context interferes, then immediately processes the new task.

### Example 8: Multiple Clears in Conversation

```
User: @Andy help with task A
Andy: [helps with A]

User: @Andy /clear help with task B
Andy: [helps with B, no reference to A]

User: @Andy /clear help with task C
Andy: [helps with C, no reference to A or B]
```

You can `/clear` as often as needed throughout the day.

---

## When to Use /clear

✅ **Use /clear when:**
- Starting a completely new topic/task
- Context has become confusing or mixed up
- You want a "fresh start" without old conversation baggage
- Testing the assistant's response without historical context
- Separating work sessions (morning vs afternoon)
- Assistant is referencing old, irrelevant information

❌ **Don't use /clear when:**
- You want to reference previous conversation
- Building on earlier work (like multi-step tasks)
- The historical context is still relevant
- You're debugging something that requires full context

---

## Tips

1. **Clear before new topics:** Start major topic changes with `/clear` to avoid confusion
2. **Combine with prompt:** Save a message by using `/clear <new question>`
3. **Files persist:** Remember that CLAUDE.md, documents, and workspace files remain accessible
4. **Use liberally:** There's no penalty for clearing too often
5. **Daily resets:** Consider `/clear` at the start of each day for clean slate

---

## Comparison: With vs Without /clear

### Without /clear (Context Confusion):
```
User: Book a flight to NYC
Assistant: Flight to NYC booked.

User: What's the weather like there?
Assistant: The weather in NYC is... [refers to NYC from earlier]

User: Actually I meant Paris
Assistant: Oh, let me check Paris weather... but you mentioned NYC earlier, should I cancel that booking?
```

### With /clear (Clean Context):
```
User: Book a flight to NYC
Assistant: Flight to NYC booked.

User: /clear What's the weather like in Paris?
Assistant: The weather in Paris is... [no confusion about NYC]
```

Much cleaner and less error-prone!
