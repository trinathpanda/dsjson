# DSJSON — LPMI Speaker Script
 
 
> How to use this: Read the **[ADVANCE SLIDE]** cues to know when to click. Everything in *italics* is a delivery note, not something to read aloud. Pace yourself — pauses are fine.
 
---
 
## SLIDE 1 — Title: DSJSON
*(Open here, slide already up)*
 
Good morning, everyone — thanks for making the time.
 
I'm Trinath. Today I want to walk you through something I've been building called **DSJSON**. In one line: it's a small tool that helps us start working with **Dataset-JSON** without touching anything we currently rely on for submissions.
 
Let me set the scene first.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 2 — Current State: XPT is King Today
 
Right now, XPT runs the show. All of us here know that — our whole world of development, QC, and delivery is built around SAS and XPT. It's proven, everyone knows how to validate it, and honestly, it's not going anywhere soon.
 
But there's a quieter shift happening. CDISC has introduced **Dataset-JSON** as a modern exchange standard. So the real question isn't *"how do we replace XPT tomorrow?"* — it's *"how do we start getting comfortable with what's coming, today?"*
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 3 — Why Dataset-JSON Matters
 
So why is everyone talking about Dataset-JSON? Let me keep this simple.
 
*(Explain JSON in one line — point at the "Readable" tile)*
**JSON is just a clean, text-based way of storing data with clear labels — it's the exact same format almost every app on your phone uses behind the scenes to send and receive information.** So instead of a binary file we can't open, it's something both a human and a machine can actually read.
 
That gives us four things: it's **readable**, it's **machine-friendly**, it can carry **Define-XML metadata** with it, and it's **future-ready**.
 
*(One line on machine-friendly / API — point at "Machine-friendly" tile)*
And when I say machine-friendly, I mean it fits how modern systems talk to each other — through **APIs. An API is simply the way two applications exchange data automatically, like how your weather app pulls today's forecast without anyone emailing a file around.** That's the direction our industry is slowly moving.
 
So Dataset-JSON isn't *just* another file format — it's a step toward more automated, connected data exchange.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 4 — The Adoption Challenge
 
Here's the catch, though. Wanting Dataset-JSON and *using* it in production are two very different things.
 
Our submission pipelines are built on XPT. You can't just rip that out — that's real risk. What teams actually need first is a simple way to **generate** Dataset-JSON, **look at it**, and **trust it**, before anyone commits to it.
 
So the first real need isn't full adoption — it's a safe place to experiment.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 5 — Problem Statement
*(This is your strongest slide — slow down here)*
 
I'll be honest with you about something. When I started this, I thought I was solving a *future* problem — something we'd care about in a few years.
 
But the more I worked on it, the more I realized the problem is already here. Organizations are evaluating Dataset-JSON adoption right now. What they lack is a practical and low-risk way to generate and review Dataset-JSON alongside existing XPT workflow **now**.
 
*(Pause — let it land)*
 
So the problem statement became simple:
 
> **Organizations need a practical, low-risk way to generate and evaluate Dataset-JSON alongside their existing XPT workflows.**
 
That reframes DSJSON — it's not a conversion utility, it's an **adoption enabler**.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 6 — Two Phases of Adoption
 
The way I see it, this happens in two phases.
 
**Phase 1 is piloting.** You keep XPT as your real submission format, but *alongside* it, you generate Dataset-JSON — validate it, compare it, build confidence. Nothing in your live workflow changes.
 
**Phase 2 is full adoption** — someday, generating Dataset-JSON straight from R or Python pipelines, with no XPT dependency at all.
 
Almost everyone today is in Phase 1. And that's exactly where DSJSON is designed to help.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 7 — Where DSJSON Fits Today
 
And the nice part is — it uses what we already have. No new inputs to create.
 
You bring your **XPT** and your **Define-XML** — things every study already produces. DSJSON takes those and gives you back three things: the **Dataset-JSON**, a **validation report**, and **execution logs**.
 
So you can start evaluating Dataset-JSON without changing a single thing in your current submission process.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 8 — How It Works
 
Under the hood it's intentionally boring — and that's a good thing.
 
**Define-XML gives the structure. XPT gives the data.** The DSJSON engine merges the two, validates the result against the Dataset-JSON schema, and produces the output.
 
The key point: it's **metadata-driven**. Nobody is hand-writing JSON. The metadata decides the structure, the data fills it in, and the tool does the rest.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 9 — Demo
 
Alright — let me actually show you.
 
Quick thing before I start: this runs **completely offline** as a desktop app — nothing leaves your machine, which matters for the data we work with. And that desktop window is really just a friendlier face on the same engine — for anyone who'd rather not touch a command line.
 
*(Run demo — keep it under 3 minutes: point to XPT input, Define-XML input, output location, then show the generated JSON + validation report)*
 
**[ADVANCE SLIDE — after demo]**
 
---
 
## SLIDE 10 — Roadmap
 
So where does this go next? Three stages.
 
**Stage 1** is what you just saw — the desktop app, for piloting.
**Stage 2** is turning the engine into a **reusable Python library**, so developers can plug Dataset-JSON generation straight into their own workflows.
**Stage 3** is **server-based automation** — building it into our enterprise data pipelines so it just runs at scale.
 
Basically: from *helping people try it* → to *helping developers use it* → to *running it automatically*.
 
Stage 3 is all my about my imagination, not sure if it is possible. But cant tell you utill I try.
 
**[ADVANCE SLIDE]**
 
---
 
## SLIDE 11 — Thank You & Call to Action
 
So to wrap up: XPT is still king today, Dataset-JSON is clearly where things are heading, and DSJSON is a small bridge to help us get there without disrupting anything.
 
Now — one honest ask before I take questions.
 
This tool is still pretty naive at this stage. I've built the foundation, but to make it genuinely solid I need more guidance and more eyes on it. So whatever your function is — programming, standards, validation, submissions — please come talk to me. I'd genuinely welcome your feedback, whether it's positive or "Trinath, this part doesn't work" — that's exactly the input that'll make this real.
 
Thank you — I'm happy to take any questions.