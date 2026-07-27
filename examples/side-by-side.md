# Side by side across three pipelines

The same prompt went through three different pipelines on two frontier
models. Everything below is a captured output. It is unedited except where the
repair trail says exactly what changed. This is a worked specimen, not a
benchmark: one generation per cell cannot establish a model pass rate,
compare providers generally or validate the scanner's thresholds.

**The pipelines.**

- **Bare model.** The default: a prompt goes in, the draft goes out, nothing
  checks it.
- **Instructions only.** The skill's constraint block is prepended to the same
  model prompt. Nothing checks the output.
- **Scan-guided repair.** The same instructions, followed by the scanner, a
  human-directed application of the attached edit rules and a rescan. The
  scanner detects configured forms; an editor or model performs the repair.

**Protocol.** Run 2026-07-23 against `gpt-5.5-2026-04-23` (OpenAI API) and
`claude-sonnet-5` (Anthropic API). Raw API calls, no system prompt, default
sampling, one generation per cell, word counts near 300 so the distribution
metrics had enough text to rate. The constraint block is in the appendix.
The recorded scores came from scanner commit `b3fa642`; later rulesets can
produce different findings.

**The prompt.** "Write a short blog post, roughly 300 words, announcing that
your team just launched an AI-powered analytics dashboard."

## Scoreboard

| Model | Bare model | Instructions only | Scan-guided repair |
|---|---|---|---|
| gpt-5.5 | 38.83 · HEAVY SLOP | 36.21 · HEAVY SLOP | 0.00 · CLEAN |
| claude-sonnet-5 | 49.18 · HEAVY SLOP | 42.86 · HEAVY SLOP | 0.00 · CLEAN |

Densities are weighted configured occurrences per 1,000 words. The labels are
the scanner's density bands, not quality grades or authorship verdicts. In
these two runs, adding instructions changed the drafts without removing every
configured pattern. The scan-guided revisions contained none of the patterns
recognized by that ruleset.

## What changed in these specimens

The instructions-only drafts added a named speaker, concrete mechanisms, a
limitation and a request for feedback. Configured forms remained: Claude used
four em dashes after an instruction that prohibited them, and GPT exceeded the
declared one-triad budget five times. Those are observations about these
outputs. Without a separate post-draft check, the pipeline has no mechanism to
surface the violations.

One more honest note: the prompt supplied no real product facts. The outputs
invented `Lena Ortiz at Brightlane` and `Priya at Fernwood`; neither exists.
The constraint requested a named actor, and the models supplied fictional
ones. Constraints shape prose. They do not supply evidence.

---

## GPT-5.5

### Bare model

```text
## Introducing Our New AI-Powered Analytics Dashboard

We’re excited to announce the launch of our new AI-powered analytics dashboard, built to help teams turn data into decisions faster, smarter, and with less manual effort.

Modern organizations have no shortage of data—but finding the right insight at the right moment can still be a challenge. Our new dashboard is designed to change that. By combining intuitive data visualization with AI-driven analysis, it helps users quickly understand performance, spot trends, and uncover opportunities that might otherwise go unnoticed.

With the dashboard, teams can monitor key metrics in real time, explore interactive charts, and receive intelligent summaries that highlight what matters most. Instead of digging through spreadsheets or manually comparing reports, users can ask better questions and get clearer answers—whether they’re tracking growth, customer behavior, operational efficiency, or campaign performance.

One of the most powerful features is automated insight detection. The dashboard can identify unusual changes, emerging patterns, and important correlations across your data. It also provides plain-language explanations, making analytics more accessible to everyone—not just data specialists.

We built this tool with flexibility in mind. Whether you’re an executive looking for a high-level overview, a manager monitoring team performance, or an analyst diving deeper into the numbers, the dashboard adapts to your needs. Custom views, configurable metrics, and seamless integrations make it easy to bring your most important data into one place.

This launch is an important step in our mission to make data more actionable and accessible. We believe AI should not replace human judgment—it should enhance it by surfacing insights, reducing busywork, and helping teams move with confidence.

The AI-powered analytics dashboard is available now. We can’t wait to see how our customers use it to make faster decisions, uncover new opportunities, and drive meaningful results.

Stay tuned for more updates as we continue improving the experience and adding new AI capabilities.
```

