# ForgeFlow AI — User Manual

## What is ForgeFlow AI, in one minute

Imagine you can build websites, but you have no customers. You would have to:

1. Find shops that might need a website.
2. Check each one: is it real, where is it, does it already have a website?
3. Make a sample website to show them.
4. Write a polite email offering it.
5. Read their answer and work out exactly what they want.
6. Write a project plan before you start building.

That is days of work for one customer. **ForgeFlow AI does all six steps for you in a few minutes.** You only make the decisions: which business to approach, and whether the email may be sent.

It works with a team of four AI assistants, each with one job:

| Assistant | Its job |
|---|---|
| **Opportunity Hunter** | Finds businesses, checks them, and researches the one you choose |
| **Builder** | Makes a sample website for that business |
| **Growth & Sales** | Writes the proposal and email, and later reads the customer's reply |
| **Requirements & Delivery** | Turns the reply into a clear project plan (a PRD) |

ForgeFlow never sends an email on its own, and it never makes up facts about a business. Everything it says about a business shows where it found it.

## How to open it

Go to **https://forgeflow-ai.streamlit.app**. Nothing to install. If the page says the app is asleep, click the button to wake it and wait about a minute.

## Step by step

### Step 1 — Say what you can build

On the first screen, choose **"Find potential clients for me"** and fill in:

| Field | Example | Required |
|---|---|---|
| What can you build? | "I build websites and online booking for local shops" | Yes |
| Type of business to target | "Mobile shops" | Yes |
| Country | "Spain" | Yes |
| City | "Pamplona" | No, but gives much better results |
| Language for the demo and email | Spanish, for a shop in Spain | Pre-set |
| Your name, your business name | Used to sign the email | No |

Press **Find potential clients**. It takes up to a minute.

### Step 2 — Choose a business

ForgeFlow shows the businesses it found **and checked**. For each one it searched again to confirm:

- it really is the type of business you asked for,
- it is located in your city (you see the address it found),
- it is not a branch of a big chain (chains already have corporate websites),
- it has its own website, map listing or social page (businesses found only in old directories are left out, because they may have closed),
- whether it already has its own website.

Businesses **without** a website are shown first, because they are the best targets for a website offer. Those that already have one are in a separate, lower-priority section. Businesses that failed a check are listed under **"Left out after checking"** with the reason.

Before you choose, press **Check it on Google Maps** to make sure the shop is really there. Web listings can be out of date.

Press **Select** on the business you want.

> **Tip:** small towns often have only chain stores online. If nothing suitable is found, try the nearest larger town.

> **Already know the business?** On the first screen choose **"I already have a client in mind"** and type its name and any details you know.

### Step 3 — Research (tab "Research & Evidence")

Press **Run research**. The Opportunity Hunter reads the web about this one business and shows:

- **Business facts** and **need signals** (reasons it could use your service).
- A label on each item:
  - **Verified**: written on a real web page; the link is shown.
  - **Likely**: a sensible guess; the reason is explained.
  - **Needs review**: not found; check it yourself.
- A **recommended solution** to offer.

If the business publishes an email address on a public page, ForgeFlow picks it up and fills it in for you.

### Step 4 — Sample website (tab "Demo")

Press **Build demo**. The Builder makes a one-page website for the business: name, services, about, contact. You get:

- a preview inside the app,
- a **shareable link** you can open on any phone or computer,
- a **Download HTML** button.

The page carries a small notice saying it is a concept demo, not the business's official site.

### Step 5 — Proposal and email (tab "Outreach & Approval")

Press **Draft proposal and email**. You get a proposal, the email (with the demo link), a follow-up for later, and a social media post.

Then the **approval** box:

1. Check the **To** address. Type the owner's email if it is empty.
2. Read and edit the subject and email as you like.
3. Tick **"I have read this email and approve sending it"**.
4. Press **Approve and send**.

Only now is the email sent. If email sending is not set up, the app shows a preview and says clearly that nothing was sent. Each mission can send only one email.

### Step 6 — The customer's reply (tab "Customer Reply")

When the owner answers, copy their reply and paste it into the box. Press **Analyse reply**. ForgeFlow shows:

- whether they are interested,
- their questions and concerns,
- the features they asked for,
- what you still need to ask them,
- a suggested polite answer.

### Step 7 — Project plan (tab "Requirements & PRD")

Press **Generate requirements and PRD**. You get the full project plan: features, pages, content needed from the customer, open questions, and acceptance criteria. Press **Download PRD** to keep it. This is the document you build from.

### Agent Activity

The last tab shows every step each assistant took, with the time, and whether it succeeded. Use it to follow what happened.

## Other things to know

- **Saved missions:** every mission is saved. Reopen it from the list in the left sidebar. Press **New mission** to start again. On the free hosting, saved missions are cleared when the app restarts.
- **Demo mode:** the third option on the first screen runs the whole flow on a made-up shop. Use it to practise or to present without internet services.
- **The status panel** in the sidebar shows which services are connected: AI, web research, email.
- **Speed:** the app uses free AI services. If it is busy, a step can take up to a minute; if it fails, wait a minute and press the button again.
- **Your responsibility:** always read the evidence and the email before sending. ForgeFlow labels what it is unsure of, but you make the final call.
