---
name: restaurant-reservation
description: Research restaurants, check availability, and make reservations on behalf of the user. Handles online booking platforms and restaurant websites. Use whenever the user asks to book a table, find a restaurant, or make a dinner reservation.
allowed-tools: Bash(agent-browser:*)
---

# Restaurant Reservation

Research restaurants, verify availability, and book tables via online platforms or restaurant websites. Always confirm with the user before submitting any reservation.

## Step 1: Extract Request Details

From the user's message, identify:

- **Date & time** — required; ask if missing
- **Party size** — required; ask if missing
- **Restaurant name** — if given, skip research and go straight to Step 3
- **Cuisine type** — if not given, check `## Restaurant Preferences` in `/workspace/group/CLAUDE.md`
- **Location** — if not given, check `/workspace/group/CLAUDE.md`; if still missing, ask the user before continuing
- **Special notes** — occasion (birthday, anniversary), dietary restrictions, seating preference
- **High-end signal** — if the request includes words like "Michelin", "gastronomic", "starred", "fine dining", "best", or "tasting menu", enable **high-end mode** (see Step 5)

## Step 2: Research Restaurants (skip if restaurant named)

Search for candidates:

```
"[cuisine] restaurant [location] open [day-of-week] reservation"
```

Also check Google Maps, TripAdvisor, TheFork, OpenTable, and Resy results.

For **high-end mode**: also search Resy, TheFork top lists, and "[location] Michelin star restaurants [year]".

Collect 8–10 candidates with: name, address, cuisine, website/booking URL.

## Step 3: Verify Each Candidate

For each candidate, before presenting it to the user:

1. **Confirm it is open** at the requested date/time — check opening hours on the restaurant website or Google Maps hours
2. **Identify booking method**: OpenTable, Resy, TheFork/LaFourchette, Quandoo, restaurant own website form, or phone-only
3. **Discard** candidates that are closed at the requested time, or flag phone-only ones as last resort

For **high-end mode**: also check that a slot for the requested date/time/party size actually appears on the booking platform — only keep restaurants where availability is confirmed.

Retain 3–5 verified options.

## Step 4: Present Options

Send the user a message listing verified options. For each:

- Name, cuisine, neighbourhood/address
- Open at the requested time ✓
- Booking method (OpenTable / Resy / TheFork / restaurant website / phone-only)
- For high-end: mention Michelin stars or prestige indicators and estimated price per person

Ask the user to pick one or say "none of these".

## Step 5: High-End Restaurant Rules

Apply when the user's request signals a prestigious restaurant, or when research only finds Michelin-starred options:

- State the price range and prestige level **before any action**
- Example: "This is a 2-star Michelin restaurant. Expect €150–200 per person. Shall I proceed?"
- Only present options where a slot genuinely appears available on the platform
- Never fill or submit any booking form without showing a screenshot and receiving **explicit confirmation**

## Step 6: Book the Reservation

Once the user selects a restaurant:

### Platform booking (OpenTable / Resy / TheFork / Quandoo)

```bash
agent-browser open <platform-url-for-restaurant>
agent-browser snapshot -i
# Select date, time, party size
agent-browser click @e_date  # or fill date picker
agent-browser select @e_time "20:00"
agent-browser select @e_party "2"
# Fill guest details (from CLAUDE.md memory or ask user)
agent-browser fill @e_name "First Last"
agent-browser fill @e_phone "+33..."
agent-browser fill @e_email "..."
agent-browser screenshot /tmp/reservation.png
```

Send screenshot and ask for confirmation:

```
mcp__nanoclaw__send_message(text="Ready to confirm — here's the booking form. Type *yes* to submit.", image_path="/tmp/reservation.png")
```

Wait for explicit "yes" before clicking submit. Then:

```bash
agent-browser click @e_submit
agent-browser wait --load networkidle
agent-browser screenshot /tmp/reservation-confirmed.png
```

Send confirmation screenshot to user.

### Restaurant website booking

Same flow: navigate to the booking/reservation page, fill the form, screenshot before submitting, wait for "yes", submit, screenshot the confirmation.

### Phone-only (last resort)

Tell the user: "This restaurant only accepts reservations by phone: [phone number]. I can't book online, but you can call them directly."

Do not attempt any form submission for phone-only restaurants.

## Step 7: Update Group Memory

After a successful booking or search, update `/workspace/group/CLAUDE.md`. Find the `## Restaurant Preferences` section (create it if absent) and update:

```markdown
## Restaurant Preferences
Location: [city/neighbourhood used in this session]
Preferred cuisines: [list, deduplicated]
Past reservations: [restaurant name] — [date] — [party size]
```

Only add a past reservation entry on confirmed bookings.

## Reservation Platforms Reference

| Platform | Coverage | URL |
|---|---|---|
| OpenTable | US, international | opentable.com |
| Resy | Upscale US/UK/FR | resy.com |
| TheFork / LaFourchette | Europe (FR, ES, IT) | thefork.com / lafourchette.com |
| Quandoo | Europe | quandoo.com |
| Restaurant website | Anywhere | varies |

## Guest Details

Look for name, phone, and email in `/workspace/group/CLAUDE.md` under `## Contact Details` or `## Restaurant Preferences`. If not stored, ask the user for the details needed to complete the booking form.

## Example Session

```
User: "Book a table for 2 at an Italian restaurant tomorrow at 8pm"

1. Extract: date=tomorrow 8pm, party=2, cuisine=Italian, location from CLAUDE.md
2. Search: "Italian restaurant [location] open [day] reservation"
3. Verify 3–5 open options with online booking
4. Send list to user, ask them to pick one
5. User picks: "Option 2"
6. Open TheFork page for that restaurant
7. Fill date/time/party/name/phone/email
8. Screenshot → send to user: "Ready to confirm, type yes to submit"
9. User: "yes"
10. Submit → screenshot confirmation → send to user
11. Update CLAUDE.md: Past reservations: [restaurant] — [date] — 2 people
```