Scanner: HEAVY SLOP, 38.83. Em-dash density 12.94 per 1k, triad density
29.13 per 1k (nine rule-of-three lists in 309 words), "seamless", an
unanchored "We built", sentence cadence nearly uniform (cv 0.382), AI
style-marker density 19.42.

### Instructions only

The same model, with the constraint block prepended and nothing checking
the result.

```text
I’m Lena Ortiz, product lead on the analytics team at Brightlane.

Today our team launched Pulse, an AI-powered analytics dashboard for Brightlane customers.

Pulse lets a customer ask a question in plain language, get a chart back, inspect the SQL behind it, and save the result to a shared dashboard. The first version supports revenue, retention, product usage, and support data that already lives in a customer’s Brightlane workspace.

A typical question might be:

“Show weekly expansion revenue from accounts that opened more than five support tickets last month.”

Pulse turns that into a query, shows the chart, and gives a short note on how it interpreted the request. If the question is too vague, it asks for the missing field or time range instead of guessing. If a user cannot access a table, Pulse cannot query that table for them.

During private beta, 18 customer teams used Pulse for pipeline reviews, churn checks, and weekly product reporting. One customer success lead told us she stopped waiting for a monthly analyst export because she could check account movement during her Tuesday account review. That is the kind of change we built for: a person with a business question can get closer to the data without opening a ticket first.

The Brightlane analytics team built Pulse with our data engineering team and design partners at five customer companies. We spent a lot of time on boring parts that matter in daily use: permission checks, saved definitions, query previews, and chart edits after the AI returns an answer.

This launch is version one. Next, our team is working on scheduled narrative summaries and better support for custom metrics.

If you use Brightlane, Pulse is live in your workspace today under the Analytics tab. I’d be glad to hear what you ask it first and where it falls short.
```

Scanner: HEAVY SLOP, 36.21. Named speaker, mechanism, honest limits: the
substance is transformed. The rhythm is not: triad density 17.24 (the
budget was one), move-line ratio 12.5%, a benefit-verb collision, an
unanchored "we built", cadence still uniform at 0.354.

### The skill's loop

The same instructions, then the gate. The scanner flagged the draft above;
the repair trail was: four triads broken by restructuring or losing the
serial-comma rhythm; "we built for" renamed to the identifiable team; the
benefit-verb collision reworded; two sentences varied for cadence. Rescan:

```text
I'm Lena Ortiz, product lead on the analytics team at Brightlane.

Today our team launched Pulse, an AI-powered analytics dashboard for Brightlane customers.

Pulse lets a customer ask a question in plain language and get a chart back, then inspect the SQL behind it and save the result to a shared dashboard. The first version covers revenue, retention, product usage and support data that already lives in a customer's Brightlane workspace.

A typical question might be:

"Show weekly expansion revenue from accounts that opened more than five support tickets last month."

Pulse turns that into a query, shows the chart, and gives a short note on how it interpreted the request. Too vague? It asks for the missing field or time range instead of guessing. If a user cannot access a table, Pulse cannot query that table for them.

During private beta, 18 customer teams used Pulse for pipeline reviews, churn checks and weekly product reporting. One customer success lead told us she stopped waiting for a monthly analyst export because she could check account movement during her Tuesday account review. That is the change the team was after: a person with a business question can get closer to the data without opening a ticket first.

The Brightlane analytics team built Pulse with our data engineering team and design partners at five customer companies. A lot of the work went into boring parts that matter in daily use: permission checks, saved definitions, query previews and chart edits after the AI returns an answer.

This launch is version one. Scheduled narrative summaries and better custom-metric support come next.

If you use Brightlane, Pulse is live in your workspace today under the Analytics tab. I'd be glad to hear what you ask it first and where it falls short.
```

