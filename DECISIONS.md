# Decision log

Working notes, kept as we go. Condensed to one page at the end.

## Assumptions

- **"Our store" is the Google Merchandise Store**, and relative dates are anchored to the dataset's last day (2021-01-31). The data covers only 2020-11-01 to 2021-01-31.
- **Revenue = sum of all `purchase` events, without de-duplicating transaction IDs.** About 300 IDs repeat (~$22K in repeated rows) and ~900 purchases have no usable ID. De-duplicating by ID would mean dropping the ID-less purchases, or treating them differently from the rest, so we sum every event and tell the model to mention the caveat when it matters.
- **Channel questions use `traffic_source.*`, the user's first-touch source.** The session-level `source`/`medium` params cover only about a third of events and are missing on `session_start`. The model states the caveat.
- **React counts as a framework**, so "no UI library" means no component or chat-UI kits. Chart and markdown libraries are allowed. *(Asked Mary; no answer yet.)*
- **Gemini is an acceptable LLM**; it's the key we have. *(Asked Mary.)*

## Decisions

- **Gemini over raw HTTP instead of the `google-genai` SDK.** The SDK can run the tool loop itself (automatic function calling), which is the part the assignment asks us to write. Raw requests make that obvious and keep every request and response visible.
- **Stateless backend.** The browser sends a compact history with each request, which works on Vercel's serverless functions and keeps context small. The client can only send text, so it can't forge tool results.
- **SQL safety comes from BigQuery's own checks, not a regex.** A dry run must report statement type `SELECT`; DML against the public data fails with 403 at dry run, and multi-statement input comes back as `SCRIPT` and is rejected. Then a byte cap (3 GB: a full scan is 3.6 GB, the heaviest realistic query ~1.4 GB), a timeout, a row cap, and a service account with only *BigQuery Job User*.
- **Charts reference a `query_id` and carry no data.** The backend attaches the rows, so a chart can't show numbers BigQuery didn't return.
- **Dataset knowledge is a curated notes file in the prompt, not a schema-dump tool.** The traps (below) aren't visible in a schema.
- **Model: `gemini-3.8-flash` (configurable).** Probed three models with a throwaway raw-HTTP loop on real data. All three got Nov vs Dec right ($144,260 vs $160,555) and applied the dataset caveats. Flash was fastest (~4–7s per call vs 5–13s for 3.1 Pro) and cheapest, with equal accuracy on our questions. Pinned a version instead of the `-latest` aliases so behaviour doesn't change under us.
- **The probe confirmed the loop design:** Gemini returns several function calls in one turn (Pro asked for 3 queries at once), and follow-ups work from plain-text history without the hidden `thoughtSignature` data.

## Where we got stuck / surprises

- **Per-product funnel numbers are misleading.** `view_item` events carry ~7 items on average (max 12) and `add_to_cart` ~11, not just the product viewed, and none of them match the page title. Products like "Google F/C Long Sleeve Tee Ash" show 28K views, 9K add-to-carts and 0 purchases. *Resolution:* the notes tell the model that per-product view counts are inflated and conversion rates are only relative, and to say so.
- **`item_id` doesn't join across event types** (only 5 IDs match between views and purchases); `item_name` does (388 of 396). *Resolution:* the notes say to join on `item_name`.
- **Obfuscation placeholders are large.** `<Other>` and `(data deleted)` appear in the source or medium of about a third of first-touch revenue. *Resolution:* keep them in totals, flag them in answers, and exclude them when ranking named items.

## Cut / deprioritized

*(filled in as we go)*

## With 40 more hours

*(filled in at the end)*