Scanner: CLEAN, 0.00. Zero high, zero medium, cadence 0.467.

---

## Claude Sonnet 5

### Bare model

```text
# Introducing Our New AI-Powered Analytics Dashboard

We're thrilled to announce the launch of our newest product: an AI-powered analytics dashboard designed to transform how you understand and act on your data.

## Why We Built This

Over the past several months, we listened closely to feedback from users who told us the same thing again and again: data is everywhere, but insight is hard to find. Traditional dashboards show you *what* happened, but rarely tell you *why* it happened or *what to do next*. We set out to close that gap.

## What's New

Our AI-powered dashboard goes beyond static charts and graphs. Here's what you can expect:

- **Smart Insights**: The dashboard automatically surfaces trends, anomalies, and patterns in your data—no need to dig through endless reports.
- **Natural Language Queries**: Simply ask a question like "Why did sales drop last week?" and get a clear, actionable answer.
- **Predictive Forecasting**: Leverage machine learning models that help you anticipate future trends based on historical data.
- **Customizable Views**: Tailor your dashboard to highlight the metrics that matter most to your team, whether that's revenue, customer engagement, or operational efficiency.
- **Real-Time Alerts**: Get notified the moment something significant happens, so you can respond quickly instead of reactively.

## Built With You in Mind

We designed this dashboard to be powerful yet intuitive. You don't need a data science background to use it—our goal was to make sophisticated analytics accessible to everyone on your team, from marketing to operations to leadership.

## What's Next

This launch is just the beginning. We're already working on new integrations, deeper customization options, and expanded AI capabilities based on your feedback. We'd love to hear what you think!

## Try It Today

The new dashboard is available now for all users. Log in to your account to explore it, or reach out to our support team if you have any questions.

Thank you for being part of this journey with us. We can't wait to see what insights you uncover!
```

Scanner: HEAVY SLOP, 49.18, four high-severity signals: a cataphoric
"Here's what you can expect", em-dash density 6.56, triad density 9.84,
and a 20% move-line ratio, plus unanchored "We Built" / "We designed".

### Instructions only

The same model, with the constraint block prepended and nothing checking
the result.

```text
We shipped the new analytics dashboard this morning. I'm Priya, and I lead the data team at Fernwood — three of us have been building this since February.

Here's what changed: the old dashboard showed you numbers. This one tells you what's driving them. If checkout conversion drops on a Tuesday, it flags the specific step where users dropped off and shows you the session recordings from that hour. Sam built the anomaly detection, Theo wired up the natural language query box, and I spent most of March arguing with our data pipeline until it stopped losing timestamps.

You can type a question like "why did signups dip last week" and get an answer that points to a specific change — a pricing page edit, a slow API response, a marketing campaign that ended. It's not a chatbot bolted onto old charts. The underlying model was trained on our own event data, not a general assistant guessing at your metrics.

A few of our beta users asked if this replaces their weekly reporting meetings. It doesn't. What it does is cut the time between "something looks off" and "here's why" from a few days of Slack threads to a few minutes.

One thing I'll flag honestly: the model still struggles with multi-week trend comparisons, especially around holidays when the baseline shifts. We're working on it, but if you're comparing this December to last December, double-check the numbers by hand for now.

The dashboard is live for all customers on the Growth and Enterprise plans starting today. If you're on Starter, reach out and we'll get you early access.

Try asking it something specific. Not "how are we doing" but "why did our trial-to-paid rate change last month." That's where it earns its keep.

Questions, bugs, complaints — send them to me directly. I read everything.

— Priya
```

Scanner: HEAVY SLOP, 42.86. Again the substance moved: named team,
mechanism, an honest limitation. Again the tics survived: a cataphoric
"Here's what changed", the stock idiom "earns its keep", and em-dash
density of 14.29 directly after an instruction banning em dashes.

### The skill's loop

The same instructions, then the gate. The repair trail on the draft above:
the cataphoric opener deleted and the content promoted; the stock idiom
replaced with the literal statement; all four em dashes converted to commas
or colons; the opening "We shipped" given its identifiable actor. Rescan:

```text
Fernwood shipped the new analytics dashboard this morning. I'm Priya, and I lead the data team: three of us have been building this since February.

The old dashboard showed you numbers. This one tells you what's driving them. If checkout conversion drops on a Tuesday, it flags the specific step where users dropped off and shows you the session recordings from that hour. Sam built the anomaly detection, Theo wired up the natural language query box, and I spent most of March arguing with our data pipeline until it stopped losing timestamps.

You can type a question like "why did signups dip last week" and get an answer that points to a specific change: a pricing page edit, a slow API response, a marketing campaign that ended. It's not a chatbot bolted onto old charts. The underlying model was trained on our own event data, not a general assistant guessing at your metrics.

A few of our beta users asked if this replaces their weekly reporting meetings. It doesn't. What it does is cut the time between "something looks off" and "here's why" from a few days of Slack threads to a few minutes.

One thing I'll flag honestly: the model still struggles with multi-week trend comparisons, especially around holidays when the baseline shifts. We're working on it, but if you're comparing this December to last December, double-check the numbers by hand for now.

The dashboard is live for all customers on the Growth and Enterprise plans starting today. If you're on Starter, reach out and we'll get you early access.

Try asking it something specific. Not "how are we doing" but "why did our trial-to-paid rate change last month." That's the kind of question it answers well.

Questions, bugs, complaints: send them to me directly. I read everything.

Priya
```

Scanner: CLEAN, 0.00. Zero findings of any severity.

---

## Reproduce it

The constraint block below is the exact text prepended in the
instructions-only and scan-guided pipelines. Swap in any model you have API
access to; the scanner side needs no key:

```bash
python3 scripts/slop_scan.py your_output.txt --fail-on never
```

That command reports the current ruleset. It does not reproduce the historical
model generation, which used default sampling, or guarantee the 2026-07-23
score under a later catalog.

<details>
<summary>The constraint block (SKILL.md build mode, distilled)</summary>

```text
Constraints for this piece. Hold every one while writing:

- Stance: one real person plainly telling their network what they built. Not a pitch voice.
- Write as a named actor. Use "we" only for a team the reader can identify from the post.
- Never evaluate a point before making it. Banned shapes: "here's why this matters", "the key insight is", "what matters most is".
- No denial of a claim nobody made. Use "not X, but Y" only if you can name who asserted X.
- No claims about unmeasured populations: "most teams", "everyone knows", "nobody talks about".
- Rebut only positions you can quote. Answer any question you raise, in the post.
- Never order the reader to re-read: "read that again", "let that sink in".
- Use only idioms you have heard a real person say. When unsure, say it plainly.
- No "which means" or "so" unless the reasoning is on the page.
- No "two kinds of" dichotomies. No count rhythms like "three tools, one goal".
- No intensity claims doing evidence's job: "the real problem is", "here's the thing".
- No deal or contract framing with the reader. No "research shows" without a named source.
- At most one hedge, attached to its reason.
- No sentence-initial Moreover, Furthermore, Additionally, Overall, Ultimately.
- Do not announce what the post will do. Do it.
- No breadth sweeps like "everything from X to Y". Name the specific cases.
- No "both benefits and challenges" balancing without weighing a side.
- No benefit-verb chains (enhance, empower, streamline, foster, unlock). State the mechanism: who does what differently now.
- Banned words and phrases: delve, tapestry, game-changer, seamless, supercharge, elevate, unlock potential, deep dive, "In today's fast-paced world", "I hope this helps", "In conclusion".
- No em dashes. Vary sentence lengths. Use a rule-of-three list once at most.

The task:
```

</details>
